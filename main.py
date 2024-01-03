import datetime
import io
import os
import re
import fitz
import openai
import requests
import tenacity
import tiktoken
from bs4 import BeautifulSoup
from PIL import Image
from collections import namedtuple
import time

ArxivParams = namedtuple(
    "ArxivParams",
    [
        "query",
        "query_list",
        "key_word",
        "page_num",
        "max_results",
        "days",
        "sort",
        "save_image",
        "file_format",
        "language",

    ],
)


class Paper:
    # ! directly copy from chatpaper repo
    def __init__(self, path, title='', url='', abs='', authers=[], date = '', tag =''):
        self.url = url  # 文章链接
        self.path = path  # pdf path
        self.section_names = [] 
        self.section_texts = {}
        self.abs = abs
        self.date = date
        self.title_page = 0
        self.title = title
        self.tag = tag
        try:
            self.pdf = fitz.open(self.path)
        except:
            print("open pdf error")
            return None
        self.parse_pdf()
        self.authers = authers
        self.roman_num = ["I", "II", 'III', "IV", "V", "VI", "VII", "VIII", "IIX", "IX", "X"]
        self.digit_num = [str(d + 1) for d in range(10)]
        self.first_image = ''

    def parse_pdf(self):
        self.pdf = fitz.open(self.path) 
        self.text_list = [page.get_text() for page in self.pdf]
        self.all_text = ' '.join(self.text_list)
        self.section_page_dict = self._get_all_page_index()
        print("section_page_dict", self.section_page_dict)
        self.section_text_dict = self._get_all_page()
        self.section_text_dict.update({"title": self.title})
        self.section_text_dict.update({"paper_info": self.get_paper_info()})
        self.pdf.close()

    def get_paper_info(self):
        try:
            first_page_text = self.pdf[self.title_page].get_text()
            if "Abstract" in self.section_text_dict.keys():
                abstract_text = self.section_text_dict['Abstract']
            else:
                abstract_text = self.abs
            first_page_text = first_page_text.replace(abstract_text, "")
            return first_page_text
        except:
            return ""

    def get_image_path(self, image_path=''):
        """
        将PDF中的第一张图保存到image.png里面，存到本地目录，返回文件名称，供gitee读取
        :param filename: 图片所在路径，"C:\\Users\\Administrator\\Desktop\\nwd.pdf"
        :param image_path: 图片提取后的保存路径
        :return:
        """
        # open file
        max_size = 0
        image_list = []
        with fitz.Document(self.path) as my_pdf_file:
            # 遍历所有页面
            for page_number in range(1, len(my_pdf_file) + 1):
                # 查看独立页面
                page = my_pdf_file[page_number - 1]
                # 查看当前页所有图片
                images = page.get_images()
                # 遍历当前页面所有图片
                for image_number, image in enumerate(page.get_images(), start=1):
                    # 访问图片xref
                    xref_value = image[0]
                    # 提取图片信息
                    base_image = my_pdf_file.extract_image(xref_value)
                    # 访问图片
                    image_bytes = base_image["image"]
                    # 获取图片扩展名
                    ext = base_image["ext"]
                    # 加载图片
                    image = Image.open(io.BytesIO(image_bytes))
                    image_size = image.size[0] * image.size[1]
                    if image_size > max_size:
                        max_size = image_size
                    image_list.append(image)
        for image in image_list:
            image_size = image.size[0] * image.size[1]
            if image_size == max_size:
                image_name = f"image.{ext}"
                im_path = os.path.join(image_path, image_name)
                print("im_path:", im_path)

                max_pix = 480
                origin_min_pix = min(image.size[0], image.size[1])

                if image.size[0] > image.size[1]:
                    min_pix = int(image.size[1] * (max_pix / image.size[0]))
                    newsize = (max_pix, min_pix)
                else:
                    min_pix = int(image.size[0] * (max_pix / image.size[1]))
                    newsize = (min_pix, max_pix)
                image = image.resize(newsize)

                image.save(open(im_path, "wb"))
                return im_path, ext
        return None, None

    # 定义一个函数，根据字体的大小，识别每个章节名称，并返回一个列表
    def get_chapter_names(self, ):
        # # 打开一个pdf文件
        doc = fitz.open(self.path)  # pdf文档
        text_list = [page.get_text() for page in doc]
        all_text = ''
        for text in text_list:
            all_text += text
        # # 创建一个空列表，用于存储章节名称
        chapter_names = []
        for line in all_text.split('\n'):
            line_list = line.split(' ')
            if '.' in line:
                point_split_list = line.split('.')
                space_split_list = line.split(' ')
                if 1 < len(space_split_list) < 5:
                    if 1 < len(point_split_list) < 5 and (
                            point_split_list[0] in self.roman_num or point_split_list[0] in self.digit_num):
                        print("line:", line)
                        chapter_names.append(line)
                    # 这段代码可能会有新的bug，本意是为了消除"Introduction"的问题的！
                    elif 1 < len(point_split_list) < 5:
                        print("line:", line)
                        chapter_names.append(line)

        return chapter_names

    def get_title(self):
        doc = self.pdf  # 打开pdf文件
        max_font_size = 0  # 初始化最大字体大小为0
        max_string = ""  # 初始化最大字体大小对应的字符串为空
        max_font_sizes = [0]
        for page_index, page in enumerate(doc):  # 遍历每一页
            text = page.get_text("dict")  # 获取页面上的文本信息
            blocks = text["blocks"]  # 获取文本块列表
            for block in blocks:  # 遍历每个文本块
                if block["type"] == 0 and len(block['lines']):  # 如果是文字类型
                    if len(block["lines"][0]["spans"]):
                        font_size = block["lines"][0]["spans"][0]["size"]  # 获取第一行第一段文字的字体大小
                        max_font_sizes.append(font_size)
                        if font_size > max_font_size:  # 如果字体大小大于当前最大值
                            max_font_size = font_size  # 更新最大值
                            max_string = block["lines"][0]["spans"][0]["text"]  # 更新最大值对应的字符串
        max_font_sizes.sort()
        print("max_font_sizes", max_font_sizes[-10:])
        cur_title = ''
        for page_index, page in enumerate(doc):  # 遍历每一页
            text = page.get_text("dict")  # 获取页面上的文本信息
            blocks = text["blocks"]  # 获取文本块列表
            for block in blocks:  # 遍历每个文本块
                if block["type"] == 0 and len(block['lines']):  # 如果是文字类型
                    if len(block["lines"][0]["spans"]):
                        cur_string = block["lines"][0]["spans"][0]["text"]  # 更新最大值对应的字符串
                        font_flags = block["lines"][0]["spans"][0]["flags"]  # 获取第一行第一段文字的字体特征
                        font_size = block["lines"][0]["spans"][0]["size"]  # 获取第一行第一段文字的字体大小
                        # print(font_size)
                        if abs(font_size - max_font_sizes[-1]) < 0.3 or abs(font_size - max_font_sizes[-2]) < 0.3:
                            # print("The string is bold.", max_string, "font_size:", font_size, "font_flags:", font_flags)
                            if len(cur_string) > 4 and "arXiv" not in cur_string:
                                # print("The string is bold.", max_string, "font_size:", font_size, "font_flags:", font_flags)
                                if cur_title == '':
                                    cur_title += cur_string
                                else:
                                    cur_title += ' ' + cur_string
                            self.title_page = page_index
                            # break
        title = cur_title.replace('\n', ' ')
        return title

    def _get_all_page_index(self):
        # 定义需要寻找的章节名称列表
        section_list = ["Abstract",
                        'Introduction', 'Related Work', 'Background',

                        "Introduction and Motivation", "Computation Function", " Routing Function",

                        "Preliminary", "Problem Formulation",
                        'Methods', 'Methodology', "Method", 'Approach', 'Approaches',
                        # exp
                        "Materials and Methods", "Experiment Settings",
                        'Experiment', "Experimental Results", "Evaluation", "Experiments",
                        "Results", 'Findings', 'Data Analysis',
                        "Discussion", "Results and Discussion", "Conclusion",
                        'References']
        # 初始化一个字典来存储找到的章节和它们在文档中出现的页码
        section_page_dict = {}
        # 遍历每一页文档
        for page_index, page in enumerate(self.pdf):
            # 获取当前页面的文本内容
            cur_text = page.get_text()
            # 遍历需要寻找的章节名称列表
            for section_name in section_list:
                # 将章节名称转换成大写形式
                section_name_upper = section_name.upper()
                # 如果当前页面包含"Abstract"这个关键词
                if "Abstract" == section_name and section_name in cur_text:
                    # 将"Abstract"和它所在的页码加入字典中
                    section_page_dict[section_name] = page_index
                # 如果当前页面包含章节名称，则将章节名称和它所在的页码加入字典中
                else:
                    if section_name + '\n' in cur_text:
                        section_page_dict[section_name] = page_index
                    elif section_name_upper + '\n' in cur_text:
                        section_page_dict[section_name] = page_index
        # 返回所有找到的章节名称及它们在文档中出现的页码
        return section_page_dict

    def _get_all_page(self):
        """
        获取PDF文件中每个页面的文本信息，并将文本信息按照章节组织成字典返回。

        Returns:
            section_dict (dict): 每个章节的文本信息字典，key为章节名，value为章节文本。
        """
        text = ''
        text_list = []
        section_dict = {}

        # 再处理其他章节：
        text_list = [page.get_text() for page in self.pdf]
        for sec_index, sec_name in enumerate(self.section_page_dict):
            print(sec_index, sec_name, self.section_page_dict[sec_name])
            if sec_index <= 0 and self.abs:
                continue
            else:
                # 直接考虑后面的内容：
                start_page = self.section_page_dict[sec_name]
                if sec_index < len(list(self.section_page_dict.keys())) - 1:
                    end_page = self.section_page_dict[list(self.section_page_dict.keys())[sec_index + 1]]
                else:
                    end_page = len(text_list)
                print("start_page, end_page:", start_page, end_page)
                cur_sec_text = ''
                if end_page - start_page == 0:
                    if sec_index < len(list(self.section_page_dict.keys())) - 1:
                        next_sec = list(self.section_page_dict.keys())[sec_index + 1]
                        if text_list[start_page].find(sec_name) == -1:
                            start_i = text_list[start_page].find(sec_name.upper())
                        else:
                            start_i = text_list[start_page].find(sec_name)
                        if text_list[start_page].find(next_sec) == -1:
                            end_i = text_list[start_page].find(next_sec.upper())
                        else:
                            end_i = text_list[start_page].find(next_sec)
                        cur_sec_text += text_list[start_page][start_i:end_i]
                else:
                    for page_i in range(start_page, end_page):
                        #                         print("page_i:", page_i)
                        if page_i == start_page:
                            if text_list[start_page].find(sec_name) == -1:
                                start_i = text_list[start_page].find(sec_name.upper())
                            else:
                                start_i = text_list[start_page].find(sec_name)
                            cur_sec_text += text_list[page_i][start_i:]
                        elif page_i < end_page:
                            cur_sec_text += text_list[page_i]
                        elif page_i == end_page:
                            if sec_index < len(list(self.section_page_dict.keys())) - 1:
                                next_sec = list(self.section_page_dict.keys())[sec_index + 1]
                                if text_list[start_page].find(next_sec) == -1:
                                    end_i = text_list[start_page].find(next_sec.upper())
                                else:
                                    end_i = text_list[start_page].find(next_sec)
                                cur_sec_text += text_list[page_i][:end_i]
                section_dict[sec_name] = cur_sec_text.replace('-\n', '').replace('\n', ' ')
        return section_dict


class Reader:
    def __init__(self, key_word, query,
                 root_path='./',
                 gitee_key='',
                 sort=None,
                 user_name='defualt', args=None):
        self.user_name = user_name  
        self.key_word = key_word 
        self.query = query 
        self.sort = sort
        self.args = args
        if args.language == 'en':
            self.language = 'English'
        elif args.language == 'zh':
            self.language = 'Chinese'
        else:
            self.language = 'Chinese'
        self.root_path = args.root_path
        
        #get chatGPT API, gitee API
        self.use_other_api = args.use_other_api
        self.chat_api_list = args.chat_api_list
        self.cur_api = 0
        self.gitee_key = args.gitee_key

        self.file_format = args.file_format
        self.max_token_num = 2000
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


    def get_url(self, keyword, page):
        '''
        Return URL based on keyword and page number
        '''
        base_url = "https://arxiv.org/search/?"
        params = {
            "query": keyword,
            "searchtype": self.args.searchtype, 
            "abstracts": "show", 
            "order": "-announced_date_first",
            "size": 50, #50 results per page
            "classification": self.args.fields
        }
        if page > 0:
            params["start"] = page * 50  # 设置起始位置
        print(base_url + requests.compat.urlencode(params))
        return base_url + requests.compat.urlencode(params)

    def get_titles(self, url, days=1):
        '''
        Get papers' titles, links, dates in a page
        '''
        titles = []
        links = []
        dates = []
        try:
            response = requests.get(url, timeout=180)  # send a GET request to the url
        except:
            print('get papers failed')
            return titles, links, dates

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("li", class_="arxiv-result")
        today = datetime.date.today()
        last_days = datetime.timedelta(days=days)
        for article in articles:
            title = article.find("p", class_="title").text
            link = article.find("span").find_all("a")
            if len(link) != 0:
                link = link[0].get('href')
            else:
                link = ''
            date_text = article.find("p", class_="is-size-7").text
            date_text = date_text.split('\n')[0].split("Submitted ")[-1].split("; ")[0]
            date_text = datetime.datetime.strptime(date_text, "%d %B, %Y").date()
            if (today - date_text) <= last_days:
                titles.append(title.strip())
                links.append(link)
                dates.append(date_text)
            else:
                break
        return titles, links, dates

    def get_all_titles_from_web(self, keyword, page_num=1, days=1):
        '''
        Get all titles, links, dates from web based on keyword
        '''
        title_list, link_list, date_list = [], [], []
        for page in range(page_num):
            url = self.get_url(keyword, page)  # generate url
            titles, links, dates = self.get_titles(url, days)
            if not titles:  # if titles is empty, it implies no more papers
                break
            for title_index, title in enumerate(titles):
                print(page, title_index, title, links[title_index], dates[title_index])
            title_list.extend(titles)
            link_list.extend(links)
            date_list.extend(dates)
        print("-" * 40)
        return title_list, link_list, date_list

    def get_arxiv_web(self, args, query, page_num=1, days=2, paper_url = None):
        titles, links, dates = self.get_all_titles_from_web(query, page_num=page_num, days=days)
        paper_list = []
        for title_index, title in enumerate(titles):
            if title_index + 1 > args.max_results:
                break
            url = links[title_index] + ".pdf"  # the link of the pdf document
            if url in paper_url:
                continue
            print(title_index, title, links[title_index], dates[title_index])
            filename = self.try_download_pdf(url, title, query)
            if filename is not None:
                paper = Paper(path=filename,
                              url=links[title_index],
                              title=title,
                              date = dates[title_index],
                              tag = query
                              )
                if paper is not None:
                    paper_list.append(paper)
                    paper_url.append(url)
        return paper_list

    def validateTitle(self, title):
        '''
        modify title to a valid file name
        '''
        rstr = r"[\/\\\:\*\?\"\<\>\|]"
        new_title = re.sub(rstr, "_", title)
        return new_title

    def download_pdf(self, url, title, query):
        try:
            response = requests.get(url, timeout=180)  # send a GET request to the url
        except:
            print('download pdf failed')
            return None
        date_str = str(datetime.datetime.now())[:13].replace(' ', '-')
        #path = self.root_path + 'pdf_files/' + self.validateTitle(query) + '-' + date_str
        #path = self.root_path + 'pdf_files/' + date_str
        path = self.root_path + date_str
        path = path + '/' + self.validateTitle(query)
        try:
            os.makedirs(path)
        except:
            pass
        filename = os.path.join(path, self.validateTitle(title)[:80] + '.pdf')
        with open(filename, "wb") as f:  # open a file with write and binary mode
            f.write(response.content)  # write the content of the response to the file
        return filename

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def try_download_pdf(self, url, title, query):
        return self.download_pdf(url, title, query)

    def summary_with_chat(self, paper_list, notion_utils):
        for paper_index, paper in enumerate(paper_list):
            htmls = [] #ouput as md content (copy from original chatpaper repo)
            #* 1. Use title,abs, and introduction to generate basic information
            text = ''
            text += 'Title:' + paper.title
            print('-------------------------------Start to chat paper:', paper.title, '-------------------------------')
            text += 'Url:' + paper.url
            try:
                if 'Abstract' in paper.section_text_dict:
                    abs = paper.section_text_dict['Abstract']
                else:
                    abs = paper.abs
            except:
                abs = paper.abs
            text += 'Abstract:' + abs
            abs = abs.split('Introduction')[0].split('Abstract')[-1]
            try:
                text += 'Paper_info:' + paper.section_text_dict['paper_info']
            except:
                text += ''

            try:
                text += list(paper.section_text_dict.values())[0]
            except:
                text += ''

            chat_summary_text = ""
            try:
                if len(text) > 2000:
                    text = text[:2000]
                chat_summary_text = self.chat_summary(text=text)
            except Exception as e:
                print("summary_error:", e)
                '''
                if "maximum context" in str(e):
                    current_tokens_index = str(e).find("your messages resulted in") + len(
                        "your messages resulted in") + 1
                    offset = int(str(e)[current_tokens_index:current_tokens_index + 4])
                    summary_prompt_token = offset + 1000 + 150
                    chat_summary_text = self.chat_summary(text=text, summary_prompt_token=summary_prompt_token)
                '''

            htmls.append('## Paper:' + str(paper_index + 1))
            htmls.append('\n\n\n')
            if "chat_summary_text" in locals():
                htmls.append(chat_summary_text)

            try:
                basic, summary = chat_summary_text.split('7. Summary:')
            except:
                basic = chat_summary_text
                summary = ''
            try:
                cn_title = re.search('Chinese Title:(.*?)\n', basic, re.S).group(1)
            except:
                cn_title = ''
            date = paper.date

            #* 2. Chat and generate method part
            method_key = ''
            for parse_key in paper.section_text_dict.keys():
                if 'method' in parse_key.lower() or 'approach' in parse_key.lower():
                    method_key = parse_key
                    break

            chat_method_text = ""
            if method_key != '':
                text = ''
                method_text = ''
                summary_text = ''
                summary_text += "<summary>" + chat_summary_text
                # methods
                method_text += paper.section_text_dict[method_key]
                text = summary_text + "\n\n<Methods>:\n\n" + method_text
                # chat_method_text = self.chat_method(text=text)
                try:
                    if len(text) > 2000:
                        text = text[:2000]
                    chat_method_text = self.chat_method(text=text)
                except Exception as e:
                    print("method_error:", e)
                    if "maximum context" in str(e):
                        current_tokens_index = str(e).find("your messages resulted in") + len(
                            "your messages resulted in") + 1
                        offset = int(str(e)[current_tokens_index:current_tokens_index + 4])
                        method_prompt_token = offset + 800 + 150
                        chat_method_text = self.chat_method(text=text, method_prompt_token=method_prompt_token)

                if "chat_method_text" in locals():
                    htmls.append(chat_method_text)
            else:
                chat_method_text = ''
            htmls.append("\n" * 4)

            #* 3. Chat and generate conclution part
            conclusion_key = ''
            for parse_key in paper.section_text_dict.keys():
                if 'conclu' in parse_key.lower():
                    conclusion_key = parse_key
                    break

            text = ''
            conclusion_text = ''
            summary_text = ''
            summary_text += "<summary>" + chat_summary_text + "\n <Method summary>:\n" + chat_method_text
            chat_conclusion_text = ""
            if conclusion_key != '':
                # conclusion
                conclusion_text += paper.section_text_dict[conclusion_key]
                text = summary_text + "\n\n<Conclusion>:\n\n" + conclusion_text
            else:
                text = summary_text
            try:
                if len(text) > 2000:
                    text = text[:2000]
                chat_conclusion_text = self.chat_conclusion(text=text)
            
            except Exception as e:
                print("conclusion_error:", e)
            '''
                if "maximum context" in str(e):
                    current_tokens_index = str(e).find("your messages resulted in") + len(
                        "your messages resulted in") + 1
                    offset = int(str(e)[current_tokens_index:current_tokens_index + 4])
                    conclusion_prompt_token = offset + 800 + 150
                    if len(text) > 2000:
                        text = text[:2000]
                    chat_conclusion_text = self.chat_conclusion(text=text, conclusion_prompt_token=conclusion_prompt_token)
            '''
            if "chat_conclusion_text" in locals():
                htmls.append(chat_conclusion_text)
            htmls.append("\n" * 4)

            #save to md
            date_str = str(datetime.datetime.now())[:13].replace(' ', '-')
            export_path = os.path.join(self.root_path, 'export')
            if not os.path.exists(export_path):
                os.makedirs(export_path)
            mode = 'w' if paper_index == 0 else 'a'
            file_name = os.path.join(export_path,
                                     date_str + '-' + self.validateTitle(self.query) + "." + self.file_format)
            self.export_to_markdown("\n".join(htmls), file_name=file_name, mode=mode)

            #save to notion
            try:
                tags = re.search('Keywords: (.*?)\n', chat_summary_text, re.S).group(1)#key word in chat_summary_text
                org  = re.search('Affiliation: (.*?)\n', chat_summary_text, re.S).group(1) #Aff in chat_summary_text
                code = re.search('Github: (.*?)\n',chat_summary_text,re.S) #github in chat_summary_text
            except:
                tags = ''
                org = ''
                code = ''

            try:
                if code is not None:
                    code = code.group(1)
            except:
                pass
            url = paper.url
            des = re.search('\(1\): (.*?)。', chat_conclusion_text, re.S)
            if des is not None:
                des = des.group(1)
            else:
                des = chat_conclusion_text.strip()

            #insert to notion
            notion_content = notion_utils.format_notion(abs, basic, date, summary, chat_method_text, chat_conclusion_text)
            n_id = notion_utils.insert_to_notion(paper.title, cn_title, paper.tag, str(paper.date), 'arxiv', org, des, code, url)
            results = notion_utils.add_children(n_id, notion_content)
            print('-------------------------------Insert Success:', paper.title, '-------------------------------')


    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def chat_conclusion(self, text, conclusion_prompt_token=800):
        if len(self.use_other_api) > 1:
            openai.api_base = self.use_other_api
        openai.api_key = self.chat_api_list[self.cur_api]
        self.cur_api += 1
        self.cur_api = 0 if self.cur_api >= len(self.chat_api_list) - 1 else self.cur_api
        text_token = len(self.encoding.encode(text))
        clip_text_index = int(len(text) * (self.max_token_num - conclusion_prompt_token) / text_token)
        clip_text = text[:clip_text_index]

        messages = [
            {"role": "system",
             "content": "You are a reviewer in the field of [" + self.key_word + "] and you need to critically review this article"},
            # chatgpt 角色
            {"role": "assistant",
             "content": "This is the <summary> and <conclusion> part of an English literature, where <summary> you have already summarized, but <conclusion> part, I need your help to summarize the following questions:" + clip_text},
            # 背景知识，可以参考OpenReview的审稿流程
            {"role": "user", "content": """                 
                 8. Make the following summary.Be sure to use {} answers (proper nouns need to be marked in English).
                    - (1):What is the significance of this piece of work?
                    - (2):Summarize the strengths and weaknesses of this article in three dimensions: innovation point, performance, and workload.                   
                    .......
                 Follow the format of the output later: 
                 8. Conclusion: \n\n
                    - (1):xxx;\n                     
                    - (2):Innovation point: xxx; Performance: xxx; Workload: xxx;\n                      

                 Be sure to use {} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """.format(self.language, self.language)},
        ]
        f = 0
        while(f > -9 and f!=1):
            try:
                response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages = messages)
                result = response["choices"][0]['message']['content']
                f = 1
            except Exception as e:
                print(e, "openai error, retry")
                f -= 1
                time.sleep(2)
        print("*******************Conclusion Chat Result:*******************\n", result)
        print("prompt_token_used:", response.usage.prompt_tokens,
              "completion_token_used:", response.usage.completion_tokens,
              "total_token_used:", response.usage.total_tokens)
        #print("response_time:", str(response.response_ms / 1000.0), 's')
        print("\n")
        return result

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def chat_method(self, text, method_prompt_token=800):
        if len(self.use_other_api) > 1:
            openai.api_base = self.use_other_api
        openai.api_key = self.chat_api_list[self.cur_api]
        self.cur_api += 1
        self.cur_api = 0 if self.cur_api >= len(self.chat_api_list) - 1 else self.cur_api
        text_token = len(self.encoding.encode(text))
        clip_text_index = int(len(text) * (self.max_token_num - method_prompt_token) / text_token)
        clip_text = text[:clip_text_index]
        messages = [
            {"role": "system",
             "content": "You are a researcher in the field of [" + self.key_word + "] who is good at summarizing papers using concise statements"},
            # chatgpt 角色
            {"role": "assistant",
             "content": "This is the <summary> and <Method> part of an English document, where <summary> you have summarized, but the <Methods> part, I need your help to read and summarize the following questions." + clip_text},
            # 背景知识
            {"role": "user", "content": """                 
                 7. Describe in detail the methodological idea of this article. Be sure to use {} answers (proper nouns need to be marked in English). For example, its steps are.
                    - (1):...
                    - (2):...
                    - (3):...
                    - .......
                 Follow the format of the output that follows: 
                 7. Methods: \n\n
                    - (1):xxx;\n 
                    - (2):xxx;\n 
                    - (3):xxx;\n  
                    ....... \n\n     

                 Be sure to use {} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """.format(self.language, self.language)},
        ]
        f = 0
        while(f > -9 and f!=1):
            try:
                response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages = messages)
                result = response["choices"][0]['message']['content']
                f = 1
            except Exception as e:
                print(e, "openai error, retry")
                f -= 1
                time.sleep(2)
        print("*******************Method Chat Result:*******************\n", result)
        print("prompt_token_used:", response.usage.prompt_tokens,
              "completion_token_used:", response.usage.completion_tokens,
              "total_token_used:", response.usage.total_tokens)
        #print("response_time:", str(response.response_ms / 1000.0), 's')
        print("\n")
        return result

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def chat_summary(self, text, summary_prompt_token=1100):
        if len(self.use_other_api) > 1:
            openai.api_base = self.use_other_api
        openai.api_key = self.chat_api_list[self.cur_api]
        self.cur_api += 1
        self.cur_api = 0 if self.cur_api >= len(self.chat_api_list) - 1 else self.cur_api
        text_token = len(self.encoding.encode(text))
        clip_text_index = int(len(text) * (self.max_token_num - summary_prompt_token) / text_token) #?
        clip_text = text[:clip_text_index]
        messages = [
            {"role": "system",
             "content": "You are a researcher in the field of [" + self.key_word + "] who is good at summarizing papers using concise statements"},
            {"role": "assistant",
             "content": "This is the title, author, link, abstract and introduction of an English document. I need your help to read and summarize the following questions: " + clip_text},
            {"role": "user", "content": """                 
                 1. Mark the title of the paper
                 2. Translate the title into Chinese
                 2. list all the authors' names (use English)
                 3. mark the first author's affiliation (output {} translation only)                 
                 4. mark the keywords of this article (use English)
                 5. link to the paper, Github code link (if available, fill in Github:None if not)
                 6. summarize according to the following four points.Be sure to use {} answers (proper nouns need to be marked in English)
                    - (1):What is the research background of this article?
                    - (2):What are the past methods? What are the problems with them? Is the approach well motivated?
                    - (3):What is the research methodology proposed in this paper?
                    - (4):On what task and what performance is achieved by the methods in this paper? Can the performance support their goals?
                 Follow the format of the output that follows:                  
                 1. Title: xxx\n\n
                 2. Chinese Title: xxx\n\n
                 3. Authors: xxx\n\n
                 4. Affiliation: xxx\n\n                 
                 5. Keywords: xxx\n\n   
                 6. Urls: xxx or xxx , xxx \n\n      
                 7. Summary: \n\n
                    - (1):xxx;\n 
                    - (2):xxx;\n 
                    - (3):xxx;\n  
                    - (4):xxx.\n\n     

                 Be sure to use {} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not have too much repetitive information, numerical values using the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed.          
                 """.format(self.language, self.language, self.language)},
        ]
        f = 0 
        while(f > -9 and f!=1):
            try:
                response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages = messages)
                result = response["choices"][0]['message']['content']
                f = 1
            except Exception as e:
                print(e, "openai error, retry")
                f -= 1
                time.sleep(2)
        print("*******************Basic Chat Result:*******************\n", result)
        print("prompt_token_used:", response.usage.prompt_tokens,
              "completion_token_used:", response.usage.completion_tokens,
              "total_token_used:", response.usage.total_tokens)
        #print("response_time:", str(response.response_ms / 1000.0), 's')
        print("\n")
        return result

    def export_to_markdown(self, text, file_name, mode='w'):
        with open(file_name, mode, encoding="utf-8") as f:
            f.write(text)

    def show_info(self):
        print(f"Key word: {self.key_word}")
        print(f"Query: {self.query}")
        print(f"Sort: {self.sort}")


def chat_arxiv_main( notion_utils, args):
    paper_list_all = []
    paper_url = [] #save download urls, to avoid download again
    for query in args.query_list:
        query = query.replace("'", "")
        print('Now query:', query)
        reader = Reader(key_word=args.key_word,
                         query=query,
                         args=args)
        reader.show_info()
        paper_list = reader.get_arxiv_web(args=args, query = query, page_num=args.page_num, days=args.days, paper_url = paper_url)
        paper_list_all.extend(paper_list)
        reader.summary_with_chat(paper_list=paper_list, notion_utils=notion_utils)

    #after download all papers, then use chatGPT to summary and write in to notion
    #reader.summary_with_chat(paper_list=paper_list_all)
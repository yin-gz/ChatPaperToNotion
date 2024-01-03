import argparse
import time
import configparser
from notion_utils import NotionUtils
from main import chat_arxiv_main, ArxivParams

search_key_words = ["large language model","social network"]

def update_config(args):
    #read openai api
    config = configparser.ConfigParser()
    config.read('apikey.ini')
    args.use_other_api = config.get('OpenAI', 'USE_OTHER_API')
    args.chat_api_list = config.get('OpenAI', 'API_KEYS')[1:-1].replace('\'', '').split(',')
    # prevent short strings from being incorrectly used as API keys.
    args.chat_api_list = [api.strip() for api in args.chat_api_list if len(api) > 20]

    #read notion api
    args.database_id = config.get('NOTION', 'database_id')
    args.notion_token = config.get('NOTION', 'notion_token')

    #read gitee api
    if args.save_image:
        args.gitee_key = args.config.get('Gitee', 'api')
    else:
        args.gitee_key = ''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    query_list = search_key_words
    parser.add_argument("--searchtype", type=str, default = 'title', help="the searching type, title/abstract/author")
    parser.add_argument("--query_list", type=list, default=query_list, help="the query key word list")
    parser.add_argument("--key_word", type=str, default='machine learning', help="the key word of user research fields, just to guide GPT's role")
    parser.add_argument("--fields", type=str, default='computer_science', help="fieds for arxiv searching")
    parser.add_argument("--page_num", type=int, default=20, help="the maximum number of page")
    parser.add_argument("--max_results", type=int, default=256, help="the maximum number of results")
    parser.add_argument("--days", type=int, default=1, help="the last days of arxiv papers of this query, if today is Monday, set it to 3; otherwise set it to 1 to get yesterday's papers")
    parser.add_argument("--sort", type=str, default="web", help="web/LastUpdatedDate")
    parser.add_argument("--save_image", default=False,
                        help="save image? It takes a minute or two to save a picture! But pretty")
    parser.add_argument("--file_format", type=str, default='md', help=".md or .txt as output")
    parser.add_argument("--language", type=str, default='cn', help="The other output lauguage is English, is en")
    parser.add_argument("--root_path", type=str, default='./pdf_files/',
                        help="The path of the paper's url")

    #arxiv_args = ArxivParams(**vars(parser.parse_args()))
    arxiv_args = parser.parse_args()
    update_config(arxiv_args)
    notion_utils = NotionUtils(arxiv_args.database_id, arxiv_args.notion_token)
    start_time = time.time()
    chat_arxiv_main(notion_utils, args=arxiv_args)
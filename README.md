<h1 align="center">ChatPaperToNotion</h1>

<div style="font-size: 1.5rem;">
  <a href="./README.md">中文</a> |
  <a href="./readme_en.md">English</a>
</div>
</br>


## 功能
- 自定义关键词及日期范围，爬取arxiv论文存储在本地并自动调用chatGPT总结文章内容更新到notion
- 可部署到github实现每日定时自动爬取分析（基于github action）

## NOTION配置
   - NotionToken获取
     - 浏览器打开https://www.notion.so/my-integrations
     - 点击New integration 输入name提交
     - copy到notion_token变量
  
   - database配置
     - 复制[这个Notion模板](https://guiltless-chalk-a57.notion.site/57c1568345a14b99bce3b3fccdc41ffe?v=89bfeb0a21db410da9460661dc2576b5&pvs=4)
     - 打开复制好的你的Notion数据库, 点击右上角"..."-"Add Connections"添加上一步配置的integration
     - 点击右上角的Share，然后点击Copy link 
     - 获取链接后比如 https://www.notion.so/57c1568345a14b99bce3b3fccdc41ffe?v=89bfeb0a21db410da9460661dc2576b5&pvs=4 中间的57c1568345a14b99bce3b3fccdc41ffe就是database_id


## 本地使用
1. 配置apikey.ini文件中NOTION 相关变量值（详情见上）

2. 配置apikey.ini文件中open AI 相关变量值
   
     - 方式一：使用open AI 提供的原始 API接口
         ```
         USE_OTHER_API = XXXX #不需要引号
         API_KEYS = [Your_keys1,] #注意默认形如list格式，不需要引号
         ```
     - 方式二：使用国内转接的API接口[例如:AiHubMix](https://aihubmix.com)
         ```
         USE_OTHER_API = https://aihubmix.com/v1 #不需要引号
         API_KEYS = [Your_keys1,] #注意默认形如list格式，不需要引号
         ```
3. 安装requirements.txt
   ```
   pip install -r requirement.txt 
   ```
   
4. 修改run_local.py 中的search_key_words为所需要的
   
5. 创建pdf 存储目录
   ```
   mkdir pdf_files
   ```

6. 运行run_local.py
   ```
   python run_local.py --days 1 --language "cn"
   ```

## 部署到github自动爬取
1. fork本项目（如果觉得本项目对您有帮助，欢迎再star下🤭）
2. 在Github的Secrets中添加以下变量
    * 打开fork的项目，点击Settings->Secrets and variables->Actions->New repository secret
    * 添加以下变量
        * USE_OTHER_API, eg. https://openai.api2d.net/v1
        * API_KEYS, eg. [Your_key, ]
        * NOTION_TOKEN, 见notion配置
        * DATABASE_ID, 见notion配置
        * SEARCH_KEY_WORDS, eg. [large language model,social network,...]
3. 手动运行Actions 中autorun, 或等待程序每日自动运行

PS： (i) 修改workflows中autorun.yml可修改启动时间(默认每天北京时间15点运行一次) (ii) 修改run_auto.py中arxiv_args.days可更改爬取近几日的文章，默认为1


## 👉ToDo
- [ ] 提高分析准确性、全面性
- [ ] 增加基于arxiv网页版的分析、方法图的爬取与分析
- [ ] 增加对dblp等网站相关论文的分析
- [ ] 英文版readme

## 参考与致谢
本项目代码主要参考并基于以下Awesome Repository:
- [ChatPaper](https://github.com/kaixindelele/ChatPaper)
- [weread2notion](https://github.com/malinkang/weread2notion)

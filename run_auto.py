import argparse
import time
from notion_utils import NotionUtils
from main import chat_arxiv_main, ArxivParams

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # read these parameters from github secrets variables
    parser.add_argument("use_other_api", type=str)
    parser.add_argument("chat_api_list", type=str)
    parser.add_argument("database_id", type=str)
    parser.add_argument("notion_token", type=str)
    parser.add_argument("search_key_words", type=str)
    parser.add_argument("ref")
    parser.add_argument("repository")
    #parser.add_argument("--gitee_key", type=str)

    arxiv_args = parser.parse_args()

    print('load success!!!!')

    arxiv_args.searchtype = 'title'
    arxiv_args.key_word ='machine learning'
    arxiv_args.fields ='computer_science'
    arxiv_args.page_num = 20
    arxiv_args.max_results =256
    arxiv_args.days = 1
    arxiv_args.sort ="web"
    arxiv_args.save_image =False
    arxiv_args.file_format = 'md'
    arxiv_args.language ='cn'
    arxiv_args.gitee_key = ''
    arxiv_args.query_list = arxiv_args.search_key_words[1:-1].split(',')
    arxiv_args.chat_api_list = arxiv_args.chat_api_list[1:-1].split(',')
    arxiv_args.chat_api_list = [api.strip() for api in arxiv_args.chat_api_list if len(api) > 20]
    branch = arxiv_args.ref.split('/')[-1]
    arxiv_args.root_path =f"https://raw.githubusercontent.com/{arxiv_args.repository}/{branch}/"


    print( "key words:", arxiv_args.query_list)
    
    

    start_time = time.time()
    notion_utils = NotionUtils(arxiv_args.database_id, arxiv_args.notion_token)
    chat_arxiv_main(notion_utils, args=arxiv_args)

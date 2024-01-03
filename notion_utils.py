from notion_client import Client
import time
import logging


class NotionUtils:
    def __init__(self,database_id, notion_token):
        self.database_id = database_id
        self.notion_token = notion_token
        self.client = Client(
            auth=notion_token,
            log_level=logging.ERROR
        )


    def insert_to_notion(self, paperName, cn_title, tags, date, source_web, org, des, code, url):
        # tags are key words when searching
        time.sleep(0.3)
        parent = {
            "database_id": self.database_id,
            "type": "database_id"
        }
        if len(des) > 2000:
            des = des[:2000]       
        properties = {
            #if one of the arrtibute format is wrong, an error will be raised
            "Name": {"title": [{"type": "text", "text": {"content": paperName}}]},
            "CNName": {"rich_text": [{"type": "text", "text": {"content": cn_title}}]},
            "Tags": {"multi_select": [{"name": tags}]},
            "When": {"rich_text": [{"type": "text", "text": {"content": date}}]},
            "Where": {"rich_text": [{"type": "text", "text": {"content": source_web}}]},
            "Who": {"rich_text": [{"type": "text", "text": {"content": org}}]},
            # 'des' is summary
            "Description": {"rich_text": [{"type": "text", "text": {"content": des}}]},
        }

        if code is not None and code.startswith('http'):
            properties["Code"] = {"url": code}
        if url is not None and url.startswith('http'):
            properties["URL"] = {"url": url}
        response = self.client.pages.create(
            parent=parent, properties=properties)
        n_id = response["id"]
        return n_id

        

    def add_children(self, id, children):
        results = []

        for i in range(0, len(children)//100+1):
            time.sleep(0.3)
            response = self.client.blocks.children.append(
                block_id=id, children=children[i*100:(i+1)*100])
            results.extend(response.get("results"))
        return results

    def get_heading(self, level, content):
        if level == 1:
            heading = "heading_1"
        elif level == 2:
            heading = "heading_2"
        else:
            heading = "heading_3"
        return {
            "type": heading,
            heading: {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": content,
                    }
                }],
                "color": "default",
                "is_toggleable": False
            }
        }

    def get_number_list(self, content):
        result = []
        content_split = content.split('\n\n')
        for content_i in content_split:
            content_i = content_i.strip()
            if len(content_i) != 0:
                result.append({
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content_i,
                                }
                            }
                        ]
                    }
                })
        return result

    def get_bullet_list(self, content, date = None):
        result = []
        content_split = content.split('\n')
        for content_i in content_split:
            content_i = content_i.strip()
            if len(content_i) != 0:
                result.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content_i,
                                }
                            }
                        ]
                    }
                })
        if date is not None:
            result.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": 'Date: ' + str(date)
                            }
                        }
                    ]
                }
            })

        return result

    def get_callout(self, content):
        max_len = 2000
        if len(content) > max_len:
            content = content[:max_len]
        return {
            "type": "callout",
            "callout": {
                "icon": {
                    "type": "emoji",
                    "emoji": "🌟"
                },
                "color": "yellow_background",
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": content,
                    }
                }],
            }
        }

    def format_notion(self, abs, basic, date, summary, chat_method_text, chat_conclusion_text):
        notion_content = []
        notion_content.append(self.get_heading(2, 'Basic Information'))
        notion_content.extend(self.get_bullet_list(basic, date))
        notion_content.append(self.get_heading(2, 'Abstract'))
        notion_content.append(self.get_callout(abs))
        notion_content.append(self.get_heading(2, 'Summary'))
        notion_content.extend(self.get_bullet_list(summary))
        notion_content.append(self.get_heading(2, 'Methods'))
        notion_content.extend(self.get_bullet_list(chat_method_text.split('Methods:')[-1]))
        notion_content.append(self.get_heading(2, 'Conclusion'))
        notion_content.extend(self.get_bullet_list(chat_conclusion_text.split('Conclusion:')[-1]))
        return notion_content

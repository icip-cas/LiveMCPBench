import argparse
import json
from typing import Dict, List, Optional, Union

import psutil
import requests
import time

class LarkReporter:

    def __init__(self, url: str):
        self.url = url

    def post(self,
             content: Union[str, List[List[Dict]]],
             title: Optional[str] = None):
        """Post a message to Lark.

        When title is None, message must be a str.
        otherwise msg can be in rich text format (see
        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/im-v1/message/create_json#45e0953e
        for details).
        """
        if title is None:
            assert isinstance(content, str)
            msg = {'msg_type': 'text', 'content': {'text': content}}
        else:
            if isinstance(content, str):
                content = [[{'tag': 'text', 'text': content}]]
            msg = {
                'msg_type': 'post',
                'content': {
                    'post': {
                        'zh_cn': {
                            'title': title,
                            'content': content
                        }
                    }
                }
            }
        requests.post(self.url, data=json.dumps(msg))


def parse_args():
    parser = argparse.ArgumentParser(description='Lark bot reporter')
    parser.add_argument('--url',type=str)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--interval',type=int,default=10)
    
    args = parser.parse_args()
    return args

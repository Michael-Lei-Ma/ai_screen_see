# # -*- coding: utf-8 -*-
# import json
# import pymysql, re
# keywrods = ""
# import logging
# import sys
# from logging.handlers import TimedRotatingFileHandler
# from typing import Optional
# import requests,socket
# from requests.adapters import HTTPAdapter
# from urllib3.util.retry import Retry
# from pathlib import Path
# import base64
#
# session = requests.Session()
# def stream_request(url, headers, payload):
#     print("请求体大小:", len(payload) / 1024, "KB")
#     with session.post(url, headers=headers, json=payload, timeout=(100,1800), stream=True) as resp:
#         content_pieces = []
#         for line in resp.iter_lines(decode_unicode=True):
#             if not line or not line.startswith("data: "):
#                 continue
#             chunk = line[6:]
#             if chunk == "[DONE]":
#                 break
#             try:
#                 id= json.loads(chunk).get("id","")
#                 if json.loads(chunk)["choices"]:
#                     delta = json.loads(chunk)["choices"][0]["delta"].get("content")
#                 else:
#                     continue
#                 if delta:
#                     content_pieces.append(delta)
#                 elif delta is None:
#                     continue
#             except Exception as e:
#                 print(e)
#                 import traceback
#                 traceback.print_exc()
#                 continue
#         return id,"".join(content_pieces)
#
# def geteventidpromot():
#     return  """
#         任务:
#             请识别图中的微粒贷号,输出以json格式返回,json的key必须是中文且必须是"微粒贷号",不做任何解释
#             微粒贷号是以DS开头的一串信息,没有的话返回空,
#         禁止:
#           微粒贷号不要拼音那样的名字
#     """
#
#
# MODEL_TOKEN = "sk-1f6e80a2a0df40909f5c2b9d5f8df592"
# file_path = "screenshot_basic_info.png"
# file_path = Path.cwd() / file_path
# print(f"file_path: {file_path}  {type(file_path)}")
# url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
# headers = {
#     "Authorization": "Bearer %s" % MODEL_TOKEN,
#     "Content-Type": "application/json"
# }
# images = []
# for p in [file_path]:
#     with open(p, "rb") as f:
#         b64 = base64.b64encode(f.read()).decode()
#     images.append({
#         "type": "image_url",
#         "image_url": {
#             "url": f"data:image/png;base64,{b64}"
#         }
#     })
# payload = {
#     "model": "qwen3.6-plus", # qwen3.6-plus   qwen-vl-max-latest
#     "stream": True,
#     # 或 qwen-vl-max-latest
#     "messages": [
#         {"role": "user", "content":
#             images +
#             [{"type": "text", "text": geteventidpromot()
#               }
#              ]
#          }
#     ]
# }
#
#
# event_id, reqData = stream_request(url, headers, payload)
# print(f"event_id: {event_id}\nreqData: {reqData}")
#

import re
import json
info ='```json\n{"工作信息": {\n"获取时间": "",\n"工作单位": "",\n"单位地址": ""\n}\n}```'


# start = info.find('{')
# end = info.rfind('}') + 1
#
# # 提取 JSON 字符串
# json_str = info[start:end]
#
# print(json_str)



# candidates = re.findall(r'\{.*\}', info, re.DOTALL)
# for cand in candidates:
#     try:
#         # 尝试解析，成功则说明是合法 JSON 字符串
#         obj = json.loads(cand)
#         json_str = cand
#         break
#     except json.JSONDecodeError:
#         continue

match = re.search(r'\{.*\}', info, re.DOTALL)
json_str = match.group(0) if match else ''
print(json_str)
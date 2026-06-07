import time

import requests
import re,json



img_path = './images/20251015170020e89d9ae8.png'
import requests, json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket

session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(total=2, backoff_factor=1))
session.mount("http://", adapter)
session.mount("https://", adapter)
def getlocalip():
    """
        获取本地 IP
    :return:
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
def send_robot(webhook, text, at_mobiles=None):
    """
    企业微信群机器人发文本
    :param webhook: 机器人 Webhook 地址
    :param text: 文本内容
    :param at_mobiles: 要@的手机号列表，填 ["@all"] 全员
    """
    body = {
        "msgtype": "text",
        "text": {
            "content": getlocalip()+" "+text,
            "mentioned_list": at_mobiles or []
        }
    }
    try:
        resp = requests.post(webhook, json=body, timeout=10)
        return resp.json()
    except Exception as e:
        return {"errcode": 1, "errmsg": str(e)}

# ====== 一键测试 ======
def get_zling(img_path):
    url = 'http://10.255.101.112:9006/ocr'
    with open(img_path, 'rb') as f:
        file_dict = {'image_file': (img_path, f, 'image/png')}
        response = session.post(url, files=file_dict, timeout=60)
    data = response.json()
    response.close()
    zling = ""
    key=""
    for item in data:
        if data[item]['rec_txt']=="账龄":
            key=item
    nextvalue=int(key)+1
    return data[str(nextvalue)]['rec_txt']



def get_retry_json(img_path,key,msg="",i=0):
    url = 'http://10.255.101.112:9006/ocr'
    with open(img_path, 'rb') as f:
        file_dict = {'image_file': (img_path, f, 'image/png')}
        print("第%s次开始请求" % i)
        response = session.post(url, files=file_dict, timeout=600)

    data = response.json()
    print(str(i)+":"+str(id(data)))
    response.close()
    payload = {
        "model": "qwen-vl-max-latest",  # 或 qwen-vl-max-latest
        "messages": [
            {"role": "user", "content":
                [{"type": "text", "text": str(data) + "假设你是一个资深的催收员,请将上述的信息提炼成json返回我,仅仅返回json,json的key必须是中文,"
                                                      "且要包含微粒贷号的信息以DS开头的;"
                                                      "如果有微信渠道的还款方式,需要包含8000开头的卡号,key的名字就叫卡号,数值是8000开头的卡号;"
                                                      +msg
                  }
                 ]
             }
        ]
    }
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": "Bearer %s" % key,
        "Content-Type": "application/json"
    }
    resp = session.post(url, headers=headers, json=payload)
    try:
        clean = re.sub(r"```(?:json)?\n(.*?)```", r"\1", resp.json()["choices"][0]["message"]["content"],
                       flags=re.S).strip()
        data = json.loads(clean)
        return data
    except json.JSONDecodeError as e:
        print(e)

    return ""
if __name__ == '__main__':
    from threading import Thread
    print(time.time())
    k=[]
    for i in range(20):
        print("当前提交的第%s次" % i)
        t=Thread(target=get_retry_json,args=(img_path,"sk-e556196964604e70a6231e9e160dd356","",i))
        t.start()
        k.append(t)
    for m in k:
        m.join()
        # print(get_retry_json(img_path,"sk-e556196964604e70a6231e9e160dd356"))
    print(time.time())

    # send_robot("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
    #            "获取重试json失败,请检查,错误信息:" + str("测试请忽略"))


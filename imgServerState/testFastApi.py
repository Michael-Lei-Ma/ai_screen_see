import os
import requests
from pathlib import Path

HOST = "http://10.255.100.202:7000"
API_TOKEN = "cbf123456."
"""
    imgServerFastApi.py 文件定义API调用调试脚本；
    
"""

def print_response(resp):
    print(f"URL: {resp.request.url}")
    print(f"Status: {resp.status_code}")
    try:
        print("JSON:", resp.json())
    except ValueError:
        print("Text:", resp.text)
    print("---")


def retry_image(image_path: str, ip: str = "10.255.50.51"):
    """POST /retryImage"""
    params = {"imagePath": image_path, "ip": ip}
    resp = requests.post(f"{HOST}/retryImage", params=params)
    print_response(resp)
    return resp


def upload_image(file_path: str, from_ip: str = "10.255.50.51"):
    """POST /upload"""
    params = {"token": API_TOKEN, "fromIp": from_ip}
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/png")}
        resp = requests.post(f"{HOST}/upload", params=params, files=files)
    print_response(resp)
    return resp


def upload_excel(file_path: str):
    """POST /excel"""
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = requests.post(f"{HOST}/excel", files=files)
    print_response(resp)
    return resp


def get_image(file_name: str):
    """GET /image/{file_name}"""
    params = {"token": API_TOKEN}
    resp = requests.get(f"{HOST}/image/{file_name}", params=params)
    print(f"URL: {resp.request.url}")
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type')}")
    print(f"Bytes: {len(resp.content)}")
    print("---")
    return resp


def hello():
    """GET /hello"""
    resp = requests.get(f"{HOST}/hello")
    print_response(resp)
    return resp


def ok():
    """GET /ok"""
    resp = requests.get(f"{HOST}/ok")
    print_response(resp)
    return resp


def clean():
    """GET /clean"""
    resp = requests.get(f"{HOST}/clean")
    print_response(resp)
    return resp


def notok():
    """GET /notok"""
    resp = requests.get(f"{HOST}/notok")
    print_response(resp)
    return resp


def download_file(file_name: str, save_to: str = None):
    """GET /download/{file_name}"""
    resp = requests.get(f"{HOST}/download/{file_name}")
    print_response(resp)
    if save_to and resp.status_code == 200:
        with open(save_to, "wb") as f:
            f.write(resp.content)
        print(f"Saved to {save_to}")
    return resp


def alert_msg(text: str, at_mobiles: list = None):
    """POST /alert"""
    if at_mobiles is None:
        at_mobiles = []
    payload = {"text": text, "at_mobiles": at_mobiles}
    resp = requests.post(f"{HOST}/alert", json=payload)
    print_response(resp)
    return resp


if __name__ == "__main__":
    print("=== API 调用示例 ===")

    file_path = "basic_info.png"
    file_path = Path.cwd() / file_path
    # print(f"file_path: {file_path}  {type(file_path)}")
    # 1. 重试图片
    # retry_image("images/example.jpg", "10.255.50.51")

    # 2. 上传图片
    # upload_image(str(file_path))

    # 3. 上传 Excel
    # upload_excel("123.xlsx")

    # 4. 查看图片
    # get_image("example.jpg")

    # 5. hello
    hello()

    # 6. ok
    # ok()

    # 7. clean
    # clean()

    # 8. notok
    # notok()

    # 9. 下载文件
    # download_file("sample.xlsx", save_to="downloaded_sample.xlsx")

    # 10. 发送告警
    # alert_msg("测试告警", ["13800138000"])

    # print("请取消注释需要调用的函数并执行。")

import os
import queue
import time
import uuid
from asyncio import Future

import pymysql
import uvicorn
import random
from fastapi import FastAPI, File, Form, HTTPException, Depends, UploadFile, status, Body
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from concurrent.futures import ThreadPoolExecutor
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import Request
from agentTools import AgentsTools, ThreadAnayPngWork
import socket
from typing import Optional

# from imgServerState.agentTools import DBTools

# ----------------------------------
executor = ThreadPoolExecutor(max_workers=26)
UPLOAD_DIR = "images"
STATIC_URL  = "/image"          # 对应 GET 路由
API_TOKEN   = "cbf123456."       # 演示用，生产请换 JWT 或 Redis
import sys
PROJECT_DIR=os.path.dirname(os.path.abspath(__file__))#当前文件所在目录
FILES_DIR = PROJECT_DIR+os.path.sep+"files"
webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4"
#-----------------------------------------------
from typing import Union
import requests
os.makedirs(UPLOAD_DIR, exist_ok=True)
app = FastAPI(title="FileSvc", version="1.0.0")
# 允许任何域名、方法、头（测试用，生产按需收窄）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 或 ["chrome-extension://*"] 只允许插件
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)   # 允许 query 里带 token
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
def get_model_key():
    conn = pymysql.connect(
        host='10.255.101.169', port=3306, user='root', passwd='cbf123456.',
        db='ioscar_info', charset='utf8mb4', use_unicode=True
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT `key` FROM `key_info` WHERE `status`=1")
            rows = cur.fetchall()  # 返回 list[dict, ...]
            if rows:
                return random.choice(rows)["key"]  # 随机抽 1 条
            return ""
    finally:
        conn.close()




    # ----------------- 依赖：token 校验 -----------------
def verify_token(
    token: Union[str, None],
    cred: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    优先读 query 参数 ?token=xxx
    其次读 Header Authorization: Bearer xxx
    """
    tok = token or (cred.credentials if cred else None)
    if tok != API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                          detail="Invalid or missing token")
    return tok


@app.post("/retryImage", summary="重试图片")
async def retry_image(imagePath:str,ip:str):
    path=imagePath
    token = get_model_key()
    worker = ThreadAnayPngWork()
    executor.submit(worker.work, token, path, ip,False)
    # 返回可访问的 URL
    return {"url": f"http://{getlocalip()}:8000{STATIC_URL}/test?token={API_TOKEN}"}
def task_callback(fut: Future,path=""):
    try:
        fut.result()  # 获取结果，若任务抛异常会在此处重新抛出
        print(f"任务成功完成（path={path}）")
    except Exception as e:
        print(f"任务执行失败（path={path}）: {e}")
# ----------------- 1. 上传接口 微粒贷 -----------------
@app.post("/upload", summary="上传图片")
async def upload_image(file: UploadFile = File(...), \
                       token: str = Depends(verify_token),\
                       fromIp:str="",
                       request:Request=None):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image allowed")

    ext   = os.path.splitext(file.filename)[1]
    t=time.strftime("%Y%m%d%H%M%S"+str(uuid.uuid4())[:8],time.localtime())
    ip = request.headers.get("X-Real-IP")
    name  = f"{t}{ext}"
    path  = os.path.join(UPLOAD_DIR, name)
    with open(path, "wb") as f:
        f.write(await file.read())
    time.sleep(4)
    # 上传到图片服务器
    # 启动线程处理图片
    worker = ThreadAnayPngWork()
    token=get_model_key()
    future=executor.submit(worker.work, token, path,ip,True)
    future.add_done_callback(task_callback)
    # 返回可访问的 URL
    return {"url": f"http://{getlocalip()}:8000{STATIC_URL}/{name}?token={API_TOKEN}"}
# ⑥ 可选：查看队列长度
@app.post("/excel",summary="测试文件")
async def upload_excel(file:UploadFile=File(...)):
    with open("123.xlsx","wb")as f:
        f.write(await file.read())
    return {"success":True,"status":200}
# ----------------- 2. 访问/下载接口 -----------------
@app.get("/image/{file_name}", summary="查看或下载图片")
async def get_image(file_name: str, token: str = Depends(verify_token)):
    path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.isfile(path):
        raise HTTPException(404, "File not found")
    # FileResponse 会自动处理 mime 类型与 Content-Disposition
    from mimetypes import guess_type
    mime_type, _ = guess_type(path)
    if not mime_type or not mime_type.startswith("image/"):
        raise HTTPException(400, "File is not a valid image")

    # 3. 返回图片（内联展示）
    return FileResponse(
        path,
        media_type=mime_type,  # 指定图片的 MIME 类型
        # 关键：设置 Content-Disposition 为 inline（内联展示）
        headers={
                    "Content-Disposition": f"inline; filename={file_name}"
                }
    )
@app.get("/hello")
def hello():
    # work_list=["10.255.50.51:8000","10.255.50.51:7000",
    #            "10.255.100.202:7000","10.255.100.202:9000",
    #            "10.255.101.169:7000","10.255.101.169:8000"]
    work_list = [
                 "10.255.100.202:7000", "10.255.100.202:9000",
                 "10.255.101.169:7000", "10.255.101.169:8000"]
    for url in work_list:
        targeturl="http://"+url+"/ok"
        resp=requests.get(targeturl)
        print(resp.status_code)

    return {"hello": " ".join(work_list)+"网络连接正常"}
@app.get("/ok")
def do_ok():
    return "ok"
@app.get("/clean")
def clean():
    clean_files("images")
    # clean_files("logs")
def clean_files(path):
    files = os.listdir(path)
    for m in files:
        try:
            os.remove(path+"/" + m)
        except Exception as e:
            print(e)
@app.get("/notok")
def do_ok():
    from agentTools import DBTools
    tool=DBTools()
    msg=tool.get_work_staff()
    del tool
    return "not-ok-%s"%msg

@app.get("/download/{file_name}")
def download_file(file_name: str):
    """
    根据文件名下载文件
    例：http://localhost:8000/download/报告.xlsx
    """
    file_path = os.path.join(FILES_DIR, file_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # FileResponse 会自动处理中文、空格
    return FileResponse(
        path=file_path,
        filename=file_name,  # 浏览器下载时默认显示的名字
        media_type='application/octet-stream'
    )

class AlertIn(BaseModel):
    text: str
    at_mobiles: list = []
@app.post("/alert")
def alert_msg( body:AlertIn):

    body = {
        "msgtype": "text",
        "text": {
            "content": body.text,
            "mentioned_list":  []
        }
    }
    try:
        resp = requests.post(webhook, json=body, timeout=10)
        return resp.json()
    except Exception as e:
        return {"errcode": 1, "errmsg": str(e)}


# ----------------- 3. 启动命令 -----------------
# uvicorn imgServerFastApi:app --reload --host 0.0.0.0 --port 8000
if __name__ == '__main__':
    datainfo=sys.argv
    if len(datainfo)==2:
        uvicorn.run(app, host="0.0.0.0", port=int(datainfo[1]))
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)


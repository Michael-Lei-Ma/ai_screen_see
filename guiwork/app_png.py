# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import requests

app = FastAPI()

# 认证 token
EXPECTED_TOKEN = "cbf123456"

# 保存目录：同目录下的 images 文件夹
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "images"


@app.post("/upload")
async def upload_image(request: Request, token: str = ""):
    # 1) 鉴权
    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    # 2) 检查 content-type
    content_type = request.headers.get("content-type", "")
    if "image/png" not in content_type.lower():
        raise HTTPException(status_code=415, detail="content-type must be image/png")

    # 3) 读取原始 PNG 字节
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty body")

    # 4) 创建目录并保存文件
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}.png"
    file_path = SAVE_DIR / filename

    with open(file_path, "wb") as f:
        f.write(body)

    return JSONResponse(
        {
            "success": True,
            "message": "upload ok",
            "filename": filename,
            "file_path": str(file_path),
            "size": len(body)
        }
    )

#
# "filename": filename,
# "file_path": str(file_path),




if __name__ == "__main__":
    # 先启动服务：
    #   python app_png.py
    #
    # 然后另开一个窗口执行测试：
    #   python app_png.py test
    # import sys
    #
    # if len(sys.argv) > 1 and sys.argv[1].lower() == "test":
    #     test_upload()
    # else:
    uvicorn.run(app, host="0.0.0.0", port=8001)
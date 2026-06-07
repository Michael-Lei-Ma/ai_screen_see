# -*- coding: utf-8 -*-
from pathlib import Path
import time
import requests
from .format_config import AlertTools

class MagicCubeAPI:

    @staticmethod
    def upload(url:str,file_path: str | Path, metadata_id: str, text,logger) -> None:
        """
        上传文件到 DMC 导入接口
        :param url: 魔方上传路径
        :param file_path: 本地文件绝对/相对路径
        :param metadata_id: 接口必填参数 dataFileMetadataId
        :param token: 若不传则使用类里默认的 Bearer token
        :return: requests.Response 对象（可 .status_code / .text / .headers 继续检查）
        """
        try:

            file_path = Path(file_path)

            if not file_path.exists():
                logger.error(f"{text}-文件不存在: {file_path}")
                return

            if file_path.stat().st_size == 0:
                logger.error(f"{text}-文件大小为 0，终止上传")
                return

            url = url.format(metadata_id=metadata_id)
            headers = {
                "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1laWRlbnRpZmllciI6IjkwMDQiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoiY2JjYmoueHVsYWkiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9naXZlbm5hbWUiOiLorrjmnaUiLCJFbXBsb3llZUNvZGUiOiJCSjE3MDU1MDYiLCJVbml0SWQiOiIzMTciLCJVbml0TmFtZSI6IuWNjuedv-aZuu-8iOWMl-S6rO-8ieenkeaKgOaciemZkOWFrOWPuCIsIkdyb3VwSWQiOiI0NTUwIiwiR3JvdXBOYW1lIjoi5pWw5o2u5YiG5p6QIiwiT3JnYW5pemVSb2xlVHlwZU5hbWUiOiJPdGhlckZ1bmNEaXJlY3RvciIsInRlbmFudGlkIjoiMjBjMmFmMzUtNDNkMy01NGY0LTI4MGYtM2EwMmY1MDA5MjUwIiwiVGVuYW50TmFtZSI6IuaWkemprCIsIlBlcm1pc3Npb25TeXN0ZW1OYW1lIjoiWmVicmEuV2ViIiwiSXAiOiI6OjEiLCJDYXRlZ29yeSI6ImQwZDM4YWM5LTNmZmEtNDZiOS1iOGQ2LTE5Y2YwNmQzMDJjOCw0ZTQyMDlhNi02NDFhLTQ0ZDAtODFhNC01YWJiNmIzMGYxODEsNGU0MjA5YTYtNjQxYS00NGQwLTgxYTQtNWFiYjZiMzBmMTgxIiwiVmlld1JhbmdlVHlwZSI6IjEiLCJDYW5WaWV3VW5pdHMiOiIxODU5LDQ2OCw1NDQsMjE5MiwzNjY0LDE2NTQsMTI5OCw0Nzc3LDE4NDIsMTg0MSwyNDIxLDQ3MiwzNjY3LDUxNiw0NzYsNDgwLDQ4NCw0ODgsNDgzOSwxNDQ1LDQ5Miw0OTYsNjE0LDU1Miw1MDAsMzk0MiwxODQ2LDQwMzcsNDc4Myw1MDQsNTA4LDYxOSw1NDgsMzg4NSw1MTIsMzY1OCw1MjgsNTIwLDEzMDUsMTkyNyw0NTMzLDQyNTMsNDYxLDQ2NDgsMTMzMiw0NjQ5LDIxMDEsMjY4MywxNDQ3LDQ3NzAsNTMyLDM5NDgsMjIxNSwxMzMwLDQ0NzYsMzk5Niw0ODIyLDMxNyw0MjIzLDQwOTAsNDI2Niw0MjY1LDQxMDAsNDAzOSwxODI5LDM5ODEsNDI3MiwxODkxLDQyNzMsNDI1MCw0MjUyLDQyNDYsNDI0Nyw0MjUxLDQyNDUsNDE5NSwxMzIzLDI0NTQsNDE1MCw0MTQxLDQxMTYsMzI5OSw0Mjc5LDQyMzgsNDI3NSw0MDQwLDM4OTEsNDI3MCwzOTA4LDQyNjksMzkwMSw0NzY5IiwiU3BlY2ljYWxQcm9wZXJ0aWVzIjoiVmlld0FsbERhdGFGaWxlLFZpZXdBbGxEYXRhLFZpZXdDYXRlZ29yeURhdGFNYWdpY0N1YmUiLCJleHAiOjE5MjAxODk0NDF9.tJKjeKUiLT0aSGjMFIGumsIC-4_mxKagNOJ4sRxNaBg"
            }
            time.sleep(3)
            retry_count = 0
            # 调用接口请求失败重试3次
            while retry_count < 3:
                # 构造 form-data：Postman 里 key = file，value = 二进制文件
                with open(file_path, "rb") as f:
                    files = {"file": (Path(file_path).name, f, "application/octet-stream")}
                    logger.info(f"{text}-API 请求前入参信息 url: {url}\nheaders: {headers}\nfiles: {files} ")
                    resp = requests.post(url, headers=headers, files=files, timeout=60, verify=False)
                logger.info(f"{text}-API 请求后响应结果 状态码: {resp.status_code}\n响应头: {resp.headers}\n响应结果: {resp.content}\n{resp.text}\n")
                if resp.status_code == 204:
                    logger.info(f"{text}-文件上传成功")
                    AlertTools.send_robot(f"{text}-上传完毕",text,logger)
                    break
                else:
                    retry_count += 1
                    logger.info(f"第 {retry_count} 次 {text}-文件上传失败")
                    if retry_count == 3:
                        AlertTools.send_robot(
                            f"尝试 {retry_count} 次，{text}-文件上传失败，调用服务 {resp.status_code}，请人工查看！",text,logger)
                    time.sleep(10)
                    continue
        except Exception as e:
            logger.error(f"文件上传异常-{e}")
            AlertTools.send_robot(f"{text}-上传失败",text,logger)
            return
        return None
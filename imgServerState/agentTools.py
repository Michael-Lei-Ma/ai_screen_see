import base64
import time
from uuid import uuid4

from PIL import Image
import os
import json
import pymysql, re
keywrods = ""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
from recordPngInfo import  send_robot
import requests,socket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

STATIC_URL  = "/image"
API_TOKEN   = "cbf123456."
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
LOCALIP=getlocalip()
def get_logger(name: str = "demo"):
    """返回一个同时写控制台 + 滚动日志文件的 logger"""
    logger = logging.getLogger(name)
    if logger.hasHandlers():  # 避免重复 addHandler
        return logger
    logger.setLevel(logging.DEBUG)  # 全局最低级别

    # ---------- 1. 控制台 ----------
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)  # 控制台只看 INFO 及以上
    console_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(name)s | %(lineno)d | %(threadName)s | %(message)s ",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # ---------- 2. 每天滚动日志文件 ----------
    # when="midnight" -> 每天 0 点切；interval=1 -> 间隔 1 天
    file_handler = TimedRotatingFileHandler(
        filename=f"logs/{name}.log",  # 会自动创建 logs 目录
        when="midnight",
        interval=1,
        backupCount=5,  # 只留最近 5 份
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


os.makedirs("logs", exist_ok=True)
log = get_logger("trade")
##################################### session #####################################
session = requests.Session()
adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200, max_retries=Retry(total=3, backoff_factor=1))
session.mount("http://", adapter)
session.mount("https://", adapter)
# 千问大模型名称 qwen-vl-max-latest  qwen3.6-plus
qianwen_model = "qwen3.6-plus"

def stream_request(url, headers, payload):
    print("请求体大小:", len(payload) / 1024, "KB")
    with session.post(url, headers=headers, json=payload, timeout=(100,1800), stream=True) as resp:
        content_pieces = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            chunk = line[6:]
            if chunk == "[DONE]":
                break
            try:
                id= json.loads(chunk).get("id","")
                # delta = json.loads(chunk)["choices"][0]["delta"].get("content")
                if json.loads(chunk)["choices"]:
                    delta = json.loads(chunk)["choices"][0]["delta"].get("content")
                else:
                    continue
                if delta:
                    content_pieces.append(delta)
            except Exception as e:
                print(e)
                import traceback
                traceback.print_exc()
                continue
        return id,"".join(content_pieces)

class PicUtils:
    @classmethod
    def crop_left_third_and_enlarge(cls, input_image_path, output_image_path=None, scale_factor=3):
        """
                将图片切割为左侧1/3部分，然后放大指定倍数并保存

                参数:
                    input_image_path: 输入图片的路径
                    output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                    scale_factor: 放大倍数，默认为3
                """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            new_width = int(width / 3)*1
            crop_region = (0, 0, new_width, height)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_left_third_enlarged{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存左侧1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def enlarge_whole(cls, input_image_path: str,
                      output_image_path="",
                      scale_factor: int = 3) -> str:
        """
        整张图等比放大指定倍数

        参数:
            input_image_path: 原图路径
            output_image_path: 输出路径，默认在原文件名后加 "_x3"
            scale_factor: 放大倍数，默认 3
        返回:
            输出图片绝对路径
        """
        with Image.open(input_image_path) as img:
            w, h = img.size
            new_size = (w * scale_factor, h * scale_factor)
            enlarged = img.resize(new_size, Image.LANCZOS)

            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_x2{ext}")

            enlarged.save(output_image_path)
            log.info(f"已保存整张放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def crop_1_3_card_img(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                将图片切割为左侧1/3部分，然后放大指定倍数并保存

                参数:
                    input_image_path: 输入图片的路径
                    output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                    scale_factor: 放大倍数，默认为3
                """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            middle_width = width / 3
            crop_region = (middle_width, height/2, middle_width*2, height)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_卡号_enlarged{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存左侧1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path
    @classmethod
    def crop_1_3_eventid_img(cls, input_image_path, output_image_path=None, scale_factor=3):
            """
                    将图片切割为左侧1/3部分，然后放大指定倍数并保存

                    参数:
                        input_image_path: 输入图片的路径
                        output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                        scale_factor: 放大倍数，默认为3
                    """
            """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存
    
                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
            # 打开图片
            with Image.open(input_image_path) as img:
                # 获取图片原始尺寸
                width, height = img.size

                # 步骤1：切割左侧1/3
                crop_region = (0, height/6*1, width/5, height/3*1.28)  # (left, upper, right, lower)
                cropped_img = img.crop(crop_region)

                # 步骤2：放大图片（使用高质量缩放算法）
                cropped_width, cropped_height = cropped_img.size
                enlarged_width = cropped_width * scale_factor
                enlarged_height = cropped_height * scale_factor

                # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
                enlarged_img = cropped_img.resize(
                    (enlarged_width, enlarged_height),
                    resample=Image.LANCZOS
                )

                # 处理输出路径
                if not output_image_path:
                    dir_name, file_name = os.path.split(input_image_path)
                    name, ext = os.path.splitext(file_name)
                    output_image_path = os.path.join(dir_name, f"{name}_微粒贷号_enlarged{ext}")

                # 保存处理后的图片
                enlarged_img.save(output_image_path)
                log.info(f"已保存左侧1/3并放大{scale_factor}倍的图片至: {output_image_path}")
                return output_image_path

    @classmethod
    def corp_1_3_org(cls,input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            middle_width = width / 4
            crop_region = (middle_width, 0, middle_width*2, height / 10*4)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_组织信息_larged{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def corp_1_3_gongan(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            middle_width = width / 6
            crop_region = (middle_width, 0, middle_width * 2*1.2, height / 10 * 4)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_公安信息_larged{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def corp_1_3_userinfo(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            middle_width = width / 6
            crop_region = (0, 0, middle_width * 2 * 1.2, height / 10 * 4)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_用户信息_larged{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path
    @classmethod
    def corp_1_3_phone_or_address(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            crop_region = (width/2*1.3,0, width, height*0.9)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_电话信息{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def corp_1_3_caiwu(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            crop_region = (width / 3 ,height/9*2, width/4*3, height / 10*7)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_财务_enlarged{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def corp_1_3_cuishouyuan(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                                  将图片切割为左侧1/3部分，然后放大指定倍数并保存

                                  参数:
                                      input_image_path: 输入图片的路径
                                      output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                                      scale_factor: 放大倍数，默认为3
                                  """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            crop_region = (width / 5, height / 9, width / 3, height / 3*1.1)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_催收员_enlarged{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def corp_1_3_person_card(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                                  将图片切割为左侧1/3部分，然后放大指定倍数并保存

                                  参数:
                                      input_image_path: 输入图片的路径
                                      output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                                      scale_factor: 放大倍数，默认为3
                                  """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            crop_region = (width / 4*0.5, height/9, width / 3*1.4, height / 3*1.2)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_身份证_{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def corp_1_3_work_address(cls, input_image_path, output_image_path=None, scale_factor=2):
        """
                          将图片切割为左侧1/3部分，然后放大指定倍数并保存

                          参数:
                              input_image_path: 输入图片的路径
                              output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                              scale_factor: 放大倍数，默认为3
                          """
        """
                                  将图片切割为左侧1/3部分，然后放大指定倍数并保存

                                  参数:
                                      input_image_path: 输入图片的路径
                                      output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                                      scale_factor: 放大倍数，默认为3
                                  """
        """
                      将图片切割为左侧1/3部分，然后放大指定倍数并保存

                      参数:
                          input_image_path: 输入图片的路径
                          output_image_path: 输出图片的路径，默认为在原文件名后加"_left_third_enlarged"
                          scale_factor: 放大倍数，默认为3
                      """
        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            crop_region = (
            width / 4 * 0.7, height / 9 *2, width / 3 * 1.6, height / 4 *1.8)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_工作单位_{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path

    @classmethod
    def corp_1_3_hook_address(cls, input_image_path, output_image_path=None, scale_factor=2):
        """



                                  """

        # 打开图片
        with Image.open(input_image_path) as img:
            # 获取图片原始尺寸
            width, height = img.size

            # 步骤1：切割左侧1/3
            crop_region = (
                width / 4 * 0.7, height / 9 * 2.5, width / 3 * 1.6, height / 3 * 1.6)  # (left, upper, right, lower)
            cropped_img = img.crop(crop_region)

            # 步骤2：放大图片（使用高质量缩放算法）
            cropped_width, cropped_height = cropped_img.size
            enlarged_width = cropped_width * scale_factor
            enlarged_height = cropped_height * scale_factor

            # 使用LANCZOS算法保持放大后的清晰度（适合照片和文本）
            enlarged_img = cropped_img.resize(
                (enlarged_width, enlarged_height),
                resample=Image.LANCZOS
            )

            # 处理输出路径
            if not output_image_path:
                dir_name, file_name = os.path.split(input_image_path)
                name, ext = os.path.splitext(file_name)
                output_image_path = os.path.join(dir_name, f"{name}_户籍地址_{ext}")

            # 保存处理后的图片
            enlarged_img.save(output_image_path)
            log.info(f"已保存中间1/3并放大{scale_factor}倍的图片至: {output_image_path}")
            return output_image_path
class ThreadAnayPngWork:

    def work(self,token,file_path,ip,default=True):
        try:
            self.ip = ip
            self.token = token
            self.filePath = file_path
            self.uuid = str(uuid4())
            agentsTools = AgentsTools(self.token, self.ip)
            dbtools = DBTools(file_path)
            if default:
                dbtools.saveImagePath(self.uuid,ip, agentsTools)

            leftPic = PicUtils.crop_1_3_eventid_img(self.filePath, scale_factor=3)
            # fPatg=self.filePath=PicUtils.enlarge_whole(self.filePath, scale_factor=2)
            agentsTools.upload_image_base64(self.filePath, leftPic, "注意:微粒贷号优先从第二个图片中提取", self.uuid)
        except Exception as e:
            import traceback
            #提取当前异常的调用栈
            stack = traceback.extract_tb(e.__traceback__)
            # 最顶层（最后一步）
            top = stack[-1]
            brief = f"{top.filename}:{top.lineno} 发生 {type(e).__name__}: {e}"
            traceback.print_exc()
            log.error(f"报警{brief}")
            send_robot("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                       "程序错误:"+brief+"-"+file_path)


class AgentsTools:
    def __del__(self):
        self.cur.close()
        self.conn.close()

    def __init__(self, api_key: str,ip:str):
        self.api_key = api_key
        self.conn = pymysql.connect(host='10.255.101.169', port=3306, user='root', passwd='cbf123456.',
                                    db='ioscar_info', charset='utf8')
        self.cur = self.conn.cursor()
        self.fromip=ip
    def add_key_workd(self,data):
        if "组织" in data:
            if "," in data["组织"]:
                value = data["组织"] = data["组织"].split(",")[-1]
                data["area"] = value
                return
            if "_" in data["组织"]:
                value=data["组织"]=data["组织"].split("_")[-1]
                data["area"]=value
                return
            data["area"] = data["组织"]
    def getcardpromot(self):
        return  """
            请识别图中卡号下面第一列的不带*号数字,输出以json格式返回,json的key必须是中文且必须是"卡号",没有数字类型的卡号就为空字符即可,不做任何解释
        """
    def geteventidpromot(self):
        return  """
            请识别图中的微粒贷号,输出以json格式返回,json的key必须是中文且必须是"微粒贷号",不做任何解释
        """
    def getorgpromot(self):
        return """
                【任务】
                从图中识别并提取以下字段，只输出 JSON 字符串，不输出任何解释。
                【字段】
                - 组织下第一个公司名称（在「组织」字段下方，第一个公司名）
                - 组名（在「公司」字段以_或者,逗号等隔开的是第一个组织）
                【格式】
                {"公司名称": "xxx", "组织": "xxx"}
                【注意】
                - 如果字段不存在，返回空字符串 "";
                - 如果字段存在且有名字，返回第一个名字。
                - 公司名称的值是必须包含公司两个汉字的，
                -  组织它是以_或者逗号之类的分隔符后面隔开的第一个组织,不要遗漏地域信息,文字要获取完整不要遗漏,
                【关键点】
                - 换行后的文字也要获取完整,不要遗漏,例如众二组等在第二行的文字。
        """

    def getPhonepromot(self):
        return """
               请识别图中电话信息,输出以json格式返回,json的key必须是中文且必须是"电话信息",不论几个电话信息格式都是{"电话信息":[{"姓名":"","电话号码":"XXX"}]},不做任何解释
           """
    def get_person_card(self):
        return """
               请识别图中客户信息中的身份证号,输出以json格式返回,json的key必须是中文且必须是"身份证",不做任何解释
              """
    def getaddresspromot(self):
        return """
               请识别图中地址内容,输出以json格式返回,json的key必须是中文且必须是"地址内容",抓取所有的地址内容放到一个字符串用,号隔开,为空的不显示,不做任何解释
              """

    def getzhangwupromot(self):
        return """
                      请识别图中账务信息,输出以json格式返回,json的key必须是中文且必须是"账务信息",必须包含字段账单日、首次借款日期、案件类型、信用额度、最近还款日期、最近还款金额、账龄、委托金额、委托本金、委托日期、委托到期日、手别。为空的不显示,不做任何解释
                     """

    def getpromot(self):
        return """
        【任务目标】
            你现在是一名拥有20年经验的资深催收专员，精通国内主流信贷系统界面（如微粒贷、招联、平安等），具备极强的视觉识别能力与业务逻辑判断力。你必须以最高标准执行以下任务。根据给你发送的图片内容,识别并提取指定字段，仅输出 JSON 字符串，不输出任何解释。
        【场景判断逻辑】
            获取到图片后首先判断图片中 重要信息 基础信息 案件流转记录 这3个标签字段哪个是高亮的
            若界面中包含"客户信息"四个字，则按照场景1的规则要求提取相关内容。
            若“基础信息”标签字段被高亮，则按照场景2的规则要求提取相关内容。
            若界面中包含"催收员"三个字，则按照场景3的规则要求提取相关内容。
            每个图片的对应的3个场景互斥，仅执行一个。
        【场景 1：重要信息字段高亮】  
          触发条件：该催收图片中“重要信息” 标签字段高亮。
        【规则要求】
        1. 所有信息必须基于图片内容提取，禁止推测、补全或联想。
        2. 字段提取必须严格遵循“标签+值”的对应关系，且仅在标签正下方或同列右侧区域提取。
        3. 若存在多个相同标签（如“账龄”），必须根据其所在模块（如“账务信息”）及上下文进行唯一性确认。
        4. 数值类字段必须为纯数字，若含字母、符号、空格则视为无效。
        5. 特殊字段需按如下规则处理：
           - “案件类型”：仅允许取值为：“普通委外”、“专项3”、“专项”，否则为空。
           - "手别"：仅允许取值为“一手”、“二手”,"三手","长账龄","三手+"，否则为空。
           -  不要把账单日的数值赋值给账龄,他俩是不同的数值。
           -  不要把最近还款日期赋值给账单日,账单日是数字.
        6. 当出现多行同类数据时（如电话信息），应完整保留所有条目，包括姓名、号码【不能有中文】、状态、操作按钮。
        7. 地址信息：只提取右侧“地址信息”模块中所有地址文本，用逗号连接。
        8. 微粒贷信息：必须包含微粒贷号、逾期总金额、结清金额、逾期总本金、逾期总利息、逾期总罚息、是否治愈/出催、催收阶段、逾期天数、入催日期、历史逾期次数、上次出催日期
           -微粒贷号位于微粒贷三个字旁边，首先
           -先数一遍总字符数（2 字母 + 24 数字 = 26 位
           -再按位读出：D-S-0-9-9-9-9-6-0-5-7-1-1-8-5-7-7-9-2-0-2-5-0-7-1-5
           -确认无误后再提取吧
           -凡是遇到 1111 四个连续 1,必须放大该区域逐位朗读，确认四位 1 全部存在后再提取，不得漏位！
            注：微粒贷中的金额不得写入账务信息。
        9.  客户信息提取注意点：
             - 身份证必须以四位数字开头（如4401****），否则忽略。
             - 手机号必须以“1”开头，共 11 位数字，或者带*,不能包含文字信息。
             - 工作单位按照图片信息提取即可,如果没有值则为空字符串.
             - 识别字段必须包括为姓名、年龄、婚姻状态、身份证、工作单位、单位地址、通讯地址、户籍地址、户籍地址2、学历、绑卡手机归属地、
        10. 账务信息：必须按照以下顺序 
                账单日、首次借款日期、案件类型、信用额度、最近还款日期、最近还款金额、账龄、委托金额、委托本金、委托日期、委托到期日、手别。
                其中“委托金额”不能为空。
        11. 还款指引【必须做】：
            1. 卡号若以数字“8”开头，则必须同时满足：
               a. 固定前缀：80000  （共 5 位，第 1 位 8，第 2-5 位 0000）；  
               b. 总长度：16 位，不能 15 也不能 17；  
               c. 正则：^80000\d{11}$  
            2. 识别后先放大 3 倍，再逐位朗读：8-0-0-0-0-3-2-1-4-1-6-6-0-5-0-2，确认第 6 位开始是“3”而不是“2”或空；  
            3. 若读到 8000xxxxxx（少 1 位 0）或 800003xxx（总长度≠16），一律在该字段返回空字符串 ""，并提示“8 开头卡号格式错误”。  
            4. 反面案例禁止输出：  
               错误：800032141660502   （少 1 个 0，共 15 位）  
               正确：8000032141660502  （16 位，80000 开头）
            5.一定要识别还款类型为转账还款的信息旁边的卡号
        12.当电话信息字体高亮的时候才提取电话信息(如果图片右边包含姓名,电话号码,则抓取否则不抓取)
        【输出格式】
        仅输出 JSON 字符串，无任何解释、注释或额外内容。
        ---  
        【场景 2：基础信息字段高亮】  
          触发条件：图片中“基础信息”标签字段高亮。
        提取要求：
        1. 必须提取：
           - 公安户籍信息
           - 当电话信息字体高亮的时候才提取电话信息(如果图片右边包含姓名,电话号码,则抓取否则不抓取),电话信息格式必须为{"电话信息":{"姓名":"XX","电话号码":"XX"}}或者
             {"电话信息":[{"姓名":"XX","电话号码":"XX"}]}
           - 当地址信息字体高亮的时候才提取地址内容(如果图片右边包含地址内容,则抓取所有的地址内容放到一个字符串用,号隔开,否则不抓取)
           - 微粒贷信息（必须字段：微粒贷号）
           - 注意事项:从第二个图片仅仅识别微粒贷号
           注：微粒贷中的金额不得写入账务信息。
        2. 不提取：账务信息。
        
        【场景 3：案件流转记录字段高亮】  
          触发条件：图片中“案件流转记录”字段高亮或者图片信息中包含"催收员"三个字体。
          提取要求：
          1. 必须提取：
             - 当电话信息字体高亮的时候才提取电话信息(如果图片右边包含姓名,电话号码,则抓取否则不抓取)
             - 当地址信息Tab高亮的时候提取地址内容（如果图片右边包含地址内容,则抓取所有的地址内容放到一个字符串用,号隔开,否则不抓取）
             - 催收员(催收员姓名在一个表格中的第一行第二列催收员列,如果没有找到则该字段为空字符串)
             - 组织（取表格中的第一行第3列,只取第一个组织信息,有催收员务必要有组织信息）
             - 微粒贷信息（必须字段：微粒贷号、结清金额、逾期总本金、逾期总利息、逾期总金额、逾期总罚息、催收阶段、逾期天数、入催日期、历史逾期次数、上次出催日期、是否治愈/出催）
         2 禁止提取:客户信息以及身份证
        ---  
        【通用校验规则】
            - 所有日期格式：YYYY-MM-DD
            - 所有金额：元，保留两位小数
            - 逾期天数：整数
            - 不可见字段留空字符串 ""，不得省略
            - 禁止输出任何注释、Markdown、代码块标记
            - 催收员并不是客户信息里面的那个人的姓名
        ---  
        【微粒贷号硬性提取规则】（★务必按顺序执行★）
        1. 微粒贷号务必从第二个图片中进行识别提取
        2. 微粒贷号位于图中微粒贷三个字的旁边,以DS开头,后面结合了24位数字，一个也不能少
        【微粒贷信息提取规则】
        1.必须提取图片中的微粒贷信息,它是单独的key,不得有遗漏.且不能在客户信息的json中出现.
        【账务信息硬核闸门】
            必提字段（共 13 项）因为图片中是一定有信息的需要认真仔细识别：
            账单日、首次借款日期、案件类型、信用额度、最近还款日期、最近还款金额、账龄、委托金额、委托本金、委托日期、委托到期日、手别。
            校验逻辑（逐项执行）：
            账龄是数字并不包含任何字母,账龄必须是一个整数
            账龄和账单日是2个不同的数据
            b. 若字段名存在，但对应值为以下任一无意义占位 →
            ""、"--"、"/"、"无"、"null"、"NULL"、" "、纯空格 →
            全部通过后方可继续后续 JSON 组装；否则一直重读图片（最多 30 次），30次仍失败 →
            返回json,字段可以为空
        ---【还款指引硬核阀门】 
            卡号提取的结果如果是80000开头的那么就应该是80000注意不要少0或者多0,并且80000开头的卡号必须是16位
        ------  
        【输出格式】  
        仅输出 JSON 字符串，示例：  
        场景 1：{"客户信息":{"姓名":"张三"},"账务信息":{"账龄":"12","账单日":"2025-08-01"},"微粒贷信息":{"微粒贷号":"DS000000000000000000000000","逾期天数":90}}  
        场景 2：{"公安户籍信息":{"曾用名":"","民族":"汉族","住址":"湖南省长沙市"},"地址内容":"深圳市南山区,XXXX"},"微粒贷信息":{"微粒贷号":"DS000000000000000000000000"},"工作信息":{"获取时间":"2025-08-01"，"工作单位":"XX"}}
        场景 3：{"催收员":"王红","地址内容":"深圳市南山区,XXXX"},"组织":"XXXXX","微粒贷信息":{"微粒贷号":"DS000000000000000000000000"}}
        
        
        """
    def upload_image_base64(self, image_path, originImgPath,msg,uuid):
        """
        上传图片 url 到数据库 不会进行放大的
        """
        # 2. 请求
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [image_path,originImgPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.getpromot() + msg
                      }
                     ]
                 }
            ]
        }
        docdata=""
        data={}
        name=os.path.basename(image_path)
        self.uploadUrl=f"http://{getlocalip()}:8000{STATIC_URL}/{name}?token={API_TOKEN}"
        for i in range(3):
            event_id = ""
            try:
                event_id,docdata = stream_request(url, headers, payload)
                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", docdata,
                                   flags=re.S).strip()
                log.info("第"+str(i+1)+"模型最终识别的json字符串为::"+cleandata)
                if "`" in docdata or 'json' in docdata:
                    match = re.search(r'\{.*\}', docdata, re.DOTALL)
                    docdata = match.group(0) if match else ''
                    data = json.loads(docdata)
                if  self.retry_record(data):
                    break
                log.info("识别有误,需要重试%s"%data)
            except Exception as e:
                time.sleep(2)
                import traceback
                traceback.print_exc()
                if i==5:
                    send_robot(
                        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                        "大模型获取重试json失败,请检查,错误信息:" + str(e)+"第"+str(i+1)+"次-事件id:"+event_id+",识别结果:"+docdata+
                    self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
        key = self.get_weili(data)
        tools = DBTools(image_path)
        if key:
            ###关键信息校验
            log.info("第一个图片:" + key)  # 微粒贷号校验
            # if len(key)!=26 and not key.startswith("DS09999"):
            #     key = key[:8] + '9' + key[8:]
            #     data["微粒贷信息"]["微粒贷号"] = key
            # elif len(key) != 26 and key.startswith("DS09999"):
            for i in range(5):
                log.info("微粒贷信息:%s,长度:%s" % (key,len(key)))
                log.info("重新识别第" + str(i + 1) + "次,进行中")
                path=PicUtils.crop_1_3_eventid_img(image_path)#仅仅扣出来微粒贷号
                eventId=self.upload_image_to_eventid(path)
                if len(eventId) == 26:
                    key = eventId
                    data["微粒贷信息"]["微粒贷号"] = eventId
                    log.info("模型识别到的微粒贷号为:%s" % eventId)
                    break
            data["卡号"] = ""
            rebackcard=self.getrebackcard(data)#还款指引号
            if rebackcard:
                data["卡号"] = rebackcard  # 够了的情况
                path = PicUtils.crop_1_3_card_img(image_path)#仅仅扣出来卡号
                for i in range(1):
                    card=self.upload_image_to_getcard(path)
                    log.info("千问再次识别:"+str(card))
                    log.info("千问识别卡号:%s,长度是:%s,旧的卡号:%s,长度是:%s" % (card,len(card),rebackcard,len(rebackcard)))
                    if card!='' and card.isdigit():
                        data["卡号"] = card
            elif rebackcard=='':
                path = PicUtils.crop_1_3_card_img(image_path)  # 仅仅扣出来卡号
                for i in range(1):
                    card = self.upload_image_to_getcard(path)
                    log.info("千问再次识别:" + str(card))
                    log.info("千问识别卡号:%s,长度是:%s,旧的卡号:%s,长度是:%s" % (
                    card, len(card), rebackcard, len(rebackcard)))
                    if len(card)>10 and card.isdigit():
                        data["卡号"] = card
            if "电话信息" in data:
                telInfo=data.get("电话信息")
                goodList=[]
                if isinstance(telInfo,dict):pass
                if isinstance(telInfo,list):
                    if len(telInfo)>1:
                        firstInfo = telInfo[0]
                        if isinstance(firstInfo, list):
                            for item in telInfo:
                                obj = {}
                                obj["姓名"] = item[0]
                                obj["电话号码"] = item[1]
                                goodList.append(obj)
                            data["电话信息"] = goodList
                    else:
                        del data["电话信息"]
            ##判断识别不到催收员的场景
            if "客户信息" not in data and "催收员" not in data and "公安" not in data:
                path=PicUtils.corp_1_3_cuishouyuan(image_path)
                cuishouyuan=self.upload_image_to_cuishouyuan(path)
                if cuishouyuan!="":
                    data["催收员"]=cuishouyuan
                    data["组织"]=""
            if "催收员" in data:
                path = PicUtils.corp_1_3_cuishouyuan(image_path)
                cuishouyuan = self.upload_image_to_cuishouyuan(path)
                if cuishouyuan != "":
                    data["催收员"] = cuishouyuan
                    data["组织"] = ""
                    data["卡号"]=""
                path = PicUtils.corp_1_3_phone_or_address(image_path)
                address = self.upload_image_to_address(path)
                if address!=[] and address != "":
                    data["地址内容"] = address
            if "组织" in data:
                log.info("开始放大组织")
                path=PicUtils.corp_1_3_org(image_path)
                org=self.upload_image_to_org(path)
                data["组织"]=org
            if "客户信息" not in data:
                path=PicUtils.corp_1_3_gongan(image_path)
                gongan=self.upload_image_to_gongan(path)
                if "没有" in gongan:
                    #再次进行补录客户信息,没有公安 没有催收员 没有客户信息
                    if "催收员" not in data:
                        path = PicUtils.corp_1_3_userinfo(image_path)
                        customer = self.upload_image_to_customer(path)
                        if customer!="":
                            data["客户信息"]=customer.get("客户信息")
                else:
                    data["公安信息"]=gongan.get("公安户籍信息","")
            if "电话信息" in data:
                path = PicUtils.corp_1_3_phone_or_address(image_path)
                phone = self.upload_image_to_phone(path)
                data["电话信息"] = phone
            if "电话信息" not in data and "客户信息" in data:
                path = PicUtils.corp_1_3_phone_or_address(image_path)
                phone = self.upload_image_to_phone(path)
                data["电话信息"] = phone
                if phone==[]:# 没有电话信息就说明是地址内容
                    path = PicUtils.corp_1_3_phone_or_address(image_path)
                    address = self.upload_image_to_address(path)
                    if address != [] and address != "":
                        data["地址内容"] = address
            if "客户信息" in data:
                path=PicUtils.corp_1_3_caiwu(image_path)
                zhangwu = self.upload_image_to_caiwu(path)
                data["账务信息"] = zhangwu
                path2=PicUtils.corp_1_3_person_card(image_path)
                person_card=self.upload_image_to_personcard(path2)
                data["客户信息"]["身份证"]=person_card
                path3=PicUtils.corp_1_3_work_address(image_path)
                work_address=self.upload_image_to_work_address(path3)
                keyA=work_address.get("工作单位","")
                if keyA!='':
                    data["客户信息"]["工作单位"]=keyA
                keyB=work_address.get("单位地址","")
                if keyB:
                    data["客户信息"]["单位地址"]=keyB
                path3 = PicUtils.corp_1_3_hook_address(image_path)
                work_address = self.upload_image_to_hook_address(path3)
                data["客户信息"]["户籍地址"] = work_address.get("户籍地址", "")
                data["客户信息"]["户籍地址2"] = work_address.get("户籍地址2", "")
                if "地址内容" in data:del data["地址内容"]
            if key == "DS099996057118577920250715":
                log.error("大模型识别错误,没有识别到微粒贷号")
                return
            if "公安户籍信息" in data:
                if "催收员" in data : del data["催收员"]
                if "组织" in data: del data["组织"]
            if "账务信息" in data:
                kZhangWu=data.get("账务信息",{})
                if "委托日期" not in kZhangWu:del data["账务信息"]
            log.info("识别完毕信息开始入库，key=%s"%key)
            log.info(data)
            self.add_key_workd(data)
            money=self.get_money(data)
            if "area" in data:
                tools.insert_or_update_with_area(key, json.dumps(data,ensure_ascii=False),money,data["area"],
                                                 uuid,self.fromip)  # 如果有则进行插入

            else:
                tools.insert_or_update(key, json.dumps(data,ensure_ascii=False),money,uuid,self.fromip)  # 如果有则进行插入
            tools = DBTools(image_path)
            tools.update_image(uuid)
        else:
            send_robot("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                       "没有识别到微粒贷号:"+self.uploadUrl)
        del tools
    def retry_record(self,data):
        if "客户信息" in data:
            weilidai=data.get("微粒贷信息",{})
            customer=data.get("客户信息",{})
            phoneInfo=data.get("电话信息",{})
            moneyInfo = data.get("账务信息", {})
            age=customer.get("年龄","")
            if age=="":
                log.info("客户信息错误:%s" % customer)
                log.info("电话信息错误:%s" % phoneInfo)
                log.info("年龄错误:%s" % age)
                return False
            zling=moneyInfo.get("账龄","")
            zdr=moneyInfo.get("账单日","")
            yqday=weilidai.get("逾期天数","")
            if zling=="" or yqday==zling:
                log.info("账龄错误:%s" % zling)
                log.info("逾期天数错误:%s" % yqday)
                log.info("账单日错误:%s" % zdr)
                return False
            # if isinstance(phoneInfo,[]):
            #     for item in phoneInfo:
            #         phone=item.get("电话号码","")
            #         if phone=="":
            #             return False
        # if "客户信息" not in data and\
        #     "公安信息" not in data and "催收员" not  in data:
        #         return False
        return True
    def upload_image_to_getcard(self,cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.getcardpromot()
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data=""
        cleandata=""
        for i in range(4):
            event_id = ""
            try:
                event_id, data = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", data,
                               flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                time.sleep(2)
                import traceback
                traceback.print_exc()
                if i==3:
                    send_robot(
                        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                        "大模型获取重试卡号json失败,请检查,错误信息:" + str(e) + "第" + str(
                            i + 1) + "次-事件id:" + event_id+cleandata+self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data,dict):
            return data.get("卡号","")
        return ""

    def upload_image_to_org(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.getorgpromot()
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        cleandata=""
        for i in range(3):
            event_id = ""
            try:
                event_id, data = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", data,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试组织json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+cleandata
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            a=data.get("组织","")
            b=data.get("公司名称","")
            if "公司" not in a:
                return a
            return b
        return ""

    def upload_image_to_gongan(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        msg="""
                如果图中有公安户籍这几个汉字,则识别图片中的公安户籍信息,并返回json格式的结果key必须是"公安户籍信息",json字段包括:
                曾用名 民族 籍贯 住址 服务地址,
                如果没有公安户籍信息,则返回{"没有":""}
        """
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": msg
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        cleandata=""
        for i in range(3):
            event_id = ""
            try:
                event_id, data = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", data,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试公安信息json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+cleandata
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data
        return ""
    def upload_image_to_phone(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.getPhonepromot()
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        cleandata=""
        for i in range(3):
            event_id = ""
            try:
                event_id, data = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", data,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试电话信息json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+cleandata
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data.get("电话信息", "")
        return ""
    def upload_image_to_eventid(self,cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.geteventidpromot()
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data=""
        reqData=""
        name = os.path.basename(cardPath)
        self.uploadUrl = f"http://{getlocalip()}:8000{STATIC_URL}/{name}?token={API_TOKEN}"
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                               flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试微粒贷号json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+reqData
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data,dict):
            return data.get("微粒贷号","")
        return ""
    def get_weili(self, dictInfo):
        """
        获取微粒贷信息
        """
        for key in dictInfo:
            if key.startswith("微粒贷"):
                weiliInfo = dictInfo[key]
                for data, value in weiliInfo.items():
                    if data.startswith("微粒贷"):
                        log.info("发现微粒贷信息:%s" % value)
                        if len(value) != 26:
                            log.info("微粒贷信息错误:%s" % len(value))
                        if value:
                            value = value.replace("D5", "DS")
                            return value
                        return ""
        return False
    def getcard(self, dictInfo):
        kData = dictInfo.get("客户信息", {})
        if kData:
            return kData.get("身份证", "")
        return ""
    def get_keyword2(self, dictInfo):
        for key in dictInfo:
            if key.startswith("客户信息2"):
                value = dictInfo.get(key, {})
                if value.get("微粒贷号", ""):
                    data = value.get("微粒贷号", "")
                    log.info("发现微粒贷信息:%s" % value)
                    value = data.replace("D5", "DS")
                    return value
                else:
                    data = value.get("微粒贷信息", "")
                    if data:
                        info = data.get("微粒贷号", "")
                        value = info.replace("D5", "DS")
                        return value
                    return ""

    def get_money(self, data):
        # day1=str(data.get("微粒贷信息",{}).get("逾期天数",""))
        day2 = str(data.get("微粒贷信息", {}).get("历史逾期次数", ""))
        return day2

    def getrebackcard(self, data):
        rebackcard=data.get("还款指引",{})
        if rebackcard:
            if isinstance(rebackcard,list):
                data=rebackcard[0]
                card=data.get("卡号","")
                log.info("识别的卡号是:%s,长度是:%s" % (card,len(card)))
                return card
            else:
                if "转账还款" in rebackcard:
                    reback=rebackcard["转账还款"]
                    if reback:
                        if "卡号" in reback:
                            card = reback.get("卡号", "")
                            return card
                        return reback
                    return ""
                else:
                    card = rebackcard.get("卡号", "")
                    return card
        return ""

    def upload_image_to_address(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.getaddresspromot()
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        reqData=""
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试地址信息json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+reqData
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data.get("地址内容", "")
        return ""

    def upload_image_to_caiwu(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.getzhangwupromot()
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        reqData=""
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试账务信息json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+reqData
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data.get("账务信息", "")
        return ""

    def upload_image_to_cuishouyuan(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        msg="""
            请识别图中催收员字段下的人名信息,输出以json格式返回,json的key是中文且必须是"催收员",只取第一个催收员名字,不做任何解释，
            如果图片中没有催收员则返回空字符串
         """
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": msg
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        reqData=""
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试催收员json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+reqData
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data.get("催收员", "")
        return ""


    def upload_image_to_personcard(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": self.get_person_card()
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        reqData=""
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试身份证号json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+reqData
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data.get("身份证", "")
        return ""

    def upload_image_to_work_address(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        msg="""识别图中的工作单位和单位地址,输出以json格式返回,json的key是中文且必须是"工作单位"和"单位地址",
        单位地址右侧数据为空就显示空字符串,不强制填充文字,不做任何解释"""
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": msg
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        reqData=""
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试工作单位和单位地址json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+reqData
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data
        return ""

    def upload_image_to_hook_address(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        msg = """
        图中同时存在“户籍地址”“户籍地址2”“通讯地址”等多个相似字段。  
        1. 只提取**明确写在“户籍地址”四个字右侧或下方**的那一行内容；**“通讯地址”“单位地址”等任何其他字段即使内容相似也不得误用**。  
        2. 若“户籍地址”四个字右侧或下方**没有任何可见文字、仅留空白或被划掉**，则必须返回空字符串 ""，**严禁用其它地址字段顶替，严禁自行补文字**。  
        3. 同理，只对**明确写在“户籍地址2”四个字右侧或下方**的那一行内容赋值；无文字则返回 ""。  
        4. 最终仅输出如下 JSON，禁止附加任何解释：  
        {"户籍地址":"","户籍地址2":""}
        """
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": msg
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        reqData=""
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试工作单位和单位地址json失败,请检查,错误信息:" + str(e) + "第" + str(
                        i + 1) + "次-事件id:" + event_id+reqData+self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data
        return ""
    def upload_image_to_customer(self, cardPath):
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json"
        }
        images = []
        for p in [cardPath]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }
            })
        msg = """识别图中的客户信息中的姓名,年龄,身份证,工作单位,单位地址,通讯录地址,户籍地址,户籍地址2,学历,绑卡手机归属省,输出以json格式返回,json的key是中文且必须是"客户信息",没有就显示空字符串不做任何解释"""
        payload = {
            "model": qianwen_model,
            "stream": True,
            # 或 qwen-vl-max-latest
            "messages": [
                {"role": "user", "content":
                    images +
                    [{"type": "text", "text": msg
                      }
                     ]
                 }
            ]
        }
        full_text = ""
        data = ""
        reqData=""
        for i in range(3):
            event_id = ""
            try:
                event_id, reqData = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")

                cleandata = re.sub(r"```(?:json)?\n(.*?)```", r"\1", reqData,
                                   flags=re.S).strip()
                log.info(cleandata)
                data = json.loads(cleandata)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试客户信息json失败,请检查,错误信息:" + str(e) + "第" + str(i + 1) + "次-事件id:" + event_id+reqData
                +self.uploadUrl)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return ""
        if isinstance(data, dict):
            return data
        return ""


class DBTools:
    _RE_16_DIGITS = re.compile(r'^\d{16}$')

    def get_connect(self):
        return pymysql.connect(host='10.255.100.202', port=3306, user='root', passwd='123.com',
                                    db='ioscar_info',
                                    charset='utf8mb4', use_unicode=True)
    def __init__(self, image_path=""):
        self.conn = pymysql.connect(host='10.255.100.202', port=3306, user='root', passwd='123.com',
                                    db='ioscar_info',
                                    charset='utf8mb4', use_unicode=True,
                                    max_allowed_packet=64 * 1024 * 1024,  # ★ 与服务器端保持一致
                                    connect_timeout=20,
                                    read_timeout=600,  # ★ 读大结果等待时间
                                    write_timeout=600
                                    )
        self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
        """
            INSERT INTO info_save (`id`,`info`)values("1","234")    
         """
        self.image_path = image_path

    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception as e:
            print(e)
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception as e:
            log.error("数据库关闭失败,错误信息:%s" % e)
    def get_work_staff(self):
        sql="select * from img_table it where check_ok is null"
        self.cursor.execute(sql)
        result=self.cursor.fetchall()
        return "%.2f"%len(result)
    # 洗输入：latin1→utf8mb4
    def safe_loads(self, text: str) -> dict:
        return json.loads(text.encode('latin1').decode('utf8mb4'))

    def get_weili(self, dictInfo):
        """
        获取微粒贷信息
        """
        for key in dictInfo:
            if key.startswith("微粒贷"):
                weiliInfo = dictInfo[key]
                for data, value in weiliInfo.items():
                    if data.startswith("微粒贷"):
                        log.info("入库发现微粒贷信息:%s,长度是:%s" % (value,len(value)))
                        if value:
                            value = value.replace("D5", "DS")
                            return value
                        return ""

    @staticmethod
    def _is_16_digits(s: Optional[str]) -> bool:   # Optional[str] == Union[str, None]
        """必须是 16 位纯数字；None 或空串直接 False。"""
        if not s:                # 同时挡掉 None 与 ''
            return False
        log.info("_is_16_digits======"+s)
        if len(s) != 16:         # 长度先行
            return False
        # 纯数字校验（预编译正则）
        log.info("_is_16_digits====长度==" + str(len(s)))
        log.info("_is_16_digits====jieguo=="+str(bool(DBTools._RE_16_DIGITS.fullmatch(s))))
        return bool(DBTools._RE_16_DIGITS.fullmatch(s))

    def getcard(self, dictInfo):
        kData = dictInfo.get("客户信息", {})
        if kData:
            return kData.get("身份证", "")
        return None
    def getAccountId(self, dict_info: dict) -> str:
        """
        取「还款指引」里第一个 800 开头的卡号。
        合法形态（递归兼容）：
        1. list[dict]  / list[str]
        2. 单个 dict
        3. json 字符串（先 loads）
        """
        raw = dict_info.get("还款指引")
        if raw is None:
            return ""

        # 1. 如果是字符串，先尝试反序列化
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return ""

        # 2. 把单个 dict 包成 list，统一后面逻辑
        if isinstance(raw, dict):
            raw = [raw]

        # 3. 现在只认 list
        if not isinstance(raw, list):
            return ""

        # 4. 遍历 list，元素可能是 dict 或 str
        for item in raw:
            card: Optional[str] = None
            if isinstance(item, dict):
                card = item.get("卡号")
                log.info("账号1：======"+card)
            elif isinstance(item, str):
                card = item
                log.info("账号2：======"+card)
            else:
                continue
            if isinstance(card, str) and card.startswith("800"): 
                log.info("账号3：======"+card)
                return card
        return ""

    def check_card_weilidai(self, info):
        data = json.loads(info)
        weili = self.get_weili(data)
        if len(weili) != 26:
            return 1

        card = self.getcard(data)
        if card!=None:
            if card[:4].find("*") > -1:
                return 2
        # 3. 校验 accountId
        #account_id = self.getAccountId(data)
        #if not self._is_16_digits(account_id):
        #    log.warning("非法 account_id，即将 return 3：%s", account_id)
        #    return 3

        return 0

    def updateInfo(self, infoA, usernameOld, dictB, key):
        username = dictB.get("客户信息", {}).get("姓名", "")
        if dictB.get("客户信息", {}).get("姓名", ""):
            if infoA != '' and infoA == username and usernameOld != username and key == "催收员":
                dictB[key] = usernameOld
                return
            else:
                dictB[key] = infoA
        if key == "账龄":
            if infoA != '' and infoA[0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                if dictB[key]=='':
                    dictB[key] = infoA
                else:
                    pass
                return
        if dictB.get(key,'')=="":
            log.info("更新%s旧的:%s 变为新的:%s" % (key,dictB.get(key,''), infoA))
            dictB[key] = infoA
    def saveImagePath(self,uuid,ip,agentsTools):

        path = PicUtils.crop_1_3_eventid_img(self.image_path)  # 仅仅扣出来微粒贷号
        eventId = agentsTools.upload_image_to_eventid(path)
        sql="insert into img_table(`id`,`image_path`,`ip`,`insert_date`,`card_id`,`from_ip`)values(%s,%s,%s,%s,%s,%s)"
        self.cursor.execute(sql,(uuid,self.image_path,LOCALIP,
                                 time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),
                                 eventId,ip))
        self.conn.commit()
        try:
            self.cursor.close()
            self.conn.close()
            log.info("数据库关闭成功")
        except Exception as e:
            log.error("数据库关闭失败,错误信息:%s" % e)
    def insert_or_update(self, id: str, info: str,money:str,uuid:str,from_ip:str):
        """
        插入或更新数据
        """
        log.info(id[-6:]+" "+str(money))
        # selectSql = "SELECT * FROM info_save WHERE RIGHT(`id`, 6) = %s AND `money` = %s"
        # self.cursor.execute(selectSql, (id[-6:],money))
        # selectSql = "SELECT * FROM info_save WHERE `id` = %s"
        # self.cursor.execute(selectSql, (id,))
        # row = self.cursor.fetchone()
        err_type = self.check_card_weilidai(info)
        if 1==1:
            sql = "INSERT INTO info_save (`id`,`info`,`insert_time`,`err_type`,`img_name`,`money`,`id_unique`,`ip`,`from_ip`) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s)"
            self.cursor.execute(sql, (
            id, info, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), err_type, self.image_path,money,
            uuid,LOCALIP,from_ip))
            self.conn.commit()
            try:
                self.cursor.close()
                self.conn.close()
                log.info("数据库关闭成功")
            except Exception as e:
                log.error("数据库关闭失败,错误信息:%s" % e)

    def insert_or_update_with_area(self, id: str, info: str,money:str,area:str,uuid:str,from_ip:str):
        """
        插入或更新数据
        """
        log.info(id[-6:]+" "+str(money))
        # selectSql = "SELECT * FROM info_save WHERE RIGHT(`id`, 6) = %s AND `money` = %s"
        # self.cursor.execute(selectSql, (id[-6:],money))
        # selectSql = "SELECT * FROM info_save WHERE `id` = %s"
        # self.cursor.execute(selectSql, (id,))
        # row = self.cursor.fetchone()
        err_type = self.check_card_weilidai(info)

        if 1==1:
            sql = "INSERT INTO info_save (`id`,`info`,`insert_time`,`err_type`,`img_name`,`money`,`area`,`id_unique`,`ip`,`from_ip`) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)"
            self.cursor.execute(sql, (
            id, info, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), err_type, self.image_path,money,area,uuid,
            LOCALIP,from_ip))
            self.conn.commit()
            try:
                self.cursor.close()
                self.conn.close()
                log.info("数据库关闭成功")
            except Exception as e:
                log.error("数据库关闭失败,错误信息:%s" % e)



    def dupestr(self,value):
        if "," in value:
            data=value.split(",")
            dData=set()
            for i in data:
                dData.add(i)
            value=",".join(dData)
        return value




    def update_image(self, uuid):
        sql="update img_table set `check_ok`='ok' where `id` = %s or `image_path`=%s"
        self.cursor.execute(sql,(uuid,self.image_path))
        self.conn.commit()
        try:
            self.cursor.close()
            self.conn.close()
            log.info("数据库关闭成功")
        except Exception as e:
            log.error("数据库关闭失败,错误信息:%s" % e)


if __name__ == '__main__':
    start=time.time()
    print(time.time())
    MODEL_TOKEN = "sk-1f6e80a2a0df40909f5c2b9d5f8df592"
    # path = r"D:\Code\Python\pyutils\imgServerState\images\20251015170020e89d9ae8.png"
    project_path = os.path.join(os.path.dirname(__file__),'images')
    path = os.path.join(project_path,'20260522181157ad5f7701.png')
    from threading import Thread
    c=ThreadAnayPngWork()
    p=[]
    for i in range(1):
        t = Thread(target=c.work, args=(MODEL_TOKEN, path,"10.255.50.51"))
        t.start()
        p.append(t)
    for t in p:
        t.join()
    end = time.time()
    print(end-start)
    # path=PicUtils.corp_1_3_userinfo(path)
    # agent=AgentsTools(MODEL_TOKEN)
    # print(agent.upload_image_to_customer(path))

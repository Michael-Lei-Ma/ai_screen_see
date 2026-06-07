# -*- coding: utf-8 -*-
import base64
import re
import io
import os
import mimetypes
import glob
import cv2
import numpy as np
import ddddocr
from PIL import Image


class Base64CaptchaRecognizer:

    def __init__(self, code_len=4, use_preprocess=True):
        self.code_len = code_len
        self.use_preprocess = use_preprocess
        self.ocr = ddddocr.DdddOcr(beta=True)

    # ---------- 轻度预处理 ----------
    def _preprocess(self, img_bytes: bytes) -> bytes:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img = np.array(img)

        img = cv2.GaussianBlur(img, (3, 3), 0)
        img = cv2.convertScaleAbs(img, alpha=1.3, beta=10)

        _, buf = cv2.imencode(".png", img)
        return buf.tobytes()

    # ---------- 字符切割 ----------
    def _split_chars(self, img_bytes: bytes):
        img = cv2.imdecode(
            np.frombuffer(img_bytes, np.uint8),
            cv2.IMREAD_GRAYSCALE
        )

        binary = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w * h < 50:
                continue
            boxes.append((x, y, w, h))

        boxes = sorted(boxes, key=lambda b: b[0])

        if len(boxes) != self.code_len:
            return None

        chars = []
        for x, y, w, h in boxes:
            chars.append(img[y:y + h, x:x + w])

        return chars

    # ---------- 单字符 OCR ----------
    def _ocr_single_char(self, char_img):
        _, buf = cv2.imencode(".png", char_img)
        text = self.ocr.classification(buf.tobytes())
        text = re.sub(r'[^0-9a-zA-Z]', '', text)
        return text.upper() if text else ''

    # ---------- 分割兜底 ----------
    def _recognize_by_split(self, img_bytes):
        chars = self._split_chars(img_bytes)
        if not chars:
            return None

        result = ''
        for ch in chars:
            c = self._ocr_single_char(ch)
            if not c:
                return None
            result += c

        return result if len(result) == self.code_len else None

    # ---------- 核心识别 ----------
    def recognize(self, base64_str: str):
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]

        img_bytes = base64.b64decode(base64_str)

        # ① 原图
        text = self.ocr.classification(img_bytes)
        text = re.sub(r'[^0-9a-zA-Z]', '', text)
        if len(text) == self.code_len:
            return text.upper()

        # ② 预处理
        if self.use_preprocess:
            img_bytes2 = self._preprocess(img_bytes)
            text2 = self.ocr.classification(img_bytes2)
            text2 = re.sub(r'[^0-9a-zA-Z]', '', text2)
            if len(text2) == self.code_len:
                return text2.upper()

        # ③ 分割
        split_text = self._recognize_by_split(img_bytes)
        if split_text:
            return split_text

        return None

class ImageFormatChange:

    def image_to_base64(self,image_path):
        """
        将图片文件转换为 base64 字符串
        :param image_path: 图片文件路径
        :return: base64 字符串（不含 data:image 前缀）
        """
        try:
            with open(image_path, 'rb') as image_file:
                # 读取图片二进制数据
                image_data = image_file.read()
                # 转换为 base64
                base64_str = base64.b64encode(image_data).decode('utf-8')
                return base64_str
        except Exception as e:
            print(f"转换失败: {e}")
            return None

    def image_to_base64_with_prefix(self,image_path):
        """
        将图片文件转换为带 data:image 前缀的 base64 字符串
        :param image_path: 图片文件路径
        :return: 带前缀的 base64 字符串
        """
        try:
            # 获取图片格式
            img = Image.open(image_path)
            img_format = img.format.lower()
            if img_format == 'jpeg':
                img_format = 'jpg'

            # 读取图片数据
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_str = base64.b64encode(image_data).decode('utf-8')
                # 添加 data:image 前缀
                return f"data:image/{img_format};base64,{base64_str}"
        except Exception as e:
            print(f"转换失败: {e}")
            return None




# =====================
# 示例调用
# =====================
# if __name__ == "__main__":
#     recognizer = Base64CaptchaRecognizer(
#         code_len=4,
#         use_preprocess=True
#     )
#
#     # 示例 base64（替换成你真实的）
#     base64_img_lt =["data:image/png;base64,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 ","data:image/png;base64,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"
# ]
#     for base64_img in base64_img_lt:
#         result = recognizer.recognize(base64_img)
#         print("识别结果：", result)

    # parent_dir = os.path.dirname(os.path.dirname(__file__))
    # # pattern = os.path.join(parent_dir, "result",'expect_images', "5FM9.png")
    # pattern = os.path.join(parent_dir, "result","*.png")
    # png_files = glob.glob(pattern, recursive=True)
    # print(f"png_files is : {png_files}")
    # error_count =0
    # error_lt = list()
    # for i,image_path in enumerate(png_files):
    #     error_dit = dict()
    #     org_image_name = image_path.split('\\')[-1]
    #     # print(f"org_image_name is : {org_image_name}")
    #     base64_img = ImageFormatChange().image_to_base64(image_path)
    #     pred = recognizer.recognize(base64_img)
    #     print(f"[{i}] 真实值: {org_image_name} | 识别值: {pred}")
    #     if org_image_name.split('.png')[0] != pred:
    #         error_dit[org_image_name]=pred
    #         error_lt.append(error_dit)
    #         error_count+=1
    # print(f"error_lt is :{error_lt}\ntotal error : {error_count} ")



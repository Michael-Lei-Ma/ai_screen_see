import base64
import time
from threading import Thread
from PIL import Image
import os
import requests
import re
import json
import pymysql, re

keywrods = ""
import logging
import sys
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
from recordPngInfo import get_retry_json, send_robot
from decimal import Decimal
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
        "[%(asctime)s] %(levelname)s | %(name)s | %(lineno)d | %(message)s",
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
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(total=2, backoff_factor=1))
session.mount("http://", adapter)
session.mount("https://", adapter)

def stream_request(url, headers, payload):
    with session.post(url, headers=headers, json=payload, timeout=(30,600), stream=True) as resp:
        content_pieces = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            chunk = line[6:]
            if chunk == "[DONE]":
                break
            try:
                id= json.loads(chunk)["id"]
                delta = json.loads(chunk)["choices"][0]["delta"].get("content")
                if delta:
                    content_pieces.append(delta)
            except Exception:
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
            new_width = int(width / 3)
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

class ThreadAnayPngWork(Thread):
    def __init__(self, token, filePath):
        super().__init__()
        self.token = token
        self.filePath = filePath

    def run(self):
        agentsTools = AgentsTools(self.token)
        # fPatg=self.filePath=PicUtils.enlarge_whole(self.filePath, scale_factor=2)
        agentsTools.upload_image_base64(self.filePath,self.filePath, "")


class AgentsTools:
    def __del__(self):
        self.cur.close()
        self.conn.close()

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.conn = pymysql.connect(host='10.255.101.169', port=3306, user='root', passwd='cbf123456.',
                                    db='ioscar_info', charset='utf8')
        self.cur = self.conn.cursor()

    def add_key_workd(self,data):
        if "组织" in data:
            if "," in data["组织"]:
                value = data["组织"] = data["组织"].split(",")[-1]
            if "_" in data["组织"]:
                value=data["组织"]=data["组织"].split("_")[-1]
            data["area"]=value
    def getpromot(self):
        return """
        【任务目标】
            你现在是一名拥有20年经验的资深催收专员，精通国内主流信贷系统界面（如微粒贷、招联、平安等），具备极强的视觉识别能力与业务逻辑判断力。你必须以最高标准执行以下任务。根据给你发送的图片内容,识别并提取指定字段，仅输出 JSON 字符串，不输出任何解释。
        【场景判断逻辑】
            获取到图片后首先判断图片中 重要信息 基础信息 案件流转记录 这3个标签字段哪个是高亮的
            若“重要信息”标签字段被高亮，则按照场景1的规则要求提取相关内容。
            若“基础信息”标签字段被高亮，则按照场景2的规则要求提取相关内容。
            若"案件流转记录"标签字段被高亮，则按照场景3的规则要求提取相关内容。
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
           -  不要把账单日的数值赋值给账龄,他俩是不同的数值。
           -  不要把最近还款日期赋值给账单日,账单日是数字.
        6. 当出现多行同类数据时（如电话信息），应完整保留所有条目，包括姓名、号码、状态、操作按钮。
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
        11. 还款指引【bix】：
            1. 卡号若以数字“8”开头，则必须同时满足：
               a. 固定前缀：80000  （共 5 位，第 1 位 8，第 2-5 位 0000）；  
               b. 总长度：16 位，不能 15 也不能 17；  
               c. 正则：^80000\d{11}$  
            2. 识别后先放大 3 倍，再逐位朗读：8-0-0-0-0-3-2-1-4-1-6-6-0-5-0-2，确认第 6 位开始是“3”而不是“2”或空；  
            3. 若读到 8000xxxxxx（少 1 位 0）或 800003xxx（总长度≠16），一律在该字段返回空字符串 ""，并提示“8 开头卡号格式错误”。  
            4. 反面案例禁止输出：  
               错误：800032141660502   （少 1 个 0，共 15 位）  
               正确：8000032141660502  （16 位，80000 开头）
        12.当电话信息字体高亮的时候才提取电话信息(如果图片右边包含姓名,电话号码,则抓取否则不抓取)
        【输出格式】
        仅输出 JSON 字符串，无任何解释、注释或额外内容。
        ---  
        【场景 2：基础信息字段高亮】  
          触发条件：图片中“基础信息”标签字段高亮。
        提取要求：
        1. 必须提取：
           - 公安户籍信息
           - 当电话信息字体高亮的时候才提取电话信息(如果图片右边包含姓名,电话号码,则抓取否则不抓取)
           - 当地址信息字体高亮的时候才提取地址内容(如果图片右边包含地址内容,则抓取所有的地址内容放到一个字符串用,号隔开,否则不抓取)
           - 微粒贷信息（必须字段：微粒贷号）
           - 注意事项:从第二个图片仅仅识别微粒贷号
           注：微粒贷中的金额不得写入账务信息。
        2. 不提取：账务信息。
        
        【场景 3：案件流转记录字段高亮】  
          触发条件：图片中“案件流转记录”字段高亮。
          提取要求：
          1. 必须提取：
             - 当电话信息字体高亮的时候才提取电话信息(如果图片右边包含姓名,电话号码,则抓取否则不抓取)
             - 当地址信息Tab高亮的时候提取地址内容（如果图片右边包含地址内容,则抓取所有的地址内容放到一个字符串用,号隔开,否则不抓取）
             - 催收员(催收员姓名在一个表格中的第一行第二列催收员列,如果没有找到则该字段为空字符串)
             - 组织（在一个表格中的第一行第3列-组织列,如果没有找到则该字段为空字符串）
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
        1. 微粒贷号位于图中微粒贷三个字的旁边,以DS开头,后面结合了24位数字，一个也不能少
        【微粒贷信息提取规则】
        1.必须提取图片中的微粒贷信息,它是单独的key,不得有遗漏.且不能在客户信息的json中出现.
        【账务信息硬核闸门】
            必提字段（共 13 项）因为图片中是一定有信息的需要认真仔细识别：
            账龄、账单日、首次借款日期、案件类型、信用额度、最近还款日期、最近还款金额、24 期账龄、委托金额、委托本金、委托日期、委托到期日、手别
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
        场景 3：{"催收员":"王红","地址内容":"深圳市南山区,XXXX"},"微粒贷信息":{"微粒贷号":"DS000000000000000000000000"}}
        
        
        """
    def upload_image_base64(self, image_path, originImgPath, msg=""):
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
        for p in [image_path]:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}"

                }
            })
        payload = {
            "model": "qwen-vl-max-latest",
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
        full_text=""
        for i in range(3):
            event_id = ""
            try:
                event_id,data = stream_request(url, headers, payload)
                log.info("模型最终识别的json字符串为:")
                log.info(data)
                data = json.loads(data)
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                send_robot(
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                    "大模型获取重试json失败,请检查,错误信息:" + str(e)+"第"+str(i+1)+"次-事件id:"+event_id)
                log.info(f"JSON 解析错误: {e}")
                continue
        else:
            log.error("大模型识别错误,3次识别都没成功")
            return
        key = self.get_weili(data)
        tools = DBTools(image_path)
        if key:
            ###关键信息校验
            log.info("第一个图片:" + key)  # 微粒贷号校验
            if len(key)!=26 and not key.startswith("DS09999"):
                key = key[:8] + '9' + key[8:]
                data["微粒贷信息"]["微粒贷号"] = key
            elif len(key) != 26 and key.startswith("DS09999"):
                for i in range(4):
                    log.info("微粒贷信息错误:%s" % len(key))
                    log.info("重新识别第" + str(i + 1) + "次,进行中")
                    try:
                        jsondata = get_retry_json(originImgPath, self.api_key)
                    except Exception as e:
                        send_robot("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4", "OCR_获取重试json失败,请检查,错误信息:"+str(e))
                        continue
                    log.info("ocr识别的结果:")
                    log.info(jsondata)
                    if jsondata!='':
                        key=jsondata.get("微粒贷号")
                    if len(key) == 26:
                        data["微粒贷信息"]["微粒贷号"]=key
                        break
                    if len(key) != 26 and not key.startswith("DS09999"):
                        key = key[:8] + '9' + key[8:]
                        data["微粒贷信息"]["微粒贷号"] = key
                        log.info("重新识别第" + str(i + 1) + "次,重新识别到的微粒贷号为:%s" % key)
                        break
            card = self.getcard(data)
            if card!="" and card!=None:
                log.info(card)  # 身份证号校验
                if card[:4].find("*") > -1:
                    log.info("身份证号错误:%s" % card)
                    for i in range(2):
                        try:
                            jsondata = get_retry_json(originImgPath, self.api_key)
                        except Exception as e:
                            send_robot(
                                "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                                "OCR_获取重试json失败,请检查,错误信息:" + str(e))
                            continue
                        log.info("ocr识别的结果:")
                        log.info(jsondata)
                        if jsondata != '':
                            card = jsondata.get("身份证号","")
                        if card!="" and card[:4].find("*") <= 0:
                            data["客户信息"]["身份证"]=card
                            break
            data["卡号"] = ""
            rebackcard=self.getrebackcard(data)#还款指引号
            if rebackcard:
                if rebackcard.startswith("8000") and len(rebackcard)!=16:
                    log.info("千问卡号识别错误:%s,进行OCR识别" % rebackcard)
                    for i in range(2):
                        try:
                            jsondata = get_retry_json(originImgPath, self.api_key)
                        except Exception as e:
                            send_robot(
                                "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4",
                                "OCR_获取重试json失败,请检查,错误信息:" + str(e))
                            continue
                        if jsondata != '':
                           newcard = jsondata.get("卡号","")
                        log.info("ocr识别结果:"+str(jsondata))
                        log.info("ORC识别卡号:%s,长度是:%s,旧的卡号:%s,长度是:%s" % (newcard,len(newcard),rebackcard,len(rebackcard)))
                        if len(newcard)==16:
                            log.info("赋值了新卡号:%s" % newcard)
                            data["卡号"]=newcard
                            break
                else:
                    data["卡号"] = rebackcard #够了的情况
            log.info("识别完毕信息开始入库")
            log.info(data)
            self.add_key_workd(data)
            money=self.get_money(data)
            if "area" in data:
                tools.insert_or_update_with_area(key, json.dumps(data,ensure_ascii=False),money,data["area"])  # 如果有则进行插入
            else:
                tools.insert_or_update(key, json.dumps(data,ensure_ascii=False),money)  # 如果有则进行插入
        # else:
        #     log.info("第二个图片:" + key)
        #     key = self.get_keyword2(data)
        #     if key:
        #         if len(key) != 26:
        #             log.info("微粒贷信息错误:%s" % len(key))
        #             for i in range(3):
        #                 key, clean = self.retry_recoginze(image_path,
        #                                                   "微粒贷号识别不足26位,请重新识别，微粒贷号从第二个图片识别即可")
        #                 if len(key) == 26:
        #                     break
        #         money = self.get_money(data)
        #         tools.work_info_pic2(key, clean,money)
        #     else:
        #         log.info("没有微粒贷号码")

        del tools
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
                card = rebackcard.get("卡号", "")
                return card
        return ""
from contextlib import closing
class DBTools:
    _RE_16_DIGITS = re.compile(r'^\d{16}$')

    def get_connect(self):
        return pymysql.connect(host='10.255.100.202', port=3306, user='root', passwd='123.com',
                                    db='ioscar_info',
                                    charset='utf8mb4', use_unicode=True)
    def __init__(self, image_path):
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

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception as e:
            log.error("数据库关闭失败,错误信息:%s" % e)

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
                        log.info("入库发现微粒贷信息:%s" % value)
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
        if card:
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

    def insert_or_update(self, id: str, info: str,money:str):
        """
        插入或更新数据
        """
        log.info(id[-6:]+" "+str(money))
        # selectSql = "SELECT * FROM info_save WHERE RIGHT(`id`, 6) = %s AND `money` = %s"
        # self.cursor.execute(selectSql, (id[-6:],money))
        selectSql = "SELECT * FROM info_save WHERE `id` = %s"
        self.cursor.execute(selectSql, (id,))
        row = self.cursor.fetchone()
        err_type = self.check_card_weilidai(info)

        if row is None:
            sql = "INSERT INTO info_save (`id`,`info`,`insert_time`,`err_type`,`img_name`,`money`) VALUES (%s, %s,%s,%s,%s,%s)"
            self.cursor.execute(sql, (
            id, info, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), err_type, self.image_path,money))
            self.conn.commit()
            try:
                self.cursor.close()
                self.conn.close()
                log.info("数据库关闭成功")
            except Exception as e:
                log.error("数据库关闭失败,错误信息:%s" % e)
            # self.insert_detail(id, json.loads(info))
        else:
            imgPathOld=row["img_name"]
            oldInfo = json.loads(row["info"])
            log.info("读取的信息:%s" % oldInfo)
            newInfo = json.loads(info)
            for k, v in newInfo.items():
                log.info("正在遍历key:%s" % k)
                if k in oldInfo:
                    log.info("正在更新key:%s" % k)
                    infoOld = oldInfo.get(k, {})
                    log.info("旧数据:%s" % infoOld)
                    infoNew = newInfo.get(k, {})
                    log.info("新数据:%s" % infoNew)
                    if infoOld == {}:
                        oldInfo[k] = infoNew
                        continue
                    print(len(infoOld))
                    print(len(infoNew))
                    if k=="卡号" and len(infoNew)==16:
                        log.info("赋值旧的信息卡号为:%s" % infoNew)
                        oldInfo[k]= infoNew
                    if k == "客户信息" and infoOld.get("身份证", "") != '' and "*" not in infoOld.get("身份证", "") \
                            and len(infoOld) >= len(infoNew): continue
                    if k == '电话信息' and isinstance(infoOld, list):
                        if infoOld == [] and newInfo == []:
                            continue
                        else:
                            if oldInfo[k]:
                                for v in infoNew:
                                    flag = False
                                    for d in infoOld:
                                        if v.get("姓名") == d.get("姓名") and v.get("电话号码") == d.get("电话号码"):
                                            flag = True
                                    if not flag:
                                        log.info("新增了电话信息:" + str(v))
                                        infoOld.append(v)
                                        # 说明有不一样的
                            else:
                                oldInfo[k] = infoNew
                    if k=="电话信息" and isinstance(infoOld,str):
                        oldInfo[k] = infoNew #如果是字符串则被替换
                    if k=="电话信息" and isinstance(infoOld,dict):
                        newTel=[]
                        flag=False
                        if isinstance(infoNew,dict):
                            log.info(infoOld)
                            if infoNew.get("姓名") != infoOld.get("姓名") and infoNew.get("电话号码") != infoOld.get("电话号码"):
                                newTel.append(infoOld)
                                newTel.append(infoNew)
                            oldInfo['电话信息'] =newTel
                        if isinstance(infoNew,list):
                            for v in infoNew:
                                newTel.append(v)
                                if v.get("姓名")==infoOld.get("姓名") and v.get("电话号码")==infoOld.get("电话号码"):
                                    flag=True
                            if flag:
                                oldInfo[k] = infoNew  # 如果是字符串则被替换
                            else:
                                newTel.append(infoOld)
                                oldInfo[k] = newTel  # 如果是字符串则被替换
                    if isinstance(infoOld, dict) and isinstance(infoNew, dict) and k =="账务信息":
                        for key, value in infoNew.items():
                            log.info("获取字段:%s" % key)
                            if infoOld.get(key, "") == '':
                                log.info("更新旧的财务信息:%s 变为新的:%s" % (infoOld.get(key, ""), value))
                                infoOld[key] = value
                            if key=="账龄":
                                if infoOld.get("账龄","")!=infoOld.get("账单日",""):
                                    continue
                                else:
                                    infoOld[key] = value
                                    log.info("哈哈开始更新账龄了")
                            if key=="账单日":
                                if "-" not in infoOld.get("账单日",""):
                                    continue
                                else:
                                    infoOld[key] = value

                        continue
                    if isinstance(infoOld, dict) and isinstance(infoNew, dict) and k not in ["电话信息","财务信息"]:
                        for key, v in infoNew.items():
                            if key != '催收员' and str(v) != '' and "*" not in str(v):
                                log.info("更新旧的:%s 变为新的:%s" % (infoOld.get(key, ""), v))
                                log.error("字段:%s,更新值为:%s" % (key,v))
                                infoOld[key] = v
                            else:
                                log.info("进入默认全局更新%s" % key)
                                self.updateInfo(v, infoOld.get(key, ""), infoOld, key)
                    if isinstance(infoNew, str) and k == "催收员":
                        username = oldInfo.get("客户信息", {}).get("姓名", "")
                        if username != '':
                            if v != '' and v != username:
                                oldInfo[k] = v
                    if isinstance(infoNew, str) and k == "地址内容":
                        if "地址内容" in oldInfo:
                            if oldInfo[k] != '':
                                if "," in oldInfo[k]:
                                    if "," in infoNew:
                                        infoNewList=infoNew.split(",")
                                        oldInfoList=oldInfo[k].split(",")
                                        for i in infoNewList:
                                            if i not in oldInfoList:
                                                oldInfo[k] = self.dupestr(oldInfo[k] + "," + i)
                                    else:
                                        oldInfo[k] = self.dupestr(oldInfo[k] + "," + infoNew)
                                else:
                                    oldInfo[k] = self.dupestr(oldInfo[k] + "," + infoNew)
                            else:
                                oldInfo[k] = v
                        else:
                            oldInfo[k] = v
                else:
                    log.info("新增key:%s,属于集体更新" % k)
                    log.info("集体更新数据%s" % v)
                    oldInfo[k] = v
            log.info("终极入库数据:%s" % oldInfo)
            log.info("更新的ID:%s" % id)
            sql = "UPDATE info_save SET `info`=%s,`err_type`=%s,`img_name`=%s,`insert_time`=%s WHERE `id` = %s"
            self.cursor.execute(sql, (json.dumps(oldInfo, ensure_ascii=False), err_type,imgPathOld+","+self.image_path,
                                      time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),id))
            self.conn.commit()
            rowcnt = self.cursor.rowcount
            log.info("UPDATE 影响行数:%s", rowcnt)
            try:
                self.cursor.close()
                self.conn.close()
                log.info("数据库关闭成功")
            except Exception as e:
                log.error("数据库关闭失败,错误信息:%s" % e)


    def insert_or_update_with_area(self, id: str, info: str,money:str,area:str):
        """
        插入或更新数据
        """
        log.info(id[-6:]+" "+str(money))
        # selectSql = "SELECT * FROM info_save WHERE RIGHT(`id`, 6) = %s AND `money` = %s"
        # self.cursor.execute(selectSql, (id[-6:],money))
        selectSql = "SELECT * FROM info_save WHERE `id` = %s"
        self.cursor.execute(selectSql, (id,))
        row = self.cursor.fetchone()
        err_type = self.check_card_weilidai(info)

        if row is None:
            sql = "INSERT INTO info_save (`id`,`info`,`insert_time`,`err_type`,`img_name`,`money`,`area`) VALUES (%s, %s,%s,%s,%s,%s,%s)"
            self.cursor.execute(sql, (
            id, info, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), err_type, self.image_path,money,area))
            self.conn.commit()
            # self.insert_detail(id, json.loads(info))
            try:
                self.cursor.close()
                self.conn.close()
                log.info("数据库关闭成功")
            except Exception as e:
                log.error("数据库关闭失败,错误信息:%s" % e)
        else:
            imgPathOld=row["img_name"]
            oldInfo = json.loads(row["info"])
            log.info("读取的信息:%s" % oldInfo)
            newInfo = json.loads(info)
            for k, v in newInfo.items():
                log.info("正在遍历key:%s" % k)
                if k in oldInfo:
                    log.info("正在更新key:%s" % k)
                    infoOld = oldInfo.get(k, {})
                    log.info("旧数据:%s" % infoOld)
                    infoNew = newInfo.get(k, {})
                    log.info("新数据:%s" % infoNew)
                    if infoOld == {}:
                        oldInfo[k] = infoNew
                        continue
                    print(len(infoOld))
                    print(len(infoNew))
                    if k=="卡号" and len(infoNew)==16:
                        log.info("赋值旧的信息卡号为:%s" % infoNew)
                        oldInfo[k]= infoNew
                    if k == "客户信息" and infoOld.get("身份证", "") != '' and "*" not in infoOld.get("身份证", "") \
                            and len(infoOld) >= len(infoNew): continue
                    if k == '电话信息' and isinstance(infoOld, list):
                        if infoOld == [] and newInfo == []:
                            continue
                        else:
                            if oldInfo[k]:
                                for v in infoNew:
                                    flag = False
                                    for d in infoOld:
                                        if v.get("姓名") == d.get("姓名") and v.get("电话号码") == d.get("电话号码"):
                                            flag = True
                                    if not flag:
                                        log.info("新增了电话信息:" + str(v))
                                        infoOld.append(v)
                                        # 说明有不一样的
                            else:
                                oldInfo[k] = infoNew
                    if k=="电话信息" and isinstance(infoOld,str):
                        oldInfo[k] = infoNew #如果是字符串则被替换
                    if k=="电话信息" and isinstance(infoOld,dict):
                        newTel=[]
                        flag=False
                        if isinstance(infoNew,dict):
                            log.info(infoOld)
                            if infoNew.get("姓名") != infoOld.get("姓名") and infoNew.get("电话号码") != infoOld.get("电话号码"):
                                newTel.append(infoOld)
                                newTel.append(infoNew)
                            oldInfo['电话信息'] =newTel
                        if isinstance(infoNew,list):
                            for v in infoNew:
                                newTel.append(v)
                                if v.get("姓名")==infoOld.get("姓名") and v.get("电话号码")==infoOld.get("电话号码"):
                                    flag=True
                            if flag:
                                oldInfo[k] = infoNew  # 如果是字符串则被替换
                            else:
                                newTel.append(infoOld)
                                oldInfo[k] = newTel  # 如果是字符串则被替换
                    if isinstance(infoOld, dict) and isinstance(infoNew, dict) and k =="账务信息":
                        for key, value in infoNew.items():
                            log.info("获取字段:%s" % key)
                            if infoOld.get(key, "") == '':
                                log.info("更新旧的财务信息:%s 变为新的:%s" % (infoOld.get(key, ""), value))
                                infoOld[key] = value
                            if key=="账龄":
                                if infoOld.get("账龄","")!=infoOld.get("账单日",""):
                                    continue
                                else:
                                    infoOld[key] = value
                                    log.info("哈哈开始更新账龄了")
                            if key=="账单日":
                                if "-" not in infoOld.get("账单日",""):
                                    continue
                                else:
                                    infoOld[key] = value

                        continue
                    if isinstance(infoOld, dict) and isinstance(infoNew, dict) and k not in ["电话信息","财务信息"]:
                        for key, v in infoNew.items():
                            if key != '催收员' and str(v) != '' and "*" not in str(v):
                                log.info("更新旧的:%s 变为新的:%s" % (infoOld.get(key, ""), v))
                                log.error("字段:%s,更新值为:%s" % (key,v))
                                infoOld[key] = v
                            else:
                                log.info("进入默认全局更新%s" % key)
                                self.updateInfo(v, infoOld.get(key, ""), infoOld, key)
                    if isinstance(infoNew, str) and k == "催收员":
                        username = oldInfo.get("客户信息", {}).get("姓名", "")
                        if username != '':
                            if v != '' and v != username:
                                oldInfo[k] = v
                    if isinstance(infoNew, str) and k == "地址内容":
                        if "地址内容" in oldInfo:
                            if oldInfo[k] != '':
                                if "," in oldInfo[k]:
                                    if "," in infoNew:
                                        infoNewList=infoNew.split(",")
                                        oldInfoList=oldInfo[k].split(",")
                                        for i in infoNewList:
                                            if i not in oldInfoList:
                                                oldInfo[k] = self.dupestr(oldInfo[k] + "," + i)
                                    else:
                                        oldInfo[k] = self.dupestr(oldInfo[k] + "," + infoNew)
                                else:
                                    oldInfo[k] = self.dupestr(oldInfo[k] + "," + infoNew)
                            else:
                                oldInfo[k] = v
                        else:
                            oldInfo[k] = v
                else:
                    log.info("新增key:%s,属于集体更新" % k)
                    log.info("集体更新数据%s" % v)
                    oldInfo[k] = v
            log.info("终极入库数据:%s" % oldInfo)
            log.info("更新的ID:%s" % id)
            sql = "UPDATE info_save SET `info`=%s,`err_type`=%s,`img_name`=%s,`insert_time`=%s,`area`=%s WHERE `id` = %s"
            self.cursor.execute(sql, (json.dumps(oldInfo, ensure_ascii=False), err_type,imgPathOld+","+self.image_path,
                                      time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),area,id))
            self.conn.commit()
            rowcnt = self.cursor.rowcount
            log.info("UPDATE 影响行数:%s", rowcnt)
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
    def insert_detail(self, id, info):
        """
        插入详情数据
        """
        account = info.get("客户信息", {})
        if account:
            self.work_people_info_table(account, id)
        payment = info.get("账务信息", {})
        # if payment:
        #     self.work_payment_info_table(payment, id)
        tel = info.get("电话信息", {})
        if tel:
            self.work_tel_info_table(tel, id)
        redirece = info.get("还款指引", {})
        if redirece:
            self.work_redirece_info_table(redirece, id)
        weili = info.get("微粒贷信息", {})
        if weili:
            self.work_weili_info_table(weili, id)

    def work_people_info_table(self, account, id):
        selectSql = "select * from people_info where id ='%s'" % id
        self.cursor.execute(selectSql)
        row = self.cursor.fetchone()
        if row is None:
            sql = "INSERT INTO people_info (`id`,`username`,`sex`,`age`,`marry`,`card_id`,`work_unit`,`work_unit_address`,`connect_address`,`address1`,`address2`,`degree`,`career`) VALUES (%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s)"
            self.cursor.execute(sql, (
                id, account.get("姓名", ""), account.get("性别", ""), account.get("年龄", 0),
                account.get("婚姻状态", ""),
                account.get("身份证号", ""), account.get("工作单位", ""), account.get("单位地址", ""),
                account.get("通讯地址", ""), account.get("户籍地址", ""), account.get("户籍地址2", ""),
                account.get("学历", ""), account.get("职业", "")))
            self.conn.commit()
        else:
            sql = "UPDATE people_info SET `username`=%s,`sex`=%s,`age`=%s,`marry`=%s,`card_id`=%s,`work_unit`=%s,`work_unit_address`=%s,`connect_address`=%s,`address1`=%s,`address2`=%s,`degree`=%s,`career`=%s WHERE `id`=%s"
            self.cursor.execute(sql, (
                account.get("姓名", ""), account.get("性别", ""), account.get("年龄", 0), account.get("婚姻状态", ""),
                account.get("身份证号", ""), account.get("工作单位", ""), account.get("单位地址", ""),
                account.get("通讯地址", ""), account.get("户籍地址", ""), account.get("户籍地址2", ""),
                account.get("学历", ""), account.get("职业", ""), id))
            self.conn.commit()

    def work_payment_info_table(self, payment, id):
        """
            账务信息更新和插入
        :param payment:
        :param id:
        :return:
        """
        selectSql = "select * from account_info where id ='%s'" % id
        self.cursor.execute(selectSql)
        row = self.cursor.fetchone()
        if row is None:
            sql = "INSERT INTO account_info (`id`,`account_date`,`first_account_date`,`event_type`,`account_money`,`last_repay_date`,`last_repay_money`,`24_period`,`period`,`outstanding_amount`,`entrusted_principal`,`entrustment_date`,`entrustment_maturity_date`,`hand_type`) VALUES (%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s)"
            self.cursor.execute(sql, (
            id, int(payment.get("账单日", 1)), payment.get("首次借款日期", ""), payment.get("案件类型", ""),
            float(payment.get("信用额度", 0)), payment.get("最近还款日期", ""), payment.get("最近还款金额", ""),
            payment.get("24期账龄", ""), int(payment.get("期数", 0)), float(payment.get("待还金额", 0)),
            payment.get("委托本金", ""), payment.get("委托日期", ""), payment.get("委托到期日", ""),
            payment.get("手别", "")))
            self.conn.commit()
        else:
            sql = "UPDATE account_info SET `account_date`=%s,`first_account_date`=%s,`event_type`=%s,`account_money`=%s,`last_repay_date`=%s,`last_repay_money`=%s,`24_period`=%s,`period`=%s,`outstanding_amount`=%s,`entrusted_principal`=%s,`entrustment_date`=%s,`entrustment_maturity_date`=%s,`hand_type`=%s WHERE `id`=%s"
            self.cursor.execute(sql, (
            int(payment.get("账单日", 1)), payment.get("首次借款日期", ""), payment.get("案件类型", ""),
            float(payment.get("信用额度", 0)), payment.get("最近还款日期", ""), payment.get("最近还款金额", ""),
            payment.get("24期账龄", ""), int(payment.get("期数", 0)), float(payment.get("待还金额", 0)),
            payment.get("委托本金", ""), payment.get("委托日期", ""), payment.get("委托到期日", ""),
            payment.get("手别", ""), id))
            self.conn.commit()

    def work_tel_info_table(self, tel, id):
        if isinstance(tel, list):
            for t in tel:
                selectSql = "select * from phone_info where id ='%s' and telphone_number ='%s'" % (
                id, t.get("电话号码", ""))
                self.cursor.execute(selectSql)
                row = self.cursor.fetchone()
                if row is None:
                    sql = "INSERT INTO phone_info (`id`,`user_name`,`telphone_number`) VALUES (%s, %s,%s)"
                    self.cursor.execute(sql, (id, t.get("姓名", ""), t.get("电话号码", "")))
                    self.conn.commit()
                else:
                    sql = "UPDATE phone_info SET `user_name`=%s,`telphone_number`=%s WHERE `id`=%s"
                    self.cursor.execute(sql, (t.get("姓名", ""), t.get("电话号码", ""), id))
                    self.conn.commit()

        else:
            selectSql = "select * from phone_info where id ='%s'" % id
            self.cursor.execute(selectSql)
            row = self.cursor.fetchone()
            if row is None:
                sql = "INSERT INTO phone_info (`id`,`user_name`,`telphone_number`) VALUES (%s, %s,%s)"
                self.cursor.execute(sql, (id, tel.get("姓名", ""), tel.get("电话号码", "")))
                self.conn.commit()
            else:
                sql = "UPDATE phone_info SET `user_name`=%s,`telphone_number`=%s WHERE `id`=%s"
                self.cursor.execute(sql, (tel.get("姓名", ""), tel.get("电话号码", ""), id))
                self.conn.commit()

    def work_redirece_info_table(self, redireces, id):

        if isinstance(redireces, list):
            for redict in redireces:
                if isinstance(redict, str):
                    redict = json.loads(redict)
                sqlCheck = "select * from reback_money_info where id ='%s' and card ='%s'" % (
                id, redict.get("卡号", ""))
                self.cursor.execute(sqlCheck)
                row = self.cursor.fetchone()
                if row is None:
                    sql = "INSERT INTO reback_money_info (`id`,`reback_type`,`chanel`,`card`,`receive_bank`,`receiver`) VALUES (%s, %s,%s,%s, %s,%s)"
                    self.cursor.execute(sql, (id, redict.get("还款类型", ""), redict.get("渠道", ""),
                                              redict.get("卡号", ""), redict.get("收款行", ""),
                                              redict.get("收款人", "")))
                    self.conn.commit()
                else:
                    sql = "UPDATE reback_money_info SET `reback_type`=%s,`chanel`=%s,`card`=%s,`receive_bank`=%s,`receiver`=%s WHERE `id`=%s"
                    self.cursor.execute(sql, (redict.get("还款类型", ""), redict.get("渠道", ""),
                                              redict.get("卡号", ""), redict.get("收款行", ""),
                                              redict.get("收款人", ""), id))
                    self.conn.commit()
        else:
            sqlCheck = "select * from reback_money_info where id ='%s' and card ='%s'" % (id, redireces.get("卡号", ""))
            self.cursor.execute(sqlCheck)
            row = self.cursor.fetchone()
            if row is None:
                sql = "INSERT INTO reback_money_info (`id`,`reback_type`,`chanel`,`card`,`receive_bank`,`receiver`) VALUES (%s, %s,%s,%s, %s,%s)"
                self.cursor.execute(sql, (id, redireces.get("还款类型", ""), redireces.get("渠道", ""),
                                          redireces.get("卡号", ""), redireces.get("收款行", ""),
                                          redireces.get("收款人", "")))
                self.conn.commit()
            else:
                sql = "UPDATE reback_money_info SET `reback_type`=%s,`chanel`=%s,`card`=%s,`receive_bank`=%s,`receiver`=%s WHERE `id`=%s"
                self.cursor.execute(sql, (redireces.get("还款类型", ""), redireces.get("渠道", ""),
                                          redireces.get("卡号", ""), redireces.get("收款行", ""),
                                          redireces.get("收款人", ""),
                                          id))
                self.conn.commit()

    def work_weili_info_table(self, weili, id):
        selectSql = "select * from weili_dai_information where id ='%s'" % id
        self.cursor.execute(selectSql)
        row = self.cursor.fetchone()
        if row is None:
            sql = "INSERT INTO weili_dai_information (`id`,`total_overdue_amount`,`settlement_amount`,`total_overdue_principal`,`total_overdue_interest`,`total_overdue_penalty_interest`,`cured_collected`,`collection_stage`,`overdue_days`,`collection_start_date`,`historical_overdue_count`,`last_cure_date`) VALUES (%s, %s,%s,%s, %s,%s,%s, %s,%s,%s, %s,%s)"
            self.cursor.execute(sql, (id, float(weili.get("逾期总金额", 0)),
                                      float(weili.get("结清金额", 0)), float(weili.get("逾期总本金", 0)),
                                      float(weili.get("逾期总利息", 0)),
                                      float(weili.get("逾期总罚息", 0)), weili.get("是否治愈/出催", ""),
                                      weili.get("催收阶段", "")
                                      , int(weili.get("逾期天数", 0)), weili.get("入催日期", ""),
                                      weili.get("历史逾期次数", 0),
                                      weili.get("上次出催日期", "")))
            self.conn.commit()
        else:
            sql = "UPDATE weili_dai_information SET `total_overdue_amount`=%s,`settlement_amount`=%s,`total_overdue_principal`=%s,`total_overdue_interest`=%s,`total_overdue_penalty_interest`=%s,`cured_collected`=%s,`collection_stage`=%s,`overdue_days`=%s,`collection_start_date`=%s,`historical_overdue_count`=%s,`last_cure_date`=%s WHERE `id`=%s"
            self.cursor.execute(sql, (weili.get("逾期总金额", ""),
                                      weili.get("结清金额", 0.0), weili.get("逾期总本金", 0.0),
                                      weili.get("逾期总利息", 0.0),
                                      weili.get("逾期总罚息", 0.0), weili.get("是否治愈/出催", ""),
                                      weili.get("催收阶段", "")
                                      , int(weili.get("逾期天数", 0)), weili.get("入催日期", ""),
                                      weili.get("历史逾期次数", 0), weili.get("上次出催日期", ""), id))
            self.conn.commit()

    def work_info_pic2(self, id, pic2, money):
        # selectSql = "select * from info_save where `id` =%s and `money`=%s"
        # self.cursor.execute(selectSql, (id[-6:], money))
        selectSql = "select * from info_save where `id` =%s"
        self.cursor.execute(selectSql, (id,))
        row = self.cursor.fetchone()
        if row is None:
            sql = "INSERT INTO info_save (`id`,`info`,`insert_time`) VALUES (%s, %s,%s)"
            self.cursor.execute(sql, (id, pic2, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
            self.conn.commit()
        else:
            oldInfo = json.loads(row["info"])
            newInfo = json.loads(pic2)
            oldInfo.update(newInfo)  # 合并
            sql = "UPDATE info_save SET `info`=%s WHERE `id`=%s"
            self.cursor.execute(sql, (json.dumps(oldInfo, ensure_ascii=False), id))
            self.conn.commit()


if __name__ == '__main__':
    pass
    print(time.time())
    MODEL_TOKEN = "sk-1f6e80a2a0df40909f5c2b9d5f8df592"
    path = r"D:\Code\Python\pyutils\imgServerState\images\20251015170020e89d9ae8.png"
    w = ThreadAnayPngWork(MODEL_TOKEN, path)
    w.start()
    w.join()
    print(time.time())


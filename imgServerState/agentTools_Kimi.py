# -*- coding: utf-8 -*-
"""
Kimi-Vision 版 – 微粒贷图片信息提取示例
依赖：
    pip install requests pillow pymysql
"""

import base64
import json
import os
import re
import time
from threading import Thread
from PIL import Image
import pymysql
import requests
from PIL import Image

###############################################################################
# 一、通用工具
###############################################################################
class PicUtils:
    """图片裁剪+放大工具，逻辑不变"""
    @classmethod
    def crop_left_third_and_enlarge(
        cls,
        input_image_path: str,
        output_image_path: str = None,
        scale_factor: int = 3,
    ) -> str:
        with Image.open(input_image_path) as img:
            w, h = img.size
            new_w = int(w / 3)
            crop_region = (0, 0, new_w, h)
            cropped = img.crop(crop_region)
            enlarged = cropped.resize(
                (new_w * scale_factor, h * scale_factor), Image.LANCZOS
            )
            if not output_image_path:
                dir_, name = os.path.split(input_image_path)
                base, ext = os.path.splitext(name)
                output_image_path = os.path.join(
                    dir_, f"{base}_left_third_enlarged{ext}"
                )
            enlarged.save(output_image_path)
            print(f"[PicUtils] 已保存左侧 1/3 并放大 ×{scale_factor}：{output_image_path}")
            return output_image_path

    @classmethod
    def enlarge_x3(cls,src_path: str, dst_path="") -> str:
        """
        把原图整体放大 3 倍（非裁剪）
        :return: 放大后图片的绝对路径
        """
        with Image.open(src_path) as im:
            w, h = im.size
            new_size = (w * 2, h * 2)
            big = im.resize(new_size, Image.LANCZOS)

            if not dst_path:
                base, ext = os.path.splitext(src_path)
                dst_path = f"{base}_x2{ext}"

            big.save(dst_path)
            print(f"[enlarge_x3] 已保存 2 倍图：{dst_path}")
            return dst_path
###############################################################################
# 二、Kimi 官方接口封装
###############################################################################
KIMI_API_BASE = "https://api.moonshot.cn/v1"
VISION_MODEL = "moonshot-v1-8k-vision-preview"      # 带视觉能力的模型[^1^]


def kimi_vision_chat(api_key: str, images_path: list[str], prompt: str) -> str:
    """
    统一封装对 Kimi 的 vision 请求
    返回：模型返回的原始字符串（去掉 ```json 包裹）
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 1. 组装图片
    content = []
    for p in images_path:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
        )

    # 2. 追加文本 prompt
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": VISION_MODEL,
        "messages": [{"role": "user", "content": content}],
        # 官方建议：不设置 max_tokens 时默认自动截断；也可按需自行调整
    }

    resp = requests.post(
        f"{KIMI_API_BASE}/chat/completions", headers=headers, json=payload, timeout=60
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Kimi API 错误：{resp.status_code} {resp.text}")

    raw: str = resp.json()["choices"][0]["message"]["content"]
    print(raw)
    # 去掉可能的 ```json 包裹
    return re.sub(r"```(?:json)?\n(.*?)```", r"\1", raw, flags=re.S).strip()


###############################################################################
# 三、业务解析 + 重试
###############################################################################
class AgentsTools:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # 数据库连接
        self.conn = pymysql.connect(
            host="10.255.101.169",
            port=3306,
            user="root",
            passwd="cbf123456.",
            db="ioscar_info",
            charset="utf8mb4",
            use_unicode=True,
        )
        self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)

    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception:
            pass

    # -------------------- 主入口 -------------------- #
    def upload_image_base64(self, image_path: str, sizepath: str, msg=""):
        """解析主图 + 放大图，落库"""
        for i in range(5):
            try:
                time.sleep(2)
                clean = kimi_vision_chat(
                    self.api_key,
                    [image_path, sizepath],
                    self._build_vision_prompt() + msg,
                )
                data = json.loads(clean)
                print(data)
                break
            except Exception as e:
                print(f"[vision] 首次识别失败：{e}")
        key = self._get_weili(data)
        if key:  # 场景 1/3
            print(f"[vision] 第一个图片微粒贷号：{key}")
            if len(key) != 26 or key.startswith("DS05"):
                for i in range(3):
                    print(f"[vision] 长度异常，重试第 {i+1} 次…")
                    sizepath = PicUtils.crop_left_third_and_enlarge(image_path, scale_factor=3)
                    clean = kimi_vision_chat(
                        self.api_key,
                        [image_path, sizepath],
                        self._build_vision_prompt()
                        + "微粒贷号识别长度不足 26 位，请重新识别，微粒贷号从第二个图片识别即可",
                    )
                    data = json.loads(clean)
                    key = self._get_weili(data)
                    if len(key) == 26:
                        break

            card = self._get_card(data)
            if card and card[:4].find("*") > -1:
                for i in range(3):
                    sizepath = PicUtils.crop_left_third_and_enlarge(image_path,  scale_factor=3)
                    clean = kimi_vision_chat(
                        self.api_key,
                        [image_path, sizepath],
                        self._build_vision_prompt()
                        + "身份证号识别不符合要求规则，请重新识别，",
                    )
                    data = json.loads(clean)
                    card = self._get_card(data)
                    if card and card[:4].find("*") <= 0:
                        break

            DBTools(image_path).insert_or_update(key, clean)
        else:  # 场景 2
            key = self._get_weili_from_cust2(data)
            if key:
                print(f"[vision] 第二个图片微粒贷号：{key}")
                if len(key) != 26:
                    for i in range(3):
                        clean = kimi_vision_chat(
                            self.api_key,
                            [image_path],
                            self._build_vision_prompt()
                            + "微粒贷号识别不足 26 位，请重新识别，微粒贷号从第二个图片识别即可",
                        )
                        data = json.loads(clean)
                        key = self._get_weili_from_cust2(data)
                        if len(key) == 26:
                            break
                DBTools(image_path).work_info_pic2(key, clean)
            else:
                print("[vision] 未提取到微粒贷号码")

    # -------------------- prompt 模板 -------------------- #
    def _build_vision_prompt(self) -> str:
        return """
  请帮我识别上面图片中的数据 并按照我固定的数据格式进行输出
 如果要求的字段在图片中没有找到,请返回空字符串,而不是不包含这个字段
【识别的字段要求】
    1.客户信息
      数据结构要求:
      "客户信息":{
        "姓名":"界面上的姓名",
	    "年龄":"整数",
		"婚姻状态":"未婚",
		"身份证":"界面上的身份证号"
	    "工作单位":"界面上的工作单位"
	    "单位地址":"界面上的单位地址",
		"通讯地址":"界面上的通讯地址",
		"户籍地址":"界面上的户籍地址",
		"户籍地址2":"界面上的户籍地址2显示的内容",
		"学历":"界面上的学历",
		"绑卡手机":"界面上的显示内容"
	  }
	  
    2.微粒贷信息:
	  数据结构要求:
	  "微粒贷信息"{
		"微粒贷号":"DS开头的共计26个字符",
		"逾期总金额":"浮点数",
		"结清金额":"浮点数",
		"逾期总本金":"浮点数",
		"逾期总利息":"浮点数",
		"逾期总罚息":"浮点数",
		"是否治愈/出催）":"是/否"，
		"催收阶段":"委外阶段与界面字符保持一致",
		"逾期天数":"整数",
		"入催日期":"2025-07-14",
		"历史逾期次数":"整数",
		"上次出催日期":"日期格式,没有则为空",
		"是否上锁":"是/否"
	  }
	 3.催收员:
	数据结构要求:
	   {"催收员":"催收员不应该是客户信息,而是界面表格中的催收员那一列的第一个人的姓名"}
	 4.财务信息
	  数据结构要求:
	  "财务信息":{
	   "账单日":"整数",
	   "首次借款日期":"日期格式yyyy-mm-dd"
	   "案件类型":"界面上的字符串",
	   "信用额度":"整数",
	   "最近还款日期":"日期格式yyyy-mm-dd",
	   "最近还款金额":"浮点数",
	   "24期账龄":"整数",
	   "账龄":"整数",
	   "委托金额":"浮点数",
	   "委托本金":"浮点数",
	   "委托日期":"日期格式yyyy-mm-dd",
	   "委托到期日":"日期格式yyyy-mm-dd"，
	   "手别":"界面上的信息直接取 例如1手"
	  }
	  5.电话信息
	   数据结构要求:
	   "电话信息":[
	     {
		  "姓名":"XX",
		  "电话号码":"156xxxx"
		 }
	   
	   ]
	   如果界面没有数据格式就是
	   "电话信息":[]
	   6.还款指引
	   数据结构要求:
	    "还款指引":[
		  {
		    "还款类型":"转账还款",
			"渠道":"微信",
			"卡号":"界面读取到的信息",
			"收款行":"界面读取到的信息",
			"收款人":"界面读取到的信息"
		  }
		
		]
		7.地址信息
		数据结构要求:
		"地址信息":[
		 '上图中多列地址内容合并在一起并以,号隔开'
		]
 
        """

    # -------------------- 字段提取 -------------------- #
    @staticmethod
    def _get_weili(data: dict) -> str:
        for k, v in data.items():
            if k.startswith("微粒贷"):
                for kk, vv in v.items():
                    if kk.startswith("微粒贷") and vv:
                        return vv.replace("D5", "DS")
        return ""

    @staticmethod
    def _get_card(data: dict) -> str:
        return data.get("客户信息", {}).get("身份证", "")

    @staticmethod
    def _get_weili_from_cust2(data: dict) -> str:
        cust2 = data.get("客户信息2", {})
        if cust2:
            return cust2.get("微粒贷号", "").replace("D5", "DS")
        return ""


###############################################################################
# 四、数据库工具（保持你原逻辑，仅把表名/字段映射略作调整即可）
###############################################################################
class DBTools:
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.conn = pymysql.connect(
            host="10.255.101.169",
            port=3306,
            user="root",
            passwd="cbf123456.",
            db="ioscar_info",
            charset="utf8mb4",
            use_unicode=True,
        )
        self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)

    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception:
            pass

    def insert_or_update(self, id_: str, info: str):
        """主表 info_save 的 upsert"""
        # 你的原逻辑，此处略
        print("[DBTools] 落库完成", id_, self.image_path)
        selectSql = "select * from info_save where `id` = %s"
        self.cursor.execute(selectSql, (id_,))
        row = self.cursor.fetchone()
        err_type = self.check_card_weilidai(info)
        if row is None:
            sql = "INSERT INTO info_save (`id`,`info`,`insert_time`,`err_type`,`img_name`) VALUES (%s, %s,%s,%s,%s)"
            self.cursor.execute(sql, (
            id_, info, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), err_type, self.image_path))
            self.conn.commit()
            self.insert_detail(id_, json.loads(info))
        else:
            oldInfo = json.loads(row["info"])
            print("读取的信息:%s" % oldInfo)
            newInfo = json.loads(info)
            #开始遍历字典
            for k,v in newInfo.items():
                if k in oldInfo:
                    if len(oldInfo.get(k)) <len(info.get(k)):
                        oldInfo[k] = v
                else:
                    oldInfo[k] = v
            oldInfo.update(newInfo)  # 合并
            sql = "UPDATE info_save SET `info`=%s,`err_type`=%s,`img_name`=%s WHERE `id`=%s"
            self.cursor.execute(sql, (json.dumps(oldInfo, ensure_ascii=False), err_type, self.image_path, id_))
            self.conn.commit()
            self.insert_detail(id_, oldInfo)

    def check_card_weilidai(self, info):
        data = json.loads(info)
        weili = self.get_weili(data)
        if len(weili) != 26:
            return 1

        card = self.getcard(data)
        if card:
            if card[:4].find("*") > -1:
                return 2
        return 0

    def insert_detail(self, id, info):
        account = info.get("客户信息", {})
        # if account:
        #     self.work_people_info_table(account, id)
        # payment = info.get("账务信息", {})
        # # if payment:
        # #     self.work_payment_info_table(payment, id)
        # tel = info.get("电话信息", {})
        # if tel:
        #     self.work_tel_info_table(tel, id)
        # redirece = info.get("还款指引", {})
        # if redirece:
        #     self.work_redirece_info_table(redirece, id)
        # weili = info.get("微粒贷信息", {})
        # if weili:
        #     self.work_weili_info_table(weili, id)

    def get_weili(self, dictInfo):
        for key in dictInfo:
            if key.startswith("微粒贷"):
                weiliInfo = dictInfo[key]
                for data, value in weiliInfo.items():
                    if data.startswith("微粒贷"):
                        print("发现微粒贷信息:%s" % value)
                        if len(value) != 26:
                            print("微粒贷信息错误:%s" % len(value))
                        if value:
                            value = value.replace("D5", "DS")
                            return value
                        return ""

    def getcard(self, dictInfo):
        kData = dictInfo.get("客户信息", {})
        if kData:
            return kData.get("身份证", "")


###############################################################################
# 五、线程工作单元
###############################################################################
class ThreadAnayPngWork(Thread):
    def __init__(self, token: str, file_path: str):
        super().__init__()
        self.token = token
        self.file_path = file_path

    def run(self):
        agent = AgentsTools(self.token)
        oripath=PicUtils.enlarge_x3(self.file_path)
        size_path = PicUtils.crop_left_third_and_enlarge(self.file_path, scale_factor=3)
        agent.upload_image_base64(oripath, size_path, "微粒贷号从第二个图片中进行识别")


###############################################################################
# 六、入口
###############################################################################
if __name__ == "__main__":
    MODEL_TOKEN = "sk-8sSoJyflYCOENFgUx2WmYOtgks1diriBkqheh4f2JHg63UUl"  # 替换为你自己的
    PATH = r"D:\Code\Python\pyutils\imgServerState\images\4444444444444444444444.png"

    t = ThreadAnayPngWork(MODEL_TOKEN, PATH)
    t.start()
    t.join()
import json
import os
import random
from typing import List

import requests,logging,sys
from logging.handlers import TimedRotatingFileHandler
import time
from threading import Thread
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import functools
pool=ThreadPoolExecutor(max_workers=1)

# 自定义装饰器
def sleep(func):  # ① 装饰器函数定义，接收一个函数作为参数
    def wrapper(*args,**kwargs):   # ② 内部包装函数，接收任意参数
        time.sleep(random.choice([1,2]))  # ③ 随机等待1或2秒
        result=func(*args,**kwargs)   # ④ 执行原始函数
        return result  # ⑤ 返回原始函数的结果
    return wrapper   # ⑥ 返回包装函数

# 配置logger 日志输出格式
def get_logger(name: str = "demo"):
    """返回一个同时写控制台 + 滚动日志文件的 logger"""
    logger = logging.getLogger(name)
    if logger.hasHandlers():  # 避免重复
        return logger
    logger.setLevel(logging.DEBUG)  # 全局最低级别

    # ---------- 1. 控制台 ----------
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)  # 控制台只看 INFO 及以上
    console_fmt = logging.Formatter(
        "[%(asctime)s] | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # ---------- 2. 每天滚动日志文件 ----------
    # when="midnight" -> 每天 0 点切；interval=1 -> 间隔 1 天
    file_handler = TimedRotatingFileHandler(
        filename=f'logs/{name}_upload_{time.strftime("%Y%m%d_%H%M%S", time.localtime())}.log',  # 会自动创建 logs 目录
        when="midnight",
        interval=1,
        backupCount=5,  # 只留最近 5 天
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "[%(asctime)s] | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt = '%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger
# 自定义logger方法调用
loger=get_logger()

#将程序运行时间秒，格式化后展示
def format_time_string(seconds):
    """将秒数格式化为易读的字符串"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    if hours > 0:
        return f"{hours}小时{minutes}分{secs:.2f}秒"
    elif minutes > 0:
        return f"{minutes}分{secs:.2f}秒"
    else:
        return f"{secs:.4f}秒"

class WorkClient:
    LIST_EP   = "/api/case/self/list"
    DETAIL_EP = "/api/case/self/info"     # 新增：详情接口
    HOST = "https://otcn-out.saicfinance.com"
    DEFAULT_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": HOST,
        "Referer": f"{HOST}/CaseDetails_3",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/101.0.0.0 Safari/537.36"),
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Accept-Encoding": "gzip, deflate, br",
    }

    def __init__(self, token: str, timeout: int = 10, proxies: dict = None):
        self.token = token
        self.timeout = timeout
        self.proxies = proxies or {}
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.session.headers["Authorization"] = self.token

    # ------------------- 1. 列表（已有） -------------------
    @sleep
    def list_cases(self, current: int = 1, size: int = 500, **criteria) -> dict:
        payload = {
            "criteria": {
                "isSubordinate": True,
                "companyCode": "CBE",
                "institutionCode": "010100501",
                "caseStatusList": ["0", "1"],
                "caseAuthority": "RCMM000001",
                "entrustedDateB": "2026/03/01",
                "entrustedDateE": "2026/03/31",
                **criteria
            },
            "size": size,
            "current": current
        }
        resp = self.session.post(url=self.HOST + self.LIST_EP, json=payload, timeout=self.timeout, proxies=self.proxies)
        resp.raise_for_status()
        data=resp.json()
        loger.info("请求的地址是:" + self.HOST + self.LIST_EP)
        return data

    @sleep
    def fetch_all_pages(self, size_per_request: int = 20) -> list:
        all_records = []
        page = 1

        while True:
            resp = self.list_cases(current=page, size=size_per_request)
            data = resp.get("data", {})

            records = data.get("records", [])
            pages = data.get("pages", 0)

            if not records:
                break

            all_records.extend(records)
            loger.info(
                f"第 {page}/{pages} 页，获取 {len(records)} 条，累计 {len(all_records)} 条"
            )

            if page >= pages:
                break

            page += 1

        return all_records


    @sleep
    # ------------------- 2. 详情（新增） -------------------
    def case_detail(self, case_code: str, debtor_id: str, payment_id: str,
                    batch_code: str, path_id: str = "/CMM000006",
                    shild_bank: bool = True) -> dict:
        """
        获取单条案件详情
        参数与 curl 一一对应，可动态覆盖
        """
        payload = {
            "caseCode": case_code,
            "debtorId": debtor_id,
            "paymentId": payment_id,
            "batchCode": batch_code,
            "pathId": path_id,
            "shildBank": shild_bank,
        }
        resp = self.session.post(
            url=self.HOST + self.DETAIL_EP,
            json=payload,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        datas=resp.json().get("data",{})
        for data in datas:
            caseccode=data["caseCode"]
            if caseccode==case_code:
                return data
        return resp.json().get("data",{})[0]

    # ------------------- 3. 获取姓名（新增） -------------------
    @sleep
    def get_name(self, debtor_id: str) -> str:
        """
        根据 debtorId 获取姓名（纯文本接口）
        :param debtor_id: 债务人ID
        :return: 姓名字符串
        """
        url = f"{self.HOST}/api/plaintext/name/{debtor_id}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        # 接口返回纯文本，去掉首尾空格
        return resp.json().get("data","") # 返回姓名

    @sleep
    def blacklist_phone_way(self, phone_id_list: list[str]) -> dict:
        """
        根据 phoneIdList 查询黑名单电话方式
        :param phone_id_list: 电话 ID 列表（元素为字符串）
        :return: 接口返回的 JSON 数据
        """
        payload = {
            "phoneIdList": phone_id_list
        }
        resp = self.session.post(
            url=f"{self.HOST}/api/blacklist/select/phoneNumber/way",
            json=payload,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------- 5. 获取手机号（新增） -------------------
    @sleep
    def get_phone(self, phone_id: str) -> str:
        """
        根据 phoneId 获取手机号纯文本
        :param phone_id: 电话 ID
        :return: 手机号字符串（已 strip）
        """
        url = f"{self.HOST}/api/plaintext/phone/{phone_id}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json().get("data","")

    # ------------------- 7. 获取户籍地（新增） -------------------
    @sleep
    def get_homeland(self, citizen_id: str) -> str:
        """
        根据 citizenId（debtorId）获取户籍地纯文本
        :param citizen_id: 公民身份证哈希（debtorId）
        :return: 户籍地字符串（已 strip）
        """
        url = f"{self.HOST}/api/plaintext/homeland/{citizen_id}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    # ------------------- 8. 获取现住址（新增） -------------------
    @sleep
    def get_now_address(self, citizen_id: str) -> str:
        """
        根据 citizenId（debtorId）获取现住址纯文本
        :param citizen_id: 公民身份证哈希（debtorId）
        :return: 现住址字符串（已 strip）
        """
        url = f"{self.HOST}/api/plaintext/now_address/{citizen_id}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    # ------------------- 9. 获取工作单位地址（新增） -------------------
    @sleep
    def get_job_address(self, citizen_id: str) -> str:
        """
        根据 citizenId（debtorId）获取工作单位地址纯文本
        :param citizen_id: 公民身份证哈希（debtorId）
        :return: 工作单位地址字符串（已 strip）
        """
        url = f"{self.HOST}/api/plaintext/job_address/{citizen_id}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json()["data"]
    @sleep
    def get_relationship_list(self, citizen_id: str, case_code: str, page: int = 1) -> dict:
        """
        根据 citizenId、caseCode、page 获取关系人列表
        :param citizen_id: 公民身份证哈希（debtorId）
        :param case_code: 案件编号
        :param page: 页码，默认 1
        :return: 接口返回的完整 JSON（含 resultCode / data / relationshipList ...）
        """
        url = f"{self.HOST}/api/relationship/list/{citizen_id}/{case_code}/{page}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json()
    # ------------------- 6. 获取本人联系方式列表（新增） -------------------
    @sleep
    def relation_way_list(self, debtor_id: str, page: int = 1, case_code: str = "") -> dict:
        """
        获取指定 citizenId（debtorId）的本人联系方式列表
        :param debtor_id:   公民身份证哈希（citizenId）
        :param page:        页码，从 1 开始
        :param case_code:   案件编号（URL 第三段）
        :return:            接口返回的完整 JSON（含 resultCode / data / relationWayList ...）
        """
        # URL 路径：/api/relationway/list/{debtorId}/{page}/{case_code}
        url = f"{self.HOST}/api/relationway/list/{debtor_id}/{page}/{case_code}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------- 11. 获取全部关系人列表（新增） -------------------
    @sleep
    def get_relationway_list_all(self, citizen_id: str, institution_code: str) -> dict:
        """
        根据 citizenId、institutionCode 获取全部关系人列表（不分页）
        :param citizen_id: 公民身份证哈希（debtorId）
        :param institution_code: 机构编号
        :return: 接口返回的完整 JSON（含 resultCode / data / relationshipList ...）
        """
        url = f"{self.HOST}/api/relationway/listAll/{citizen_id}/{institution_code}"
        resp = self.session.get(
            url=url,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        resp.raise_for_status()
        return resp.json()
    def writeToExcel(self,datas:List,maxNumbser:int,start_time):
        newDataExcel=[]
        # try:
        #     os.remove("合同全部联系人.xlsx")
        # except Exception as e:
        #     pass
        for item in datas:
            base={
                "合同编号": item["合同编号"],
                "委托时预期金额": item["委托时预期金额"],
                "债务人姓名": item["债务人姓名"],
                "逾期天数": item["逾期天数"],
                "车价": item["车价"],
                "户籍所在详细地址": item.get("户籍所在详情地址",""),
                "现居住详细地址": item["现居住详细地址"],
                "工作单位": item.get("工作单位",""),
                "单位所在详细地址": item["单位所在详细地址"],
                "贷款金额": item["贷款金额"],
                "当前剩余本金": item["当前剩余本金"],
            }
            for idx, contact in enumerate(item["联系信息"][:maxNumbser], 1):
                base[f"联系关系{idx}"] = contact.get("联系关系", "")
                base[f"联系人{idx}"] = contact.get("联系人", "")
                base[f"联系类型{idx}"] = contact.get("联系类型", "")
                base[f"联系方式{idx}"] = contact.get("联系方式", "")
                # 不足 MAX_CONTACT 的列留空
            for idx in range(len(item["联系信息"]) + 1, maxNumbser + 1):
                base[f"联系关系{idx}"] = ""
                base[f"联系人{idx}"] = ""
                base[f"联系方式{idx}"] = ""
                base[f"联系类型{idx}"] = ""
            newDataExcel.append(base)
        df = pd.DataFrame(newDataExcel)
        current_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        df.to_excel(f"合同全部联系人_{current_time}.xlsx", index=False, engine="openpyxl")
        end_time = time.time()
        elapsed_time = end_time - start_time
        # print(f"已写入 合同全部联系人_{current_time}.xlsx,\t程序运行花费时间: {format_time_string(elapsed_time)},\t总计写入数据:{len(newDataExcel)}组")
        loger.info(f"已写入 合同全部联系人_{current_time}.xlsx,\t程序运行花费时间: {format_time_string(elapsed_time)},\t总计写入数据:{len(newDataExcel)}组")
class TWork:
    def work(self,client,index,collectlist,maxNumber,c=None):
        self.client = client
        self.index = index
        self.collect = collectlist
        client=self.client
        cases = client.fetch_all_pages(size_per_request=20)
        loger.info("共获取" + str(len(cases)) + "条案件")
        for case in cases:
            loger.info("首条示例：" + json.dumps(case, ensure_ascii=False, indent=4))
            baseData = {}
            collectList.append(baseData)
            baseData["合同编号"] = case["caseFileNo"]
            detail = client.case_detail(
                case_code=case["caseCode"],
                debtor_id=case["debtorId"],
                payment_id=case["paymentId"],
                batch_code=case["batchCode"],
            )
            institutionCode=detail.get('institutionCode',"")
            loger.info("案件详情:" + json.dumps(detail, ensure_ascii=False, indent=2))
            baseData["委托时预期金额"] = detail["caseAmount"]
            nameResult = client.get_name(detail["debtorId"])
            baseData["债务人姓名"] = nameResult
            baseData["联系信息"] = []
            baseData["车价"]=detail.get("otherInfoMap",{}).get("车价")
            baseData["贷款金额"] = detail.get("otherInfoMap", {}).get("贷款金额")
            baseData["当前剩余本金"] =detail.get("remainPrincipal")
            baseData["逾期天数"] = detail.get("overdueDays")
            baseData["工作单位"]=detail.get("otherInfoMap",{}).get("工作单位")
            cityId=detail.get("id")
            baseData["户籍所在详情地址"]=client.get_homeland(cityId)
            baseData["单位所在详细地址"]=client.get_job_address(cityId)
            baseData["现居住详细地址"]=client.get_now_address(cityId)

            # resultData = client.get_relationway_list_all(case["debtorId"], institutionCode)
            # resultData = client.relation_way_list(case["debtorId"], 1, case["caseCode"])
            #这是自己
            allRelations=[]
            resultData = client.relation_way_list(case["debtorId"], 1,case["caseCode"])
            releaList = resultData.get("data", {}).get("relationWayList")
            allRelations.extend(releaList)
            #这是其他人
            resultData = client.get_relationship_list(case["debtorId"], case["caseCode"], 1)
            releaList = resultData.get("data", {})
            allRelations.extend(releaList)
            nowMax = len(allRelations)
            maxNumber = max(nowMax, maxNumber)
            for relation in allRelations:
                infoBase = {}
                infoBase["联系类型"]=relation["relationWayTypeName"]
                infoBase["联系关系"] = relation["relation"]
                infoBase["联系人"] = client.get_name(relation["citizenId"])
                infoBase["联系方式"] = client.get_phone(relation["relationWayId"])
                baseData["联系信息"].append(infoBase)
            loger.info(json.dumps(baseData, indent=2, ensure_ascii=False))
# ----------------- 快速测试 -----------------

if __name__ == "__main__":
    strat_time = time.time()
    token = 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJocnhscyIsImF1ZGllbmNlIjoid2ViIiwiY3JlYXRlZCI6MTc3MjQyOTYzNTg4OSwiZXhwIjoxNzczMDM0NDM1fQ.Z6nQzGohehgjga0bDsuKsKqjf1t8qI82l7pX2xYalcJjIK8FpeW_3R4mk-dW0cc5NI7nlih7dwvAW8aQPQt_1g'
    client = WorkClient(token=token)
    collectList=[]
    maxNumber=7
    workJoin=[]
    t=TWork()
    # for i in range(1,2):
    t.work(client,1,collectList,maxNumber)
    client.writeToExcel(collectList,maxNumber,strat_time)


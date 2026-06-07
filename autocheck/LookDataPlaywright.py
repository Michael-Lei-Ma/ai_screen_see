# -*- coding: utf-8 -*-
import json
import sys
from datetime import date, timedelta,datetime
from logging.handlers import TimedRotatingFileHandler

import os, tempfile, subprocess
import traceback
import time,requests
from playwright.sync_api import sync_playwright
import logging


projectPath=os.path.dirname(__file__)+os.sep
chrome_path =projectPath+os.sep+"chrome"+os.sep+"chrome.exe"        # 你的绿色版
driver_path = projectPath+os.sep+"driver"+os.sep+"chromedriver.exe"  # 对应版本驱动
config_file = projectPath+os.sep+"config"+os.sep+"LookDataConfig.json"
png_folder= projectPath+os.sep+"png"+os.sep
# if not os.path.isdir(png_folder):
#     os.mkdir(png_folder)
os.makedirs(png_folder,exist_ok=True)
err_png_folder = png_folder+"error_png"+os.sep
os.makedirs(png_folder,exist_ok=True)

WORK_PATH=os.path.dirname(chrome_path)
webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4"
targetUrl=""
#获取当前文件名 不含扩展名
current_file_name = os.path.splitext(os.path.basename(__file__))[0]


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
        "[%(asctime)s] %(levelname)-8s | %(name)s | %(lineno)d  | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    current_project_path = os.path.dirname(__file__)
    logs_path = os.path.join(current_project_path,'logs')
    os.makedirs(logs_path, exist_ok=True)

    # ---------- 2. 每天滚动日志文件 ----------
    # when="midnight" -> 每天 0 点切；interval=1 -> 间隔 1 天
    file_handler = TimedRotatingFileHandler(
        filename=f'{logs_path}/{current_file_name[:8]}.log',  # 会自动创建 logs 目录
        when="midnight",  # 每天午夜滚动
        interval=1, # 间隔数量，与 when 共同决定轮转周期
        backupCount=5,  # 只留最近 5 份
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt =logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(name)s | %(lineno)d  | %(message)s ",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger

logger=get_logger()
class AlertTools:
    @classmethod
    def send_robot(cls,text, at_mobiles=None):
        """
        企业微信群机器人发文本
        :param webhook: 机器人 Webhook 地址
        :param text: 文本内容
        :param at_mobiles: 要@的手机号列表，填 ["@all"] 全员
        """
        body = {
            "text": "浦发"+text
        }
        try:
            resp = requests.post("http://10.255.100.202:8000/alert", json=body, timeout=30)
            logger.info(resp.json())
        except Exception as e:
            logger.error(e)
            return {"errcode": 1, "errmsg": str(e)}

class ReadConfigUtil:
    configJson={}
    @classmethod
    def loadFile(cls):
        with open(config_file, "r", encoding="utf-8") as f:
            cls.configJson = json.loads(f.read())
            logger.info("加载配置文件完毕:"+json.dumps(cls.configJson))
    @classmethod
    def getFileByKey(cls,key):
        logger.info("获取key:"+key)
        return cls.configJson.get(key)
    @classmethod
    def getDesc(cls,key):
        logger.info("获取key:" + key)
        return cls.configJson.get(key,{}).get("desc")

    @classmethod
    def getLocator(cls, key):
        logger.info("获取key:" + key)
        return cls.configJson.get(key, {}).get("locator")


class WorkAgent:
    def click(self,xpath,desc,ignore=False):
        try:
            logger.info("正在点击%s" % desc)
            handler = self.page.locator(xpath).element_handle()
            self.page.evaluate("el => el.click()", handler)
            time.sleep(4)
            logger.info("点击成功%s" % desc)
        except Exception as e:
            traceback.print_exc()
            if not ignore:
                pngname=time.strftime("%Y_%m_%d_%H%M%S",time.localtime())
                self.page.screenshot(path=err_png_folder+pngname + ".png")
                AlertTools.send_robot("点击定位%s"%desc+"失败了,请排查")
            return

    def fill_value(self,xpath,value,desc):
        try:
            logger.info("正在点击%s" % desc)
            self.page.locator(xpath).fill(value)
            time.sleep(1)
            logger.info("点击成功%s" % desc)
        except Exception as e:
            traceback.print_exc()
            AlertTools.send_robot("点击定位%s" % desc + "失败了,请排查")
            return
    def click_by_index(self,xpath,index,desc):
        logger.info(f"开始点击{desc}->{xpath}")
        self.page.locator(xpath).nth(index).click()
        logger.info(f"点击完毕{desc}->{xpath}")
        time.sleep(1)

    def type_by_index(self, xpath, index,desc, value):
        logger.info(f"开始点击{desc}->{xpath}")
        self.page.locator(xpath).nth(index).fill(value)
        time.sleep(2)
        logger.info(f"点击完毕{desc}->{xpath}")
    def kill_chrome(self):
        time.sleep(5)
        try:
            subprocess.check_output("taskkill /f /im chrome.exe", shell=True)
        except Exception as e:
            print(e)
        try:
            subprocess.check_output("taskkill /f /im Google.exe", shell=True)
        except Exception as e:
            print(e)
    def __init__(self):
        self.kill_chrome()
        # subprocess.Popen("chrome.exe", shell=True, cwd=WORK_PATH)
        subprocess.Popen("chrome.exe --remote-debugging-port=9222", shell=True, cwd=WORK_PATH)

        time.sleep(5)

    def open_browser(self):
        p=self.P=sync_playwright().start()
        # 1. 连接到本地已启动的 Chrome（--remote-debugging-port=9222）
        browser = self.driver =p.chromium.connect_over_cdp("http://127.0.0.1:9222")

        logger.info("开始启动连接driver成功")
        # 如果只想用第一个打开的页面，可直接取 context.pages[0]
        # 否则新建一个标签页
        if not browser.contexts:
            context = browser.new_context()
        else:
            context = browser.contexts[0]
        page = self.page=context.pages[0] if context.pages else context.new_page()

        # 2. 设置默认最大等待时间 80 秒（相当于 Selenium 的 implicitly_wait）
        # 3. 打开网址
        page.set_default_timeout(8000)
        page.set_default_navigation_timeout(8000)
        page.goto(ReadConfigUtil.getFileByKey("Web-Url"))
        logger.info("打开网页成功")
        self.click("//*[text()='退出']","退出",True)
        self.click('//span[contains(text(),"确定")]',"确定",True)
    def get_yesterday(self) -> str:
        """返回昨天的日期（date 类型）"""
        lastday = date.today() - timedelta(days=1)
        return lastday.strftime("%Y-%m-%d")
    def do_detail(self):
        self.type_by_index(ReadConfigUtil.getLocator("username"),0,
                           ReadConfigUtil.getDesc("username"),ReadConfigUtil.getFileByKey("usernamevalue"))
        self.type_by_index(ReadConfigUtil.getLocator("password"), 1,
        ReadConfigUtil.getDesc("password"),ReadConfigUtil.getFileByKey("passwordvalue"))
        #
        time.sleep(1)
        # AlertTools.send_robot("点击进行中")
        keyboard=self.page.keyboard
        keyboard.press("Enter")
        time.sleep(3)
        # self.click(ReadConfigUtil.getLocator("login-btn"), ReadConfigUtil.getDesc("login-btn"))
        self.click(ReadConfigUtil.getLocator("left-btn"), ReadConfigUtil.getDesc("left-btn"))
        self.click(ReadConfigUtil.getLocator("ts-btn"), ReadConfigUtil.getDesc("ts-btn"))

        self.click(ReadConfigUtil.getLocator("time-input"),ReadConfigUtil.getDesc("time-input"))

        self.click(ReadConfigUtil.getLocator("time-input-select"), ReadConfigUtil.getDesc("time-input-select"))
        hour=time.localtime().tm_hour
        if hour<10:
            self.type_by_index(ReadConfigUtil.getLocator("begin-time"), 0,
            ReadConfigUtil.getDesc("begin-time"), self.get_yesterday()+" 00:00:00")

            self.type_by_index(ReadConfigUtil.getLocator("end-time"), 0,ReadConfigUtil.getDesc("begin-time"),
                              self.get_yesterday()+" 23:59:59")
        else:
            now=time.strftime("%Y-%m-%d",time.localtime())
            self.type_by_index(ReadConfigUtil.getLocator("begin-time"), 0,
                               ReadConfigUtil.getDesc("begin-time"),now)

            self.type_by_index(ReadConfigUtil.getLocator("end-time"), 0, ReadConfigUtil.getDesc("begin-time"),
                               now)
        self.page.keyboard.press("Enter")

        self.click(ReadConfigUtil.getLocator("cui-shou"), ReadConfigUtil.getDesc("cui-shou"))
        #点击搜索
        self.click(ReadConfigUtil.getLocator("search-btn"), ReadConfigUtil.getDesc("search-btn"))
        #获取页码
        pngname = time.strftime("%Y_%m_%d_%H%M%S", time.localtime())
        self.page.screenshot(path=png_folder+pngname + ".png")
        self.click(ReadConfigUtil.getLocator("page-count"), ReadConfigUtil.getDesc("page-count"))
        #选择100页码
        self.click(ReadConfigUtil.getLocator("100"), ReadConfigUtil.getDesc("100"))
        time.sleep(4)
        text=self.page.locator(ReadConfigUtil.getLocator("last-page")).last.inner_text()
        for i in range(int(text)-1):
            self.click(ReadConfigUtil.getLocator("next-btn"), ReadConfigUtil.getDesc("next-btn"),True)
            time.sleep(3)
    def save_screen(self):
        pngname = time.strftime("%Y_%m_%d_%H%M%S", time.localtime())
        self.page.screenshot(path=png_folder +f"{current_file_name[:8]}_"+ pngname + ".png")
    def done_work_over(self):
        try:
            self.save_screen()
            self.page.keyboard.press("Alt+F4")
            self.page.close()
            self.P.stop()
            # self.kill_chrome()
        except Exception as e:
            print(e)
if __name__ == '__main__':
    AlertTools.send_robot("定时点击开始")
    ReadConfigUtil.loadFile()
    agent=WorkAgent()
    agent.open_browser()
    agent.do_detail()
    agent.done_work_over()
    AlertTools.send_robot("定时点击结束")
    logger.info("程序完整运行结束了")

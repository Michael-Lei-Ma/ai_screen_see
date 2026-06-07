import json
import sys
from codecs import ignore_errors
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
import logging
import os,subprocess
import time,requests
import traceback
from tools.excel_operat import GetFileStatus
from tools.format_config import ClearExpiredFile,GetFilePath

"""
    招行下载到本地的文件，对应业务含义: 
        经办维度明细.xlsx  -- >  慧见下载
        经办外呼操作明细.xlsx --> 经办下载
"""


projectPath=os.path.dirname(__file__)+os.sep
# chrome_path =projectPath+os.sep+"chrome"+os.sep+"Google.exe"        # 你的绿色版
chrome_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe"
driver_path = projectPath+os.sep+"driver"+os.sep+"chromedriver.exe"  # 对应版本驱动
config_file = projectPath+os.sep+"config"+os.sep+"UploadScript.json" #配置文件
WORK_PATH=os.path.dirname(chrome_path)#启动goole
downloadFolder=projectPath+os.sep+"download"
if not os.path.exists(downloadFolder):os.mkdir(downloadFolder)
png_folder= projectPath+os.sep+"png"+os.sep
if not os.path.isdir(png_folder):
    os.mkdir(png_folder)

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
        "[%(asctime)s] %(levelname)s | %(name)s | %(lineno)d | %(threadName)s | %(message)s ",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # ---------- 2. 每天滚动日志文件 ----------
    # when="midnight" -> 每天 0 点切；interval=1 -> 间隔 1 天
    file_handler = TimedRotatingFileHandler(
        filename=f"logs/{name}_upload.log",  # 会自动创建 logs 目录
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
           "text":"招行->"+text
        }
        try:
            targeturl=ReadConfigUtil.getValueByKey("alert-url")
            logger.info(f"target-url->{targeturl}")
            resp = requests.post("http://10.255.100.202:8000/alert", json=body, timeout=30,verify=False)
            data=resp.json()
            logger.info(data)
        except Exception as e:
            logger.info(e)
            return {"errcode": 1, "errmsg": str(e)}
class ReadConfigUtil:
    configJson={}
    @classmethod
    def loadFile(cls):
        with open(config_file, "r", encoding="utf-8") as f:
            cls.configJson = json.loads(f.read())
            logger.info("加载配置文件完毕:"+json.dumps(cls.configJson))
    @classmethod
    def getValueByKey(cls, key):
        logger.info("获取key:"+key)
        return cls.configJson.get(key,"")
    @classmethod
    def getDesc(cls,key):
        logger.info("获取key:" + key)
        return cls.configJson.get(key,{}).get("desc")

    @classmethod
    def getLocator(cls, key):
        logger.info("获取key:" + key)
        return cls.configJson.get(key, {}).get("locator")
class DmcUploader:
    """DMC 文件导入接口封装"""
    # 如 token 会过期，可改成参数或在方法内刷新

    UPLOAD_URL_TEMPLATE=""
    @staticmethod
    def upload(file_path: str | Path, metadata_id: str,text) -> None:
        """
        上传文件到 DMC 导入接口
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
            url = DmcUploader.UPLOAD_URL_TEMPLATE.format(metadata_id=metadata_id)
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
                logger.info(
                    f"{text}-API 请求后响应结果 状态码: {resp.status_code}\n响应头: {resp.headers}\n响应结果: {resp.content}\n{resp.text}\n")
                if resp.status_code == 204:
                    logger.info(f"{text}-文件上传成功")
                    AlertTools.send_robot(f"{text}-上传完毕")
                    break
                else:
                    retry_count += 1
                    logger.info(f"第 {retry_count} 次 {text}-文件上传失败")
                    if retry_count == 3:
                        AlertTools.send_robot(f"尝试 {retry_count} 次，{text}-文件上传失败，调用服务 {resp.status_code}，请人工查看！")
                    time.sleep(10)
                    continue
        except Exception as e:
            logger.error(f"文件上传异常-{e}")
            AlertTools.send_robot(f"{text}-上传失败")
            return
        return None
class PlaywrightWork:
    def click_by_xpath(self,xpath,desc,ignore=False):
        try:
            logger.info("开始点击 %s xpath->%s"%(desc,xpath))
            self.page.locator(xpath).click(delay=500)
            time.sleep(2)
            logger.info("结束点击 %s %s" % (desc, xpath))
        except:
            if not ignore:
                pngname = time.strftime("%Y_%H_%D_%H%M%S", time.localtime())
                self.page.screenshot(path=pngname + ".png")
                AlertTools.send_robot("点击"+desc+"失败了,请排查")
            return

    def click_by_xpath_inner_iframe(self,iframe,xpath, desc):
        try:
            logger.info("开始点击 %s xpath->%s" % (desc, xpath))
            iframe.locator(xpath).click(delay=500)
            time.sleep(2)
            logger.info("结束点击 %s %s" % (desc, xpath))
        except:
            AlertTools.send_robot("点击" + desc + "失败了,请排查")
            return
    def hover_by_xpath_inner_iframe(self,iframe,xpath, desc,index=0):
        try:
            logger.info("开始hover %s xpath->%s" % (desc, xpath))
            loc = iframe.locator(xpath)
            if loc.count()>1:
                loc.nth(index).hover()
            else:
                loc.hover()
            iframe.page.wait_for_timeout(1000)  # 悬停后停 1 秒
            logger.info("结束hover %s %s" % (desc, xpath))
        except:
            # AlertTools.send_robot("hover" + desc + "失败了,请排查")
            return
    def fill_by_xpath(self, xpath, value,desc,ignore=False):
        try:
            logger.info("针对输入框"+xpath+" " +desc+"填写"+value)
            time.sleep(1)
            target=self.page.locator(xpath)
            target.fill(value)
            time.sleep(1)
            # target.clear()
            # target.type(value,delay=80)
        except Exception as e:
            if not ignore:
                AlertTools.send_robot("填写" + desc + "失败了,请排查")
            return
    def kill_chrome(self):
        try:
            subprocess.check_output("taskkill /f /im chrome.exe", shell=True)
            subprocess.check_output("taskkill /f /im Google.exe", shell=True)
        except Exception as e:
            print(e)
    def __init__(self):
        self.kill_chrome()
        subprocess.Popen(r"chrome.exe --remote-debugging-port=9222", shell=True, cwd=WORK_PATH)
        time.sleep(8)
        p=self.p=sync_playwright().start()
        browser = self.driver =p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        AlertTools.send_robot("开始启动连接driver成功")
        # 如果只想用第一个打开的页面，可直接取 context.pages[0]
        # 否则新建一个标签页
        if not browser.contexts:
            context = browser.new_context()
        else:
            print("使用旧的网页")
            context = browser.contexts[0]
        # context = browser.new_context()
        # page=self.page=context.new_page()
        # print(page)
        page = self.page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(60000) # 页面超时30秒
        page.set_default_navigation_timeout(60000) # 导航超时30秒
        page.goto(ReadConfigUtil.getValueByKey('Web-Url'))
        # page.goto("https://www.baidu.com")
        # page.goto("http://10.255.100.202:9000/ok")
        logger.info(ReadConfigUtil.getValueByKey("Web-Url"))
        # c=input("input")
    def do_dowloadwork_hui(self):
        self.login()
        self.enter_left_btn()
        self.enter_right_iframe()
    def do_downloadwork__jingban(self):
        self.page.goto(ReadConfigUtil.getValueByKey('Web-Url'))
        self.enter_left_jingban()
    def enter_left_jingban(self):
        self.click_by_xpath(ReadConfigUtil.getLocator("left-cui-btn"), ReadConfigUtil.getDesc("left-cui-btn"))
        self.click_by_xpath(ReadConfigUtil.getLocator("left-workmng-btn"), ReadConfigUtil.getDesc("left-workmng-btn"))
        self.click_by_xpath(ReadConfigUtil.getLocator("left-data-btn"), ReadConfigUtil.getDesc("left-data-btn"))
        self.click_by_xpath(ReadConfigUtil.getLocator("left-call-btn"), ReadConfigUtil.getDesc("left-call-btn"))

        iframe2=self.page.frame_locator(ReadConfigUtil.getValueByKey("iframe-2"))
        time.sleep(5)
        self.hover_by_xpath_inner_iframe(iframe2,ReadConfigUtil.getLocator("table"),
                                         ReadConfigUtil.getDesc("table"),0)

        iframe2.locator(ReadConfigUtil.getLocator("down-icon")).nth(1).click()
        self.click_by_xpath_inner_iframe(iframe2,ReadConfigUtil.getLocator("excel"),
                                         ReadConfigUtil.getDesc("excel"))
        logger.info("等待3秒进入数据中心")
        time.sleep(3)
        logger.info("寻找进入数据中心的图标")
        iframe2.locator(ReadConfigUtil.getLocator("data-center")).nth(1).click()

        # 防止下载文件为空，增加重试机制 默认3次
        download_count = 0
        download_timeout_count = 3
        while download_count < download_timeout_count:
            with self.page.expect_download() as d:
                self.click_by_xpath_inner_iframe(iframe2, ReadConfigUtil.getLocator('td'),
                                                 ReadConfigUtil.getDesc('td'))
            # 获取下载对象
            download = d.value
            time_str = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
            try:
                # 创建文件夹
                os.mkdir(downloadFolder + "/" + time_str)
            except Exception as e:
                pass
            # 拼接下载到的保存文件路径
            final_path = Path(downloadFolder+"/"+time_str) / download.suggested_filename
            if final_path.exists():
                os.remove(final_path)
            # 将已下载的文件保存到指定的完整路径
            download.save_as(final_path)

            # 判断文件下载状态，下载完成True，等待60s
            if GetFileStatus.wait_for_download_complete(final_path, timeout=60):
                if final_path.stat().st_size <= 0:
                    logger.info(f"文件保存不完整: {final_path} 文件大小为 {final_path.stat().st_size} 字节")
                    raise IOError(f"文件保存不完整: {final_path} 为空文件")
                logger.info(f"文件保存完整: {final_path} 文件大小为{final_path.stat().st_size / 1024:.2f} KB ")
                break
            else:
                logger.info(f"文件第 {download_count+1} 次下载超时")
                download_count+=1
                continue

        # 相对路径转化为绝对路径，判断路径是否存在，不存在抛异常
        final_path.resolve(strict=True)
        logger.info("下载完成 →%s" % str(final_path))
        DmcUploader.UPLOAD_URL_TEMPLATE = ReadConfigUtil.getValueByKey("Upload-url")
        DmcUploader.upload(str(final_path), ReadConfigUtil.getValueByKey("ZS-JingBan"),
                           "经办外呼")

    def login(self):
        self.fill_by_xpath(ReadConfigUtil.getLocator("username"),
                           ReadConfigUtil.getValueByKey("usernamevalue"),
                           ReadConfigUtil.getDesc("username"),True
                           )
        self.fill_by_xpath(ReadConfigUtil.getLocator("password"),
                           ReadConfigUtil.getValueByKey("passwordvalue"),
                           ReadConfigUtil.getDesc("password"),True)

        self.click_by_xpath(ReadConfigUtil.getLocator("login-btn"),ReadConfigUtil.getDesc("login-btn"))
        self.click_by_xpath(ReadConfigUtil.getLocator("i-know"), ReadConfigUtil.getDesc("i-know"),True)
        AlertTools.send_robot(f"登录成功")

    def save_screen(self):
        pngname = time.strftime("%Y_%m_%d_%H%M%S", time.localtime())
        self.page.screenshot(path=png_folder + pngname + ".png")
    def close(self):
        time.sleep(3)
        self.save_screen()
        self.page.keyboard.press("Alt+F4")
        try:
            self.page.close()
        except Exception as e:
            pass
        try:
            time.sleep(3)
            self.p.stop()
        except Exception as e:
            pass

    def enter_left_btn(self):
        self.click_by_xpath(ReadConfigUtil.getLocator("left-cui-btn"),ReadConfigUtil.getDesc("left-cui-btn"))
        self.click_by_xpath(ReadConfigUtil.getLocator("manage-btn"), ReadConfigUtil.getDesc("manage-btn"))
        self.click_by_xpath(ReadConfigUtil.getLocator("hui-jian"), ReadConfigUtil.getDesc("hui-jian"))

    def enter_right_iframe(self):
        logger.info("等待加载开始")
        time.sleep(2)
        logger.info("等待加载完毕")
        iframe=self.page.frame_locator(ReadConfigUtil.getValueByKey("iframe-1"))

        if self.get_now_hour()<10:
            iframe.locator(ReadConfigUtil.getLocator("begin-time")).fill(self.get_yesterday())
            iframe.locator(ReadConfigUtil.getLocator("end-time")).fill(self.get_yesterday())
        iframe.locator("//*[@placeholder='请输入经办员编']").clear()
        self.click_by_xpath_inner_iframe(iframe,ReadConfigUtil.getLocator("search-btn"),ReadConfigUtil.getDesc("search-btn"))

        # 防止下载文件为空，增加重试机制 默认3次
        download_count = 0
        download_timeout_count = 3
        while download_count < download_timeout_count:
            self.hover_by_xpath_inner_iframe(iframe, ReadConfigUtil.getLocator("d-button"),
                                             ReadConfigUtil.getDesc("d-button"))
            with self.page.expect_download() as d:
                self.click_by_xpath_inner_iframe(iframe, ReadConfigUtil.getLocator('d-button-jingban'),
                                                 ReadConfigUtil.getDesc('d-button-jingban'))
            download = d.value
            time_str = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
            try:
                os.mkdir(downloadFolder + "/" + time_str)
            except Exception as e:
                pass
            final_path = Path(downloadFolder + "/" + time_str) / download.suggested_filename
            if final_path.exists():
                os.remove(final_path)
            # 将已下载的文件保存到指定的完整路径
            download.save_as(final_path)

            # 判断文件下载状态，下载完成True，等待60s
            if GetFileStatus.wait_for_download_complete(final_path, timeout=60):
                if final_path.stat().st_size <= 0:
                    logger.info(f"文件保存不完整: {final_path} 文件大小为 {final_path.stat().st_size} 字节")
                    raise IOError(f"文件保存不完整：{final_path} 为空文件")
                logger.info(f"文件保存完整: {final_path} 文件大小为{final_path.stat().st_size / 1024:.2f} KB ")
                break
            else:
                logger.info(f"文件第 {download_count + 1} 次下载超时")
                download_count += 1
                continue

        final_path .resolve(strict=True)
        logger.info("下载完成 →%s"%str(final_path ))
        DmcUploader.UPLOAD_URL_TEMPLATE=ReadConfigUtil.getValueByKey("Upload-url")
        DmcUploader.upload(str(final_path),ReadConfigUtil.getValueByKey("ZS-HuiJian"),
                          "慧见")

    def get_yesterday(self) -> str:
        """返回昨天的日期（date 类型）"""
        lastday=date.today() - timedelta(days=1)
        return lastday.strftime("%Y%m%d")
    def get_now_hour(self):
        d=time.localtime()
        return d.tm_hour

if __name__ == '__main__':
    AlertTools.send_robot(f"开始运行")
    try:

        # 清除 download文件夹下过期历史数据，默认 保存最近 15天的
        target_dir = GetFilePath.get_folder_file_path('download')
        ClearExpiredFile(logger).delete_old_folders_by_time_format(root_dir=target_dir, time_format="%Y_%m_%d_%H_%M_%S",
                                                                   days_threshold=15,
                                                                   dry_run=False)
        ReadConfigUtil.loadFile()
        playwright=PlaywrightWork()
        playwright.do_dowloadwork_hui()
        playwright.do_downloadwork__jingban()
        playwright.close()
    except Exception as e:
        err_msg = traceback.format_exc()
        logger.error(f"程序运行异常 error info : {err_msg}")
        AlertTools.send_robot(f"程序运行异常，请人工查看！")
    AlertTools.send_robot(f"运行结束")


# -*- coding: utf-8 -*-

import time, requests,os,traceback,subprocess
from .format_config import AlertTools,GetFilePath
from playwright.sync_api import sync_playwright
import psutil

#页面操作
class PageLocator:
    '''
        : 进入网页后, 页面 click()、fill()、screenshot() 等操作 ;

    '''

    png_folder = GetFilePath.get_png_path(level_one_folder='png',create_folder=True)
    err_png_folder = GetFilePath.get_png_path(level_one_folder='png', level_two_folder='error_png',create_folder=True)

    def __init__(self,page,logger,current_file_name):
        self.page = page
        self.logger = logger
        self.current_file_name = current_file_name


    # xpath路径下，点击操作
    def click(self, xpath, desc, ignore=False):
        try:
            self.logger.info("正在点击%s" % desc)
            # 执行点击操作
            self.page.locator(xpath).click()
            time.sleep(2)
            self.logger.info("点击成功%s" % desc)
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"点击定位 {desc} 失败了,请排查! error info : {e}")
            if not ignore:
                self.save_screen(png_folder=self.err_png_folder)
                # 调用企微webhook API 发送操作异常步骤信息
                AlertTools.send_robot(current_file_name=self.current_file_name,
                                      text="点击定位%s" % desc + "失败了,请排查", logger=self.logger)

    # xpath路径下，标签链式调用，点击事件操作
    def click_by_index(self, xpath, index, desc,ignore=False):
        try:
            self.logger.info(f"链式开始点击{desc}->{xpath}")
            # 链式调用，在 xpath 路径下，指定下标下，点击操作
            self.page.locator(xpath).nth(index).click()
            self.logger.info(f"链式点击完毕{desc}->{xpath}")
            time.sleep(2)
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"链式点击定位 {desc} 失败了,请排查! error info : {e}")
            if not ignore:
                self.save_screen(png_folder=self.err_png_folder)
                # 调用企微webhook API 发送操作异常步骤信息
                AlertTools.send_robot(current_file_name=self.current_file_name,
                                      text="链式点击定位%s" % desc + "失败了,请排查", logger=self.logger)


    # 获取标签对象，可以用于对标签中的属性取值
    def get_tag_object(self, xpath, desc):
        try:
            self.logger.info("正在获取%s" % desc)
            # 链式调用，在 xpath 路径下，指定下标下，填充文本
            page_element = self.page.locator(xpath)
            time.sleep(2)
            self.logger.info("获取成功%s" % desc)
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"获取元素 {desc} 失败了,请排查! error info : {e}")
            AlertTools.send_robot(current_file_name=self.current_file_name,
                                  text="获取元素定位%s" % desc + "失败了,请排查", logger=self.logger)
        return page_element


    # xpath路径下，文本填充操作
    def fill_value(self, xpath, value, desc):
        try:
            self.logger.info("正在填充%s" % desc)
            # 链式调用，在 xpath 路径下，指定下标下，填充文本
            self.page.locator(xpath).fill(value)
            time.sleep(2)
            self.logger.info("填充成功%s" % desc)
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"{desc} 填充失败了,请排查! error info : {e}")
            AlertTools.send_robot(current_file_name=self.current_file_name,
                                  text=f"{desc} 填充失败了,请排查! ", logger=self.logger)

    # xpath路径下，链式调用，文本填充操作
    def type_by_index(self, xpath, index, desc, value):

        try:
            self.logger.info(f"链式正在填充{desc}->{xpath}")
            # 链式调用，在 xpath 路径下，指定下标下，填充文本
            self.page.locator(xpath).nth(index).fill(value)
            time.sleep(2)
            self.logger.info(f"链式填充成功{desc}->{xpath}")
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"{desc} 链式填充失败了,请排查! error info : {e}")
            AlertTools.send_robot(current_file_name=self.current_file_name,
                                  text=f"{desc} 链式填充失败了,请排查! ", logger=self.logger)


    # 截图操作
    def save_screen(self, png_folder=png_folder):
        pngname = time.strftime("%Y_%m_%d_%H%M%S", time.localtime())
        # self.page.screenshot(path=png_folder+ f"{self.current_file_name}_" + pngname + ".png")
        self.page.screenshot(path=GetFilePath.get_folder_file_path(f"{self.current_file_name}_" + pngname + ".png",current_project_path=png_folder),timeout=60000)


# 浏览器操作
class ChromeOperat:
    '''
        :
        params:
            logger: 自定义 log 日志句柄 ;
            url: 要访问的网页地址 ;
            folder_name: 浏览器所在文件夹名称, 也就是 chrome.exe 所在文件夹名称 ;

    '''

    def __init__(self,logger,url,folder_name='chrome'):
        self.logger = logger
        self.url = url
        self.folder_name = folder_name
    # 打开浏览器
    def open_browser(self)->dict:
        '''
            更新chrome包，运行程序出现 报错 BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:9222 ，
           是因为研发那边打开浏览器子进程缺少入参 --remote-debugging-port=9222，让他添加一下就行;
           return: 返回一个字典对象  {"playwright_client":p,"chrome_drive":browser,"browser_page":page} ;
                playwright_client: playwright 客户端对象 ;
                chrome_drive: chrome 浏览器驱动对象 ;
                browser_page: 浏览器上下文页面对象 ;
        '''
        try:
            # 关闭chrome
            self.kill_chrome()
            # 在chrome 安装目录下执行 开启 chrome指令
            WORK_PATH = GetFilePath.get_folder_path(folder_name=self.folder_name)
            subprocess.Popen("chrome.exe --remote-debugging-port=9222", shell=True, cwd=WORK_PATH)
            time.sleep(5)

            # 打开playwright client
            p = sync_playwright().start()

            # 1. 连接到本地已启动的 Chrome（--remote-debugging-port=9222）
            browser  = p.chromium.connect_over_cdp("http://127.0.0.1:9222")

            self.logger.info("开始启动连接driver成功")
            # 如果只想用第一个打开的页面，可直接取 context.pages[0]
            # 否则新建一个标签页
            if not browser.contexts:
                context = browser.new_context()
            else:
                context = browser.contexts[0]

            # 判断新建标签，浏览器是否开启页面
            page = context.pages[0] if context.pages else context.new_page()

            # 2. 设置默认最大等待时间 60 秒（相当于 Selenium 的 implicitly_wait）
            # 3. 打开网址
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(60000)
            page.goto(self.url)
            self.logger.info("打开网页成功")

            time.sleep(5)
            return {"playwright_client":p,"chrome_drive":browser,"browser_page":page}
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"打开浏览器异常，error info : {e}")

    #关闭浏览器
    def kill_chrome(self):
        '''
           方法1: 通过 CMD 指令杀死 chrome 进程 ;
           方法2: psutil 是一个跨平台的进程管理库，代码更清晰且不依赖命令行的输出解析，更稳定。 ;(推荐！！!)
        '''
        time.sleep(5)

        #方法1
        # check_cmd = 'tasklist /fi "imagename eq chrome.exe"'
        # result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        #
        # # 如果输出中包含 chrome.exe，说明进程存在
        # if "chrome.exe" in result.stdout.strip().lower():
        #     # print("发现 Chrome 进程，正在终止...")
        #     self.logger.info(f"发现 Chrome 进程，正在终止...")
        #     try:
        #         subprocess.run("taskkill /f /im chrome.exe", shell=True,check=True)
        #         self.logger.info("Chrome 进程已终止")
        #     except subprocess.CalledProcessError as e:
        #         self.logger.error(f"终止失败，返回码：{e.returncode}")
        # else:
        #     self.logger.info("未找到 Chrome 进程，无需操作")

        #方法2  这是跨平台的，优先使用此方法
        try:
            chrome_found = False
            for proc in psutil.process_iter(['name']):
                name = proc.info["name"]
                if name and "chrome.exe" in name.strip().lower():
                    chrome_found = True
                    self.logger.info(f"发现 Chrome 进程 (PID: {proc.pid})，正在终止...")
                    proc.kill()  # 强制终止
                    self.logger.info(f"发现 Chrome 强制终止")
            if not chrome_found:
                self.logger.info(f"未找到 Chrome 进程，无需操作")
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"执行关闭浏览器程序异常, error info : {e}")
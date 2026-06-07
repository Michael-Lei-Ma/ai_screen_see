# -*- coding: utf-8 -*-

import os
import traceback
import time
import re
from tools.ddddocr_captcha_parse import Base64CaptchaRecognizer
from tools.page_operat import PageLocator,ChromeOperat
from tools.format_config import LogConfig,AlertTools,ReadConfigUtil,GetFilePath


'''
    兴业项目运行注意事项：
        1、访问URL之前谈chrome认证证书，需要用系统管理员账号，去注册表配置 AutoSelectCertificateForUrls 策略;
        2、验证码识别用的 ddddocr ，所以python环境 Python 3.8 ~ 3.10， 高于 python 3.10 没法用;
        3、更新chrome包，运行程序出现 报错BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:9222 ，
           是因为研发那边打开浏览器子进程缺少入参 --remote-debugging-port=9222，让他添加一下就行;
    以上注意事项详细操作步骤见wiki ：https://wiki.icbf.group/pages/viewpage.action?pageId=86249272 

'''






# 获取当前文件名 不含扩展名
current_file_name = os.path.splitext(os.path.basename(__file__))[0][:6]
# 获取 error_png 路径
err_png_folder = GetFilePath.get_png_path(level_one_folder='png', level_two_folder='error_png', create_folder=True)
# 获取logger 对象
logger = LogConfig.get_logger(current_file_name)

# 获取配置文件
ReadConfigUtil = ReadConfigUtil(logger=logger, file_name="XingyeBankClientConfig.json")
ReadConfigUtil.loadFile()
url = ReadConfigUtil.getFileByKey("Web-Url")
ChromeOperat = ChromeOperat(logger=logger, url=url)
# 打开浏览器
chrome_obj_dit = ChromeOperat.open_browser()  # 返回对象 {"playwright_client":p,"chrome_drive":browser,"browser_page":page}

page = chrome_obj_dit.get("browser_page", '获取 page object 失败！')
PageLocator = PageLocator(page=page, logger=logger, current_file_name=current_file_name)
browser = chrome_obj_dit.get("chrome_drive", '获取 browser object 失败！')
playwright_client = chrome_obj_dit.get("playwright_client", '获取 playwright_client object 失败！')



class WorkAgent:

    # 开始工作流
    def do_detail(self):

        try:
            # 获取登录按钮
            get_login_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("login-btn"), ReadConfigUtil.getDesc("login-btn"))
            if get_login_obj.is_visible():
                PageLocator.fill_value(ReadConfigUtil.getLocator("username"),
                                ReadConfigUtil.getFileByKey("usernamevalue"), ReadConfigUtil.getDesc("username"))
                PageLocator.fill_value(ReadConfigUtil.getLocator("password"),
                                ReadConfigUtil.getFileByKey("passwordvalue"), ReadConfigUtil.getDesc("password"))
                # 判断验证码验证是否成功
                login_error_count = 1
                # 验证码验证登录，最多只能尝试5次，大于5次账号会被封禁，这里做3次校验
                while login_error_count < 4:
                    # # 匹配到验证码xpath路径下的imag标签
                    captcha_element = PageLocator.get_tag_object(ReadConfigUtil.getLocator("captcha-code-image"),
                                                          ReadConfigUtil.getDesc("captcha-code-image"))
                    # 等待元素可见
                    time.sleep(2)

                    # 1. 获取 src 属性（验证码图片URL）
                    base64_img = captcha_element.get_attribute("src")
                    logger.info(f"验证码图片 base64_image_str : {base64_img}")
                    # 获取captcha str from image base64 str

                    recognizer = Base64CaptchaRecognizer(
                        code_len=4,
                        use_preprocess=True
                    )
                    captcha_str = recognizer.recognize(base64_img)

                    logger.info(f"验证码图片 captcha_str : {captcha_str}")

                    if captcha_str is not None:
                        # 验证码输入框输入验证码字符串
                        PageLocator.fill_value(ReadConfigUtil.getLocator("captcha-code"), captcha_str
                                        , ReadConfigUtil.getDesc("captcha-code"))

                        # time.sleep(5)
                        # 点击登录按钮
                        PageLocator.click(ReadConfigUtil.getLocator("login-btn"), ReadConfigUtil.getDesc("login-btn"))

                        # 判断是否登录成功
                        get_login_error_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("login-btn"),
                                                                  ReadConfigUtil.getDesc("login-btn"))

                        if get_login_error_obj.count() > 0:
                            # 截图操作
                            PageLocator.save_screen(png_folder=err_png_folder)
                            logger.info(f"第{login_error_count}次验证码登录失败！")
                            if login_error_count == 3:
                                AlertTools.send_robot(current_file_name=current_file_name,
                                                      text=f"第{login_error_count}次验证码登录失败，请人工手动介入操作！", logger=logger)
                            login_error_count += 1
                            continue
                        else:
                            break
                    else:
                        PageLocator.click(ReadConfigUtil.getLocator("captcha-code-image"),
                                                          ReadConfigUtil.getDesc("captcha-code-image"))
                        continue

            # 登录后页面业务操作
            get_login_success_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("home-page-tag"),
                                                        ReadConfigUtil.getDesc("home-page-tag"))
            if get_login_success_obj.is_visible():
                # 关闭首页面tips页面
                PageLocator.click(ReadConfigUtil.getLocator("home-page-tips"), ReadConfigUtil.getDesc("home-page-tips"))

                # '个人中心' 业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("personal-center-btn-lt"),
                           ReadConfigUtil.getDesc("personal-center-btn-lt"))
                # '个人中心-账号管理'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("account-management-btn-lt"),
                           ReadConfigUtil.getDesc("account-management-btn-lt"))
                # '个人中心-账号管理-条件筛选-用户状态' 点击操作
                PageLocator.click(ReadConfigUtil.getLocator("acct-manat-query-conditions-value-rt"),
                           ReadConfigUtil.getDesc("acct-manat-query-conditions-value-rt"))
                # 下拉选择列表，选择启用选项
                PageLocator.page.locator("div").filter(has_text=re.compile(r"^启用$")).nth(1).click()

                # '账号管理-条件查询-点击 查询'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("acct-manat-query-conditions-query-rt"),
                           ReadConfigUtil.getDesc("acct-manat-query-conditions-query-rt"))

                # '账号管理-条件查询-查询-查询结果表头-CBC'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("acct-manat-query-form-head-rt"),
                           ReadConfigUtil.getDesc("acct-manat-query-form-head-rt"))

                # '账号管理-条件查询-查询-查询结果表头-CBC-查询结果表单-默认分页变更'点击操作
                page.get_by_text("条/页").click()
                page.get_by_text("100 条/页").click()

                # '人中心-账号管理-查询结果，总条数'
                element = page.query_selector(ReadConfigUtil.getLocator("acct-manat-query-form-totalNumber"))
                if element:
                    text = element.text_content().strip()
                    logger.info("获取查询结果总条数%s" % ReadConfigUtil.getDesc("acct-manat-query-form-head-rt"))

                    # 提取数字
                    match = re.search(r'共\s*(\d+)\s*条', text)
                    if match:
                        count = int(match.group(1))
                        # print(f"提取的数字: {count}")
                        logger.info(f"查询结果总条数,提取的数字:{count}")
                    if count:
                        pageNumberInt = count // 100
                        pageNumberDecimal = count % 100
                        if pageNumberInt > 0 and pageNumberDecimal != 0:
                            pageNumber = pageNumberInt
                        elif pageNumberInt > 0 and pageNumberDecimal == 0:
                            pageNumber = pageNumberInt - 1
                        else:
                            pageNumber = 0
                # 翻页查询 ，点击下一页
                if pageNumber and pageNumber > 0:
                    for j in range(pageNumber):
                        PageLocator.click(ReadConfigUtil.getLocator("acct-manat-query-page-break-check-rt"),
                                   ReadConfigUtil.getDesc("acct-manat-query-page-break-check-rt"))
                        time.sleep(3)


                # '通用查询'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("general-search-btn-lf"),
                           ReadConfigUtil.getDesc("general-search-btn-lf"))

                # '通用查询-通时通次报表'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("timed-number-report-form-btn-lt"),
                           ReadConfigUtil.getDesc("timed-number-report-form-btn-lt"))

                # '通用查询-通时通次报表-当日通时通次'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("current-time-number-tab-rt"),
                           ReadConfigUtil.getDesc("current-time-number-tab-rt"))

                # '通用查询-通时通次报表-当日通时通次-查询'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("current-time-number-tab-query-btn-rt"),
                           ReadConfigUtil.getDesc("current-time-number-tab-query-btn-rt"))

                # '通用查询-通时通次报表-当日通时通次-查询-查询结果列表默认分页查询选择'业务填充操作
                page.get_by_text("条/页").click()
                page.get_by_text("2000 条/页").click()
            else:
                # AlertTools.send_robot(f"自动化脚本进入业务页面失败，请人工查看！！！")
                logger.info(f"自动化脚本进入业务页面失败，请人工查看！！！")
                AlertTools.send_robot(current_file_name="兴业银行",
                                      text=f"自动化脚本进入业务页面失败，请人工查看！！！", logger=logger)
        except Exception as e:
            traceback.print_exc()
            logger.error(f"执行业务程序异常，异常信息 {e}")
            # AlertTools.send_robot(f"执行业务程序异常，请人工手动介入操作！")
            AlertTools.send_robot(current_file_name="兴业银行",
                                  text=f"执行业务程序异常，请人工手动介入操作！", logger=logger)

    # 结束工作流
    def done_work_over(self):
        try:
            PageLocator.save_screen()
            page.keyboard.press("Alt+F4")  # 关闭当前活动窗口或程序
            browser.close()
            playwright_client.stop()
            ChromeOperat.kill_chrome()
        except Exception as e:
            traceback.print_exc()
            logger.error(f"结束工作流异常, 异常信息 {e}")


if __name__ == '__main__':


    AlertTools.send_robot(current_file_name="兴业银行",
                          text=f"定时点击开始", logger=logger)
    # 获取class object
    agent = WorkAgent()
    # config文件，全部业务操作逻辑
    agent.do_detail()
    # 结束工作流程操作
    agent.done_work_over()
    AlertTools.send_robot(current_file_name="兴业银行",
                          text=f"定时点击结束", logger=logger)
    logger.info("程序完整运行结束了")

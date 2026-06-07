# -*- coding: utf-8 -*-

import os
import traceback
import time
from tools.page_operat import PageLocator,ChromeOperat
from tools.format_config import LogConfig,AlertTools,ReadConfigUtil,GetFilePath,ClearExpiredFile
from tools.excel_operat import ExcelReadWriter



# 获取当前文件名 不含扩展名
current_file_name = os.path.splitext(os.path.basename(__file__))[0]
# 获取 error_png 路径
err_png_folder = GetFilePath.get_folder_file_path('png','error_png')
# 获取logger 对象
logger = LogConfig.get_logger(current_file_name)

# 获取配置文件
ReadConfigUtil = ReadConfigUtil(logger=logger, file_name=f"{current_file_name}.json")
ReadConfigUtil.loadFile()
url = ReadConfigUtil.getFileByKey("Web_Url")
ChromeOperat = ChromeOperat(logger=logger, url=url)
# 打开浏览器
chrome_obj_dit = ChromeOperat.open_browser()  # 返回对象 {"playwright_client":p,"chrome_drive":browser,"browser_page":page}

page = chrome_obj_dit.get("browser_page", '获取 page object 失败！')
PageLocator = PageLocator(page=page, logger=logger, current_file_name=current_file_name)
browser = chrome_obj_dit.get("chrome_drive", '获取 browser object 失败！')
playwright_client = chrome_obj_dit.get("playwright_client", '获取 playwright_client object 失败！')

magic_cube_url = ReadConfigUtil.getFileByKey("Nginx_upload_url")


class WorkAgent:

    # 开始工作流
    def do_detail(self):
        # 在这里暂停，打开 Inspector
        # page.pause()
        try:
            # 获取登录按钮
            get_login_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("login_btn"), ReadConfigUtil.getDesc("login_btn"))
            if get_login_obj.is_visible():
                PageLocator.fill_value(ReadConfigUtil.getLocator("username"),
                                ReadConfigUtil.getFileByKey("usernamevalue"), ReadConfigUtil.getDesc("username"))
                PageLocator.fill_value(ReadConfigUtil.getLocator("password"),
                                ReadConfigUtil.getFileByKey("passwordvalue"), ReadConfigUtil.getDesc("password"))
                PageLocator.click(ReadConfigUtil.getLocator("login_btn"),ReadConfigUtil.getDesc("login_btn"))

                # 二次登录
                second_get_login_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("second_login_tag"), ReadConfigUtil.getDesc("second_login_tag"))
                if second_get_login_obj.is_visible():
                    PageLocator.click(ReadConfigUtil.getLocator("second_login_btn"),ReadConfigUtil.getDesc("second_login_btn"))

            # 登录后页面业务操作
            get_login_success_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("case_handle_lt"),
                                                        ReadConfigUtil.getDesc("case_handle_lt"))
            # 登录成功
            if get_login_success_obj.is_visible():

                # 案件处理
                PageLocator.click(ReadConfigUtil.getLocator("case_handle_lt"), ReadConfigUtil.getDesc("case_handle_lt"))

                # '案件处理-案件查询'
                PageLocator.click(ReadConfigUtil.getLocator("case_query_lt"),
                           ReadConfigUtil.getDesc("case_query_lt"))
                # '案件查询-条件筛选-团队'
                PageLocator.click(ReadConfigUtil.getLocator("teams_rt"),
                           ReadConfigUtil.getDesc("teams_rt"))
                # '案件查询-条件筛选-团队-展开筛选项 全选'
                PageLocator.click(ReadConfigUtil.getLocator("teams_value_rt"),
                           ReadConfigUtil.getDesc("teams_value_rt"))
                # '案件查询-条件筛选-团队-展开筛选项 确认'+
                PageLocator.click(ReadConfigUtil.getLocator("teams_value_confirm_rt"),
                                 ReadConfigUtil.getDesc("teams_value_confirm_rt"))

                data_path = GetFilePath.get_folder_file_path('datas','data','广发缺失id_4.xlsx')
                card_id_dict= ExcelReadWriter.read_all_sheets(data_path)
                cradId_lt =card_id_dict['Sheet']
                for i in range(1,len(cradId_lt)):
                    cradId = cradId_lt[i][0]
                    print('查询账号以及次数',i,cradId)
                    # '案件查询-条件筛选-持卡人代号'
                    PageLocator.fill_value(ReadConfigUtil.getLocator("cardholder_id_number_rt"),cradId,
                                           ReadConfigUtil.getDesc("cardholder_id_number_rt"))

                    # '案件查询-查询'
                    PageLocator.click(ReadConfigUtil.getLocator("case_query_btn_rt"),
                               ReadConfigUtil.getDesc("case_query_btn_rt"))


            else:
                logger.info(f"自动化脚本进入业务页面失败，请人工查看！！！")
                AlertTools.send_robot(current_file_name="广发银行",
                                      text=f"自动化脚本进入业务页面失败，请人工查看！！！", logger=logger)
        except Exception as e:
            traceback.print_exc()
            logger.error(f"执行业务程序异常，异常信息 {e}")
            AlertTools.send_robot(current_file_name="广发银行",
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

    # 清除 download文件夹下过期历史数据，默认 保存最近 15天的
    target_dir = GetFilePath.get_folder_file_path('download')
    ClearExpiredFile(logger).delete_old_folders_by_time_format(root_dir=target_dir, time_format="%Y_%m_%d_%H_%M_%S",
                                                               days_threshold=15,
                                                               dry_run=False)
    AlertTools.send_robot(current_file_name="广发银行",
                          text=f"定时点击开始", logger=logger)
    # 获取class object
    agent = WorkAgent()
    # config文件，全部业务操作逻辑
    agent.do_detail()
    # 结束工作流程操作
    agent.done_work_over()
    AlertTools.send_robot(current_file_name="广发银行",
                          text=f"定时点击结束", logger=logger)
    logger.info("程序完整运行结束了")




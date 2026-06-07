# -*- coding: utf-8 -*-

import os
import traceback
import time
from tools.page_operat import PageLocator,ChromeOperat
from tools.format_config import LogConfig,AlertTools,ReadConfigUtil,GetFilePath,ClearExpiredFile
from tools.time_format import TimeFormatData
from tools.str_format import StrRegularExtract
from tools.excel_operat import GetFileStatus,ExcelAllSheetsCleaner,ExcelFileUpload
from tools.magic_cube import MagicCubeAPI


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

    def news_get_password(self,code_file_name,output_file):
        """
            : 异步任务tab 完成下载，然后从 '消息'获取下载 excel 的访问密码，删除文件的文件锁，优化文件的格式

        """

        try:
            # '顶部导航栏，消息'
            PageLocator.click(ReadConfigUtil.getLocator("news_top"),
                              ReadConfigUtil.getDesc("news_top"))
            # '顶部导航栏，消息，查看更多'
            PageLocator.click(ReadConfigUtil.getLocator("news_view_more"),
                              ReadConfigUtil.getDesc("news_view_more"))
            # 历史消息查询 tab
            PageLocator.click(ReadConfigUtil.getLocator("history_news_query_tab_li"),
                              ReadConfigUtil.getDesc("history_news_query_tab_li"))

            # 历史消息查询 tab 页面，点击查询
            PageLocator.click(ReadConfigUtil.getLocator("history_news_query_bt"),ReadConfigUtil.getDesc("history_news_query_bt"))

            time.sleep(5)
            # 历史消息查询tab页面 history_news_query_tab
            history_query_tab = PageLocator.get_tag_object(ReadConfigUtil.getLocator("history_news_query_tab_span"),
                                                           ReadConfigUtil.getDesc("history_news_query_tab_span"))
            # 判断标签可见
            if history_query_tab.is_visible():
                # 判断是否在当前标签页面
                history_query_tab_li = PageLocator.get_tag_object(ReadConfigUtil.getLocator("history_news_query_tab_li"),
                                                                  ReadConfigUtil.getDesc("history_news_query_tab_li"))
                # 在当前页面为True , 否则 False
                if history_query_tab_li.get_attribute("aria-selected"):

                    history_table_rows_lt = PageLocator.get_tag_object(ReadConfigUtil.getLocator("case_excel_password"),
                                                                       ReadConfigUtil.getDesc("case_excel_password")).all()
                    # time.sleep(5)
                    for row in history_table_rows_lt:
                        # 判断文件名称一致
                        sen_cont = row.locator('xpath=.//td[@data-col="3"]/span[@class="wisgrid-cell-span plain"]').first.inner_text()
                        # sen_cont = sen_cont_td.locator('span').text_content()
                        if ".xlsx" in sen_cont:
                            # 正则提取文件名和密码
                            file_pw_lt = StrRegularExtract.re_get_file_password(sen_cont)
                            # code_file_name = "案件流转明细_20260420104934.xlsx"
                            # 文件名一致
                            if file_pw_lt[0] == code_file_name:
                                # 文件锁密码
                                file_pw = file_pw_lt[1]
                                break
                            else:
                                continue
                        else:
                            continue
                    logger.info(f"文件 {file_pw_lt[0]} 提取到密码 {file_pw_lt[1]}")
                    # # 9YL483Lpf   H28OqUa7t Cbc123BjCF
                    # 删除execl锁密码
                    excel_decrypt = ExcelFileUpload.remove_excel_password(input_file=output_file, password=file_pw)
                    logger.info(f"{code_file_name} 文件，删除锁密码结果: {excel_decrypt}")

                    # 清理Excel文件合并单元
                    EASC = ExcelAllSheetsCleaner(output_file,output_file)
                    clean_result = EASC.smart_clean_all_sheets()
                    logger.info(f"{code_file_name} 文件，清理合并单元格结果: {clean_result}")
                    # 处理成功 True 处理失败 False
                    return  clean_result


        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"异步任务执行异常 {error_msg}")

    def async_task_table(self,task_name:str)->list:
        """
            : 异步任务 tab下的操作
        """
        try:
            time.sleep(5)
            # 查询列表结果table区域操作
            elem_hand = PageLocator.page.locator(ReadConfigUtil.getLocator("async_task_table")).first
            # rows = elem_hand.locator('td')
            # 等待异步任务下载完成
            while elem_hand.locator('td').nth(2).inner_text() in ["等待运行","运行中"]:
            # while elem_hand.locator('td').nth(2).get_attribute('class') in [ "status_0","status_1"]:
                time.sleep(1)
                logger.info(f"循环中，文件状态 {elem_hand.locator('td').nth(2).inner_text()}")
                # logger.info(f"循环中，文件状态 {elem_hand.locator('td').nth(2).get_attribute('class')}")
                continue

            time.sleep(3)
            logger.info(f"循环外，文件状态 {elem_hand.locator('td').nth(2).inner_text()}")
            if elem_hand.locator('td').nth(2).inner_text() in ["运行完毕"] :
            # logger.info(f"循环外，文件状态 {elem_hand.locator('td').nth(2).get_attribute('class')}")
            # if elem_hand.locator('td').nth(2).get_attribute('class') in ["status_2"] :
                # 点击附加下载到本地
                with page.expect_download() as d:
                    # 下载文件
                    elem_hand.locator('td').nth(4).locator('a').click()

                download = d.value  # 获取下载对象
                code_file_name = download.suggested_filename  # 获取附件名称
                time_str = TimeFormatData.today_format_str(time_format="%Y_%m_%d_%H_%M_%S")
                # 文件保存到指定路径
                output_file = GetFilePath.get_folder_file_path('download', time_str, code_file_name)
                if output_file.exists():
                    os.remove(output_file)
                # 将已下载的文件保存到指定的完整路径, 会等到文件下载完成后保存
                download.save_as(output_file)
                logger.info(f"{task_name} 异步任务，完成文件下载 {code_file_name} ")

                # 判断文件下载状态，下载完成True，等待最多60s
                if GetFileStatus.wait_for_download_complete(output_file, timeout=60):
                    if output_file.stat().st_size <= 0:
                        logger.info(f"文件保存不完整: {output_file} 文件大小为 {output_file.stat().st_size} 字节")
                    logger.info(f"文件保存完整: {output_file} 文件大小为{output_file.stat().st_size / 1024:.2f} KB ")
                else:
                    logger.info(f"文件{code_file_name}下载超时")

                # 相对路径转化为绝对路径，判断路径是否存在，不存在抛异常
                output_file.resolve(strict=True)

            return [code_file_name,output_file]

        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"异步任务执行异常 {error_msg}")

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
            get_login_success_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("case_manage_lt"),
                                                        ReadConfigUtil.getDesc("case_manage_lt"))
            # 登录成功
            if get_login_success_obj.is_visible():

                # 分案管理只是每日 19点获取数据
                if TimeFormatData.get_now_hour() in [19] :

                    # 分案管理
                    PageLocator.click(ReadConfigUtil.getLocator("case_manage_lt"), ReadConfigUtil.getDesc("case_manage_lt"))

                    # '分案管理-案件流转查询'
                    PageLocator.click(ReadConfigUtil.getLocator("case_flow_query_lt"),
                               ReadConfigUtil.getDesc("case_flow_query_lt"))
                    # ''分案管理-案件流转查询-流转明细'
                    PageLocator.click(ReadConfigUtil.getLocator("case_flow_details_lt"),
                               ReadConfigUtil.getDesc("case_flow_details_lt"))
                    # '流转明细-条件筛选-流转类型-展开筛选项'
                    PageLocator.click(ReadConfigUtil.getLocator("flow_type_rt"),
                               ReadConfigUtil.getDesc("flow_type_rt"))

                    # '流转明细-条件筛选-流转类型-展开筛选项'
                    PageLocator.page.locator(ReadConfigUtil.getLocator("flow_type_value_rt")).nth(4).click() # 退案
                    PageLocator.page.locator(ReadConfigUtil.getLocator("flow_type_value_rt")).nth(9).click() # 回收
                    # '流转明细-条件筛选-流转类型-收回筛选项'
                    PageLocator.click(ReadConfigUtil.getLocator("flow_type_rt"),
                               ReadConfigUtil.getDesc("flow_type_rt"))

                    # '流转明细-条件筛选-流转时间'
                    PageLocator.click(ReadConfigUtil.getLocator("flow_date_rt"),
                               ReadConfigUtil.getDesc("flow_date_rt"))

                    # 获取时间控件
                    target_date = TimeFormatData.today_format_str()
                    date_xpath = ReadConfigUtil.getLocator("flow_date_value_rt").format(target_date=target_date)

                    date_comp_lt = PageLocator.page.locator(date_xpath).all()
                    for date_comp in date_comp_lt:
                        if date_comp.is_visible():
                            date_comp.dblclick()
                            break
                        else:
                            continue

                    # '流转明细-查询'
                    PageLocator.click(ReadConfigUtil.getLocator("flow_query_btn"),
                               ReadConfigUtil.getDesc("flow_query_btn"))
                    # '流转明细-查询后-导出'
                    PageLocator.click(ReadConfigUtil.getLocator("flow_export_btn"),
                                      ReadConfigUtil.getDesc("flow_export_btn"))
                    # '流转明细-导出后进入-异步任务tab'
                    flow_export_lt = self.async_task_table(task_name="案件")
                    # [code_file_name, output_file]
                    code_file_name = flow_export_lt[0] # 文件名称
                    code_output_file = flow_export_lt[1] # 文件存储路径
                    # 获取文件密码，去除文件锁，优化文件格式，覆盖源文件
                    code_upload = self.news_get_password(code_file_name,code_output_file)
                    # 上传解密文件到魔方
                    if code_upload:
                        code_metadata_id = ReadConfigUtil.getFileByKey("AnJian")
                        MagicCubeAPI.upload(magic_cube_url,code_output_file,code_metadata_id,"AnJian",logger)


                # 监控管理 获取数据时间没有限制
                PageLocator.click(ReadConfigUtil.getLocator("monitor_manage_lt"),
                           ReadConfigUtil.getDesc("monitor_manage_lt"))

                # 报表
                PageLocator.click(ReadConfigUtil.getLocator("mm_report_lt"),
                           ReadConfigUtil.getDesc("mm_report_lt"))
                # 外呼报表
                PageLocator.page.locator(ReadConfigUtil.getLocator("out_call_report_lt")).dblclick()
                # 自取坐席维度监测表
                PageLocator.click(ReadConfigUtil.getLocator("seat_report_lt"),
                                  ReadConfigUtil.getDesc("seat_report_lt"))
                # 筛选条件
                if TimeFormatData.get_now_hour() < 9 :
                    # 8点获取昨天数据
                    seat_report_start_date = TimeFormatData.past_days_format_str()
                    seat_report_end_date = seat_report_start_date
                    PageLocator.click(ReadConfigUtil.getLocator("seat_report_start_date"),
                                      ReadConfigUtil.getDesc("seat_report_start_date"))

                    PageLocator.fill_value(ReadConfigUtil.getLocator("seat_report_start_date"), seat_report_start_date,
                                           ReadConfigUtil.getDesc("seat_report_start_date"))

                    PageLocator.click(ReadConfigUtil.getLocator("seat_report_end_date"),
                                      ReadConfigUtil.getDesc("seat_report_end_date"))

                    PageLocator.fill_value(ReadConfigUtil.getLocator("seat_report_end_date"), seat_report_end_date,
                                           ReadConfigUtil.getDesc("seat_report_end_date"))

                # 9点后获取的是当天数据 ，默认是当天
                # 运行button
                PageLocator.click(ReadConfigUtil.getLocator("sr_run_btn"),
                                  ReadConfigUtil.getDesc("sr_run_btn"))

                # '自取坐席-导出后进入-异步任务tab'
                seat_export_lt = self.async_task_table(task_name="坐席")
                # [code_file_name, output_file]
                seat_file_name = seat_export_lt[0]  # 文件名称
                seat_output_file = seat_export_lt[1]  # 文件存储路径
                # 获取文件密码，去除文件锁，优化文件格式，覆盖源文件
                seat_upload =self.news_get_password(seat_file_name, seat_output_file)
                # 上传解密文件到魔方
                if seat_upload:
                    seat_metadata_id = ReadConfigUtil.getFileByKey("ZuoXi")
                    MagicCubeAPI.upload(magic_cube_url,seat_output_file,seat_metadata_id,"ZuoXi",logger)




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




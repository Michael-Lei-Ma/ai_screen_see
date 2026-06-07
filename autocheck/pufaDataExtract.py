# -*- coding: utf-8 -*-

import os
import traceback
import time
import random
from tools.page_operat import PageLocator,ChromeOperat
from tools.format_config import LogConfig,AlertTools,ReadConfigUtil,GetFilePath,ClearExpiredImage
from tools.time_format import TimeFormatData,Timer
from tools.str_format import StrDataExtract
from tools.excel_operat import ExcelDynamicWriter,ExcelReadWriter
from tools.env_variable import EnvVariableOperate
import sys
import multiprocessing
from datetime import datetime, timedelta


# 当前客户端名称
project_name = "浦发银行"
# 获取当前文件名 不含扩展名
current_file_name = os.path.splitext(os.path.basename(__file__))[0]
# 获取 error_png 路径
err_png_folder = GetFilePath.get_png_path(level_one_folder='png', level_two_folder='error_png', create_folder=True)
# 获取logger 对象
logger = LogConfig.get_logger(current_file_name)

# 获取配置文件
ReadConfigUtil = ReadConfigUtil(logger=logger, file_name=f"{current_file_name}.json")
ReadConfigUtil.loadFile()
# 获取页面查询结果字符串后的数据提取处理逻辑
StrDataExtract=StrDataExtract(logger)

# 记录数据结果路径
time_str = TimeFormatData.today_format_str(time_format="%Y%m%d_%H")
file_path = GetFilePath.get_folder_file_path('datas',f'reduce_process_history_data_{time_str}.xlsx')
# 动态写入excel
rows_per_sheet = 10000  # 单个sheet写入行数
ExcelDynamicWriter= ExcelDynamicWriter(filename=file_path,rows_per_sheet=rows_per_sheet)

# 打开浏览器，进入登录页面
url = ReadConfigUtil.getFileByKey("Web_Url")
ChromeOperat = ChromeOperat(logger=logger, url=url)
chrome_obj_dit = ChromeOperat.open_browser()  # 返回对象 {"playwright_client":p,"chrome_drive":browser,"browser_page":page}

page = chrome_obj_dit.get("browser_page", '获取 page object 失败！')
browser = chrome_obj_dit.get("chrome_drive", '获取 browser object 失败！')
playwright_client = chrome_obj_dit.get("playwright_client", '获取 playwright_client object 失败！')
# 页面元素操作类
PageLocator = PageLocator(page=page, logger=logger, current_file_name=current_file_name)

#程序时间计时器
Timer=Timer(logger=logger)

# 环境变量文件夹数据操作
EnvVariableOperate = EnvVariableOperate(logger=logger)


# ==================== 定时任务配置区 ====================
START_TIME = (8, 40, 0)          # 每日开始时间 (时, 分, 秒)
END_TIME = (20, 30, 0)           # 每日结束时间 (时, 分, 秒)
RETRY_INTERVAL = 10 * 60         # 重试间隔（秒），10分钟
# RETRY_INTERVAL = 1 * 10    # 测试用 10 秒循环一次
MAX_RETRIES = 3                 # 最大重试次数
CHECK_INTERVAL = 10             # 时间检查间隔（秒），用于等待时及时响应结束时间


# ================= 清除程序过期 png =====================
ClearExpiredImage = ClearExpiredImage(logger)
# 清除 png 目录下, 默认保留最近7天
png_path = GetFilePath.get_folder_file_path('png')
ClearExpiredImage.delete_old_images(folder_path=png_path)
# 清除 error_png 目录下, 默认保留最近7天
error_png_path = GetFilePath.get_folder_file_path('png','error_png')
ClearExpiredImage.delete_old_images(folder_path=error_png_path)

#  程序按照开始结束时间自动执行 True , 指定 exel 文件执行 False
exe_auto_status = False    # True False
# 指定 excel 文件
target_file = "浦发分期待跑id.xlsx"

manual_file = GetFilePath.get_folder_file_path('datas','data',target_file)


"""
    业务要求: 浦发--案件跟踪--减免流水--条件筛选-查询时间：按月查询+处理状态：减免过程--条件查询--查询结果，按条点击'详情'-然后关闭
    设计思路: 
        1、按照业务写 playwright 自动化脚本, 特意添加拟人随机点击、随机思考 操作
        2、将操作信息动态写入 excel 文件
        3、每月点击操作完成，在 .env 文件将程序下次开始查询时间更新为下月的第一天，记录累计操作完成数 
        4、整个程序在自定义定时任务程序中持续运行
            4.1、定时任务默认工作时间开始、结束时间 : 每天 08:40~20:30
            4.2、定时任务执行异常有3次，每次间隔10分钟重试机制
            4.3、在工作时间段，程序可以重启，时间之外无处于等待状态
        5、当 .env 查询开始时间大于当前时间，程序直接结束运行
    自定义快速修改参数：
        1、定时任务：修改 START_TIME、END_TIME中的值，改变定时任务执行时间
        2、修改 envVariable.env 文件中 pufa_target_start_date 的值
    系统支持按照条件 和 指定文件运行俩种模式：
        exe_auto_status = True
        1、 程序按照开始结束时间自动执行 True 
        2、 指定 exel 文件执行 False
    指定文件运行模式操作步骤:
        1、在本地获得 excel 文件, 然后粘贴复制到  C:\AutoProgram\Exec\autocheck\datas\data 目录下
        2、程序修改 exe_auto_status = False  ，target_file = "上传文件名"
        3、其他不需要多余操作

"""




class SummaryLog:

    @staticmethod
    def get_single_search_log(single_check_data_total_dit,single_check_total_writer_count):
        # 统计单次查询与写入次数
        single_check_data_total = sum(single_check_data_total_dit.values())
        logger.info(
            f"单次查询共 {single_check_data_total} 条数据, 脚本执行了 {single_check_total_writer_count} 次点击操作, 查询结果与执行操作差值 {single_check_data_total - single_check_total_writer_count}\n查询结果原始数据 {single_check_data_total_dit}")

    @staticmethod
    def get_all_search_log(check_data_total_dit,writer_count):
        # 统计总的查询与写入次数
        check_data_total = sum(check_data_total_dit.values())
        logger.info(
            f"一共查询到 {check_data_total} 条数据, 脚本执行了 {writer_count} 次点击操作, 查询结果与执行操作差值 {check_data_total - writer_count}\n查询结果原始数据 {check_data_total_dit}")

class  CaseTrack:

    @staticmethod
    def reduce_rush_water(start_date:str,end_date:str,check_data_total_dit:dict,apply_date:tuple,
                          writer_count:int,single_check_total_writer_count:int=0,single_check_data_total_dit=dict(),custom_id=str())->list:
        """
            : 按键跟踪 -- 减免流水 tab，支持俩种模式，获取历史数据
                模式1: 指定开始结束时间，触发定时任务，自动执行
                模式2: 指定 datas/data/excel.xlsx 文件，触发定时任务，自动执行
                注意: 俩种模式不能并行运行，因为互相影响
            **kwargs:
                start_date: 开始时间  时间格式"%Y-%m-%d"
                end_date: 结束时间
                check_data_total_dit: 统计程序运行全部的查询数据字典
                apply_date: 查询时间范围元祖
                writer_count: 统计程序运行写入次数计数
                single_check_total_writer_count: 单次时间范围查询查询数据写入计数
                single_check_data_total_dit: 单次时间范围查询查询数据字典
                custom_id: 查询条件-客户号
            return: 返回统计类数据 list

        """
        try:
            # '案件跟踪-减免流水-条件筛选-申请日期' 点击操作
            PageLocator.click(ReadConfigUtil.getLocator("red_stat_apply_date"),
                              ReadConfigUtil.getDesc("red_stat_apply_date"))
            PageLocator.fill_value(xpath=ReadConfigUtil.getLocator("red_stat_begin_time"),
                                   desc=ReadConfigUtil.getDesc("red_stat_begin_time"), value=start_date)
            PageLocator.fill_value(xpath=ReadConfigUtil.getLocator("red_stat_end_time"),
                                   desc=ReadConfigUtil.getDesc("red_stat_end_time"), value=end_date)

            # 指定 exel 业务
            if not exe_auto_status :
                PageLocator.fill_value(xpath=ReadConfigUtil.getLocator("red_custom_id"),
                                       desc=ReadConfigUtil.getDesc("red_custom_id"), value= custom_id)

            # '案件跟踪-减免流水-条件筛选-点击 查询'业务直接点击操作
            PageLocator.click(ReadConfigUtil.getLocator("red_stat_search_btn"),
                              ReadConfigUtil.getDesc("red_stat_search_btn"))

            # 单次条件查询结果
            single_check_total_element = PageLocator.get_tag_object(
                ReadConfigUtil.getLocator("red_stat_result_total_number"),
                ReadConfigUtil.getDesc("red_stat_result_total_number"))
            if single_check_total_element:
                text = single_check_total_element.text_content().strip()
                # 单次查询结果总数
                single_check_total = StrDataExtract.get_page_totalNumber_from_str(text=text)

                check_data_total_dit[apply_date] = single_check_total
                single_check_data_total_dit[apply_date] = single_check_total

                # 分页数
                pageNumber = StrDataExtract.get_page_pagesNumber_from_str(text=text)

            # 查询有结果，执行业务操作
            if single_check_total > 0:

                # 查看下一页数据button
                next_btn = PageLocator.get_tag_object(
                    ReadConfigUtil.getLocator("red_stat_result_last_page"),
                    ReadConfigUtil.getDesc("red_stat_result_last_page"))

                for last_page in range(pageNumber + 1 if pageNumber > 0 else 1):

                    # 查询列表结果table区域操作
                    table_rows = PageLocator.page.locator(ReadConfigUtil.getLocator("red_stat_result_table")).all()
                    # print(f"当前页找到 {len(table_rows)} 条记录")

                    for row in random.sample(table_rows, len(table_rows)):
                        data_dit = dict()
                        table_header_name_lt = ['申请时间', '申请人员', '申请人作业点', '客户号',
                                                '方案名称', '方案类型', '处理状态']
                        # 滚动到当前行可见
                        row.scroll_into_view_if_needed()
                        detail_button = row.locator(
                            ReadConfigUtil.getLocator("red_stat_result_table_row_detail"))
                        # #滚动到详情按钮可见
                        # detail_button.scroll_into_view_if_needed()

                        # 获取到tr标签下全部的td -> list
                        cell_tds = row.locator('td').all()

                        for col_idx, cell_td in enumerate(cell_tds):
                            # 提取文本，去除首尾空白
                            text = cell_td.locator('div').text_content().strip()
                            if col_idx < 7:
                                data_dit[table_header_name_lt[col_idx]] = text
                            else:
                                continue

                        # 详情、关闭点击操作
                        if detail_button.count() > 0 and detail_button.is_visible():
                            # 点击详情
                            detail_button.click()

                            # 模拟思考时间
                            think_time = random.randint(2, 5)
                            time.sleep(think_time)
                            # 点击关闭
                            PageLocator.click(ReadConfigUtil.getLocator("red_stat_result_table_row_detail_close"),
                                              ReadConfigUtil.getDesc("red_stat_result_table_row_detail_close"))

                            if data_dit is not dict():
                                # 动态写入 Excel
                                ExcelDynamicWriter.write_data(data_dit)
                                # 记录程序写入次数
                                writer_count += 1
                                single_check_total_writer_count += 1

                    # 按查询条件，写入一页数据，excel文件保存一次
                    ExcelDynamicWriter.save_workbook()

                    # 翻页查询，点击下一页
                    if next_btn and not next_btn.is_disabled():
                        PageLocator.click(ReadConfigUtil.getLocator("red_stat_result_last_page"),
                                          ReadConfigUtil.getDesc("red_stat_result_last_page"))
                        continue
                    else:
                        break

            # 统计单次查询与写入次数log
            SummaryLog.get_single_search_log(single_check_data_total_dit, single_check_total_writer_count)

            if exe_auto_status :
                # 单次查询业务操作完成, 更新他下次程序重新开始的时间, 写入环境变量文件中
                pufa_target_start_date = TimeFormatData.coming_days_format_str(date_str=end_date)
                EnvVariableOperate.writer_update_env_file(key='pufa_target_start_date', value=pufa_target_start_date)

                # 单次查询业务操作完成, 更新本次 diff 为 0 的查询总数, 写入环境变量文件中
                single_check_data_total = sum(single_check_data_total_dit.values())
                single_check_data_diff = single_check_data_total - single_check_total_writer_count
                if int(single_check_data_diff) <= 0:
                    pufa_check_data_count = EnvVariableOperate.get_env_simple_keyValue(key='pufa_check_data_count')
                    if pufa_check_data_count:
                        pufa_check_data_count = int(pufa_check_data_count)
                        pufa_check_data_count += single_check_data_total
                        EnvVariableOperate.writer_update_env_file(key='pufa_check_data_count',
                                                                  value=str(pufa_check_data_count))
                    else:
                        pufa_check_data_count = 0
                        pufa_check_data_count += single_check_data_total
                        EnvVariableOperate.writer_update_env_file(key='pufa_check_data_count',
                                                                  value=str(pufa_check_data_count))

            return [single_check_data_total_dit, single_check_total_writer_count,check_data_total_dit,writer_count]
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"减免流水流程异常,{error_msg}")

class WorkAgent:

    # 开始工作流
    def do_detail(self):

        # 记录动态excel文件写入次数
        writer_count = 0

        try:
            # 获取登录按钮
            get_login_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("login_btn"), ReadConfigUtil.getDesc("login_btn"))
            #判断打开 url 是否处于登录页面
            if get_login_obj.is_visible():
                PageLocator.fill_value(ReadConfigUtil.getLocator("username"),
                                ReadConfigUtil.getFileByKey("username_value"), ReadConfigUtil.getDesc("username"))
                PageLocator.fill_value(ReadConfigUtil.getLocator("password"),
                                ReadConfigUtil.getFileByKey("password_value"), ReadConfigUtil.getDesc("password"))
                # 点击登录按钮
                PageLocator.click(ReadConfigUtil.getLocator("login_btn"), ReadConfigUtil.getDesc("login_btn"))

            # 登录后页面业务操作
            get_login_success_obj = PageLocator.get_tag_object(ReadConfigUtil.getLocator("case_track_lt"),
                                                        ReadConfigUtil.getDesc("case_track_lt"))
            # 登录成功后页面判断
            if get_login_success_obj.is_visible():
                # '案件跟踪' 业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("case_track_lt"),
                           ReadConfigUtil.getDesc("case_track_lt"))
                # '案件跟踪-减免流水'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("tab_reduce_statement"),
                           ReadConfigUtil.getDesc("tab_reduce_statement"))

                # '案件跟踪-减免流水-查询结果-每页展示'业务直接点击操作
                PageLocator.click(ReadConfigUtil.getLocator("red_stat_result_page_count"),
                                  ReadConfigUtil.getDesc("red_stat_result_page_count"))
                PageLocator.page.get_by_text("100条/页").nth(1).click()

                # 查询页面逻辑,查询结果总数字典
                check_data_total_dit = dict()
                # 按照开始结束时间执行
                if exe_auto_status :
                    # '案件跟踪-减免流水-条件筛选-处理状态' 点击操作
                    PageLocator.click(ReadConfigUtil.getLocator("red_stat_approve_status"),
                                      ReadConfigUtil.getDesc("red_stat_approve_status"))
                    PageLocator.page.locator('span').filter(has_text="减免过程中").click()

                    # 获取条件查询，开始结束时间 2021-01-01
                    target_start_date = EnvVariableOperate.get_env_simple_keyValue(key='pufa_target_start_date')

                    target_end_date = TimeFormatData.today_format_str()

                    apply_date_lt = TimeFormatData.get_gap_month_ranges(start_date=target_start_date,
                                                                    end_date=target_end_date,gap_number=1)

                    for i in apply_date_lt:

                        start_date = i[0]
                        end_date = i[1]
                        single_check_total_lt = CaseTrack.reduce_rush_water(start_date=start_date, end_date=end_date, check_data_total_dit=check_data_total_dit,
                                                                            apply_date=i, writer_count=writer_count)
                        check_data_total_dit = single_check_total_lt[2]
                        writer_count = single_check_total_lt[3]

                    single_check_data_total_dit = single_check_total_lt[0]
                    single_check_total_writer_count = single_check_total_lt[1]

                # 按照指定 excel 文件执行
                else:
                    all_sheet_dit = ExcelReadWriter.read_all_sheets(manual_file)

                    for ky,vl in all_sheet_dit.items():
                        for j in range(len(vl)):
                            if j > 0:
                                start_date = vl[j][0].split(' ')[0]
                                end_date = start_date
                                custom_id = vl[j][3]
                                single_check_total_lt = CaseTrack.reduce_rush_water(start_date=start_date, end_date=end_date, check_data_total_dit=check_data_total_dit,
                                                                                    apply_date=(start_date,start_date), writer_count=writer_count,custom_id = custom_id)

                                check_data_total_dit = single_check_total_lt[2]
                                writer_count = single_check_total_lt[3]

                        single_check_data_total_dit = single_check_total_lt[0]
                        single_check_total_writer_count = single_check_total_lt[1]

                # 统计总的查询与写入次数log
                SummaryLog.get_all_search_log(check_data_total_dit,writer_count)

            else:
                logger.info(f"自动化脚本进入业务页面失败，请人工查看！！！")
                PageLocator.save_screen(png_folder=err_png_folder)
                AlertTools.send_robot(current_file_name=current_file_name,
                                      text=f"自动化脚本进入业务页面失败，请人工查看！！！", logger=logger)
        except Exception as e:
            traceback.print_exc()
            logger.error(f"执行业务程序异常，异常信息 {e}")
            PageLocator.save_screen(png_folder=err_png_folder)
            AlertTools.send_robot(current_file_name=current_file_name,
                                  text=f"执行业务程序异常，请人工手动介入操作！", logger=logger)
            # 统计最后一次查询与写入次数log
            SummaryLog.get_single_search_log(single_check_data_total_dit, single_check_total_writer_count)
            # 统计总的查询与写入次数log
            SummaryLog.get_all_search_log(check_data_total_dit, writer_count)

            # # 统计总的查询与写入次数
            # check_data_total = sum(check_data_total_dit.values())
            # logger.info(
            #     f"一共查询到 {check_data_total} 条数据, 脚本执行了 {writer_count} 次点击操作, 查询结果与执行操作差值 {check_data_total - writer_count}\n查询结果原始数据 {check_data_total_dit}")

    # 结束工作流
    def done_work_over(self):
        try:
            PageLocator.save_screen()
            page.keyboard.press("Alt+F4")  # 关闭当前活动窗口或程序
            browser.close()
            playwright_client.stop()
            ChromeOperat.kill_chrome()
            ExcelDynamicWriter.save_workbook() # 保存最终结果（此时最后一个 sheet 也会被保存）
        except Exception as e:
            traceback.print_exc()
            logger.error(f"结束工作流异常, 异常信息 {e}")

    @staticmethod
    def task_main():
        # 程序运行计时器开始
        Timer.start()

        AlertTools.send_robot(current_file_name=current_file_name,
                              text=f"案件跟踪-减免流水-操作开始", logger=logger)
        # 获取class object
        agent = WorkAgent()
        # config文件，全部业务操作逻辑
        agent.do_detail()
        # 结束工作流程操作
        agent.done_work_over()
        AlertTools.send_robot(current_file_name=current_file_name,
                              text=f"案件跟踪-减免流水-操作结束", logger=logger)
        logger.info("程序完整运行结束了")
        # 程序计时器结束
        elapsed = Timer.stop()
        logger.info(f"{current_file_name}项目,程序运行花费时间 {elapsed} ")


#定时任务程序
class ScheduledTask:

    def check_termination(self,now,pufa_target_start_date):
        """
            : 业务条件查询时间大于当前时间，终止定时任务
            return: bool -> True 终止程序, False 继续程序
        """
        pufa_target_start_date = datetime.strptime(pufa_target_start_date,"%Y-%m-%d")
        if pufa_target_start_date > now:
            return True
        return False


    def is_time_between(self,now, start, end):
        """判断当前时间是否在指定时间段内（不考虑日期）"""
        start_dt = now.replace(hour=start[0], minute=start[1], second=start[2], microsecond=0)
        end_dt = now.replace(hour=end[0], minute=end[1], second=end[2], microsecond=0)
        return start_dt <= now <= end_dt

    def wait_until_start(self):
        """等待到下一个开始时间（每天 START_TIME）"""
        now = datetime.now()
        start_dt = now.replace(hour=START_TIME[0], minute=START_TIME[1], second=START_TIME[2], microsecond=0)
        if now >= start_dt:
            # 如果今天已经开始，则等待明天的开始时间
            start_dt += timedelta(days=1)
        wait_seconds = (start_dt - now).total_seconds()
        logger.info(f"[系统] 距离下次任务开始还有 {TimeFormatData.format_time_seconds(wait_seconds)} 秒")
        # print(f"[系统] 距离下次任务开始还有 {wait_seconds:.2f} 秒")
        # time.sleep(wait_seconds)

        pufa_target_start_date = EnvVariableOperate.get_env_simple_keyValue(key="pufa_check_data_count")
        # 分段等待，每 CHECK_INTERVAL 秒检查一次终止条件
        while wait_seconds > 0:
            if self.check_termination(now,pufa_target_start_date):
                logger.info(f"[系统] 环境变量文件 pufa_target_start_date = {pufa_target_start_date}, 大于当前时间，终止条件满足，定时任务程序终止！")
                ChromeOperat.kill_chrome()
                sys.exit(0)
            sleep_time = min(CHECK_INTERVAL, wait_seconds)
            time.sleep(sleep_time)
            wait_seconds -= sleep_time

    # ==================== 任务执行封装（子进程） ====================
    def run_task_in_subprocess(self):
        """在子进程中执行用户任务，用于超时强制终止"""
        try:
            #业务程序主入口
            WorkAgent.task_main()
            sys.exit(0)      # 成功退出码 0
        except Exception as e:
            traceback.print_exc()
            logger.error(f"[业务任务] 执行失败: {e}")
            # print(f"[任务] 执行失败: {e}")
            sys.exit(1)      # 失败退出码 1

    # ==================== 核心调度逻辑 ====================
    def run_daily_tasks(self):
        """在当天时间段内执行带重试机制的任务循环"""
        retry_count = 0
        while True:
            now = datetime.now()
            pufa_target_start_date = EnvVariableOperate.get_env_simple_keyValue(key="pufa_target_start_date")
            # 每次循环开始前检查终止条件
            if self.check_termination(now,pufa_target_start_date):
                logger.info(f"[系统] 环境变量文件 pufa_target_start_date = {pufa_target_start_date}, 大于当前时间，终止条件满足，定时任务程序终止！")
                break

            # 1. 检查是否超出结束时间
            if not self.is_time_between(now, START_TIME, END_TIME):
                logger.info(f"[系统] 已超出当天结束时间，停止任务")
                # print("[系统] 已超出当天结束时间，停止任务")
                break

            # 2. 启动子进程执行用户任务
            process = multiprocessing.Process(target=self.run_task_in_subprocess)
            process.start()

            # 3. 监控子进程，直到它结束或时间到达 END_TIME
            while process.is_alive():
                if not self.is_time_between(datetime.now(), START_TIME, END_TIME):
                    # 时间已到 20:30，强制终止子进程
                    # print("[系统] 到达结束时间，强制终止当前任务")
                    logger.info("[系统] 到达结束时间，强制终止当前任务")
                    process.terminate()
                    process.join()
                    break

                pufa_target_start_date = EnvVariableOperate.get_env_simple_keyValue(key="pufa_target_start_date")
                # 监控期间也检查终止条件
                if self.check_termination(now,pufa_target_start_date):
                    logger.info(f"[系统] 环境变量文件 pufa_target_start_date = {pufa_target_start_date}, 大于当前时间，终止条件满足，定时任务程序终止！")
                    process.terminate()
                    process.join()
                    ChromeOperat.kill_chrome()
                    sys.exit(0)
                time.sleep(CHECK_INTERVAL)  # 定期检查时间

            # 4. 处理子进程结束结果
            exit_code = process.exitcode
            if exit_code == 0:
                # 成功执行，重置重试计数器
                retry_count = 0
                # print("[系统] 任务成功完成，继续下一轮")
                logger.info("[系统] 任务成功完成，继续下一轮")
                # 可以选择添加一个短暂的延时再进入下一轮，避免过紧循环（可选）
                time.sleep(60)  # 例如每轮之间间隔1分钟
                continue
            else:
                # 执行失败或被超时终止
                if not self.is_time_between(datetime.now(), START_TIME, END_TIME):
                    # 因为超时终止导致的失败，直接退出当天循环
                    # print("[系统] 任务因时间截止而中断，不再重试")
                    logger.error("[系统] 任务因时间截止而中断，不再重试")
                    break
                else:
                    # 任务执行失败，进入重试流程
                    retry_count += 1
                    if retry_count <= MAX_RETRIES:
                        # print(f"[系统] 任务失败，{RETRY_INTERVAL//60} 分钟后进行第 {retry_count} 次重试")
                        logger.info(f"[系统] 任务失败，{RETRY_INTERVAL//60} 分钟后进行第 {retry_count} 次重试")
                        # 等待重试间隔，期间持续检查是否超时
                        wait_remaining = RETRY_INTERVAL
                        while wait_remaining > 0:
                            if not self.is_time_between(datetime.now(), START_TIME, END_TIME):
                                # print("[系统] 重试等待期间已超时，放弃重试")
                                logger.info("[系统] 重试等待期间已超时，放弃重试")
                                break

                            pufa_target_start_date = EnvVariableOperate.get_env_simple_keyValue(
                                key="pufa_target_start_date")
                            if self.check_termination(now,pufa_target_start_date):
                                logger.info(f"[系统] 环境变量文件 pufa_target_start_date = {pufa_target_start_date}, 大于当前时间，终止条件满足，定时任务程序终止！")
                                ChromeOperat.kill_chrome()
                                sys.exit(0)
                            sleep_step = min(CHECK_INTERVAL, wait_remaining)
                            time.sleep(sleep_step)
                            wait_remaining -= sleep_step
                        if not self.is_time_between(datetime.now(), START_TIME, END_TIME):
                            logger.info("[系统] 重试等待期间已超时，退出循环")
                            break  # 超时，退出循环
                        # 继续下一次循环，重新启动任务
                        logger.info("[系统]任务执行失败，进入重试流程，继续下一次循环，重新启动任务")
                        continue
                    else:
                        # 重试次数耗尽，发送警报并退出当天任务

                        AlertTools.send_robot(current_file_name=current_file_name,
                                              text=f"自动化任务连续失败3次，已终止当天任务", logger=logger)
                        logger.info("[系统] 达到最大重试次数，停止当天任务")
                        # print("[系统] 达到最大重试次数，停止当天任务")
                        break

    # ==================== 定时任务启动主程序 ====================

    def cron_job_main(self):
        # print("自动化调度程序启动")
        logger.info("定时任务-自动化调度程序启动")
        while True:
            now = datetime.now()
            pufa_target_start_date = EnvVariableOperate.get_env_simple_keyValue(key="pufa_target_start_date")
            if self.check_termination(now,pufa_target_start_date):
                logger.info(f"[系统] 环境变量文件 pufa_target_start_date = {pufa_target_start_date}, 大于当前时间，终止条件满足，定时任务程序终止！")
                ChromeOperat.kill_chrome()
                sys.exit(0)

            # 支持随时重启：如果当前时间在时间段内，立即进入当天任务
            if self.is_time_between(now, START_TIME, END_TIME):
                # print("[系统] 当前时间在运行时间段内，立即开始执行")
                logger.info("[系统] 当前时间在运行时间段内，立即开始执行")
            else:
                # 否则等待下一个开始时间
                logger.info("[系统] 当前时间不在运行时间段内，等待下一个开始时间")
                self.wait_until_start()

            # 执行当天任务
            self.run_daily_tasks()

            # 当天任务结束后，强制关闭所有 Chrome 进程
            ChromeOperat.kill_chrome()
            # 循环会继续等待第二天的开始时间

if __name__ == "__main__":
    # 确保子进程能够正常启动
    AlertTools.send_robot(current_file_name=current_file_name,
                          text=f"自动化定时任务开始执行", logger=logger)
    #守护进程，必须要有
    multiprocessing.freeze_support()
    #启动定时任务程序
    ScheduledTask().cron_job_main()

    AlertTools.send_robot(current_file_name=current_file_name,
                      text=f"自动化定时任务完成执行, 请人工介入查看！", logger=logger)



#
# if __name__ == '__main__':
#     # 程序运行计时器开始
#     Timer.start()
#
#     AlertTools.send_robot(current_file_name=current_file_name,
#                           text=f"案件跟踪-减免流水-操作开始", logger=logger)
#     # 获取class object
#     agent = WorkAgent()
#     # config文件，全部业务操作逻辑
#     agent.do_detail()
#     # 结束工作流程操作
#     agent.done_work_over()
#     AlertTools.send_robot(current_file_name=current_file_name,
#                           text=f"案件跟踪-减免流水-操作结束", logger=logger)
#     logger.info("程序完整运行结束了")
#     # 程序计时器结束
#     elapsed = Timer.stop()
#     logger.info(f"{current_file_name}项目,程序运行花费时间 {elapsed} ")
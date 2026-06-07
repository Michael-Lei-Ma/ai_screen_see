# -*- coding: utf-8 -*-
from datetime import date,datetime,timedelta
from dateutil.relativedelta import relativedelta
import time



class TimeFormatData:

    @staticmethod
    def get_gap_month_ranges(start_date: str, end_date: str,gap_number:int)->list:
        '''
            : 获取开始日期 - 结束日期，固定间隔，时间数组，用于条件筛选，时间控件选择开始结束时间；
            params:
                start_date: 开始日期, 时间格式 YYYY-MM-DD;
                end_date: 结束日期, 时间格式 YYYY-MM-DD;
                gap_number: 每次选择间隔的月数, 例: gap_number=6 ,含义间隔6个月;
            return:
                ranges: 返回时间区间内, gap_number间隔数的数组，元素是tuple;

        '''
        start_date = date.fromisoformat(start_date)
        end_date = date.fromisoformat(end_date)
        ranges = []
        current = start_date

        while current < end_date:
            next_date = current + relativedelta(months=gap_number)
            range_end = min(next_date - relativedelta(days=1), end_date)
            ranges.append((current.strftime("%Y-%m-%d"), range_end.strftime("%Y-%m-%d")))
            current = next_date

        return ranges

    @staticmethod
    def today_format_str(time_format:str = "%Y-%m-%d")->str:
        '''
            : 当日格式化时间字符串；
            params:
                time_format: 格式化时间格式, 默认格式 "%Y-%m-%d";
            return:
                today_time: 时间字符串；
        '''
        today_time = datetime.now().strftime(time_format)
        return today_time

    @staticmethod
    def coming_days_format_str(date_str, time_format='%Y-%m-%d',days=1)->str:
        '''
            : 获取目标时间几天后的格式化时间字符串；
            params:
                date_str: 目标时间字符串 ;
                time_format: 字符串时间格式, 这个格式化规则要跟 date_str 输入类型保持一致, 默认格式 "%Y-%m-%d" ;
                days: 查询后的间隔天数，默认查询转天的时间 ;
            return:
                coming_days: 目标时间未来几天后的时间字符串；
        '''
        """获取指定日期的明天日期字符串"""
        date_obj = datetime.strptime(date_str, time_format).date()
        coming_days = date_obj + timedelta(days=days)
        return coming_days.strftime(time_format)

    @staticmethod
    def past_days_format_str(date_str:str=None, time_format='%Y-%m-%d',days=1)->str:
        '''
            : 获取目标时间几天前的格式化时间字符串；
            params:
                date_str: 目标时间字符串 ;
                time_format: 字符串时间格式, 这个格式化规则要跟 date_str 输入类型保持一致, 默认格式 "%Y-%m-%d" ;
                days: 查询后的间隔天数，默认查询昨天的时间 ;
            return:
                coming_days: 目标时间过去几天后的时间字符串；
        '''
        if date_str is None:
            # 获取当前日期几天前日期字符串
            past_days= datetime.now() - timedelta(days=days)
        else:
            # 获取指定日期的几天前日期字符串
            date_obj = datetime.strptime(date_str, time_format).date()
            past_days = date_obj - timedelta(days=days)
        return past_days.strftime(time_format)
    @staticmethod
    def format_time_seconds(seconds):
        """
        将秒数转换为 HH:MM:SS.fff 格式。
        例如：1小时2分钟3.456秒 -> 01:02:03.456
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        # milliseconds = int((seconds % 1) * 1000)
        # 智能格式：根据时长自动选择格式
        if hours > 0:
            return f"{hours:02d}小时{minutes:02d}分{secs:06.3f}秒"
        elif minutes > 0:
            return f"{minutes:02d}分{secs:06.3f}秒"
        else:
            return f"{secs:06.3f}秒"

    @staticmethod
    def get_now_hour()->int:
        """
            : 计算当日，现在已经过去了多少小时;
            return:
                hours_passed : int ;
        """
        # 获取当前时间
        now = datetime.now()
        hours_passed = now.hour
        return hours_passed


class Timer:
    """
        计时器类，支持上下文管理器（with 语句）和手动开始/结束。
        运行结束后自动将耗时格式化为 HH:MM:SS.fff 格式。
        : 程序运行时长计时器 ;
        params:
            logger: 自定义的 log 日志句柄 ;
            auto_start: 是否在创建实例时自动开始计时 ;
        return:
            返回程序运行时长字符串 ;
        用法详解:
            例1:
                # 方式1：使用上下文管理器（推荐）
                with Timer(logger):
                    # 此处放置需要计时的代码
                    time.sleep(2.5)          # 模拟耗时操作
                    sum(range(1000000))      # 模拟计算
            例2:
                # 方式2：手动控制, 自动开始计时
                timer = Timer(auto_start=True)
                time.sleep(1.2) # 你的程序
                elapsed = timer.stop()
                print(f"手动计时结果：{elapsed}")
            例3:
                # 方式3：手动控制, 手动开始计时
                timer = Timer(auto_start=False)
                timer.start()
                time.sleep(1.2) # 你的程序
                elapsed = timer.stop()
                print(f"手动计时结果：{elapsed}


    """

    def __init__(self, logger,auto_start=False):
        """
        初始化计时器。
        :param auto_start: 是否在创建实例时自动开始计时
        """
        self.start_time = None
        self.end_time = None
        if auto_start:
            self.start()
        self.logger = logger

    def start(self):
        """开始计时"""
        self.start_time = time.perf_counter()
        self.end_time = None

    def stop(self):
        """停止计时，返回格式化的时间字符串"""
        if self.start_time is None:
            raise RuntimeError("计时尚未开始，请先调用 start() 方法")
        self.end_time = time.perf_counter()
        elapsed = self.end_time - self.start_time
        return self._format_time(elapsed)

    def _format_time(self, seconds):
        """
        将秒数转换为 HH:MM:SS.fff 格式。
        例如：1小时2分钟3.456秒 -> 01:02:03.456
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        # milliseconds = int((seconds % 1) * 1000)
        # 智能格式：根据时长自动选择格式
        if hours > 0:
            return f"{hours:02d}小时{minutes:02d}分{secs:06.3f}秒"
        elif minutes > 0:
            return f"{minutes:02d}分{secs:06.3f}秒"
        else:
            return f"{secs:06.3f}秒"

    def __enter__(self):
        """进入上下文时开始计时"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时结束计时并打印结果"""
        elapsed_str = self.stop()
        self.logger.info(f"程序运行时间：{elapsed_str}")





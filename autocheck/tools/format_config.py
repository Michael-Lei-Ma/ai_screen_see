# -*- coding: utf-8 -*-
import traceback
from logging.handlers import TimedRotatingFileHandler
import logging,sys,os,json
import requests
from pathlib import Path
import os
import re
import glob
from datetime import datetime, timedelta
import shutil

#log日志输出配置
class LogConfig:

    # 设置日志格式
    log_fmt = logging.Formatter(
        '[%(asctime)s] | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    @staticmethod
    def get_logger(current_file_name: str = 'logs',console_level: logging.Logger  =logging.DEBUG,file_level:logging.Logger =logging.DEBUG,
                   log_fmt=log_fmt)->logging.Logger:
        '''
            : 设置 控制台 + 滚动日志文件的 logger ;
            params:
                current_file_name: 调用程序文件名称, 默认 None 用根日志器;
                console_level: 控制台日志级别 ;
                file_level: 文件日志级别 ;
            return: 返回一个 logger 对象;
        '''

        """返回一个同时写控制台 + 滚动日志文件的 logger"""
        logger = logging.getLogger(current_file_name)

        # # 防止重复添加处理器（例如多次调用该函数）
        # for handler in logger.handlers[:]:
        #     logger.removeHandler(handler)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        logger.setLevel(file_level)  # 全局最低级别

        # ---------- 1. 控制台 - 设置输出级别为INFO----------
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(console_level)  # 控制台只看 INFO 及以上
        # 控制台日志输出操作
        console.setFormatter(log_fmt)
        logger.addHandler(console)

        # ---------- 2. 每天滚动日志文件 ----------
        logs_path = GetFilePath.get_folder_path('logs')
        file_handler = TimedRotatingFileHandler(
            filename=f'{logs_path}/{current_file_name}.log',  # 会自动创建 logs 目录
            when="midnight",  # 每天午夜滚动  midnight
            interval=1,  # 间隔数量，与 when 共同决定轮转周期
            backupCount=5,  # 只留最近 5 份
            encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        # 输出日志文件操作
        file_handler.setFormatter(log_fmt)
        logger.addHandler(file_handler)

        return logger

# 获取文件path路径
class GetFilePath:

    # 获取二级文件夹路径
    @staticmethod
    def get_folder_path(folder_name:str,file_name:str=str()):
        current_project_path = os.path.dirname(os.path.dirname(__file__))
        folder_path = os.path.join(current_project_path, folder_name,file_name)
        # os.makedirs(folder_path, exist_ok=True)
        return folder_path
    # 获取二、三级文件夹路径, 支持自动创建文件夹
    @staticmethod
    def get_png_path(level_one_folder:str =str(),level_two_folder:str =str(),file_name:str = str(),create_folder:bool = False)->str:
        current_project_path = os.path.dirname(os.path.dirname(__file__))
        folder_path = os.path.join(current_project_path, level_one_folder, level_two_folder,file_name)
        if create_folder:
            os.makedirs(folder_path, exist_ok=True)

        return folder_path

    @staticmethod
    def get_config_file_path(file_name:str):
        current_project_path = os.path.dirname(os.path.dirname(__file__))
        file_path = os.path.join(current_project_path, 'config',file_name)
        return file_path

    #获取文件夹、文件路径, 不受层级限制
    @staticmethod
    def get_folder_file_path(*args: str, current_project_path: str = None)->Path:
        '''
            : 该方法获取目标文件夹、文件 绝对路径, 访问文件夹、文件层级不受限制, 返回对象是 pathlib.Path,
              查询文件夹路径不存在, 会默认创建查询文件夹链路全部不存在的文件夹 ;
            params:
                *args: 动态获取入参，入参之间用英文逗号 ',' 隔开 ;
                current_project_path: 默认None, 目标文件夹绝对路劲 ,一般是当前项目根目录 ;
            return:
                返回一个 pathlib.Path 对象 , 要想获取的str 对象, 只需要调用函数后获取返回结果格式化就行 例: str(relay_path)
            用法详解:
                用法1:
                    GetFilePath.get_folder_file_path('folder1','folder2','fileName') -> C:\ProgramData\Exec\autocheck\png\error_png\fiyu_134.png
                用法2:
                    GetFilePath.get_folder_file_path('folder1','folder2') -> 正常调用方法
                    GetFilePath.get_folder_file_path('folder1','folder2','')
                    GetFilePath.get_folder_file_path('folder1','folder2','/')
                    GetFilePath.get_folder_file_path('folder1','folder2','\\')
                    以上方法结果都是如下:(想表达兼容常见异常写法)
                    result -> C:\ProgramData\Exec\autocheck\png\error_png
                用法3:
                    GetFilePath.get_folder_file_path('fileName') -> 正常调用方法
                    GetFilePath.get_folder_file_path('‘,’/‘,'\\','fileName')
                    以上方法结果都是如下:(想表达兼容常见异常写法)
                    result -> C:\ProgramData\Exec\autocheck\fiyu_134.png
                用法4:
                    GetFilePath.get_folder_file_path('folder1'，'‘,’/‘,'\\','fileName') -> C:\ProgramData\Exec\autocheck\png\fiyu_134.png
        '''



        if current_project_path:
            # str 格式化为 Path 对象
            current_project_path = Path(current_project_path)
        else:
            current_project_path = Path(__file__).resolve().parents[1]
        # 清理空字符串和首尾斜杠
        clean_args = [p.strip().strip("/\\") for p in args if p and p.strip()]

        # 判断是否传参 *args
        if clean_args:
            #将路径转换为绝对路径
            relay_path = current_project_path.joinpath(*clean_args).resolve()
            # 获取最后一个组成部分
            last_part = relay_path.name
            # 通过后缀判断 path 路径有无扩展名 或 通过最后部分筛选  .gitignore 、 archive.tar.gz 等特殊类型文件
            if relay_path.suffix or '.' in last_part:
                # 如果最后一段是文件名，则去掉它，只保留文件夹链路
                dir_args = clean_args[:-1]
                # 获取文件夹路径
                dir_path = current_project_path.joinpath(*dir_args).resolve()
            else:
                dir_path = relay_path

            # 判断文件夹路径是否存在
            if dir_path.exists():
                return relay_path
            else:
                # 文件夹路径不存在, 创建文件夹路径
                dir_path.mkdir(parents=True, exist_ok=True)
                return relay_path
        else:
            #没有参数，返回当前项目路径
            relay_path = current_project_path
            return relay_path

# a ="fiyu"
# b= '134'
# ry_pt = GetFilePath.get_folder_file_path(f'{a}_'+b+'.png',current_project_path="C:\\ProgramData\\Exec\\autocheck\\png\\error_png\\")
# print(ry_pt)

# 报警工具
class AlertTools:

    webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fd05c3f4-78b0-4206-bd96-7c421b2107c4"
    # 请求 企微 weekhook 机器人 API
    @classmethod
    def send_robot(cls,current_file_name:str,text:str,logger:logging.Logger, at_mobiles=None):
        """
        企业微信群机器人发文本
        :param webhook: 机器人 Webhook 地址
        :param current_file_name: 调用程序文件名，或自动定义字符串；
        :param text: 文本内容
        :param logger: 调用程序启动的logger 处理器,;
        :param at_mobiles: 要@的手机号列表，填 ["@all"] 全员
        """
        body = {
            "text": current_file_name + text
        }
        try:
            resp = requests.post("http://10.255.100.202:8000/alert", json=body, timeout=60)
            logger.info(resp.json())
            # print(f"resp data: {resp.text}")
        except Exception as e:
            traceback.print_exc()
            logger.error(e)
            return {"errcode": 1, "errmsg": str(e)}

# 获取配置文件中的信息
class ReadConfigUtil:

    def __init__(self,logger,file_name):
        self.logger = logger
        self.configJson = {}
        self.file_name = file_name

    # 读取配置文件信息
    def loadFile(self):
        config_file = GetFilePath.get_config_file_path(self.file_name)
        with open(config_file, "r", encoding="utf-8") as f:
            self.configJson = json.loads(f.read())
            self.logger.info("加载配置文件完毕:" + json.dumps(self.configJson))
        return self.configJson

    # 获取配置文件指定 key 的 value
    def getFileByKey(self, key):
        self.logger.info("获取key:" + key)
        return self.configJson.get(key)

    # 获取配置文件指定 key 下 desc 的value
    def getDesc(self, key):
        self.logger.info("获取key:" + key)
        return self.configJson.get(key, {}).get("desc")

    # 取配置文件指定 key 下 locator 的value
    def getLocator(self, key):
        self.logger.info("获取key:" + key)
        return self.configJson.get(key, {}).get("locator")

#清除目录下的文件
class ClearExpiredImage:

    def __init__(self,logger):
        self.logger = logger

    def extract_timestamp(self,filename: str,time_format:str = "%Y_%m_%d_%H%M%S")->datetime:
        """
            从文件名中提取 YYYY_MM_DD_HHMMSS 格式的时间戳。
                time_format: 时间戳格式变化，需要同步修改 pattern 正则匹配规则
            返回 datetime 对象，若未找到则返回 None。
        """
        # 匹配 4位数字_2位数字_2位数字_6位数字
        pattern = r'(\d{4}_\d{2}_\d{2}_\d{6})'
        match = re.search(pattern, filename)
        if not match:
            return None
        timestamp_str = match.group(1)  # 例如 "2026_04_01_120105"
        try:
            # 解析为 datetime 对象
            return datetime.strptime(timestamp_str, time_format)
        except ValueError:
            return None

    def delete_old_images(self,folder_path:str, days:int =7)->None:
        """
            删除指定文件夹中超过指定天数的 PNG 图片。
            folder_path: 文件夹路径
            days: 保留天数（默认7天）
        """
        # # 确保路径末尾有斜杠（便于拼接）
        # if not folder_path.endswith(os.sep):
        #     folder_path += os.sep

        # 获取所有 PNG 文件
        png_files = glob.glob(os.path.join(folder_path, "*.png"))

        # 当前时间
        now = datetime.now()
        cutoff = now - timedelta(days=days)

        deleted_count = 0
        for file_path in png_files:
            filename:str = os.path.basename(file_path)  # 带后缀的文件名称
            file_time:datetime = self.extract_timestamp(filename) # 文件名称中提取的时间对象
            if file_time is None:
                # 文件名不符合时间格式，跳过
                self.logger.info(f"跳过（无法解析时间）: {filename}")
                continue
            if file_time < cutoff:
                try:
                    os.remove(file_path)
                    self.logger.info(f"已删除: {filename} (时间 {file_time})")
                    deleted_count += 1
                except OSError as e:
                    traceback.print_exc()
                    self.logger.error(f"删除失败 {filename}: {e}")
            # else:
            #     self.logger.info(f"保留: {filename} (时间 {file_time})")
        self.logger.info(f"共删除过期图片 {deleted_count} 个文件")
        # print(f"\n共删除 {deleted_count} 个文件")

    def delete_include_name_images(self,folder_path:str, fileName:str):
        '''
            删除指定文件夹中包含指定文件名的 PNG 图片。
            folder_path: 文件夹路径
            fileName: 指定文件名
                : fileName = xinye -> 就会删除包含 xingye  的全部文件
                : fileName = .png -> 就会删除包含 .png  的全部文件
        '''

        # 获取所有 PNG 文件
        png_files = glob.glob(os.path.join(folder_path, "*.png"))
        deleted_count = 0
        for file_path in png_files:
            filename:str = os.path.basename(file_path)  # 带后缀的文件名称
            if fileName in filename:
                try:
                    os.remove(file_path)
                    self.logger.info(f"已删除: {filename}")
                    deleted_count += 1
                except OSError as e:
                    traceback.print_exc()
                    self.logger.error(f"删除失败 {filename}: {e}")
        self.logger.info(f"共删除 {deleted_count} 个文件")

# project_path = 'D:\\ProjectCollection\\malei\\ai_screen_see\\autocheck'
# logger = LogConfig.get_logger()
# ClearExpiredImage = ClearExpiredImage(logger)
# GetFilePath = GetFilePath()
# png_path = GetFilePath.get_folder_file_path('png')
# print(png_path)
# # ClearExpiredImage.delete_old_images(folder_path=png_path)
# ClearExpiredImage.delete_include_name_images(folder_path=png_path,fileName='.png')

class ClearExpiredFile:

    def __init__(self,logger):
        self.logger = logger

    def delete_old_folders_by_time_format(self,root_dir, time_format, days_threshold=15, dry_run=True):
        """
        删除指定目录下，文件夹名称中包含指定时间格式且时间超过阈值的文件夹。

        Args:
            root_dir (str): 要清理的根目录路径
            time_format (str): 时间格式，如 " %Y_%m_%d_%H_%M_%S " 或 "%Y_%m_%d"
            days_threshold (int): 保留最近多少天，默认 15 天
            dry_run (bool): True 时仅打印不实际删除，False 时执行删除
        """
        # 保留原始格式字符串，用于 strptime
        original_format = time_format
        # 1. 将时间格式转换为正则表达式（匹配时间子串）
        # 格式符与正则的映射
        format_map = {
            '%Y': r'(?P<Y>\d{4})',
            '%m': r'(?P<m>\d{2})',
            '%d': r'(?P<d>\d{2})',
            '%H': r'(?P<H>\d{2})',
            '%M': r'(?P<M>\d{2})',
            '%S': r'(?P<S>\d{2})',
        }
        # 临时替换格式符为占位符，避免转义
        placeholders = []
        for i, fmt in enumerate(format_map.keys()):
            placeholder = f"__PH_{i}__"
            placeholders.append((fmt, placeholder))
            time_format = time_format.replace(fmt, placeholder)
        # 转义剩余字符（此时格式符已被占位符替代）
        escaped = re.escape(time_format)
        # 将占位符替换回对应的正则表达式
        for i, (fmt, placeholder) in enumerate(placeholders):
            regex = format_map[fmt]
            escaped = escaped.replace(re.escape(placeholder), regex)
        # 最终正则，不要求完全匹配，只搜索子串
        pattern = re.compile(escaped)

        # 2. 计算截止时间
        now = datetime.now()
        cutoff = now - timedelta(days=days_threshold)

        if not os.path.exists(root_dir):
            print(f"错误：路径不存在 - {root_dir}")
            return

        deleted_count = 0
        kept_count = 0
        skipped_count = 0

        for item in os.listdir(root_dir):
            item_path = os.path.join(root_dir, item)
            if not os.path.isdir(item_path):
                continue

            # 在文件夹名中搜索匹配的时间子串
            match = pattern.search(item)
            if not match:
                # 无时间戳，跳过
                skipped_count += 1
                continue

            time_str = match.group(0)  # 提取的时间字符串
            try:
                # 解析时间（注意：若格式缺少部分字段，strptime 会用默认最小值，如时分秒为0）
                folder_time = datetime.strptime(time_str, original_format)
            except ValueError as e:
                # print(f"警告：时间解析失败，跳过文件夹 '{item}' -> {e}")
                error_msg  = traceback.format_exc()
                self.logger.error(f"时间解析异常 : {error_msg}")
                skipped_count += 1
                continue

            # 判断是否过期
            if folder_time < cutoff:
                # print(f"[删除] {item} (时间: {folder_time})")
                if not dry_run:
                    try:
                        shutil.rmtree(item_path, ignore_errors=False)
                        # print(f"  已删除: {item_path}")
                    except Exception as e:
                        error_msg = traceback.format_exc()
                        self.logger.error(f"删除文件夹异常 : {error_msg}")
                        # print(f"  删除失败: {e}")
                else:
                    # print(f"  [试运行] 将删除: {item_path}")
                    pass
                deleted_count += 1
            else:
                # print(f"[保留] {item} (时间: {folder_time})")
                kept_count += 1

        # print(f"\n统计：保留 {kept_count} 个，删除 {deleted_count} 个，跳过 {skipped_count} 个（无时间戳或解析失败）")
        self.logger.info(f"\n统计：保留 {kept_count} 个，删除 {deleted_count} 个，跳过 {skipped_count} 个（无时间戳或解析失败）")
        if dry_run:
            # print("提示：当前为试运行模式，未实际删除。设置 dry_run=False 执行真实删除。")
            self.logger.info("提示：当前为试运行模式，未实际删除。设置 dry_run=False 执行真实删除。")

# # ========== 使用示例 ==========
# # 请修改为实际要清理的根目录路径
# target_dir = GetFilePath.get_folder_file_path('download')
# # print(target_dir)
# # # 示例：不同时间格式
# time_format_example = "%Y_%m_%d_%H_%M_%S"  # 注意前后空格
# # time_format_example = "%Y_%m_%d_%H%M%S"
# # time_format_example = "%Y_%m_%d_%H%M"
# # time_format_example = "%Y_%m_%d_%H"
# # time_format_example = "%Y_%m_%d"
# logger = LogConfig.get_logger()
# # 先试运行（仅打印）
# ClearExpiredFile(logger).delete_old_folders_by_time_format(target_dir, time_format_example, days_threshold=15, dry_run=True)
#
# # 确认无误后，改为 dry_run=False 执行真实删除
# # ClearExpiredFile(logger).delete_old_folders_by_time_format(target_dir, time_format_example, days_threshold=15, dry_run=False)




# -*- coding: utf-8 -*-

import re


class StrDataExtract:
    """
        : web UI 自动化中，获取到查询结果页面总数字符串 如: '共 100 条'，数字提取 ;
            params:
                logger: 自定义全局记录log 日志句柄 ;
    """
    def __init__(self,logger):
        self.logger =logger

    def get_page_pagesNumber_from_str(self,text:str)->int:
        '''
            text: 获取到查询结果页面总数字符串 如: '共 100 条' ;
            return:
                pageNumber: 需要点击翻页查询的次数, 默认: 0 ;
        '''

        self.logger.info("获取查询结果总条数%s" % text)
        # 提取数字
        match = re.search(r'共\s*(\d+)\s*条', text)
        if match:
            count = int(match.group(1))
            # print(f"提取的数字: {count}")
            self.logger.info(f"查询结果总条数,提取的数字:{count}")
        if count>=0:
            pageNumberInt = count // 100
            pageNumberDecimal = count % 100
            if pageNumberInt > 0 and pageNumberDecimal != 0:
                pageNumber = pageNumberInt
            elif pageNumberInt > 0 and pageNumberDecimal == 0:
                pageNumber = pageNumberInt - 1
            else:
                pageNumber = 0

            return pageNumber

    def get_page_totalNumber_from_str(self,text:str)->int:
        '''
            text: 获取到查询结果页面总数字符串 如: '共 100 条' ;
            return:
                count: 正则提取的查询总数 ;
        '''
        # 提取数字
        match = re.search(r'共\s*(\d+)\s*条', text)
        if match:
            count = int(match.group(1))
            self.logger.info(f"查询结果总条数,提取的数字:{count}")
            return count

class StrRegularExtract:
    """
        : 正则表达式提取字符串中的信息
    """
    @staticmethod
    def re_get_file_password(msg_str:str)->list:
        """
            : 正则表达式提取字符串中的文件名、文件访问密码
            Args:
                msg_str: 要提取的字符串, 例: "您下载的[案件流转明细_20260416150712.xlsx]，文件解锁请使用[2Cl4gp3cr]，请勿外泄。"
            return:
                返回一个 list, 例: ['案件流转明细_20260416150712.xlsx', '2Cl4gp3cr']
        """
        ext_lt = re.findall(r'\[(.*?)\]', msg_str)
        return ext_lt



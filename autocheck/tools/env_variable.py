# -*- coding: utf-8 -*-

from dotenv import set_key, unset_key, get_key,dotenv_values
import os
import traceback
from typing import Any, Optional, Union, Type
from .format_config import GetFilePath

class EnvVariableOperate:

    def __init__(self,logger,folder_name='configFiles'):
        self.folder_name = folder_name
        self.logger = logger

    def get_project_env_dict(self,envFile: str ='envVariable.env') -> dict:
        '''
            将环境变量读取到一个字典中
            : 读取 .env 环境变量文件 ;
            params:
                envFile: 支持 config 文件下的其他 .env 文件读取，默认读取 envVariable.env ;
            return: 返回 .env 文件全部信息 dict ;
        '''
        try:
            env_path = GetFilePath.get_folder_file_path(self.folder_name,envFile)
            env_dit = dotenv_values(env_path)
            self.logger.error(f"获取环境变量字典 {env_dit}")
            # print(f"env_dic: {env_dit}")
            return env_dit

            # # 1. 基础用法 - 指定文件路径查找.env文件
            # load_dotenv(dotenv_path=env_path)
            # # 读取环境变量
            # db_host = os.getenv('project_env', 'prod')  # 带默认值
            # print(db_host)

        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"获取环境变量字典 error info : {e}")
            # print(f"获取环境变量 error : {e}")


    def writer_update_env_file(self,key:str,value: Any = None,envFile: str ='envVariable.env') :
        '''
            : 新增 or 修改 .env 环境变量文件指定 key:value  ;
            params:
                envFile: 支持 config 文件下的其他 .env 文件读取，默认读取 envVariable.env ;
        '''
        try:
            env_path = GetFilePath.get_folder_file_path(self.folder_name, envFile)
            set_key(env_path, key, value)
            self.logger.info(f".env file writer success! {key}：{value}")
            # print(f".env file writer success!!!")
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"新增&编辑环境变量 error info : {e}")

    # writer_update_env_file(key='test_key',value='test_value')



    def get_env_simple_keyValue(self,key:str,envFile: str ='envVariable.env') :
        '''
            : 查询 .env 环境变量文件指定 key:value  ;
            params:
                key: 要查询的目标 key str ;
                envFile: 支持 config 文件下的其他 .env 文件读取，默认读取 envVariable.env ;
            return: 返回 key对应的 value信息，返回任何数据类型, 不存在返回 None ;
        '''
        try:
            env_path = GetFilePath.get_folder_file_path(self.folder_name, envFile)
            config = dotenv_values(env_path)
            if key in config:
                value = get_key(env_path, key)
                self.logger.info(f"查询环境变量成功 {key}: {value}")
                return value
            else:
                return None
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"查询环境变量 error info : {e}")

    # env_vl =get_env_simple_keyValue('project_env')
    # print(f"read .env file key : {env_vl}")



    def delete_env_simple_keyValue(self,key : str, envFile : str ='envVariable.env') :
        '''
            : 删除 .env 环境变量文件指定 key:value  ;
            params:
                key: 要删除的目标 key str ;
                envFile: 支持 config 文件下的其他 .env 文件读取，默认读取 envVariable.env ;
        '''
        try:
            env_path = GetFilePath.get_folder_file_path(self.folder_name, envFile)
            unset_key(env_path, key)
            self.logger.info(f"删除环境变量成功 {key}")
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"删除环境变量 error info : {e}")

    # delete_env_simple_keyValue('API_KEY')



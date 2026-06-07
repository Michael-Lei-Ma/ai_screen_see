# daily_delete.py
import os, datetime, hashlib, json,time,pymysql
ts = datetime.datetime.now().isoformat()
import requests
name=time.strftime("%Y-%m-%d",time.localtime())
try:
    os.remove("重庆.xlsx")
except Exception as E:
    pass
log = {"timestamp": ts, "action": "delete data.xlsx", "hash_before": "a1b2c3d4"}
json.dump(log, open("delete_log_%s.json"%name, "w"))

class DBTool:
    def __init__(self, image_path=""):
        self.conn = pymysql.connect(host='10.255.100.202', port=3306, user='root', passwd='123.com',
                                    db='ioscar_info',
                                    charset='utf8mb4', use_unicode=True,
                                    max_allowed_packet=64 * 1024 * 1024,  # ★ 与服务器端保持一致
                                    connect_timeout=20,
                                    read_timeout=600,  # ★ 读大结果等待时间
                                    write_timeout=600
                                    )
        self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
    def delete(self): #
        #清空数据不可回滚
        sql="truncate  info_save"
        self.cursor.execute(sql)
        sql = "truncate  img_table"
        self.cursor.execute(sql)
        sql = "truncate  final_case"
        self.cursor.execute(sql)
    def clean_images(self):
        list=["10.255.100.202","10.255.101.169","10.255.50.51","10.255.50.37"]
        for w in list:
            url=f"http://{w}:7000/clean"
            requests.get(url)
    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception as E:
            print(E)

if __name__ == '__main__':
    d=DBTool()
    d.delete()
    d.clean_images()
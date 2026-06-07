
import pymysql
import re
import requests
import random
class DBTools:
    _RE_16_DIGITS = re.compile(r'^\d{16}$')

    def get_connect(self):
        return pymysql.connect(host='10.255.100.202', port=3306, user='root', passwd='123.com',
                                    db='ioscar_info',
                                    charset='utf8mb4', use_unicode=True)
    def __init__(self):
        self.conn = pymysql.connect(host='10.255.100.202', port=3306, user='root', passwd='123.com',
                                    db='ioscar_info',
                                    charset='utf8mb4', use_unicode=True,
                                    max_allowed_packet=64 * 1024 * 1024,  # ★ 与服务器端保持一致
                                    connect_timeout=20,
                                    read_timeout=600,  # ★ 读大结果等待时间
                                    write_timeout=600
                                    )
        self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
        """
            INSERT INTO info_save (`id`,`info`)values("1","234")    
         """
    def get_not_ok(self):
        sql=("select * from img_table it where check_ok is null and card_id like '%DS%' and "
             "insert_date >'2025-12-16 04:08:00'")
        self.cursor.execute(sql)
        results=self.cursor.fetchall()
        print("总数:%s"%len(results))
        choisesA=["7000","8000"]
        choisesB = ["7000", "9000"]
        for index,result in enumerate(results):
            print(result)
            ip=result.get("ip")
            fromip=result.get("from_ip","")
            if not fromip:
                fromip="10.200.16.120"
            imgPath=result.get("image_path")
            if ip=="10.255.100.202":
                chip = random.choice(choisesB)
                response=requests.post(f"http://{ip}:{chip}/retryImage",
                              params={"imagePath": imgPath,"ip":fromip})
                print(response.content)
            else:
                chip=random.choice(choisesA)
                try:
                    response = requests.post(f"http://{ip}:{chip}/retryImage",
                                         params={"imagePath": imgPath,"ip":fromip})
                    print(response.content)
                except Exception as e:
                    print(e)
    def __del__(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception as e:
            print(e)
    def demo_send(self):
        requests.post("http://127.0.0.1:8000/retryImage",
                      params={"imagePath":"images/2025120410484160889313.png",
                              "ip":""})
    def remove_not_null(self,imagePath):
        sql="delete from img_table where image_path=%s and check_ok is null"
        self.cursor.execute(sql,(imagePath,))
        self.conn.commit()

if __name__ == '__main__':
    db=DBTools()
    db.get_not_ok()
    # db.demo_send()

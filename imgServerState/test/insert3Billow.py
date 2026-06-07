from datetime import datetime

import pymysql,re,socket


def getlocalip():
    """
        获取本地 IP
    :return:
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
if __name__ == '__main__':
    print(getlocalip())
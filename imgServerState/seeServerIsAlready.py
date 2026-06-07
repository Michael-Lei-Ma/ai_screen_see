import re
import requests,time

def timefun(func):
    def wrapper(*args,**kwargs):
        start=time.time()
        result=func(*args,**kwargs)
        end=time.time()
        print("耗时:%s秒"%(end-start))
        return result
    return wrapper
@timefun
def read_files():
    with open("files/loadbalance.conf","r",encoding="utf-8")as f:
        for line in f:
            if line.strip().startswith("server") and ":" in line:
                data=[m for m in line.split(" ") if m]
                ip=data[1].strip()
                print(ip)
                if ip.startswith("127.0.0.1"):
                    ip="10.255.100.202:7000"
                data=requests.get(f"http://{ip}/ok")
                print(data)

if __name__ == '__main__':
    read_files()
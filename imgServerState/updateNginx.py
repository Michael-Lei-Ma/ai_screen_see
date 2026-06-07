
username="root"
password="cbf123456."
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动接受未知 host key
ssh.connect(
hostname='10.255.100.202',
port=22,
username='root',
password=password,
timeout=10
)
sftp=ssh.open_sftp()
sftp.put("files/loadbalance.conf","/etc/nginx/conf.d/loadbalance.conf")
sftp.close()
ssh.exec_command('cat /etc/nginx/conf.d/loadbalance.conf')
stdin, stdout, stderr=ssh.exec_command('nginx -t')
result=stdout.read().decode()
print(result)
ssh.exec_command('cat /etc/nginx/conf.d/loadbalance.conf')
print(stdout.read().decode(), stderr.read().decode())
if "successful" in result:
    ssh.exec_command('nginx -s reload')
ssh.close()
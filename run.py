import os
import paramiko
import requests
import json
from datetime import datetime, timezone, timedelta

def ssh_multiple_connections(hosts_info):
    users = []
    hostnames = []
    script_outputs = []
    for host_info in hosts_info:
        hostname = host_info['hostname']
        username = host_info['username']
        password = host_info['password']
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=hostname, port=22, username=username, password=password)
            
            # 上传 sing.sh 脚本
            sftp = ssh.open_sftp()
            local_path = 's1.sh'
            remote_path = f'/home/{username}/s1.sh'
            sftp.put(local_path, remote_path)
            sftp.chmod(remote_path, 0o755)
            sftp.close()
            
            # 切换到用户主目录并执行 sing.sh 脚本
            stdin, stdout, stderr = ssh.exec_command(f'cd ~ && ./s1.sh')
            script_output = stdout.read().decode().strip()
            script_error = stderr.read().decode().strip()
            if script_error:
                script_outputs.append(f"{hostname} 上的 sing.sh 执行错误: {script_error}")
            else:
                script_outputs.append(f"{hostname} 上的 sing.sh 输出: {script_output}")
            ssh.close()
        except Exception as e:
            print(f"用户：{username}，连接 {hostname} 时出错: {str(e)}")
            script_outputs.append(f"{hostname} 上的 sing.sh 执行失败: {str(e)}")
    return users, hostnames, script_outputs

def get_env_variable(var_name, default_value=None):
    value = os.getenv(var_name)
    if value is None:
        if default_value is not None:
            return default_value
        else:
            raise EnvironmentError(f"环境变量 {var_name} 未设置")
    return value

ssh_info_str = get_env_variable('SSH_INFO', '[]')
hosts_info = json.loads(ssh_info_str)

user_list, hostname_list, script_outputs = ssh_multiple_connections(hosts_info)
user_num = len(user_list)
content = "SSH服务器登录信息：\n"
for user, hostname in zip(user_list, hostname_list):
    content += f"用户名：{user}，服务器：{hostname}\n"
beijing_timezone = timezone(timedelta(hours=8))
time = datetime.now(beijing_timezone).strftime('%Y-%m-%d %H:%M:%S')
menu = requests.get('https://api.zzzwb.com/v1?get=tg').json()
loginip = requests.get('https://api.ipify.org?format=json').json()['ip']
content += f"本次登录用户共： {user_num} 个\n登录时间：{time}\n登录IP：{loginip}\n\n"

# 添加 sing.sh 脚本的执行结果
content += "sing.sh 脚本执行结果：\n"
for output in script_outputs:
    content += f"{output}\n"

def telegram_push(message, menu):
    url = f"https://api.telegram.org/bot{get_env_variable('TELEGRAM_BOT_TOKEN')}/sendMessage"
    payload = {
        'chat_id': get_env_variable('TELEGRAM_CHAT_ID'),
        'text': message,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps({
            "inline_keyboard": menu,
            "one_time_keyboard": True
         })
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"发送消息到Telegram失败: {response.text}")

telegram_push(content, menu)

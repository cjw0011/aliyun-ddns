import subprocess
import requests
import os
import json
import pickle
import logging
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
import platform
import traceback  # 用于捕获详细的错误信息

# 设置日志配置
logging.basicConfig(filename="dns_update.log", level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s", 
                    filemode="a")  # 使用 "a" 模式追加日志

CONFIG_FILE = "dns_config.pkl"

def log_and_print(message, level="info"):
    print(message)
    if level == "info":
        logging.info(message)
    elif level == "error":
        logging.error(message)

def clear_dns_cache():
    os_name = platform.system()
    try:
        if os_name == "Windows":
            subprocess.run(["ipconfig", "/flushdns"], check=True)
        elif os_name == "Darwin":  # macOS
            subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], check=True)
        elif os_name == "Linux":
            subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=True)
        log_and_print("DNS缓存已清理。")
    except subprocess.CalledProcessError:
        log_and_print("清理DNS缓存时出错。", level="error")

def get_user_input(prompt, default=None):
    user_input = input(f"{prompt} (默认: {default}): ") or default
    return user_input

def save_config(config):
    with open(CONFIG_FILE, 'wb') as f:
        pickle.dump(config, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def clear_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        log_and_print("配置已清除。")
    else:
        log_and_print("没有找到配置文件。")

def main():
    try:
        # 清理DNS缓存
        clear_dns_cache()

        # 检查是否存在已保存的配置
        saved_config = load_config()
        using_saved_config = False
        if saved_config:
            dns_server, domain, dns_type, domain_name = saved_config
            using_saved_config = True
            log_and_print("使用保存的配置：")
        else:
            dns_server = get_user_input("请输入自定义DNS服务器", "8.8.8.8")
            domain = get_user_input("请输入子域名", "abc")
            dns_type = get_user_input("请输入DNS记录类型", "A")
            domain_name = get_user_input("请输入域名（domainname）", "mylabcdd.top")

        log_and_print(f"DNS服务器: {dns_server}, 子域名: {domain}, 记录类型: {dns_type}, 域名: {domain_name}")

        # 使用 nslookup 解析域名
        full_domain = f"{domain}.{domain_name}"
        resolved_ip = None
        try:
            result = subprocess.run(["nslookup", full_domain, dns_server], capture_output=True, text=True, check=True)
            output = result.stdout
            for line in output.splitlines():
                if "Address" in line and not line.startswith("Non-authoritative"):
                    ip_candidate = line.split()[-1]
                    if ip_candidate != dns_server:
                        resolved_ip = ip_candidate
                        break
            log_and_print(f"解析的IP: {resolved_ip}")
        except subprocess.CalledProcessError:
            log_and_print("无法解析域名", level="error")

        # 检测出口公网地址
        response = requests.get("http://members.3322.org/dyndns/getip")
        public_ip = response.text.strip()
        log_and_print(f"检测到的公网地址: {public_ip}")

        # 比对IP
        if resolved_ip and resolved_ip == public_ip:
            log_and_print("解析的IP和检测到的公网地址一致，无需更新DNS记录。")
        else:
            log_and_print(f"解析的IP和检测到的公网地址不一致，准备更新 {full_domain} 的DNS记录。")

            # 获取RecordID
            credentials = AccessKeyCredential(os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'], os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'])
            client = AcsClient(region_id='cn-hangzhou', credential=credentials)

            request = DescribeDomainRecordsRequest()
            request.set_accept_format('json')
            request.set_DomainName(domain_name)
            request.set_RRKeyWord(domain)  # 使用子域名部分作为RR

            response = client.do_action_with_exception(request)
            record_id = None

            if response:
                records = json.loads(response)
                if records['DomainRecords']['Record']:
                    record_id = records['DomainRecords']['Record'][0]['RecordId']  # 根据实际返回格式调整

            if record_id:
                update_request = UpdateDomainRecordRequest()
                update_request.set_accept_format('json')
                update_request.set_RecordId(record_id)
                update_request.set_RR(domain)
                update_request.set_Type(dns_type)
                update_request.set_Value(public_ip)

                try:
                    update_response = client.do_action_with_exception(update_request)
                    log_and_print("DNS记录更新成功", str(update_response, encoding='utf-8'))
                except ServerException as e:
                    if e.error_code == "DomainRecordDuplicate":
                        log_and_print("错误：DNS记录已存在，无法重复更新。", level="error")
                    else:
                        log_and_print(f"DNS记录更新时发生错误：{e.error_code} - {e.message}", level="error")
            else:
                log_and_print("未找到RecordID，无法更新DNS记录", level="error")

        # 如果没有使用保存的配置，询问是否保存当前配置
        if not using_saved_config and input("是否保存当前配置？(y/n)").lower() == 'y':
            save_config((dns_server, domain, dns_type, domain_name))
            log_and_print("配置已保存。")
    except Exception as e:
        log_and_print("程序运行时发生异常：", level="error")
        log_and_print(traceback.format_exc(), level="error")

if __name__ == "__main__":
    if len(os.sys.argv) > 1 and os.sys.argv[1] == 'clear':
        clear_config()
    else:
        main()

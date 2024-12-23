"""
校验ARP demo，用来对指定文件夹内的infoScanner.py扫描结果进行ARP校验以发现隐藏的主机
"""
import ipaddress
import json
from checkResult import find_json_files  # 检查结果脚本的获取json文件列表函数
from colorama import init, Fore, Style
import os


res = {}  # 结果
'''
IP
    uuid
    business_name
    be_mentioned: [(IP, business_name, uuid)]
'''
skip_list = ['127.0.0.1', '255.255.255.255', '224.0.0.0/4']  # 遇到这些IP则跳过
skipped = []  # 已跳过的IP


def need_skip(ip: str):
    global skipped
    ret = False
    if ip.endswith('.255'):
        ret = True  # 保留的广播地址
    target_ip = ipaddress.ip_address(ip)
    for network in skip_list:
        # 尝试将每个元素转换为网络对象；如果失败，则认为它是单个IP
        try:
            net = ipaddress.ip_network(network, strict=False)
            if target_ip in net:
                ret = True
        except ValueError:
            # 如果不是有效的网络表达式，则当作单个IP处理
            if ipaddress.ip_address(network) == target_ip:
                ret = True
    if ret:
        if ip not in skipped:
            skipped.append(ip)
            print(Fore.GREEN + f'已忽略IP:{ip}' + Style.RESET_ALL)
        return True
    return False


if __name__ == '__main__':
    path = input('请拖入文件夹路径')
    while not os.path.isdir(path):
        path = input(f'拖入内容{path}非文件夹，请拖入文件夹路径')
    paths = find_json_files(path)
    for path in paths:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            business_name = data['business_name']
            uuid = data['uuid']
            ips = list(set(data['ips']))
            arp = data['arp']
            for ip in ips:  # 填充uuid和business_name
                if need_skip(ip):  # 在过滤名单，就不添加了
                    continue
                if ip not in res.keys():  # 没有这个IP就将其加入记录
                    res[ip] = {'uuid': [], 'business_name': [], 'be_mentioned': []}
                if uuid in res[ip]['uuid']:  # 测当前的uuid值是否已经被包含，已被包含则说明有重复文件，需提醒
                    file_name = os.path.basename(path)
                    print(Fore.LIGHTYELLOW_EX + f'存在重复uuid{uuid}，文件{file_name}' + Style.RESET_ALL)
                else:
                    res[ip]['uuid'].append(uuid)
                    res[ip]['business_name'].append(business_name)
            for source in arp.keys():  # 填充be_mentioned
                targets = arp[source]
                for target in targets:
                    if need_skip(target):  # 在过滤名单，就不添加了
                        continue
                    if target not in res.keys():  # 没有这个IP就将其加入记录
                        res[target] = {'uuid': [], 'business_name': [], 'be_mentioned': []}
                    res[target]['be_mentioned'].append((source, business_name, uuid))
    # 输出结果
    for ip in res.keys():
        if len(res[ip]['uuid']) == 0:  # 说明存在未被认领的IP
            print(Fore.RED + ip, '\t被以下机器提及：')
            for info in res[ip]['be_mentioned']:
                print('\t\t', info)
            print(Style.RESET_ALL)
        else:
            print(ip, '\t被以下机器提及：')
            for info in res[ip]['be_mentioned']:
                print('\t\t', info)
            print()

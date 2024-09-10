# -*- coding: utf-8 -*-
"""
脚本作用：
竭尽全力地提供被扫描主机的软硬件信息，可以后期不用，不能前期没有

此文件为信息收集脚本，编写原则（此原则建立在Linux直接运行本py文件，Windows运行pyinstaller打包本py文件后的exe文件上）：
1、单文件原则--为方便上传下载，脚本需以单个文件形式存在
2、结构化原则--尽可能提供结构化结果，方便后期处理；实在难以进行结构化的部分则应直接提供原始数据
3、开箱即用原则--尽量使用python自带库完成功能实现

不满足上述原则的内容：
暂无
"""

import platform
from datetime import datetime
import hashlib
import json
import socket
import subprocess
import importlib
import sys
import codecs  # python2 open用
from collections import OrderedDict  # 为了兼容python2，python3.7以上自然有序
import os

PLATFORM = platform.system()  # 运行环境
output = OrderedDict()
output['version'] = 'v0.0.1'  # 软件版本
output['start_time'] = ''  # 扫描开始时间，输入系统名称后记录
output['end_time'] = ''  # 扫描结束时间
output['used_time'] = 0  # 扫描用时
output['err_msg'] = []  # 扫描中的出错情况
output['business_name'] = ''  # 系统名称
output['host_name'] = ''  # 主机名称
output['host_name_other'] = []  # 主机别名
output['ips'] = []  # 所有ip
output['os_type'] = ''  # 操作系统类型 Windows/Linux
output['os_uname'] = []  # uname信息
output['os_linux_info'] = ''  # platform信息
output['arp'] = {}  # arp表'ip_local':{'ip_dst':{'mac':'', type:''}}
output['apps'] = {}  # 已安装应用列表'name':{'version':'', 'path':''}
PY3 = sys.version_info[0] >= 3


def log_error(msg):
    global output
    output['err_msg'].append(msg)
    print(msg)


def run_command(command):
    try:
        # 执行命令并捕获输出
        result = subprocess.check_output(command, shell=True, universal_newlines=True)
        return result.strip()
    except subprocess.CalledProcessError as e:
        if 'which' in str(e) and 'returned non-zero exit status 1' in str(e):  # 忽略该报错
            pass
        else:
            log_error("run_command error:{}".format(e))
        return ''


def Win():
    global output
    print('获取host_name、host_name_other、ips')
    output['host_name'], output['host_name_other'], output['ips'] = socket.gethostbyname_ex(socket.gethostname())

    print('获取arp信息')
    arp_raw = run_command('arp -a')
    try:
        arp_info = {}
        now_ip = ''
        arp = arp_raw.split('\n')
        for line in arp:
            info = line.split()
            if len(info) == 4:
                if 'Inter' not in info[0]:  # 首行
                    now_ip = info[1]
                    arp_info[now_ip] = {}
            elif len(info) == 3:  # 信息行
                arp_info[now_ip][info[0]] = {
                    'mac': info[1],
                    'type': info[2]
                }
    except Exception as e:
        print(e)
        output['arp'] = arp_raw
    else:
        output['arp'] = arp_info
    # 补充ips
    for ip in output['arp'].keys():
        if ip not in output['ips']:
            output['ips'].append(ip)

    print('获取os信息')
    output['os_uname'] = list(platform.uname())

    print('获取apps')
    winreg = importlib.import_module('winreg')
    installed_programs = {}
    for registration_path in [r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                              r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
                              r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall']:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, registration_path)
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
                try:
                    program_name = str(winreg.QueryValueEx(subkey, "DisplayName")[0])
                except:
                    program_name = str(subkey_name)
                try:
                    program_version = str(winreg.QueryValueEx(subkey, "DisplayVersion")[0])
                except:
                    program_version = ''
                try:
                    program_location = str(winreg.QueryValueEx(subkey, "InstallLocation")[0])
                except:
                    program_location = ''
                if program_version == '' and program_location == '' and '{' in program_name:  # 疑似没什么用的条目，即只有一串编号
                    continue
                if program_name in installed_programs.keys():
                    continue
                installed_programs[program_name] = {
                    'version': program_version,
                    'path': program_location
                }
                winreg.CloseKey(subkey)
            except Exception as e:
                print(e)
    output['apps'] = installed_programs


def Linux():
    print('获取host_name、host_name_other、ips')
    output['host_name'], output['host_name_other'], output['ips'] = socket.gethostbyname_ex(socket.gethostname())

    print('获取arp信息')
    arp_raw = run_command('arp -n')
    arp_info = {}
    eth_raw = run_command('ifconfig')
    eth = {}
    for part in eth_raw.split('\n\n'):
        lines = part.split('\n')
        eth_name = lines[0].split(':')[0]
        eth_ip = lines[1].split()[1]
        eth[eth_name] = eth_ip
    arp = arp_raw.split('\n')[1:]
    for line in arp:
        infos = line.split()
        if len(infos) == 5:  # 正常情况
            now_ip = eth[infos[4]]
            if now_ip not in arp_info.keys():
                arp_info[now_ip] = {}
            arp_info[now_ip][infos[0]] = {
                'mac': infos[2],
                'type': infos[3]
            }
        elif len(infos) == 3:  # 硬件不存在
            now_ip = eth[infos[2]]
            if now_ip not in arp_info.keys():
                arp_info[now_ip] = {}
            arp_info[now_ip][infos[0]] = {
                'mac': '',
                'type': ''
            }
        else:
            log_error('出错了，请联系管理员。信息：' + str(infos))
    output['arp'] = arp_info
    # 补充ips
    for ip in output['arp'].keys():
        if ip not in output['ips']:
            output['ips'].append(ip)

    print('获取os信息')
    output['os_uname'] = list(platform.uname())
    output['os_linux_info'] = platform.platform()

    print('获取apps')
    installed_programs = {}
    is_app_get = False  # dpkg或rpm存在则为True
    if subprocess.call("which dpkg", shell=True) == 0:
        is_app_get = True
        dpkg_info = run_command('dpkg -l').split('\n')
        '''
        dpkg_info期望的开头内容：
        dpkg_info[0] 第一行  期望状态=未知(u)/安装(i)/删除(r)/清除(p)/保持(h)
        dpkg_info[1] 第二行  | 状态=未安装(n)/已安装(i)/仅存配置(c)/仅解压缩(U)/配置失败(F)/不完全安装(H)/触发器等待(W)/触发器未决(T)
        dpkg_info[2] 第三行  |/ 错误?=(无)/须重装(R) (状态，错误：大写=故障)
        dpkg_info[3] 第四行  ||/ 名称                             版本                             体系结构       描述
        dpkg_info[4] 第五行  +++-===============================-===============================-============-========
        '''
        if '======' not in dpkg_info[4]:  # 简单检测是否符合上述格式
            log_error('dpkg -l输出结果格式与预期不符（第五行不是分隔符），请检查')
        info = dpkg_info[5:]
        for line in info:
            index = line.split()
            path = run_command('which {}'.format(index[1]))
            installed_programs[index[1]] = {
                'version': index[2],
                'path': path,
                'state': index[0]
            }
    if subprocess.call("which rpm", shell=True) == 0:
        is_app_get = True
        rpm_info = run_command('rpm -qa').split('\n')
        '''
        linux-secure-enhancement-2.3-7.oe2203.linux.arch
        '''
        for line in rpm_info:
            index = line.split('-')
            i = 0  # 查找谁第一个出现的“.”
            for i in range(len(index)):
                if '.' in index[i]:
                    break
            name = '-'.join(index[:i])
            version = '-'.join(index[i:])
            path = run_command('which {}'.format(name))
            if name not in installed_programs.keys():
                installed_programs[name] = {
                    'version': version,
                    'path': path
                }
    if not is_app_get:
        log_error('未获取到dpkg或rpm信息')
    output['apps'] = installed_programs


if __name__ == '__main__':
    print('当前操作系统为{}\n当前软件版本为{}'.format(PLATFORM, output['version']))
    if PY3:
        output['business_name'] = input('请输入系统名称：')
    else:
        output['business_name'] = raw_input('请输入系统名称：')
    start_time = datetime.now()
    output['start_time'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
    output['os_type'] = PLATFORM
    if PLATFORM == 'Windows':
        Win()
    elif PLATFORM == 'Linux':
        Linux()
    end_time = datetime.now()
    output['end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
    output['used_time'] = (end_time - start_time).total_seconds()
    md5_short = hashlib.md5(str(output).encode()).hexdigest()
    output['md5'] = md5_short
    if len(output['ips']) == 0:
        output['ips'] = ['']  # 避免主机没有ip
    temp_file_name = 'temp-' + start_time.strftime('%Y%m%d_%H%M%S') + '.json'
    if PY3:
        with open(temp_file_name, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=4, ensure_ascii=False)
    else:
        with codecs.open(temp_file_name, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=4, ensure_ascii=False)
    with open(temp_file_name, 'rb') as f:
        data = f.read()
        md5_short = hashlib.md5(data).hexdigest()[::4]
    file_name = (output['business_name'] + '-' +
                 output['ips'][0] + '-' +
                 start_time.strftime('%Y%m%d_%H%M%S') + '-' +
                 md5_short + '.json')
    os.rename(temp_file_name, file_name)
    print('\n生成文件{}'.format(file_name))
    if PLATFORM == 'Windows':
        input('已完成，请按回车退出')
    elif PLATFORM == 'Linux':
        print('已完成')

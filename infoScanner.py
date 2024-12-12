# -*- coding: utf-8 -*-
"""
脚本作用：
竭尽全力地提供被扫描主机的软硬件信息，可以后期不用，不能前期没有

此文件为信息收集脚本，编写原则（此原则建立在Linux直接运行本py文件，Windows直接运行py文件或运行pyinstaller打包本py文件后的exe文件上）：
1、单文件原则--为方便上传下载，脚本需以单个文件形式存在
2、结构化原则--尽可能提供结构化结果，方便后期处理；实在难以进行结构化的部分则应直接提供原始数据
3、开箱即用原则--尽量使用python自带库完成功能实现

脚本内不满足上述原则的内容：
暂无
"""

import platform
from datetime import datetime, timedelta, timezone
import hashlib
import json
import socket
import subprocess
import importlib
import sys
import os
import uuid


PLATFORM = platform.system()  # 运行环境
output = {
    'script_version': 'v0.0.2',  # 软件版本
    'python_version': sys.version,  # python版本
    'start_time': '',  # 扫描开始时间，输入系统名称后记录
    'end_time': '',  # 扫描结束时间
    'used_time': 0,  # 扫描用时
    'business_name': '',  # 系统名称
    'uuid': uuid.getnode(),  # 主机uuid
    'host_name': '',  # 主机名称
    # 'host_name_other': [],  # 主机别名
    'ips': [],  # 所有ip
    'os_type': '',  # 操作系统类型 Windows/Linux
    'os_uname': [],  # uname信息
    'os_linux_info': '',  # platform信息
    'arp': {},  # arp表'ip_local':{'ip_dst':{'mac':'', type:''}}
    'apps': {},  # 已安装应用列表'name':{'version':'', 'path':''}
    'log': [],  # 扫描信息记录
    'err_msg': []  # 扫描中的出错情况
}
PY3 = sys.version_info[0] >= 3


def log_error(msg):  # 将传递的msg输出到命令行和json文件的err_msg字段
    global output
    output['err_msg'].append(msg)
    print(msg)


def run_command(command):  # python3.5
    try:
        # 执行命令并捕获输出
        result = subprocess.run(command, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        # universal_newlines=True是3.6及之前的写法，3.6之后是text=true，但3.6之后前者仍能用
    except subprocess.CalledProcessError as e:
        log_error("subprocess.CalledProcessError:{}".format(e))
        return ''
    else:
        if result.stderr != '':
            if len(command) >= 5 and command[0:5] == 'which':
                pass
            else:
                log_error('stderr,{}:{}'.format(command, result.stderr))
        return result.stdout


def Win():
    global output
    print('获取host_name、ips')
    output['host_name'] = socket.gethostname()
    info = socket.getaddrinfo(output['host_name'], None, family=socket.AF_INET)
    output['ips'] = [item[4][0] for item in info]
    output['log'].append(f'ips socket方法获取{len(info)}条')

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
    old_ips_num = len(output['ips'])
    for ip in output['arp'].keys():
        if ip not in output['ips']:
            output['ips'].append(ip)
    output['log'].append('ips arp补充{}条'.format(len(output['ips'])-old_ips_num))

    print('获取os信息')
    output['os_uname'] = list(platform.uname())

    print('获取apps')
    winreg = importlib.import_module('winreg')
    installed_programs = {}
    last_log_num = 0  # 用来记录上一次写入log时installed_programs的数量
    # 检查HKEY_LOCAL_MACHINE
    for registration_path in [r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                              r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall']:
        with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as reg:
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
            output['log'].append('HKEY_LOCAL_MACHINE\\' + registration_path +
                                 f'：读取{winreg.QueryInfoKey(key)[0]}条信息，{len(installed_programs)-last_log_num}条有效')
            last_log_num = len(installed_programs)
    # 检查HKEY_USERS（会包含HKEY_CURRENT_USERS）
    with winreg.ConnectRegistry(None, winreg.HKEY_USERS) as reg:
        registration_path = []
        with winreg.OpenKey(reg, '') as sub_key:
            index = 0
            while True:
                try:
                    
                    sub_key_name = winreg.EnumKey(sub_key, index)
                    registration_path.append(str(sub_key_name) +
                                             r'\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall')
                    registration_path.append(str(sub_key_name) +
                                             r'\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall')
                    index += 1
                except OSError:
                    break
        for reg_path in registration_path:
            try:
                key = winreg.OpenKey(reg, reg_path)
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
            except FileNotFoundError:
                # print('没有{}'.format(reg_path))  # 调试用
                pass  # 没有该路径，忽略
            output['log'].append(reg_path +
                                 f'：读取{winreg.QueryInfoKey(key)[0]}条信息，{len(installed_programs) - last_log_num}条有效')
            last_log_num = len(installed_programs)
    output['apps'] = installed_programs


def Linux():
    print('获取host_name、ips')
    output['host_name'] = socket.gethostname()
    info = socket.getaddrinfo(output['host_name'], None, family=socket.AF_INET)
    output['ips'] = [item[4][0] for item in info]
    output['log'].append(f'ips socket方法获取{len(info)}条')

    print('获取arp信息')
    arp_raw = run_command('arp -n').strip()
    arp_info = {}
    eth_raw = run_command('ifconfig').strip()
    eth = {}
    old_ips_num = len(output['ips'])
    for part in eth_raw.split('\n\n'):
        lines = part.split('\n')
        try:  # 如果有网卡没启动就会出错
            eth_name = lines[0].split(':')[0]
            eth_ip = lines[1].split()[1]
            eth[eth_name] = eth_ip
            # 补充ips
            if eth_ip not in output['ips']:
                output['ips'].append(eth_ip)
        except IndexError as e:
            log_error(str(lines) + str(e))
            continue
    output['log'].append('ips arp补充{}条'.format(len(output['ips'])-old_ips_num))
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

    print('获取os信息')
    output['os_uname'] = list(platform.uname())
    output['os_linux_info'] = platform.platform()

    print('获取apps')
    installed_programs = {}
    is_app_get = False  # dpkg或rpm存在则为True
    last_log_num = 0  # 用来记录上一次写入log时installed_programs的数量
    if subprocess.call("which dpkg", shell=True) == 0:
        is_app_get = True
        dpkg_info = run_command('dpkg -l').strip().split('\n')
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
                'path': path.strip(),
                'state': index[0]
            }
        output['log'].append('dpkg' +
                             f'：读取{len(info)}条信息，{len(installed_programs) - last_log_num}条有效')
        last_log_num = len(installed_programs)
    if subprocess.call("which rpm", shell=True) == 0:
        is_app_get = True
        rpm_info = run_command('rpm -qa').strip().split('\n')
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
        output['log'].append('dpkg' +
                             f'：读取{len(info)}条信息，{len(installed_programs) - last_log_num}条有效')
        last_log_num = len(installed_programs)
    if not is_app_get:
        log_error('未获取到dpkg或rpm信息')
    output['apps'] = installed_programs


if __name__ == '__main__':
    print('当前操作系统为{}\n当前软件版本为{}\npython环境为{}'.
          format(PLATFORM, output['script_version'], output['python_version']))
    if PY3:
        output['business_name'] = input('请输入系统名称：')
    else:
        print('当前使用的python环境为python2，请使用python3运行本软件！！')
        exit(1)
    start_time = datetime.now(timezone.utc) + timedelta(hours=8)
    output['start_time'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
    output['os_type'] = PLATFORM
    if PLATFORM == 'Windows':
        Win()
    elif PLATFORM == 'Linux':
        Linux()
    end_time = datetime.now(timezone.utc) + timedelta(hours=8)
    output['end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
    output['used_time'] = (end_time - start_time).total_seconds()
    if len(output['ips']) == 0:
        output['ips'] = ['']  # 避免主机没有ip
    temp_file_name = 'temp-' + start_time.strftime('%Y%m%d_%H%M%S') + '.json'
    with open(temp_file_name, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    with open(temp_file_name, 'rb') as f:
        data = f.read()
        md5_short = hashlib.md5(data).hexdigest()[::4]
    uuid_short = str(output['uuid'])[0:6]
    nontrivial_ip = output['ips'][0]
    for i in output['ips']:
        if i != '127.0.0.1':
            nontrivial_ip = i
            break
    file_name = (output['business_name'] + '-' +
                 uuid_short + '-' +
                 nontrivial_ip + '-' +
                 start_time.strftime('%Y%m%d_%H%M%S') + '-' +
                 md5_short + '.json')
    os.rename(temp_file_name, file_name)
    print('\n生成文件{}'.format(file_name))
    if PLATFORM == 'Windows':
        input('已完成，请按回车退出')
    elif PLATFORM == 'Linux':
        print('已完成')

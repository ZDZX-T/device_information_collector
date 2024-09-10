import hashlib
import json
import os
from colorama import init, Fore
from collections import OrderedDict

init()


def find_json_files(folder_path):
    json_files = []
    if os.path.isdir(folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
    return json_files


if __name__ == '__main__':
    path = input('请拖入文件或文件夹路径')
    if os.path.isdir(path):
        paths = find_json_files(path)
    else:
        paths = [path]
    for path in paths:
        with open(path, 'rb') as f:
            data = f.read()
            md5_short = hashlib.md5(data).hexdigest()[::4]
            challenge = path[-13:-5]
            if md5_short == challenge:
                print(Fore.GREEN + str(path))
            else:
                print(Fore.RED + str(path))
            print(Fore.RESET)

import hashlib
import json
import os
from colorama import init, Fore

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
        with open(path, 'r', encoding='utf-8') as f:
            info = json.load(f)
            md5 = info['md5']
            del info['md5']
            challenge = hashlib.md5(str(info).encode()).hexdigest()
            if md5 == challenge:
                print(Fore.GREEN + str(path))
            else:
                print(Fore.RED + str(path))
            print(Fore.RESET)

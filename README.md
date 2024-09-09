# infoScanner.py介绍
## 作用
收集目标主机的各种软硬件信息
## 使用方法
### linux系
`python3 infoScanner.py`
### windows系
首先打包为.exe  
`pyinstaller -F infoScanner.py`  
然后再在目标主机运行exe文件
## 目前可收集内容
- [x] 主机名称
- [x] 主机别名
- [x] ip（来自arp信息以及socket信息）
- [x] 操作系统信息（uname）
- [x] arp信息
- [x] 已安装应用列表
- [ ] 已安装应用安装的插件列表
  
  
  
# checkResult.py介绍
## 作用
简单校验infoScanner收集到的信息是否被篡改，原理是对infoScanner结果进行md5，所以要伪造也很简单，并不能100%验出篡改
## 使用方法
可单个验证或批量验证infoScanner输出结果。  
单个验证时，运行程序后输入单个json文件的路径。  
批量验证时，将所有json文件放入一个文件夹内，运行程序后输入该文件夹路径。

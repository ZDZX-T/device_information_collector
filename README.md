# infoScanner.py介绍
## 作用
收集目标主机的各种软硬件信息
## 使用方法
### linux系
推荐python3运行  
`python3 infoScanner.py`  
~~如果没有python3的话，python2也做了适配  
`python2 infoScanner.py`~~
### windows系
首先打包为.exe  
`pyinstaller -F infoScanner.py`  
然后再在目标主机运行exe文件
## 目前可收集内容
- [x] 主机名称
- [x] uuid，主机识别码，可以用来做主键
- [x] python版本（用来调整后续脚本兼容性）
- [x] ip（来自arp信息以及socket信息）
- [x] 操作系统信息（使用uname）
- [x] arp信息
- [x] 已安装应用列表
- [x] 服务
- [ ] 已安装应用安装的插件列表
  
  
  
# checkResult.py介绍
## 作用
简单校验infoScanner收集到的信息是否被篡改，原理是对infoScanner结果进行md5，所以要伪造也很简单，并不能100%验出篡改
## 使用方法
可单个验证或批量验证infoScanner输出结果。  
单个验证时，运行程序后输入单个json文件的路径。  
批量验证时，将所有json文件放入一个文件夹内，运行程序后输入该文件夹路径。



# ARPCheck.py介绍
## 作用
通过收集的APR信息尝试发现是否有疑似未报备的IP
## 使用方法
将infoScanner.py的运行结果放入一个文件夹内，然后运行ARPCheck.py，将该文件夹拖入命令行中。
首先会以绿色字体打印检查过程中忽略掉的IP，包括本地环回、广播地址等，可更改代码的skip_list变量进行自定义。
然后会打印检查结果，如果以白色字体打印，说明该IP有对应的infoScanner输出文件；如果以红色字体打印，说明该IP无对应的infoScanner输出文件。
注意：即使输出结果为白色，也不代表台账中有该IP的记录，应单独核对扫描结果的IP是否在台账中；即使为红色，也不代表台账中无该IP的记录，有可能只是这台主机忘运行了。
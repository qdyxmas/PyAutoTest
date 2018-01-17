#coding=utf8
import os,sys
import time
import ConfigParser
def cur_file_dir():
     #获取脚本路径
     path = sys.path[0]
     #判断为脚本文件还是py2exe编译后的文件，如果是脚本文件，则返回的是脚本的目录，如果是py2exe编译后的文件，则返回的是编译后的文件路径
     if os.path.isdir(path):
         return path.decode('gbk')
     elif os.path.isfile(path):
         return os.path.dirname(path).decode('gbk')
#打印结果
def gettime():
    timestr=time.strftime(u"%Y-%m-%d_%H%M%S",time.localtime())
    return timestr
def gettime2():
    timestr=time.strftime(u"%Y-%m-%d %H:%M:%S",time.localtime())
    return timestr
def ParserCfg(filename):
    kargs={}
    cf = ConfigParser.ConfigParser()
    cf.read(filename.replace("\\","/"))
    for opt in cf.sections():
        if opt:
            kargs[opt]={}
    for opt in kargs.keys():
        for k,v in cf.items(opt):
            kargs[opt][k]=v
    return kargs
#定义主目录
MainDir=cur_file_dir()
#定义当前的日志目录
ConfigFile=os.path.join(MainDir,"config.ini")
# ReportDir=os.path.join(MainDir,"result/%s" %(gettime()))
ConfigDir=os.path.join(MainDir,"config")
TestDir=os.path.join(MainDir,"test")
G_MainDict=ParserCfg(ConfigFile)
# Result_Module = os.path.join(MainDir,u"IXIA仪器性能测试V1.7.xlsx").replace("\\","/")
Report_module = os.path.join(ConfigDir,u"Standard_Report.xls").replace("\\","/")
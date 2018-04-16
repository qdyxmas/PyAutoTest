#coding=utf-8
import os,sys
import copy
import codecs
import re
import xlrd
import shutil
import subprocess
import win32com.client
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from PyQt4 import QtCore,QtGui,QtXml
from configobj import ConfigObj
from Global import *
from Form_Main import Ui_MainWindow
from xml.dom.minidom import Document
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from lib import *
cf = ConfigParser.ConfigParser()

#定义运行脚本的线程
class RunThread(QtCore.QThread):
    #把打印的字符串发送给UI主线程
    signal_text= QtCore.pyqtSignal(str,str) # 信号
    log_text= QtCore.pyqtSignal(str,int,unicode,str) # 信号
    # log_text= QtCore.pyqtSignal(str,int,unicode,bool) # 信号
    # create_hyperlinks = QtCore.pyqtSignal(unicode,unicode) # Log!A12#DictLog!C33
    def __init__(self, parent=None):
        super(RunThread, self).__init__(parent)
        #获取主UI线程的obj
        self.parent = parent
        self.start_flag = 0
    def start_test(self):
        self.start()
    def stop_test(self):
        self.terminate()
        self.wait()
        # self.quit()
    def judge(self,args):
        if not args.strip():
           return None 
        cc=re.search(r'([^a-zA-Z0-9_])',args)
        #如果为xxx.bbb 形式则表示函数调用,如果ac=XXXX() 表示赋值
        if cc.group() == ".":
            return True
        else:
            return False
    def sorted_keys(self,*kargs):
        kargs=list(kargs)
        flag = 0
        if 'C' in kargs:
            flag = 1
            kargs.remove('C')
        m_keys = kargs
        m_keys = map(lambda x:int(x),m_keys)
        num_keys = sorted(m_keys)
        if flag:
            num_keys.append('C')
        return num_keys
    def run(self):
        if not self.parent.start_flag:
            product=str(self.parent.ui.product.currentText())
            subprod=str(self.parent.ui.son_product.currentText())
            
            importlst = self.parent.config['import']['type'].split(",")
            for i in importlst:
                importclass="from lib.%s." %(i)+product+" import "+subprod+" as %s_" %(i)+subprod
                print importclass
                exec importclass
            #初始化kc 与 kt函数对象
            classname=[]
            dut_init_args=str(self.parent.config['dut'])
            client_init_args=str(self.parent.config['client'])
            server_init_args=str(self.parent.config['server'])
            km_init_args=str(self.parent.config['km'])
            # print "kc_init_args=",kc_init_args
            # ktcl_init_args = {}
            # init_args 为从GUI上读取的变量字典集合
            # kc = eval(subprod)(**kc_init_args)
            # kt = KT(filedir=self.parent.reportdir)   #
            # ks = KS()   #需要填写波特率 也可以直接在初始化时强制写入
            # kt = TclClass(**ktcl_init_args)
            #循环tree结构得到需要测试的用例字典
            #先得到所有模块的的字典参数
            cx = Createxml(self.parent.testcasedir,"",product+"_"+subprod)
            treedict = cx.getModules()
            # modules = sorted(self.parent.need_testcases.keys())
            modules = self.parent.need_testcases.keys()
            print u"开始测试模块:",modules
            # print "treedict=",treedict
            #定义初始化三张sheet的操作起始行
            sum_row = 9
            dict_row = 7
            log_row = 0
            row=10
            ret=True
            retlst = []
            #module_dict 从第七行开始计算
            logdict_row = 7
            start_item_row = 0
            # sum_row = 9
            #从测试文件中得到测试用例点
            for module in modules:
                testspass = 0
                testsfail = 0
                testblock = 0
                items_dict = self.parent.need_testcases[module]
                print "items_dict=",items_dict
                if not self.parent.module_isnull(**items_dict):
                    #如果模块为空则跳过
                    continue
                #导入模块testcases字典
                # modulefile=
                # tcasemoduleimport = self.parent.readfile(file)
                #开始测试 模块脚本DHCPSer.DHCPSer-AP_W85AP 17:27:45
                self.log_text.emit("Module",row,u'开始测试 模块脚本'+module+" =>"+gettime2(),str(False))
                self.msleep(100)
                row=row+2
                # items_dict = self.parent.need_testcases[module]
                module_dict={}
                # print "treedict=",treedict
                module_dict = eval(treedict[module])
                items_len = len(module_dict)
                # print "module_dict.keys=",module_dict.keys()
                #先把字典的keys进行排序 然后循环keys
                # m_keys = module_dict.keys()
                # m_keys = map(lambda x:int(x),m_keys)
                num_keys = self.sorted_keys(*module_dict.keys())
                dict_row = logdict_row
                for i in num_keys:
                    print "i=",i
                    testDict = {}
                    if i == 'C':
                        testDict =  module_dict['C']
                    else:
                        if not module_dict.has_key(str(i)):
                            continue
                        testDict = module_dict[str(i)]
                    if i == 0:
                        items_dict[str(i)] = module_dict[str(i)]
                    elif i == 'C':
                        items_dict[str(i)] = module_dict['C']
                    print "items_dict=",items_dict
                    #如果测试项中的测试点为空则跳过
                    
                    #如果itemlist不全部为空则进行循环
                    if not items_dict.has_key(str(i)):
                        continue
                    if any(items_dict[str(i)]['testcases']):
                        item_lst = []
                        # print "type=",type(treedict[module])
                        # print "Itemname=",items_dict[i]['itemname']
                        # print "type(Itemname)=",type(items_dict[i]['itemname'])
                        # i = 0和C使用 Module_dict
                        cases_list = items_dict[str(i)]['testcases']
                        if not any(cases_list):
                            continue
                        itemname_ = u"Item%s" %(i)+u"测试项:"+testDict['itemname']+" =>"+gettime2()
                        print itemname_
                        self.log_text.emit("Item",row,itemname_,str(False))
                        start_item_row = row
                        row=row+1
                        self.msleep(100)
                        
                        cases_len = len(cases_list)
                        # cases_list 为 1 2 4 6 这样的列表
                        # 前置设置执行可以放在这里
                        # 如果前置失败 则后面cases_list不循环执行
                        # 先打印pre_actsteps里面的内容 然后再执行右边的步骤
                        # 使用列表长度循环2个列表
                        self.log_text.emit("Act",row,u"//BeforeItem",str(False))
                        row = row+1
                        pre_len = len(testDict['pre_codesteps'])
                        #如果有测试点则执行前置条件
                        if cases_len>0:
                            for step in xrange(pre_len):
                                # 打印act
                                # 打印结果
                                if testDict['pre_codesteps'][step]:
                                    self.log_text.emit("Act",row,testDict['pre_actsteps'][step],str(False))
                                    row=row+1
                                    retjudge = self.judge(testDict['pre_codesteps'][step])
                                    if retjudge:
                                        ret=eval(testDict['pre_codesteps'][step])
                                    elif retjudge == False:
                                        exec testDict['pre_codesteps'][step]
                                        ret = True
                                    elif retjudge == None:
                                        continue
                                    # ret = eval(testDict['pre_codesteps'][step])
                                    self.log_text.emit("Code",row,testDict['pre_codesteps'][step],str(ret))
                                    row=row+1
                        row = row+2
                        #得到Cases_list的字典
                        # print "type(items_dict[i]['itemname'])",type(items_dict[i]['itemname'])
                        # item_lst.append(items_dict[i]['itemname'])
                        # cases_len = len(cases_list)
                        item_write_msg = testDict['itemname']+u"  (执行用例数=%s)" %(cases_len)
                        # print "type(item_write_msg)=",type(item_write_msg)
                        # print "cases_list=",cases_list
                        item_lst.append(item_write_msg)
                        case_num = 0
                        for case in cases_list:
                            if not case:
                                case_num=case_num+1
                                continue
                            # 得到字典
                            # 1> 变量赋值 通过循环字典对除了steps的变量进行赋值
                            # 2> steps
                            #打印casename
                            # print "case=",case
                            # print "testDict['testcases']=",testDict['testcases']
                            casename_ = testDict['testcases'][case_num]['casename']
                            # casename_ =case['casename']
                            
                            self.log_text.emit("Case",row,u"开始测试 "+casename_,str(True))
                            row=row+1
                            print u"开始测试"+casename_
                            self.msleep(100)
                            data_source = u"          "
                            if case:
                                for k,v in testDict['testcases'][case_num].iteritems():
                                    #循环字典进行变量初始化赋值
                                    if k != 'steps' and len(k)>0:
                                        exec "%s=v" %(k)
                                        if k != "casename":
                                            data_source = data_source+" %s=%s " %(k,v)
                            #执行steps里面的内容
                            case_len = len(testDict['codesteps'])
                            retlst=[]
                            for step in xrange(case_len):
                                # QApplication.processEvents()
                                try:
                                    retjudge = self.judge(testDict['codesteps'][step])
                                    if retjudge:
                                        ret=eval(testDict['codesteps'][step])
                                        retstr = ret
                                    elif retjudge == False:
                                        exec testDict['codesteps'][step]
                                        ret = True
                                    elif retjudge == None:
                                        continue
                                except Exception,e:
                                    #如果有一步执行失败则直接跳出循环进行下一个case
                                    ret = False
                                    print "error step=",testDict['codesteps'][step]
                                    break
                                    # self.parent.writeData2Excel(ret,sheet_location)
                                # print testDict['actsteps'][step]
                                self.log_text.emit("Act",row,testDict['actsteps'][step]+data_source,str(False))
                                row=row+1
                                self.msleep(100)
                                # ret = eval(step)
                                retlst.append(str(ret))
                                self.log_text.emit("Code",row,testDict['codesteps'][step],str(ret))
                                # 
                                row=row+1
                                self.msleep(100)
                            # self.log_text.emit("Case",row,casename_+u"测试完成",False)
                            # print "retlst=",retlst
                            if 'False' in retlst:
                                self.log_text.emit("Case",row,u"测试完成:"+casename_+u" => Fail",str(False))
                                item_lst.append(u"×  "+casename_)
                                testsfail = testsfail + 1
                                if i == 0 or i == items_len-1:
                                    testsfail = testsfail - 1
                            else:
                                self.log_text.emit("Case",row,u"测试完成:"+casename_+u" => Pass",str(True))
                                item_lst.append(u"√  "+casename_)
                                testspass = testspass + 1
                                if i == 0 or i == items_len-1:
                                    testspass = testspass - 1
                            row=row+2
                            case_num = case_num+1
                                # step="kc.config_channel(**kc_args)"
                                # step="kt.config_channel(**kt_args)"
                            #这里可以把执行结果打印到指定文件中去
                        #对于测试项环境清理
                        self.log_text.emit("Act",row,u"//AfterItem",str(False))
                        row = row+1
                        #suf_actsteps': [], 'suf_codesteps'
                        suf_len = len(testDict['suf_codesteps'])
                        #Item清理步骤
                        for step in xrange(suf_len):
                            # 打印act
                            # 打印结果
                            if testDict['suf_codesteps'][step]:
                                self.log_text.emit("Act",row,testDict['suf_actsteps'][step],str(False))
                                row=row+1
                                # ret = eval(testDict['suf_codesteps'][step])
                                retjudge = judge(testDict['suf_codesteps'][step])
                                if retjudge:
                                    ret=eval(testDict['suf_codesteps'][step])
                                elif retjudge == False:
                                    exec testDict['suf_codesteps'][step]
                                    ret = True
                                elif retjudge == None:
                                    continue
                                self.log_text.emit("Code",row,testDict['suf_codesteps'][step],str(ret))
                                row=row+1
                        row = row+2
                        #打印Item_lst 到LogDict表格中
                        self.log_text.emit("LogDict_E",logdict_row,u"\n".join(item_lst),str(False))
                        self.log_text.emit("LogDict_C",logdict_row,u"%s" %(i),str(False))
                        self.msleep(100)
                        lkmsg="Log!A%s#LogDict!C%s" %(start_item_row,logdict_row)
                        self.log_text.emit("Link",logdict_row,lkmsg,str(False))
                        #设置模块名合并单元格
                        logdict_row=logdict_row+1
                #
                # print "dict_row=",dict_row
                # print "items_len=",items_len
                module_msg = u"%s\n%s" %(module,dict_row+items_len-1)
                self.log_text.emit("LogDict_B",dict_row,module_msg,str(False))
                self.log_text.emit("Sum",sum_row,module+u"\n"+u"%s" %(testspass)+u"\n"+u"%s" %(testsfail),str(False))
                sum_module_msg = "Sum!B%s#LogDict!B%s" %(sum_row,dict_row)
                self.log_text.emit("Link",logdict_row,sum_module_msg,str(False))
                # 打印Sum信息和Module模块信息,这里logdict_row 需要到上一行
                row=row+1
                sum_row = sum_row+1
                self.msleep(100)
        #完成测试后弹窗然后保存Excel文件
        self.log_text.emit("Done",row,u"测试完成",str(True))
class MainWindow(QMainWindow):
    def __init__(self,parent=None):
       # os.chdir(mainpath);
        # global kt,ks
        super(MainWindow,self).__init__(parent)
        # self.setWindowTitle("Main.exe")
        self.ui=Ui_MainWindow()
        self.ui.setupUi(self)
        # self.ui.testlog.verticalScrollBar().setValue(self.ui.testlog.verticalScrollBar().maximumHeight())
        #把树上打勾的存入到字典中
        self.need_testcases={}
        #从配置文件中获取所有产品类
        self.init_product()
        self.product = self.ui.product.currentText()
        self.son_product = self.ui.son_product.currentText()
        self.source = QXmlInputSource()
        self.handler = XmlHandler(self.ui.casetree)
        self.reader = QXmlSimpleReader()
        self.reader.setContentHandler(self.handler)
        self.reader.setErrorHandler(self.handler)
        #初始化用例树
        self.build_case_tree()
        #添加测试用例的响应事件
        self.connect(self.ui.selectall,SIGNAL("clicked()"),self.selectAllTestcases)
        self.connect(self.ui.selectnone,SIGNAL("clicked()"),self.selectNoneTestcases)
        self.connect(self.ui.casetree,QtCore.SIGNAL("itemClicked (QTreeWidgetItem*,int)"),self.refresh_testcases)
        self.connect(self.ui.exceltoxml,QtCore.SIGNAL("clicked()"),self.exceltoxml)
        self.connect(self.ui.py2xml,QtCore.SIGNAL("clicked()"),self.pytoxml)
        self.connect(self.ui.savecfg,QtCore.SIGNAL("clicked()"),self.savecfg)
        # self.connect_menu()
        self.connect(self.ui.start_test,QtCore.SIGNAL("clicked()"),self.run_test)
        #testcase目录为test/product下product_son_product
        self.testcasedir=os.path.join(TestDir,str(self.product))
        # try:
            # self.stdout=sys.stdout
            # self.stderr=sys.stderr
            # sys.stdout=LogMsg(self.ui.testlog)
            # sys.stderr=sys.stdout
        # except Exception,e:
            # print "%s init error:%s" %(__name__,str(e))
        self.runthread = RunThread(self)
        self.runthread.signal_text.connect(self.writeData2Excel)
        self.runthread.log_text.connect(self.writelog)
        
        # self.logdir = os.path.join(ReportDir)
        self.start_flag = 0
    def module_isnull(self,**kargs):
        #判断模块里面是否有需要测试的点
        for k,v in kargs.iteritems():
            if k == "0" or k == "C":
                continue
            else:
                #返回True表示需要测试
                if any(v['testcases']):
                    return True
        return False
    def writelog(self,type,row,value,result):
        # print "start write Excel data"
        # print "type=",type
        # print "row=",row
        # print "value=",type(value)
        # print type == "Module"
        #主要向第三张表Log 里面填写数据
        #type 分为Module BItem AItem Item Act Code Link 7种 每一种对应的风格和单元格不一样
        #module font.color =blue font.size=10 A-I 列
        value = unicode(value)
        type = unicode(type)
        sht=self.Log_Report
        sht.Activate()
        if type == "Module":
            # sht.Range(sht.Cells(4,1), sht.Cells(5,1)).Merge()
            cell = "A%s" %(row)
            cell_me=sht.Range("A%s"%(row), "I%s" %(row))
            cell_me.MergeCells = True
            time.sleep(0.1)
            # sht.Range(cell).Value=value
            print "start write value=",value
            cell_me.Value = value
            cell_me.Font.Size = 10
            cell_me.Font.Color = 0xff0000
            print "start write done",
        elif type == "Item":
            cell_me=sht.Range("A%s"%(row), "I%s" %(row))
            cell_me.MergeCells = True
            cell_me.Value = value
            cell_me.Font.Size = 12
            cell_me.Font.Color = 0xff0000
            cell_me.Font.Underline = True    #下划线
        elif type == "BItem" or type == "AItem":
            cell0 = "A%s" %(row)
            cell = "B%s" %(row)
            sht.Range(cell0).Value = Value
            sht.Range(cell).Value = "//BeforeItem"
            if type == "AItem":
                sht.Range(cell).Value = "//AfterItem"
            sht.Range(cell).Font.Size = 10
            sht.Range(cell).Font.Color = 0xff0000
            sht.Range(cell0).Font.Size = 10
            sht.Range(cell0).Font.Color = 0xff0000
        elif type == "Act" or type == 'Code':
            if type == "Act":
                cell_me=sht.Range("B%s"%(row), "I%s" %(row))
                cell_me.MergeCells = True
            else:
                cell_me=sht.Range("C%s"%(row), "I%s" %(row))
                cell_me.MergeCells = True
            cell_me.Value = value
            cell_me.Font.Size = 10
            if type == "Code":
                cell = "J%s" %(row)
                cell1 = "K%s" %(row)
                if result == 'True':
                    sht.Range(cell).Value = u"  √"
                    sht.Range(cell).Font.Color = 0xff0000
                else:
                    sht.Range(cell).Value = u"  ×"
                    # sht.Range(cell1).Value = result
                    sht.Range(cell).Font.Color = 0x0000ff
        elif type == "Case":
            cell0 = "A%s" %(row)
            cell = "B%s" %(row)
            sht.Range(cell).Value = value
            print "Case result =",result
            # print "Case=",result
            if result == 'True':
                #返回正常为蓝色 返回失败为红色
                sht.Range(cell).Font.Color = 0xff0000
            else:
                sht.Range(cell).Font.Color = 0x0000ff
            sht.Range(cell).Font.Size = 10
        elif type == "Link":
            source = value.split("#")[0] 
            target = value.split("#")[1]
            self.createlink(source,target)
            # sht.Hyperlinks.Add(Anchor=sht.Range("A10"),Address="Report_%s.xls" %(self.reportfile),SubAddress="Log!A100",TextToDisplay="A100")
            # 主要用于创建超链接
        elif type.startswith("LogDict"):
            #把数据写入到LogDict里面
            sht = self.Module_Report
            if type.endswith("_C"):
                cell = "C%s" %(row)
                sht.Range(cell).Font.Size = 12
                sht.Range(cell).Value = value
            elif type.endswith("_E"):
                cell = "E%s" %(row)
                sht.Range(cell).Font.Size = 9
                sht.Range(cell).Value = value
            elif type.endswith("_B"):
                # print "value=",value
                var = value.split("\n")[0]
                end_row = value.split("\n")[1]
                cell_me=sht.Range("B%s"%(row), "B%s" %(end_row))
                cell_me.MergeCells = True
                cell_me.Value = var
                cell_me.Font.Size = 12
        elif type == "Sum":
            # 打印模块统计信息
            #{'red':0x0000ff,'blue':0xff0000,'green':0x00ff00,'black':0x00000}
            module,tspass,tsfail = value.split("\n")
            sht = self.Sum_Report
            cell_module = "B%s" %(row)
            cell_tspass = "C%s" %(row)
            cell_tsfail = "D%s" %(row)
            sht.Range(cell_module).Value = module
            sht.Range(cell_tspass).Value = tspass
            sht.Range(cell_tspass).Font.Color = 0x00ff00
            sht.Range(cell_tspass).Font.Size = 12
            sht.Range(cell_tsfail).Value = tsfail
            sht.Range(cell_tsfail).Font.Color = 0x0000ff
            sht.Range(cell_tsfail).Font.Size  = 12
        elif type == "Done":
            QMessageBox.information(self,"Done",u"测试完成",QMessageBox.Yes)
            self.wb.Save()
            self.ui.start_test.setText(u"开始测试")
    def createlink(self,source,target):
        filename = "Report_%s.xls" %(self.reportfile)
        s_sheet = source.split("!")[0]
        s_location = source.split("!")[1]    
        t_sheet = target.split("!")[0]
        t_location = target.split("!")[1]
        s_obj = self.wb.Worksheets(s_sheet)
        t_obj = self.wb.Worksheets(t_sheet)
        s_obj.Hyperlinks.Add(Anchor=s_obj.Range(s_location),Address=filename,SubAddress=target)
        t_obj.Hyperlinks.Add(Anchor=t_obj.Range(t_location),Address=filename,SubAddress=source)
    def open_config(self):
        pass
    def savecfg(self,flag=True):
        #先把以前的信息读取出来,然后保存成字典,然后把GUI上有的参数替换掉,没有的参数不操作
        global ConfigFile
        init_dict = ParserCfg(ConfigFile)
        guidict = {}
        guidict['kt']={}
        guidict['km']={}
        guidict['dut']={}
        
        cf = ConfigParser.ConfigParser()
        
        guidict['dut']['dip'] = unicode(self.ui.ip.text())
        guidict['dut']['product'] = unicode(self.ui.product.currentText())
        guidict['dut']['subprod'] = unicode(self.ui.son_product.currentText())
        guidict['dut']['username']=unicode(self.ui.username.text())
        guidict['dut']['pwd'] = unicode(self.ui.password.text())
        
        guidict['kt']['host'] = unicode(self.ui.sship.text())
        guidict['km']['com'] = unicode(self.ui.com.text())
        for key,value in init_dict.iteritems():
            cf.add_section(key)
            for k,v in value.iteritems():
                if guidict.has_key(key):
                    if guidict[key].has_key(k):
                        cf.set(key, k, guidict[key][k])
                        continue
                cf.set(key, k, v)
        with open(ConfigFile.replace("\\","/"),"w+") as f:
            cf.write(f)
        self.config=ParserCfg(ConfigFile)
        if flag:
            QMessageBox.information(self,"savecfg",u"保存配置成功",QMessageBox.Yes)
    def run_test(self):
        # self.refresh_testcases()
        text=unicode(self.ui.start_test.text())
        if text == u"停止测试":
            self.run_stop()
            self.ui.start_test.setText(u"开始测试")
        else:
            self.savecfg(False)
            self.init_report()
            self.ui.start_test.setText(u"停止测试")
            self.runthread.start_test()
    def init_report(self):
        self.reportfile = gettime()
        reportdir = os.path.join(MainDir,"result/%s" %(self.reportfile))
        if not os.path.exists(reportdir):
            os.makedirs(reportdir)
        self.reportdir = reportdir
        reportfile = os.path.join(reportdir,"Report_%s.xls" %(self.reportfile)).replace("\\","/")
        # resultfile=os.path.join(reportdir,u"IXIA仪器性能测试V1.7%s.xlsx" %(self.reportfile)).replace("\\","/")
        # shutil.copy(Result_Module,resultfile)
        shutil.copy(Report_module,reportfile)
        excel = win32com.client.gencache.EnsureDispatch('Excel.Application')
        self.wb=excel.Workbooks.Open(reportfile)
        # self.workbook=excel.Workbooks.Open(resultfile)
        excel.Visible=True
        self.Sum_Report=self.wb.Worksheets("Sum")
        self.Log_Report = self.wb.Worksheets("Log")
        self.Module_Report=self.wb.Worksheets("LogDict")
    def run_stop(self):
        self.runthread.stop_test()
    def writeData2Excel(self,value,kargs):
        #此函数以前用于把结果填写到指定表格中去
        kargs = unicode(kargs)
        try:
            kargs=eval(kargs)
        except Exception,e:
            pass
        value = unicode(value)
        # print "value=",value
        #每次写入后保存一次
        if kargs:
            sheet = self.workbook.Worksheets(kargs['sheet'])
            # sheet.Activate()
            #需要判断value值是否为逗号分割的字符串,如果是需要对数据进行拆分处理
            value = value.split(",")
            v_len = len(value)
            # polst = kargs['pos'].split(" ")
            polst = re.split(" +",kargs['pos'])
            if v_len == 1:
                sheet.Range(polst[0]).Value=value[0]
            else:
                for i in range(v_len):
                    sheet.Range(polst[i]).Value=value[i]
            self.workbook.Save()
    def refresh_testcases(self):
        # self.build_case_tree()
        testcases_sum = 0
        # print "len(self.ui.casetree)",len(self.ui.casetree.items())
        modules=self.ui.casetree.topLevelItemCount()
        # modules=self.root.childCount()
        # self.ui.casetree.topLevelItem(i_module)
        self.root=self.ui.casetree
        # print "modules=",type(modules)
        self.need_testcases = {}
        for i_modue in xrange(modules):
            module=self.ui.casetree.topLevelItem(i_modue)
            module_str=unicode(module.text(0))
            self.need_testcases[module_str]={}
            items=module.childCount()
            #items 表示有多少个测试项
            # print "len(items)=",repr(items)
            for i_item in range(items):
                item=module.child(i_item)
                #再循环case
                test_item_key = i_item+1
                test_item_key_str = str(test_item_key)
                self.need_testcases[module_str][test_item_key_str]={}
                self.need_testcases[module_str][test_item_key_str]['itemname']=unicode(item.text(0))
                self.need_testcases[module_str][test_item_key_str]['testcases']=[]
                # print item_str
                testcases=item.childCount()
                for i_tcase in xrange(testcases):
                    #根据caseindex得到节点
                    testcase = item.child(i_tcase)
                    if testcase.checkState(0) == Qt.Checked:
                        testcases_sum=testcases_sum+1
                        #如果勾选上了则把该测试点加入到需要测试字典中
                        self.need_testcases[module_str][test_item_key_str]['testcases'].append(str(i_tcase))
                    else:
                        #如果没有勾选也要把该测试点存入进行占位
                        self.need_testcases[module_str][test_item_key_str]['testcases'].append("")
                        # print unicode(testcase.text(0))
        self.ui.sumtestcases.setText(str(testcases_sum))
        # 循环模块得到Items,然后循环Items得到case
    def selectAllTestcases(self):
        self.handler.flag = 1
        self.handler.cases={}
        self.build_case_tree()
        
    def selectNoneTestcases(self):
        self.handler.flag = 0
        self.handler.cases={}
        self.build_case_tree()
    def init_config(self):
        self.ui.ip.setText(self.config['dut']['dip'])
        self.ui.username.setText(self.config['dut']['username'])
        self.ui.password.setText(self.config['dut']['pwd'])
        self.ui.sship.setText(self.config['kt']['host'])
        self.ui.com.setText(self.config['km']['com'])
        # self.ui.password.setText(self.config['dut']['pwd'])
    def init_product(self):
        #读取config/AllPro.ini的文件
        # global G_MainDict
        self.config=ParserCfg(ConfigFile)
        self.productfile=os.path.join(ConfigDir,"AllPro.ini").replace("\\","/")
        #
        current_pro=self.config['dut']['product']
        current_sonpro=self.config['dut']['subprod']
        #GUI配置初始化
        self.init_config()
        self.cur_product = current_pro
        self.current_sonpro = current_sonpro
        #根据产品类获取子产品所有参数
        son_productDir=os.path.join(ConfigDir,current_pro)
        son_productfile=os.path.join(son_productDir,"%s_AllSonProd.ini" %(current_pro)).replace("\\","/")
        
        productlist=self.readfile(self.productfile)
        sonproductlist=self.readfile(son_productfile)
        
        self.ui.product.addItem(current_pro)
        self.ui.son_product.addItem(current_sonpro)
        #首先删除掉所有元素
        for pro in productlist:
            if current_pro != pro.strip():
                self.ui.product.addItem(pro.strip())
        # self.ui.product.setEditText (current_pro)
        for sonpro in sonproductlist:
            if current_sonpro != sonpro.strip():
                self.ui.son_product.addItem(sonpro.strip())
        #创建2个响应事件,如果产品类改变则调用build_sunprod 函数刷新子产品
        self.connect(self.ui.product,SIGNAL("currentIndexChanged(int)"),self.build_subprod)
        self.connect(self.ui.son_product,SIGNAL("currentIndexChanged(int)"),self.build_case_tree)
        # self.ui.product.setItemText(0,current_pro)
        # self.load_config()
    def build_subprod(self):
        #得到第一个下拉列表的值,然后加载相应的文件
        cur_product=unicode(self.ui.product.currentText())
        self.cur_product=cur_product
        # cur_product=cur_product.toStdString()
        # print "cur_product=,",cur_product
        son_productDir=os.path.join(ConfigDir,cur_product)
        son_productfile=os.path.join(son_productDir,"%s_AllSonProd.ini" %(cur_product)).replace("\\","/")
        #先获取当前子产品列表长度
        sonproductlist=self.readfile(son_productfile)
        #获取子产品系列
        self.current_sonpro=sonproductlist[0].strip()
        self.ui.son_product.clear()
        # self.ui.son_product.addItem("")
        for sonpro in sonproductlist:
            self.ui.son_product.addItem(sonpro.strip())
        self.current_sonpro=unicode(self.ui.son_product.currentText()) 
    def build_case_tree(self):
        #加载获取xml文件
        #第一步 获得当前的
        xmlDir=os.path.join(ConfigDir,self.cur_product)
        #判断改变之前子产品是否为空
        if self.ui.son_product.currentText():
            self.current_sonpro=unicode(self.ui.son_product.currentText()) 
        xmlfile=os.path.join(xmlDir,"%s_%s.xml" %(self.cur_product,self.current_sonpro)).replace("\\","/")
        # 开始解析xml文件到tree里面去
        # print "xmlfile=",xmlfile
        if os.path.exists(xmlfile):
            xmlstr="".join(self.readfile(xmlfile)).replace("\n","")
            # print "xmlstr=",xmlstr
            xmlstr=xmlstr.decode('utf8')
            #循环xml文件进行解析
            #先要把以前的树节点使用clear清除
            self.ui.casetree.clear()
            self.ui.casetree.header().setResizeMode(QtGui.QHeaderView.Stretch)
            self.source.setData(xmlstr)
            #先清空解析一次
            # reader.parse()
            self.reader.parse(self.source)
            #重新刷新用例树
            self.testcasedir=os.path.join(TestDir,str(self.cur_product))
            self.xmldir = os.path.join(ConfigDir,str(self.cur_product))
            self.refresh_testcases()
    def readfile(self,filename):
        fd=open(filename,"r")
        productlist=fd.readlines()
        fd.close()
        return productlist
    def exceltoxml(self):
        #得到测试用例目录
        self.product = unicode(self.ui.product.currentText())
        self.current_sonpro=unicode(self.ui.son_product.currentText()) 
        self.testcasedir=os.path.join(TestDir,str(self.product))
        files=os.listdir(self.testcasedir)
        for file in files:
            if file.endswith(".xlsx") or file.endswith(".xls"):
                #如果为excel文件则解析
                self.exceltopy(os.path.join(self.testcasedir,file).replace("\\","/"))
        QMessageBox.information(self,"excel2py",u"Excel转换.py脚本成功",QMessageBox.Yes)
    def pytoxml(self):
        self.xmldir = os.path.join(ConfigDir,str(self.product))
        pro_spro=str(self.product)+"_"+str(self.current_sonpro)
        self.xmlfile = os.path.join(self.xmldir,pro_spro+".xml").replace("\\","/")
        # print "start createxml"
        cx = Createxml(self.testcasedir,self.xmlfile,pro_spro)
        cx.createxmlfile()
        self.build_case_tree()
        QMessageBox.information(self,"excel2py",u"Excel转换.py脚本成功",QMessageBox.Yes)
    def exceltopy(self,filename):
        print "filename=",filename
        rc=ReadCase(filename)
        rc.saveItem()
    def normalOutputWritten(self, text):
        """Append text to the QTextEdit."""
        # Maybe QTextEdit.append() works as well, but this is how I do it:
        cursor = self.ui.testlog.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.ui.testlog.setTextCursor(cursor)
        self.ui.testlog.ensureCursorVisible()    
class XmlHandler(QXmlDefaultHandler):
    def __init__(self, root):
        QXmlDefaultHandler.__init__(self)
        self._root = root   ;#实际上root即为self.ui.casetree
        self._item = None   ;#_item 为里面需要使用的节点信息
        self._text = ''
        self._error = ''
        self.testcases_num=0
        self.flag   = 1 ;# 1表示选中 0表示不选中
        self.cases = {}
        # self.modules =self._root.childCount()
    def startElement(self, namespace, name, qname, attributes):
        dict_map={"Mod":"tm","Item":"ti","Case":"tc"}
        qname=unicode(qname)
        if qname == 'Mod' or qname == 'Item' or qname == 'Case':
            if self._item is not None:
                self._item = QtGui.QTreeWidgetItem(self._item)
            else:
                self._item = QtGui.QTreeWidgetItem(self._root)
            self._item.setData(0, QtCore.Qt.UserRole, qname)
            self._item.setText(0, attributes.value(dict_map[qname]))
            self._item.setFlags(self._item.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
            if qname == 'Case':
                self.selecttestcases(attributes.value(dict_map[qname]))
        self._text = ''
        # self.testcases_num=0
        return True

    def endElement(self, namespace, name, qname):
        qname=unicode(qname)
        if qname == 'tiName':
            if self._item is not None:
                self._item.setText(0, self._text)
                # pass
        elif qname == 'Mod' or qname == 'Item' or qname == 'Case':
        # elif qname == 'Item' or qname == 'Case':
            if qname == 'Case':
                # self.selecttestcases()
                self._item.setText(0, self._text)
            self._item = self._item.parent()
        # self.testcases_num=0
        return True

    def characters(self, text):
        self._text += text
        return True

    def fatalError(self, exception):
        print('Parse Error: line %d, column %d:\n  %s' % (
              exception.lineNumber(),
              exception.columnNumber(),
              exception.message(),
              ))
        return False

    def errorString(self):
        return self._error
    def selecttestcases(self,key):
        # if self.cases.has_key(key):
            # print "key=",key
        if self.flag == 1:
            self._item.setCheckState(0, Qt.Checked)
            self.cases[key] = 1
        elif self.flag == 0:
            self._item.setCheckState(0, Qt.Unchecked)
            self.cases[key] = 0
#
class ReadCase:
    def __init__(self,filename):
        self.fname=filename
        (shotname,extension) = os.path.splitext(self.fname);
        self.pycase=shotname+".py"
        # print "self.fname=",self.fname
        self.wkbook= xlrd.open_workbook(self.fname)
        #获取testcase工作表
        self.sheet=self.wkbook.sheet_by_name('testcases')
        self.nrows=self.sheet.nrows
        self.ncols=self.sheet.ncols
        self.modules={}
    def parserItem(self):
        #解析Item列
        self.modules={}
        itemdict={}
        itemnum = -1
        for row in range(1,self.nrows):
            itemname=self.sheet.cell(row,0).value
            if itemname:
                itemdict['itemname']=itemname
                item_id=itemname.split("]")[0]
                itemnum = itemnum+1
                if itemname.startswith("0]") or itemname.startswith("C]"):
                    itemdict['testcases']=self.parserCase0E(row)
                    itemdict['codesteps'] = self.parserSteps(1,self.sheet.cell(row,3).value)
                    itemdict['actsteps'] = self.parserSteps(0,self.sheet.cell(row,2).value)
                    itemdict['pre_actsteps'] = []
                    itemdict['pre_codesteps'] = []
                    itemdict['suf_codesteps'] =[]
                    itemdict['suf_actsteps'] =[]
                else:
                    itemdict['testcases']=self.parserCase(row)
                    casenum = len(itemdict['testcases'])
                    itemdict['codesteps'] = self.parserSteps(1,self.sheet.cell(row+1,3).value)
                    itemdict['actsteps'] = self.parserSteps(0,self.sheet.cell(row+1,2).value)
                    itemdict['pre_actsteps'] = self.parserSteps(0,self.sheet.cell(row,2).value)
                    itemdict['pre_codesteps'] = self.parserSteps(1,self.sheet.cell(row,3).value)
                    itemdict['suf_codesteps'] =self.parserSteps(1,self.sheet.cell(row+casenum+1,3).value)
                    itemdict['suf_actsteps'] =self.parserSteps(0,self.sheet.cell(row+casenum+1,2).value)
            #得到所有的参数
            new_itemdict=copy.deepcopy(itemdict)
            if item_id == 'C':
                self.modules['%s' %(item_id)] =  new_itemdict
            else:
                self.modules['%s' %(itemnum)] =  new_itemdict
    def parserSteps(self,flag,stepstr=""):
        u"""flag=1 1> kc xxxxx 2>kt xxxx 的字符串解析['kc xxxx','kt xxxx']"""
        retlst =[]
        stepslst = stepstr.split("\n")
        for step in stepslst:
            if flag == 0:
                retlst.append(step)
            else:
                retlst.append(re.sub("[0-9]+> ?","",step))
        return retlst
    def parserCase0E(self,row):
        ret_list=[]
        key_list={}
        value_list=[]
        testcases={}
        for s_row in xrange(row,self.nrows):
            casename = self.sheet.cell(s_row,1).value
            if casename:
                    testcases['casename'] = casename
            else:
                break
            new_tcase=copy.deepcopy(testcases)
            ret_list.append(new_tcase)
        return ret_list
    def parserCase(self,row):
        ret_list=[]
        key_list={}
        value_list=[]
        testcases={}
        for col in range(4,self.ncols):
            key_list['%s' %(col)]= self.sheet.cell(row,col).value
        new_row = row+1
        for s_row in xrange(new_row,self.nrows):
            casename = self.sheet.cell(s_row,1).value
            if casename:
                if casename.startswith("E)") or casename.startswith("0)"):
                    continue
                else:
                    testcases['casename'] = casename
            else:
                break
            for col in range(4,self.ncols):
                testcases[key_list[str(col)]]=self.sheet.cell(s_row,col).value
            new_tcase=copy.deepcopy(testcases)
            ret_list.append(new_tcase)
        return ret_list
    def saveItem(self):
        self.parserItem()
        try:
            fd=codecs.open(self.pycase,'w','utf-8')
            # fd.write('#coding=utf8\n')
            fd.write('%s' %(self.modules))
            fd.close()
        except Exception,e:
            print e
class Createxml:
    def __init__(self,rootdir=None,xmlfile=None,pro_spro=None):
        self.pyfiles=[]
        if rootdir:
            files=os.listdir(rootdir)
        prefix=pro_spro+"_"
        suffix=".py"
        for file in files:
            if file.startswith(prefix) and file.endswith(suffix):
                filepath=os.path.join(rootdir,file).replace("\\","/")
                self.pyfiles.append(filepath)
        self.cfgfile=xmlfile
        # print "self.pyfiles=",self.pyfiles
        self.pros=pro_spro
    def createxmlfile(self):
        self.doc = Document()  #创建DOM文档对象
        self.root = self.doc.createElement('Prod') #创建根元素
        self.root.setAttribute('Tp',self.pros)
        #把各个模块添加到root里面去
        #self.root.appendChild()
        # self.root.appendChild(self.modules)
        moduledict=self.getModules()
        # print "moduledict=",moduledict
        self.parserdict(**moduledict)
        self.doc.appendChild(self.root)
        fd = open(self.cfgfile,'w+')
        fd.write(self.doc.toprettyxml(indent='',encoding='UTF-8'))
        fd.close()
    def getModules(self):
        treedict={}
        for file in self.pyfiles:
            module=os.path.join(file).split(".")[0]
            module=module.split("_",2)[-1]
            treedict[module]=self.readpyfile(file)
        return treedict
    def readpyfile(self,filename):
        # print "filename=",filename
        fd=open(filename)
        retstr=fd.readlines()[0]
        fd.close()
        return retstr
    def parserdict(self,**kargs):
        for k,v in kargs.iteritems():
            if k == "0" or k == "C":
                continue
            module_node = self.doc.createElement('Mod')
            module_node.setAttribute('tm',k)
            module_node.setAttribute('name',k)
            curdict=eval(v)
            itemlen=len(curdict)-2
            for i in xrange(1,itemlen+1):
                if not curdict.has_key(str(i)):
                    continue
                itemdict=curdict[str(i)]
                item_node=self.doc.createElement('Item')
                item_text=itemdict['itemname']
                item_node.setAttribute('ti',item_text)
                for case in itemdict['testcases']:
                    self.addNode(item_node,'Case',case['casename'])
                module_node.appendChild(item_node)
            self.root.appendChild(module_node)
    def addNode(self,parent,node_name,node_text="",attribute=''):
        #添加有<node_name>node_text</node_name>标签
        node_info=self.doc.createElement(node_name)
        if attribute:
            node_info.setAttribute('name',attribute)
        if node_text:
            cur_node_text = self.doc.createTextNode(node_text)
            node_info.appendChild(cur_node_text)
        parent.appendChild(node_info)
        return node_info          
#主要用于把日志重定向到GUI上并且保证GUI在执行时不卡死
class LogMsg:
    def __init__(self,editobj):
        self.edit=editobj
        self.cache=""
    def write(self,msg):
        msg=msg.strip()
        if msg:
            if not isinstance(msg,unicode):
                msg=unicode(msg,'gbk')
            self.edit.append(msg)
            self.cache+=msg
            global app
            app.processEvents()
class Report:
    u"""对日志文件的处理"""
    def __init__(self):
        reportdir = os.path.join(MainDir,"result/%s" %(gettime()))
        if not os.path.exists(reportdir):
            os.makedirs(reportdir)
        reportfile = os.path.join(reportdir,"Report_%s.xls" %(gettime())).replace("\\","/")
        shutil.copy(Report_module,reportfile)
        excel = win32com.client.gencache.EnsureDispatch('Excel.Application')
        self.wb=excel.Workbooks.Open(reportfile)
        excel.Visible=True
        # excel = win32com.client.Dispatch('Excel.Application')  
        # excel.Visible=True
        # self.wb = excel.Workbooks.Add()
        #添加工作簿后默认会有一个sheets工作表
        #获取工作表
        self.Sum_Report=self.wb.Worksheets("Sum")
        self.Log_Report = self.wb.Worksheets("Log")
        self.Module_Report=self.wb.Worksheets("LogDict")
        
    def CellValue(self,cell,key,value):
        setattr(cell,key,value)
    def writeCell(self,sheetname,cell,Value):
        mapdict = {"Log":'Log',"Dict":'ModuleDict',"Sum":'Sum'}
        #直接切换
        wb = self.wb.Worksheets(mapdict[sheetname])
        wb.Activate()
        wb.Range(cell).Value = Value
        # func = getattr(mapdict[sheet],Range(cell))
    def writelog(self,type='Item',row=6,value=None,result=True):
        print "start write Excel data"
        print "type=",type
        print "row=",row
        print "value=",value
        print type == "Module"
        #主要向第三张表Log 里面填写数据
        #type 分为Module BItem AItem Item Act Code 6种 每一种对应的风格和单元格不一样
        #module font.color =blue font.size=10 A-I 列
        sht=self.Log_Report
        sht.Activate()
        if type == "Module":
            # sht.Range(sht.Cells(4,1), sht.Cells(5,1)).Merge()
            cell = "A%s" %(row)
            cell_me=sht.Range("A%s"%(row), "I%s" %(row))
            # cell_me.MergeCells = True
            time.sleep(0.1)
            sht.Range(cell).Value=value
            print "start write value=",value
            cell_me.Value = value
            cell_me.Font.Size = 10
            cell_me.Font.Color = 0xff0000
            print "start write done",
        elif type == "Item":
            cell_me=sht.Range("A%s"%(row), "I%s" %(row))
            cell_me.MergeCells = True
            cell_me.Value = value
            cell_me.Font.Size = 12
            cell_me.Font.Color = 0xff0000
            cell_me.Font.Underline = True    #下划线
        elif type == "BItem" or type == "AItem":
            cell0 = "A%s" %(row)
            cell = "B%s" %(row)
            sht.Range(cell0).Value = Value
            sht.Range(cell).Value = "//BeforeItem"
            if type == "AItem":
                sht.Range(cell).Value = "//AfterItem"
            sht.Range(cell).Font.Size = 10
            sht.Range(cell).Font.Color = 0xff0000
            sht.Range(cell0).Font.Size = 10
            sht.Range(cell0).Font.Color = 0xff0000
        elif type == "Act" or type == 'Code':
            if type == "Act":
                cell_me=sht.Range("B%s"%(row), "I%s" %(row))
                cell_me.MergeCells = True
            else:
                cell_me=sht.Range("C%s"%(row), "I%s" %(row))
                cell_me.MergeCells = True
            cell_me.Value = value
            cell_me.Font.Size = 10
            if type == "Code":
                cell = "J%s" %(row)
                if result:
                    sht.Range(cell).Value = "  √"
                    sht.Range(cell).Font.Color = 0xff0000
                else:
                    sht.Range(cell).Value = "  ×"
                    sht.Range(cell).Font.Color = 0x0000ff
        # sht.ScrollBars("A%s" %(row))   
        return True
    def FontAttribute(self,cell,**kargs):
        for key,value in kargs.iteritems():
            setattr(cell,key,value)
        #对某个单元格设置值只ws.Range("A1").Value=""
        #Module_Report 记录测试点测试结果
        #Excel中单元格属性
        #1、背景颜色 ws.Cells(i,1).Interior.ColorIndex = 
        # colordict={'black':1,'white':2,"red":3,"green":4,'blue':5,'yellow':6}
        # 2、列宽 
        #  ws.Columns("B:C").ColumnWidth = 16 #设置固定宽度
        #  ws.Columns.AutoFit() 自动调整列宽    #根据数据自动调整宽度
        # 3、行高
        #   ws.Rows(1).RowHeight = 60 #设置固定行高
        #   ws.Rows.AutoFit() #设置自动行高
        #   ws.Range("4").VerticalAlignment = win32.constants.xlCenter #垂直对齐
        # 4、单元格字体
        #    ws.Range("B4").Font.Name = u'宋体'
        #    ws.Range("B4").Font.Size = 12 #设置字体大小
        #    ws.Range("B4").Font.Color = 0xff0000 #蓝色 {'red':0x0000ff,'blue':0xff0000,'green':0x00ff00,'black':0x00000}
        #   ws.Range("B4").Font.Bold = True 表示字体加粗
        #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setWindowIcon(QIcon("./images/icon.png"))
    form = MainWindow()
    form.show()
    app.exec_()

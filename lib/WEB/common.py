#coding=utf8
import os,sys

import re
import time
import xlrd
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
#第一个为webdriver对象 第二个oprate 为Set/Get 第三个为要传入的参数值

def getCMapDict(filename,sheetname):
    path = os.path.dirname(os.path.realpath(__file__)).decode('gbk')
    filename = os.path.join(path,filename).replace("\\","/")
    data = xlrd.open_workbook(filename)
    table = data.sheet_by_name(sheetname)
    retdict = {}
    nrows = table.nrows
    #获取列表中的元素,B列的为模块关键字
    colB = table.col_values(1)
    colD = table.col_values(3)
    colE = table.col_values(4)
    colF = table.col_values(5)
    colG = table.col_values(6)
    colH = table.col_values(7)
    colI = table.col_values(8)
    #如果不为偶数个则返回失败
    
    for x in xrange(1,nrows):
        if colB[x]:
            module = colB[x]
            retdict[module] = {}
        #模块字段初始赋值
        colIlst=[]
        if colI[x]:
            colIlst = re.split("[\t ]+",colI[x])
        colIdict = {}
        # print "colIlst=",colIlst
        colIlen = len(colIlst)
        if colIlen%2 == 0:
            if colIlen != 0:
                for k in xrange(0,colIlen,2):
                    colIdict[colIlst[k]] = colIlst[k+1]
        else:
            print u"字典中第%s行 第I列字符串个数必须为偶数" %(x)
            sys.exit(0)
        
        lst = [colE[x],colF[x],colG[x],colH[x],str(colIdict)]

        retdict[module][colD[x]] = lst
    return retdict
class BaseWeb():
    def setobj(self,obj,type,value,attribute="{}"):
        
        attr_dict = eval(attribute)
        # print "value=",value
        # print "attribute=",attribute
        func = getattr(self,type)
        if obj.is_displayed():
            func(obj,value,'set',**attr_dict)
    def getobj(self,obj,type,value,attribute="{}"):
        #如果获取到的元素和value值一致则返回True,否则返回False
        attr_dict = eval(attribute)
        func = getattr(self,type)
        if obj:
            if obj.is_displayed():
                return func(obj,value,'get',**attribute)
        return False
    def sys_get(self,obj,*element):
        #判断某个标签是否存在
        prefix = element [0]
        self.switchframe(obj,prefix,flag=1)  
        ret = self.getElement(obj,'',*element)
        self.switchframe(obj,prefix,flag=0)
        if ret:
            if ret.is_displayed():
                return True
        return False
    def sys_set(self,obj,*element):
        #判断某个标签是否存在
        ret = self.getElement(obj,'',*element)
        if ret:
            return ret
        else:
            return False
    def getElement(self,obj,value,*element):
        # #element = [prefix id 'xxxxx' text_field value]形式
        #根据key得到调用那个函数,name为里面的值 一般使用id name class xpath获取
        key = element[1]
        name = element[2]
        type = element[3]   #对于select radio 需要特殊处理
        curobj = None
        if key == "id":
            curobj = self.findId(obj.driver,name,value)
        elif key == "name":
            curobj = self.findName(obj.driver,name,value)
        elif key == "class":
            curobj = self.findClassName(obj.driver,name,value)
        elif key == "xpath":
            curobj = self.findXpath(obj.driver,name,value)
        elif key == 'href':
            curobj = self.findTagName(obj.driver,type,name)
        if curobj:
            return curobj
        else:
            return False
    def switchframe(self,obj,frame='',flag=1):
        if frame:
            if flag:
                frame = obj.driver.find_element_by_xpath("//%s" %(frame))
                obj.driver.switch_to_frame(frame)

            else:
                obj.driver.switch_to_default_content()
        return True
    def SetValue(self,obj,funcname,value,key):
        #得到模块字典
        moduledict  = obj.cmapdict[funcname]
        #element = prefix id 'xxxxx' text_field value形式
        element = moduledict[key]
        prefix = element[0]
        type = element[3]
        attribute = element[4]
        print "element=",element
        #1、切换iframe 2、获取元素 3、操作元素 4、框架切换回来
        self.switchframe(obj,prefix,flag=1)
        #切换frame完成
        curelement = self.getElement(obj,value,*element)
        if not curelement.is_displayed():
            self.switchframe(obj,prefix,flag=0)
            return False
        self.setobj(curelement,type,value,attribute)
        self.switchframe(obj,prefix,flag=0)
    def GetValue(self,obj,funcname,value,key):
        moduledict  = obj.cmapdict[funcname]
        element = moduledict[key]
        prefix = element[0]
        type = element[3]
        #1、切换iframe 2、获取元素 3、操作元素 4、框架切换回来
        self.switchframe(obj,prefix,flag=1)
        obj = self.getElement(obj,value,*element)
        if not obj.is_displayed():
            self.switchframe(obj,prefix,flag=0)
            return False
        ret = self.getobj(obj,type,value)
        self.switchframe(obj,prefix,flag=0)
        return ret
    def div(self,obj,value,opt,**attribute):
        print u"开始配置开关选项"
        if opt == "set":
            if attribute:
                reversedict=dict([val,key] for key,val in attribute.items())
                atr_value = obj.get_attribute(attribute['attribute'])
                print "value=",value
                print "reversedict[value]=",reversedict[atr_value]
                if reversedict[atr_value] != value:
                    obj.click()
            else:
                obj.click()
    def checkbox(self,obj,value,opt,**attribute):
        curstatus = obj.is_selected()
        flag = False
        if value == "ON":
            flag = True
        if opt == "set":
            if curstatus ^ flag:
                obj.click()
            return True
        else:
            return curstatus == flag
    def select(self,obj,value,opt,**attribute):
        if opt == "set":
            Select(obj).select_by_value(value)
        else:
            if value == obj.get_attribute('value'):
                return True
            return False
    def text_field(self,obj,value,opt,**attribute):
        if opt == "set":
            obj.clear()
            obj.send_keys(value)
        else:
            if value == obj.get_attribute('value'):
                return True
            return False
    def radio(self,obj,value,opt,**attribute):
        if opt == "set":
            obj.click()
        return True
    def button(self,obj,value,opt,**attribute):
        obj.click()
        return True
    def href(self,obj,value,opt,**attribute):
        obj.click()
        return True
    def a(self,obj,value,opt,**attribute):
        obj.click()
        return True
    #通过id定位
    def findId(self,driver,id,value):
        try:
            f = driver.find_element_by_id(id)
            return f
        except Exception as e:
            print u"未找到%s"%(id)
            return False
    #通过tag_name定位 一般用于a标签
    def findTagName(self,driver,type,value):
        try:
            f_lst = driver.find_elements_by_tag_name(type)
            url = driver.current_url
            if len(f_lst) == 1:
                return f_lst[0]
            else:
                for i in f_lst:
                    #i.get_attribute('href')返回的是当前站点的
                    if i.get_attribute('href').endswith(value):
                        return i
        except Exception as e:
            print u"未找到%s"%(value)
            return None
        return None
    #通过name定位
    def findName(self,driver,name,value):
        try:
            f_lst = driver.find_elements_by_name(name)
            if len(f_lst) == 1:
                return f_lst[0]
            else:
                for i in f_lst:
                    if value == i.get_attribute('value'):
                        return i
        except Exception as e:
            print u"未找到%s"%(name)
            return None
        return None
    #通过class定位
    def findClassName(self,driver,name,value):
        try:
            f = driver.find_element_by_class_name(name)
            return f
        except Exception as e:
            print u"未找到%s"%(name)
    def findClassNames(self, driver,name,value):
        try:
            f = driver.find_elements_by_class_name(name)
            return f
        except Exception as e:
            print u"未找到%s"%(name)
    #通过text定位
    def findAU(self,driver,name,value):
        try:
            f = driver.find_element_by_android_uiautomator('text(\"' + name +'\")')
            return f
        except Exception as e:
            print u"未找到%s"%(name)

    #通过xpath定位
    def findXpath(self,driver,xpath,value):
        try:
            f = driver.find_element_by_xpath(xpath)
            return f
        except Exception as e:
            print u"未找到%s"%(xpath)

    #通过content-desc
    def findAI(self,driver,content_desc):
        try:
            f = driver.find_element_by_accessibility_id(content_desc)
            return f
        except Exception as e:
            print u"未找到%s"%(content_desc)
    def sys_pre(self,obj,*mainflag,**kargs):
        #obj 是子产品的self对象
        #先判断是否在主页面,如果不在则先进入主页面
        FLAGGET = kargs['get']  #[id,xxxxx,text_field]
        FLAGSET = kargs['set']  #多个三元组组成的列表
        # print "kargs['set']=",kargs['set']
        #如果在当前页面则不需要操作,
        obj.driver.refresh()
        time.sleep(1)
        print u'开始进入指定页面'
        if self.sys_get(obj,*FLAGGET):
            return True
        if not self.sys_get(obj,*mainflag):
            obj.gotomain()
        #cc
        print u'开始进入指定页面'
        try:
            for i in FLAGSET:
                #先判断该内容是字典还是列表
                cur_element = self.sys_set(obj,*i)
                if cur_element:
                    cur_element.click()
                time.sleep(1)
            return True
        except Exception,e:
            print e
            return False

           
if __name__ == "__main__":
    cc=getCMapDict("AC_CMAP.xlsx","AC10")
    print cc
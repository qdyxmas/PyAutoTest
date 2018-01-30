#coding=utf8
import os,sys

import re
import time
import xlrd
import colorsys

from PIL import Image
from appium import webdriver

path = os.path.dirname(os.path.realpath(__file__)).decode('gbk')
def getCMapDict(filename,sheetname):
    # path = os.path.dirname(os.path.realpath(__file__)).decode('gbk')
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
    colJ = table.col_values(9)
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
            print "colI[x]=",colI[x]
            print u"字典中第%s行 第I列字符串个数必须为偶数" %(x)
            sys.exit(0)
        
        lst = [colE[x],colF[x],colG[x],colH[x],str(colIdict),colJ[x]]
        retdict[module][colD[x]] = lst
    return retdict
class BaseApp():
    def setobj(self,obj,label_type,value,attribute="{}"):
        attr_dict = eval(attribute)
        func = getattr(self,label_type)
        func(obj,value,'set',**attr_dict)
    def getobj(self,obj,label_type,value,attribute="{}"):
        #如果获取到的元素和value值一致则返回True,否则返回False
        attr_dict = eval(attribute)
        func = getattr(self,label_type)
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
        label_type = element[3]   #对于select radio 需要特殊处理
        attribute = element[4]
        if attribute:
            attribute=eval(attribute)
        direction = element[5]
        curobj = None
        dircDict = {"left":self.swipLeft,"right":self.swipRight,"up":self.swipeUp,"down":self.swipeDown}
        function = ""
        if direction:
            function = dircDict[direction]
        for x in xrange(10):
            if key == "id":
                curobj = self.findId(obj.driver,name,value)
            elif key == "name":
                curobj = self.findName(obj.driver,name,value)
            elif key == "class":
                curobj = self.findClassName(obj.driver,name,value)
            elif key == "xpath":
                curobj = self.findXpath(obj.driver,name,value)
            elif key == 'href':
                curobj = self.findTagName(obj.driver,label_type,name)
            elif key == "au":
                curobj = self.findAU(obj.driver,name,value)
            print "curobj=",curobj
            if curobj:
                if len(curobj) == 1:
                    return curobj[0]
                else:
                    return self.parser_objlst(value,*curobj,**attribute)
            if function:
               function(obj.driver,1000)
            time.sleep(0.5)
        return False
    def parser_objlst(self,value,*args,**kargs):
        attr = kargs['attribute']
        if attr == "index":
            if kargs.has_keys("TEXT"):
                return args[int(kargs['TEXT'])]
            else:
                retobj = args[int(kargs[value])]
            return retobj
        elif attr == "value":
            for i in args:
                if i.get_attribute('value') == value:
                    return i
        elif attr == "no":
            return args
        elif attr == "text":
            for i in args:
                if i.get_attribute('text') == value:
                    return i
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
        label_type = element[3]
        attribute = element[4]
        print "element=",element
        #1、切换iframe 2、获取元素 3、操作元素 4、框架切换回来
        self.switchframe(obj,prefix,flag=1)
        #切换frame完成
        curelement = self.getElement(obj,value,*element)
        # if curelement.is_displayed():
            # self.switchframe(obj,prefix,flag=0)
            # return None
        self.setobj(curelement,label_type,value,attribute)
        # time.sleep(0.5)
        self.switchframe(obj,prefix,flag=0)
    def GetValue(self,obj,funcname,value,key):
        moduledict  = obj.cmapdict[funcname]
        element = moduledict[key]
        prefix = element[0]
        label_type = element[3]
        #1、切换iframe 2、获取元素 3、操作元素 4、框架切换回来
        self.switchframe(obj,prefix,flag=1)
        obj = self.getElement(obj,value,*element)
        if not obj.is_displayed():
            self.switchframe(obj,prefix,flag=0)
            return False
        ret = self.getobj(obj,label_type,value)
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
        curstatus = obj.get_attribute(attribute["attribute"])
        if curstatus == "true":
            curstatus = True
        else:
            curstatus = False
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
        #select进行拖拽
            Select(obj).select_by_value(value)
        else:
            if value == obj.get_attribute('value'):
                return True
            return False
    def text_field(self,obj,value,opt,**attribute):
        if opt == "set":
            obj.clear()
            if re.search(r"[^0-9A-Za-z_]+",value):
                self.adbSendText(value)
            else:
                obj.send_keys(value)
            # obj.send_keys(value) 此函数运行较慢
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
    #获取元素的text值
    def text(self,obj):
        return obj.text
    #通过id定位
    def findId(self,driver,id,value):
        try:
            f = driver.find_elements_by_id(id)
            return f
        except Exception as e:
            print u"未找到%s"%(id)
            return False
    #通过tag_name定位 一般用于a标签
    def findTagName(self,driver,label_type,value):
        try:
            f = driver.find_elements_by_tag_name(label_type)
            return f_lst
            # url = driver.current_url
            # if len(f_lst) == 1:
                # return f_lst[0]
            # else:
                # for i in f_lst:
                    # if i.get_attribute('href').endswith(value):
                        # return i
        except Exception as e:
            print u"未找到%s"%(value)
            return None
        return None
    #通过name定位
    def findName(self,driver,name,value):
        try:
            f = driver.find_elements_by_name(name)
            return f
        except Exception as e:
            print u"未找到%s"%(name)
            return None
        return None
    #通过class定位
    def findClassName(self,driver,name,value):
        try:
            f = driver.find_elements_by_class_name(name)
            return f
        except Exception as e:
            return None
            print u"未找到%s"%(name)
    #通过text定位
    def findAU(self,driver,name,value):
        try:
            f = driver.find_elements_by_android_uiautomator('text(\"' + value +'\")')
            return f
        except Exception as e:
            print u"未找到%s"%(value)

    #通过xpath定位
    def findXpath(self,driver,xpath,value):
        try:
            f = driver.find_elements_by_xpath(xpath)
            return f
        except Exception as e:
            print u"未找到%s"%(xpath)

    #通过content-desc
    #192.168.5.185
    def findAI(self,driver,content_desc):
        try:
            f = driver.find_elements_by_accessibility_id(content_desc)
            return f
        except Exception as e:
            print u"未找到%s"%(content_desc)
    def search_element(self,obj,funcname,**expe):
        #其中k是个关键字可以用来存放
        factdict = {}
        #下滑的最大次数
        # 匹配次数
        expe_match_num = len(expe)
        for x in xrange(5):
            #一次循环可以得到一屏显示的内容
            factdict = {}
            for k,v in expe.iteritems():
                factdict[k]=[]
                element = obj.cmapdict[funcname][k]
                curobjs = self.getElement(obj,'',*element)
                #存放元素
                for i in curobjs:
                    factdict[k].append(i)
            #判断此屏中是否有预期的值
            #根据列表长度
            lstlen = len(curobjs)
            fact_match_num = 0
            for index in xrange(lstlen):
                for key,value in expe.iteritems():
                    curtext = factdict[key][index].text
                    time.sleep(0.5)
                    if curtext == value.upper():
                        fact_match_num = fact_match_num+1
                    else:
                        break
                if expe_match_num == fact_match_num:
                    factdict[key][index].click()
                    return True
            #下滑一屏
            self.swipeDown(obj.driver,obj.driver.get_window_size()['height'])
        return False
    def sys_pre(self,obj,*mainflag,**kargs):
        #obj 是子产品的self对象
        #先判断是否在主页面,如果不在则先进入主页面
        FLAGGET = kargs['get']  #[id,xxxxx,text_field]
        FLAGSET = kargs['set']  #多个三元组组成的列表
        # print "kargs['set']=",kargs['set']
        #如果在当前页面则不需要操作,
        # obj.driver.refresh()
        time.sleep(1)
        print u'开始执行Get操作'
        if self.sys_get(obj,*FLAGGET):
            return True
        if not self.sys_get(obj,*mainflag):
            obj.gotomain()
        #cc
        print u'开始执行Set操作'
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

    def screenshot(self,obj):
        #截图
        filename = self.getFileName()
        obj.driver.save_screenshot(filename)
        return filename
    #获取元素的主颜色
    def getFileName(self):
        tmpdir = os.path.join(path,"tmp")
        timestr="%s.png" %(time.time())
        filename = os.path.join(tmpdir,timestr).replace("\\","/")
        return filename
    def element_picture(self,obj,*elementlst):
        #得到屏幕图片,然后使用坐标截取
        filename = self.screenshot(obj)
        time.sleep(1)
        retlst = []
        elepicfile=[]
        for i in xrange(len(elementlst)):
            s_x,s_y = elementlst[i].location['x'],elementlst[i].location['y']
            width = elementlst[i].size['width']
            height = elementlst[i].size['height']
            image = Image.open(filename)
            elepic = image.crop((s_x,s_y,width+s_x,height+s_y))
            newfile = self.getFileName()
            time.sleep(0.1)
            elepic.save(newfile)
            elepicfile.append(newfile)
        for i in elepicfile:
            if self.getMainColor(i):
               retlst.append("ON")
            else:
               retlst.append("OFF")
            os.remove(i)
        os.remove(filename)
        #删除目录下的所有文件
        return retlst
    def getMainColor(self,filename):  
        #第一步对图片进行裁剪  
        #颜色模式转换，以便输出rgb颜色值
        image = Image.open(filename)
        
        image = image.convert('RGBA')  
        max_score = 0
        dominant_color = 0 
        for count, (r, g, b, a) in image.getcolors(image.size[0] * image.size[1]):  
            # 跳过纯黑色  
            # if a == 0:  
                # continue  
            saturation = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)[1]  
             
            y = min(abs(r * 2104 + g * 4130 + b * 802 + 4096 + 131072) >> 13, 235)  
             
            y = (y - 16.0) / (235 - 16)  
              
            # 忽略高亮色  
            if y > 0.9:  
                continue  
              
            # Calculate the score, preferring highly saturated colors.  
            # Add 0.1 to the saturation so we don't completely ignore grayscale  
            # colors by multiplying the count by zero, but still give them a low  
            # weight.  
            score = (saturation + 0.1) * count  
              
            if score > max_score:
                max_score = score  
                dominant_color = (r, g, b)  
        #如果是97-104-117,则表示为没有被选中
        print dominant_color
        if dominant_color == (97, 107, 114):
            return False
        elif dominant_color == (255, 100, 43):
            return True
        return False
    def adbSendText(self,msg):
        #对msg进行分析,如果msg中有特殊字符,则需要进行特殊处理后进行发送
        cmd = """adb shell  input text "%s" """ % (msg)
        try:
            return os.popen(cmd)
        except Exception,e:
            print e
            return False
    def swipeToElement(self,obj,direction,func,key):
        #向某个方向滑动直到某个元素出现
        dircDict = {"left":self.swipLeft,"right":self.swipRight,"up":self.swipeUp,"down":self.swipeDown}
        moduledict  = obj.cmapdict[func]
        element = moduledict[key]
        for i in range(0,10):
            try:
                print u"开始尝试滑动"
                dircDict[direction](obj.driver,1000)
                if self.getElement(obj,'',*element):
                    return True
            except Exception,e:
                pass
        return False
    def getSize(self,driver):
        x = driver.get_window_size()['width']
        y = driver.get_window_size()['height']
        self.width = x
        self.height = y
        return (x, y)
    def date_time(self,**kargs):
        #objlst 第一个对象为结果对象,后面的设置各个对象完成后和结果对象值value一致就算设置完成
        driver = kargs['driver']    #driver对象
        s_obj = kargs['s_obj']      #select 源对象
        d_obj = kargs['d_obj']      #需要操作的对象
        value = kargs['value']      #预期的值
        splitchr = kargs['split']   #预期分隔符
        number = kargs['number']    #预期循环次数
        index = kargs['index']      #获取预期值字符串的序号
        print "date_time kargs=",kargs
        for x in xrange(number):
            textstr = s_obj.text.split(splitchr)[index]
            # print "x=",x
            # print "textstr=,value=",textstr,value
            if textstr == value:
                break
            else:
                self.element_swipe(driver,d_obj)
                time.sleep(0.7)
        return True
    def element_swipe(self,driver,obj):
        x,y = obj.location['x'],obj.location['y']
        width,height= obj.size['width'],obj.size['height']
        obj.click()
        driver.swipe(x,y,x,y-height/4)
    #屏幕向下滑动
    def swipeDown(self,driver,t):
        l = self.getSize(driver)
        x1 = int(l[0] * 0.5)  #x坐标
        y1 = int(l[1] * 0.75)   #起始y坐标
        y2 = int(l[1] * 0.25)   #终点y坐标
        driver.swipe(x1, y1, x1, y2,t)
    #屏幕向上滑动
    def swipeUp(self,driver,t):
        l = self.getSize(driver)
        x1 = int(l[0] * 0.5)  #x坐标
        y1 = int(l[1] * 0.25)   #起始y坐标
        y2 = int(l[1] * 0.75)   #终点y坐标
        driver.swipe(x1, y1, x1, y2,t)
    #屏幕向右滑动
    def swipRight(self,driver,t):
        l=self.getSize(driver)
        x1=int(l[0]*0.75)
        y1=int(l[1]*0.5)
        x2=int(l[0]*0.05)
        driver.swipe(x1,y1,x2,y1,t)
    #屏幕向左滑动
    def swipLeft(self,driver,t):
        l=self.getSize(driver)
        x1=int(l[0]*0.05)
        y1=int(l[1]*0.5)
        x2=int(l[0]*0.75)
        driver.swipe(x1,y1,x2,y1,t) 
if __name__ == "__main__":
    cc=getCMapDict("Mesh_CMAP.xlsx","Nova")
    print cc['portmap']['rinport']

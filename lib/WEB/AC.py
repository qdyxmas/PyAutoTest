#!/usr/bin/evn python
# -*- coding:utf-8 -*-
#
"""
config dut class
"""

import os
import platform
import re
import time
import subprocess
import sys

# import utils.timetools
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
# from AC_CMap import *
from common import *
from common import BaseWeb as BaseWeb

class AC10(BaseWeb):
    def __init__(self,kargs='{}'):
        init_default_args = {"downdir": "D:\\","lang": "zh-CN","dip":"192.168.0.1","user":"admin","pwd":"123456","flag":"1","dport":"80","pro":"http"}
        kargs = self.init_args(kargs,**init_default_args)
        
        self.prefs = {"download.default_directory":kargs['downdir'],"intl.accept_languages":kargs['lang']}
        # prefs = {"download.default_directory": "D:\\"}
        # prefs = {"intl.accept_languages": "en-US"}
        self.dip = kargs['dip']
        self.user = kargs['user']
        self.pwd = kargs['pwd']
        self.dport = "80"
        self.pro = kargs['pro']
        self.cmapdict = getCMapDict("AC_CMAP.xlsx",self.__class__.__name__)
        self.maindict = self.cmapdict['main']
        if kargs['flag'] == "1":
            self.f_dip = kargs['dip']
            self.f_user = kargs['user']
            self.f_pwd = kargs['pwd']
        self.browser_init()
    def browser_init(self):
        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.add_experimental_option("prefs", self.prefs)
        # driver = webdriver.Chrome(chrome_options=chromeOptions)
        # if hasattr(self,driver):
            
        self.driver = webdriver.Chrome(chrome_options=chromeOptions)
        # self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
        self.login()
        time.sleep(1)
        # self.home(flag=1)
        #跳转到主页上去
    def login(self,kargs='{}'):
        funcname = sys._getframe().f_code.co_name
        
        init_dict = {"user":"admin","pwd":"admin"}
        login_default_dict = {"dip":self.dip,"user":self.user,"pwd":self.pwd,"dport":self.dport,"pro":self.pro}
        
        kargs = self.init_args(kargs,**login_default_dict)
        url = "%s://%s:%s/" %(kargs.pop('pro'),kargs.pop('dip'),kargs.pop('dport'))
        self.driver.get(url)
        #判断是否在主页
        self.SetValue(self,funcname,self.pwd,'pwd')
        self.SetValue(self,funcname,self.user,'user')
        #点击登陆
        self.SetValue(self,funcname,'','submit')
    def home(self,kargs='{}',flag=1):
        funcname = sys._getframe().f_code.co_name
        if flag == 1:
            #直接点击
            self.SetValue(self,funcname,'','tomain')
        else:
            #进行home页面的配置
            pass
    def gotomain(self):
        #1、如果在登陆页面则登陆
        #2、如果在Home页面则进行切换到主页面
        #3、如果在主页面则返回,如果都不在则重新初始化对象登陆
        for x in xrange(3):
            try:
                if self.getobj(self,self.cmapdict['login']['pwd'],''):
                    self.login()
                if self.getobj(self,self.cmapdict['home']['flag'],''):
                    self.home(flag=1)
                if self.getobj(self,self.cmapdict['main']['flag'],''):
                    return True
                else:
                    self.driver.quit()
                    self.browser_init()
                    return True
            except Exception,e:
                print str(e)
                return False
    def closebrowser(self):
        #关闭浏览器
        self.driver.quit()
        return True
    def internet_pppoe(self,kargs='{}'):
        #配置DUT 接入为PPPoE
        #初始化列表中的值为页面上需要操作的值
        funcname = sys._getframe().f_code.co_name
        init_lst =  [['user',''],['pwd',''],['dnsmode',''],['dns1',''],['dns2','']]
        #页面前置 进入到指定配置页面
        predict = {'set':[self.maindict['internet']],'get':self.cmapdict[funcname]['flag']}
        mainflag = self.maindict['flag']
        print u"start 页面前置"
        self.sys_pre(self,*mainflag,**predict)
        kargs = eval(kargs)
        # 
        # 循环配置输入的参数到页面上
        try:
            self.SetValue(self,funcname,'2','type')
            largs = self.init_lstargs(*init_lst,**kargs)
            for key in largs:
                self.SetValue(self,funcname,key[1],key[0])
            #然后点击保存
            self.SetValue(self,funcname,'','submit')
            time.sleep(1)
            return True
        except Exception,e:
            print str(e)
            return False
    def internet_dhcp(self,kargs='{}'):
        #配置DUT DHCP接入
        #先进入到此页面
        funcname = sys._getframe().f_code.co_name
        init_lst =  [['dnsmode',''],['dns1',''],['dns2','']]
        #先进入到当前页面
        predict = {'set':[self.maindict['internet']],'get':self.cmapdict[funcname]['flag']}
        
        mainflag = self.maindict['flag']
        #页面前置
        print u"start 页面前置"
        self.sys_pre(self,*mainflag,**predict)
        kargs = eval(kargs)
        # dnsmode = kargs['dnsmode']
        #选择为Pppoe
        try:
            self.SetValue(self,funcname,'0','type')
            largs = self.init_lstargs(*init_lst,**kargs)
            for key in largs:
                self.SetValue(self,funcname,key[1],key[0])
            #然后点击保存
            self.SetValue(self,funcname,'','submit')
            time.sleep(1)
            return True
        except Exception,e:
            print str(e)
            return False
    def internet_static(self,kargs='{}'):
        #配置DUT 静态接入
        #先进入到此页面
        funcname = sys._getframe().f_code.co_name
        init_lst =  [['ip',''],['mask','255.255.255.0'],['gateway',''],['dns1',''],['dns2','']]
        #先进入到当前页面
        predict = {'set':[self.maindict['internet']],'get':self.cmapdict[funcname]['flag']}
        
        mainflag = self.maindict['flag']
        #页面前置
        print u"start 页面前置"
        self.sys_pre(self,*mainflag,**predict)
        kargs = eval(kargs)
        # dnsmode = kargs['dnsmode']
        #选择为Pppoe
        try:
            self.SetValue(self,funcname,'1','type')
            largs = self.init_lstargs(*init_lst,**kargs)
            for key in largs:
                self.SetValue(self,funcname,key[1],key[0])
            #然后点击保存
            self.SetValue(self,funcname,'','submit')
            time.sleep(1)
            return True
        except Exception,e:
            print str(e)
            return False
    def vpnclient(self,kargs='{}'):
        #配置DUT vpnclient 有iframe
        #先进入到此页面
        funcname = sys._getframe().f_code.co_name
        init_lst =  [['switch','ON'],['type','pptp'],['serip',''],['user',''],['pwd','']]
        #先进入到当前页面
        predict = {'set':[self.maindict['vpn'],self.maindict['vpnclient']],'get':self.cmapdict[funcname]['flag'],'funcname':funcname}
        mainflag = self.maindict['flag']
        #页面前置
        print u"start 页面前置"
        self.sys_pre(self,*mainflag,**predict)
        kargs = eval(kargs)
        try:
            largs = self.init_lstargs(*init_lst,**kargs)
            for key in largs:
                self.SetValue(self,funcname,key[1],key[0])
            #然后点击保存
            self.SetValue(self,funcname,'','submit')
            time.sleep(1)
            return True
        except Exception,e:
            print str(e)
            return False
    def init_args(self,args,**kargs):
        retdict =eval(args)
        for k,v in kargs.iteritems():
            if not retdict.has_key(k):
                retdict[k] = v
        return retdict
    def init_lstargs(self,*args,**kargs):
        retlst = []
        for i in args:
            k,v = i[0],i[1]
            if kargs.has_key(k):
                retlst.append([k,kargs[k]])
        return retlst
if __name__ == '__main__':
    cc = {"dip":"192.168.0.1","user":"admin","pwd":"123456","dport":"80","pro":"http"}
    kc = AC10(str(cc))
    pppoedict = {'user':'123','pwd':'123','dnsmode':'1'}
    dhcpdict = {'dnsmode':'0','dns1':'1.1.1.1','dns2':'2.2.2.2'}
    staticdict = {'ip':'1.1.1.100','mask':'255.255.255.0','gateway':'1.1.1.1','dns1':'1.1.1.1','dns2':'2.2.2.2'}
    vpndict = {'switch':'ON','type':'pptp','serip':'1.1.1.1','user':'123','pwd':'123'}
    # kc.internet_pppoe(str(pppoedict))
    # time.sleep(3)
    # kc.internet_dhcp(str(dhcpdict))
    # kc.internet_static(str(staticdict))
    kc.vpnclient(str(vpndict))
    # kc.login()
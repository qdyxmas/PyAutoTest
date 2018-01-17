#!/usr/bin/python
#coding=utf-8
import requests
import time,io,sys,os,re
import md5
__doc__=u"主要用于配置不同产品和交换机产品的基类"

#主要用于检测tag之间的信息
class A18:
    def __init__(self,**kargs):
        # kargs={"user":"admin","pwd":"admin"}
        #解析把kargs赋值为self对象
        self.user="admin"
        self.pwd="admin"
        self.dip="192.168.0.1"
        self.parser_kargs(**kargs)
        self.session=requests.Session()
        self.config_wireless()
    def parser_kargs(self,**kargs):
        for key,value in kargs.items():
            if key == "smac" or key == "dmac":
                value = ":".join(value.split("-"))
            setattr(self,key,value)
    def sys_login(self):
        data={"username":self.user,'password':self.md5encr(self.pwd)}
        ret=self.session.post("http://%s/login/Auth" %(self.dip),data=data)
        if ret.url.find("main") != -1:
            print u"login suc"
            return True
        else:
            return False
    def md5encr(self,password):
        cc=md5.new()
        cc.update(password)
        return cc.hexdigest()
    def config_wan(self,kargs=None):
        if not kargs or kargs == "static":
            init_args = {"wanType":"1","adslUser":"123","adslPwd":"123","vpnServer":"","vpnUser":"","vpnPwd":"","vpnWanType":"1","dnsAuto":"1","staticIp":"192.168.100.100","mask":"255.255.255.0","gateway":"192.168.100.200", "dns1":"192.168.100.200","dns2":"","module":"wan1", "downSpeedLimit":""}
        elif kargs == "dhcp":
            init_args = {"wanType":"0","adslUser":"123","adslPwd":"123","vpnServer":"","vpnUser":"","vpnPwd":"","vpnWanType":"1","dnsAuto":"1","staticIp":"","mask":"","gateway":"", "dns1":"","dns2":"","module":"wan1", "downSpeedLimit":""}
        elif kargs == "pppoe":
            init_args =  {"wanType":"2","adslUser":"123","adslPwd":"123","vpnServer":"","vpnUser":"","vpnPwd":"","vpnWanType":"1","dnsAuto":"1","staticIp":"","mask":"","gateway":"", "dns1":"","dns2":"","module":"wan1", "downSpeedLimit":""}
        if self.sys_login():
            print "start config_wan"
            url="http://%s/goform/WanParameterSetting?0.10657474784897802" %(self.dip)
            print "url=",url
            ret=self.session.post(url=url,data=init_args)
            if ret.status_code==200:
                time.sleep(3)
                return True
        return False
    def config_wireless(self,kargs=None):
        if not kargs:
            kargs = {"wrlEn":"1","wrlEn_5g":"1","security":"none","security_5g":"none","ssid":"DUT_24G_TEST","ssid_5g":"DUT_5G_TEST","hideSsid":"0","hideSsid_5g":"0","wrlPwd":"","wrlPwd_5g":""}
        else:
            kargs = eval(kargs)
        print "kargs=",kargs
        if  self.sys_login():
            url="http://%s/goform/WifiBasicSet" %(self.dip)
            ret=self.session.post(url=url,data=kargs)
            if ret.status_code==200:
                time.sleep(5)
                return True
        return False
    def config_wireless_24G(self,kargs=None):
        #ssid='' encrypt= WPA2-PSK/AES password
        init_dict = {"wrlEn":"1","wrlEn_5g":"1","security":"none","security_5g":"none","ssid":"DUT_24G_TEST","ssid_5g":"DUT_5G_TEST","hideSsid":"0","hideSsid_5g":"0","wrlPwd":"","wrlPwd_5g":""}
        if kargs:
            kargs = eval(kargs)
            print "kargs=",kargs
            if kargs.has_key('ssid'):
                init_dict['ssid'] = kargs['ssid']
            if kargs.has_key('password'):
                init_dict['wrlPwd'] = kargs['password']
                init_dict['security']='wpawpa2psk'
            return self.config_wireless(str(init_dict))
    def config_wireless_5G(self,kargs=None):
        #ssid='' encrypt= WPA2-PSK/AES password
        init_dict = {"wrlEn":"1","wrlEn_5g":"1","security":"none","security_5g":"none","ssid":"DUT_24G_TEST","ssid_5g":"DUT_5G_TEST","hideSsid":"0","hideSsid_5g":"0","wrlPwd":"","wrlPwd_5g":""}
        if kargs:
            kargs = eval(kargs)
            if kargs.has_key('ssid'):
                init_dict['ssid_5g'] = kargs['ssid']
            if kargs.has_key('password'):
                init_dict['wrlPwd_5g'] = kargs['password']
                init_dict['security_5g']='wpawpa2psk'
            return self.config_wireless(str(init_dict))
    def config_channel(self,kargs=None):
        #初始化配置信道的字典
        init_dict = {"adv_mode":"bgn","adv_channel":"1","adv_band":"40","adv_mode_5g":"ac","adv_channel_5g":"149","adv_band_5g":"80"}
        if kargs:
            kargs = eval(kargs)
            if int(kargs['channels']) >14:
                init_dict['adv_channel_5g'] = kargs['channels']
                init_dict['adv_band_5g'] = kargs['bandwidth']
            else:
                init_dict['adv_channel'] = kargs['channels']
                init_dict['adv_band'] = kargs['bandwidth']
        if  self.sys_login():
            url="http://%s/goform/WifiRadioSet" %(self.dip)
            ret=self.session.post(url=url,data=init_dict)
            if ret.status_code==200:
                time.sleep(6)
                return True
        return False
    def config_apclient(self,**kargs):
        #http://192.168.0.1/goform/WifiExtraSet
        if  self.sys_login():
            url="http://%s/goform/WifiExtraSet" %(self.dip)
            ret=self.session.post(url=url,data=kargs)
            if ret.status_code==200:
                #请求重启DUT
                return config_reboot()
        return False
    def config_wisp(self,**kargs):
        return True
    def config_vpnclient(self,**kargs):
        if  self.sys_login():
            url="http://%s/goform/SetPptpClientCfg" %(self.dip)
            ret=self.session.post(url=url,data=kargs)
            if ret.status_code==200:
                return True
        return False        
    def config_reboot(self):
        url="http://%s/goform/WifiExtraSet" %(self.dip)
    def test(self,kargs=None):
        print "kc_test=",kargs
        return True
A9=A18    
if __name__ == "__main__":
    kc=A18()
    #http://192.168.0.1/goform/WanParameterSetting?0.9382516425730241
    # kc.config_wireless_24G('{"ssid":"DUT_24G_TEST","password":"1234567890"}')
    # kc.config_wireless_5G('{"ssid":"DUT_5G_TEST","password":"1234567890"}')
    kc.config_wan()
    # kc.config_channel('{"channels":"1","bandwidth":"40"}')
    # ac.config_channel(**wifi_chan_dict)
    # ac.config_vpnclient(**vpn_dict)
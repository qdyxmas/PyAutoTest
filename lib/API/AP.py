#!/usr/bin/python
#coding=utf-8
import requests
import time,io,sys,os,re
import md5
import base64
__doc__=u"主要用于配置不同产品和交换机产品的基类"

#主要用于检测tag之间的信息
class W9:
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
        # usertype:user
        # password:MQ==
        # time:2017;10;26;9;10;29
        # username:1
        t = time.localtime()
        now_time = "%s;%s;%s;%s;%s;%s" %(t[0],t[1],t[2],t[3],t[4],t[5])
        data={"usertype":"user","username":self.user,'password':self.base64encr(self.pwd),"time":now_time}
        ret=self.session.post("http://%s/login/Auth" %(self.dip),data=data)
        if ret.url.find("index.asp") != -1:
            print u"login suc"
            return True
        else:
            return False
    def base64encr(self,password):
        return base64.b64encode(password)
    def md5encr(self,password):
        cc=md5.new()
        cc.update(password)
        return cc.hexdigest()
    def config_wan(self,kargs='{}'):
        if self.sys_login():
            url="http://%s/goform/WanParameterSetting?0.10657474784897802" %(self.dip)
            ret=self.session.post(url=url,data=kargs)
            if ret.status_code==200:
                return True
        return False
    def config_wireless(self,kargs=None):
        if not kargs:
            kargs = {'wepKey2': '12345', 'wifiPwd': '12345678', 'enableWireless': '', 'maxClients': '48', 'wepKey4Type': '1', 'wepAuth': 'open', 'secMode': 'wpawpa2psk', 'ssid': 'DUT_24G_TEST', 'radiusServerIp': '', 'cipherType': 'aes+tkip', 'wepKey1Type': '1', 'ssidIndex': '0', 'ssidEncode': 'utf-8', 'apIsolationEn': 'false', 'wepDefaultKey': '1', 'radiusPwd': '12345678', 'wepKey2Type': '1', 'broadcast': '', 'radiusPort': '1812', 'wmfEn': 'true', 'GO': 'wireless_basic.asp', 'wepKey1': '12345', 'ssidEn': 'true', 'wepKey3': '12345', 'wepKey4': '12345', 'wrlRadio': '2.4G', 'probeEn': 'false', 'hideSsid': 'false', 'keyPeriod': '0', 'broadcastSsidEn': 'true', 'radio': '2.4G', 'wepKey3Type': '1'}
        else:
            kargs = eval(kargs)
        if  self.sys_login():
            url="http://%s/goform/setWrlBasicInfo" %(self.dip)
            ret=self.session.post(url=url,data=kargs)
            if ret.status_code==200:
                time.sleep(2)
                return True
        return False
    def config_wireless_24G(self,kargs=None):
        #ssid='' encrypt= WPA2-PSK/AES password
        init_dict = {'wepKey2': '12345', 'wifiPwd': '12345678', 'enableWireless': '', 'maxClients':'48', 'wepKey4Type': '1', 'wepAuth': 'open', 'secMode': 'none', 'ssid': 'DUT_24G_TEST', 'radiusServerIp': '', 'cipherType': 'aes', 'wepKey1Type': '1', 'ssidIndex': '0', 'ssidEncode': 'utf-8', 'apIsolationEn': 'false', 'wepDefaultKey':'1', 'radiusPwd': '', 'wepKey2Type': '1', 'broadcast': '', 'radiusPort': '1812','wmfEn': 'true', 'GO': 'wireless_basic.asp', 'wepKey1': '12345', 'ssidEn': 'true', 'wepKey3': '12345', 'wepKey4': '12345', 'wrlRadio': '2.4G', 'probeEn': 'false', 'hideSsid': 'false', 'keyPeriod': '0', 'broadcastSsidEn': 'true', 'radio': '2.4G', 'wepKey3Type': '1'}
        if kargs:
            kargs = eval(kargs)
            if kargs.has_key('ssid'):
                init_dict['ssid'] = kargs['ssid']
            if kargs.has_key('password'):
                init_dict['wrlPwd'] = kargs['password']
                init_dict['secMode']='wpawpa2psk'
        return self.config_wireless(str(init_dict))
    def config_wireless_5G(self,kargs=None):
        #ssid='' encrypt= WPA2-PSK/AES password
        init_dict = {'wepKey2': '12345', 'wifiPwd': '12345678', 'enableWireless': '', 'maxClients': '48', 'wepKey4Type': '1', 'wepAuth': 'open', 'secMode': 'none', 'ssid': 'DUT_5G_TEST', 'radiusServerIp': '', 'cipherType': 'aes', 'wepKey1Type': '1', 'ssidIndex': '0', 'ssidEncode': 'utf-8', 'apIsolationEn': 'false', 'wepDefaultKey': '1', 'radiusPwd': '12345678', 'wepKey2Type': '1', 'broadcast': '', 'radiusPort': '1812', 'wmfEn': 'true', 'GO': 'wireless_basic_5g.asp', 'wepKey1': '12345', 'ssidEn': 'true', 'wepKey3': '12345', 'wepKey4': '12345', 'wrlRadio': '5G', 'probeEn': 'false', 'hideSsid': 'false', 'keyPeriod': '0', 'broadcastSsidEn': 'true', 'radio': '5G', 'wepKey3Type': '1'}
        if kargs:
            kargs = eval(kargs)
            if kargs.has_key('ssid'):
                init_dict['ssid'] = kargs['ssid']
            if kargs.has_key('password'):
                init_dict['wifiPwd'] = kargs['password']
                init_dict['secMode']='wpawpa2psk'
        return self.config_wireless(str(init_dict))
    def config_channel(self,kargs=None):
        #初始化配置信道的字典
        init_dict_24G = {'channelLockEn': 'false', 'wrlRadio': '0', 'wirelessEn': 'true', 'wmmEn': 'true', 'country': 'CN', 'setPower': 'true', 'txPower': '18', 'Plcp': '1', 'bandwidth': '40', 'extendChannel': 'lower', 'GO': 'wireless_radio.asp', 'radio': '2.4G', 'sgiTx': '1', 'netMode': 'bgn', 'channel': '1', 'ssidIsolationEn': 'false'}
        init_dict_5G = {'channelLockEn': 'false', 'wrlRadio': '1', 'wirelessEn': 'true', 'ssidIsolationEn': 'false', 'country': 'CN', 'setPower': 'true', 'txPower': '17', 'Plcp': '1', 'bandwidth': '80', 'extendChannel': 'lower', 'GO': 'wireless_radio_5g.asp', 'radio': '5G', 'sgiTx': '1', 'netMode': 'ac', 'channel': '36'}
        if kargs:
            kargs = eval(kargs)
            if int(kargs['channels']) >14:
                init_dict = init_dict_5G
            else:
                init_dict = init_dict_24G
            init_dict['channel'] = kargs['channels']
            init_dict['bandwidth'] = kargs['bandwidth']
        if  self.sys_login():
            url="http://%s/goform/setWrlRadioInfo" %(self.dip)
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
if __name__ == "__main__":
    kc=W9()
    #http://192.168.0.1/goform/WanParameterSetting?0.9382516425730241
    kc.config_wireless_24G()
    # kc.config_wireless_24G('{"ssid":"DUT_24G_TESTttt"}')
    kc.config_wireless_5G()
    # kc.config_channel('{"channels":"13","bandwidth":"40"}')
    # kc.config_channel('{"channels":"149","bandwidth":"80"}')
    # ac.config_channel(**wifi_chan_dict)
    # ac.config_vpnclient(**vpn_dict)
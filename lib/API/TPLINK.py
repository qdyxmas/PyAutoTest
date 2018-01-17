#!/usr/bin/env python
#coding=utf8
import requests
import email.utils as eut
import math
import sys
import utils
import demjson
import json
import urllib
import md5
import time
class WAR1200:
    def __init__(self, **kargs):
        self.user="123456"
        self.pwd="123456"
        self.dip="192.168.1.1"
        self.parser_kargs(**kargs)
        self.url = "http://%s" %(self.dip)
        self.cookies = None
        self.token = ""
        self.key = None
        self.headers = {"Accept":"application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding":"gzip, deflate",
        "Accept-Language":"zh-CN,zh;q=0.8",
        "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
        "Host":"%s" %(self.dip),
        "Origin":"http://%s" %(self.dip),
        "Proxy-Connection":"keep-alive",
        "Referer":"http://%s/webpages/login.html" %(self.dip),
        "User-Agent":"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36",
        "X-Requested-With":"XMLHttpRequest"}
        self.s = requests.Session()
    def parser_kargs(self,**kargs):
        for key,value in kargs.items():
            setattr(self,key,str(value))
    def post(self, path, data,headers=None):
        url = '%s/cgi-bin/luci/;stok=%s/%s'%(self.url, self.token, path)
        # print "url=",url
        return self.s.post(url, data=data, cookies=self.cookies,headers=headers)

    def createCode(self):
        data = {
            "method": "get",
        }
        r = self.post("login?form=login", data)
        if r.status_code != 200:
            # print "something went wrong"
            print r.status_code
            print r.text
            exit(-1)

    def resetAdmin(self, time):
        code = utils.random(time, 100000, 999999)

        data = {
            "operation": "write",
            "vercode": code
        }

        json = self.post("login?form=vercode", data).json()
        if json["success"] == True:
            print "Found code %d, admin password reset"%code
            return True
        return False

    def guessCode(self, time):
        if self.resetAdmin(time):
            return True
        else:
            for i in range(time, time+5):
                if self.resetAdmin(i):
                    return True

        return False

    def getDate(self):
        r = requests.get(self.url)
        if r.status_code != 200:
            print "something went wrong"
            print r.status_code
            print r.text
            exit(-1)
        dateStr = r.headers["Date"]

        return eut.mktime_tz(eut.parsedate_tz(dateStr))

    def setUsbSharing(self):
        print "Making sure the sharing account is the default account"
        data = {
            "operation": "write",
            "account": "admin"
        }
        json = self.post("admin/folder_sharing?form=account", data).json()
        assert json["success"]

    def getRsaKey(self):
        # print "Reading RSA key"
        # json = self.post("login?form=login", {"method":"get"}).json()
        # jdata = json.dumps({"method":"get"})
        jdata = {"data":'{"method":"get"}'}
        data = urllib.urlencode(jdata)
        ret_json = self.post("login?form=login",data=data,headers=self.headers)
        # assert json["success"]   
        # print "ret_json.text=",ret_json.text
        datas=demjson.decode(ret_json.text)
        n,e = datas["result"]["password"]
        self.key = utils.pubKey(n,e)
        self.cookies = ret_json.cookies
    def login(self,kargs='{}',expe='{}'):
        if not self.key:
            self.getRsaKey()
        kargs = eval(kargs)
        if not kargs:
            en_password = utils.encrypt(self.key,self.pwd)
            data = {"data":'{"method":"login","params":{"username":"%s","password":"%s"}}'%(self.user,en_password)}
        else:
            en_password = utils.encrypt(self.key,kargs['pwd'])
            data = {"data":'{"method":"login","params":{"username":"%s","password":"%s"}}'%(kargs['user'],en_password)}
        data = urllib.urlencode(data)
        headers={"Host": "%s" %(self.dip),
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "http://%s" %(self.dip), 
        "Proxy-Connection": "keep-alive",
        "Referer": "http://%s/webpages/login.html"  %(self.dip),
        "X-Requested-With": "XMLHttpRequest"}
        r = self.post("login?form=login", data=data,headers=headers)
        jsondata = demjson.decode(r.text)
        # print "jsondata = ",jsondata
        if not kargs:
            self.cookies = r.cookies
            self.token = jsondata["result"]["stok"]
            return True
        else:
            expe=eval(expe)
            for k,v in expe.iteritems():
                if jsondata.has_key(k):
                    if expe[k] != jsondata[k]:
                        return str(jsondata)
                else:
                    return str(jsondata)
            return True

    def login_out(self):
        #退出登陆
        data={'data':'{"method":"set"}'}
        data = urllib.urlencode(data)
        if self.token:
            self.post("admin/system?form=logout",data=data)
    def test_login(self,kargs='{}',expe='{}'):
        #kargs为传入的字典,expe为预期的字典值
        self.login_out()
        
    def createAccount(self, username, password):
        assert len(username) < 16 and ' ' not in username
        assert len(password) < 16 and ' ' not in password

        if not self.key:
            self.getRsaKey()

        data = {
          "operation": "set",
            "new_acc": username,
            "new_pwd": utils.encrypt(self.key, password),
            "cfm_pwd": utils.encrypt(self.key, password)
        }

        # print "Creating user account"
        json = self.post("admin/administration?form=account", data).json()
        assert json["success"]

    def config_wan(self,kargs=None):
        if not kargs:
            kargs = {'data':'{"method":"set","params":{"wan_id":"1","proto":"static","ipaddr":"192.168.100.100","netmask":"255.255.255.0","gateway":"192.168.100.200","s_dns1":"192.168.100.200","s_dns2":"","t_dialtype":"normal","mon":"","fromHour":"","fromMin":"","toHour":"","toMin":"","time1":"","time2":"","time3":"","time4":"","time5":"","time6":"","time7":"","time8":"","time9":"","time10":"","time11":"","time12":"","slots":"","service":"","uplink":"1000000","downlink":"1000000","lcpechointerval":"10","lcpechofailure":"5","mtu":"1500","wanrate":"auto","macmode":"original","macaddr":"20-6B-E7-E6-75-9C","olmode":"auto"}}'}
        else:
            kargs = eval(kargs)
        headers = self.headers
        headers['Referer'] = "http://%s/webpages/index.html" %(self.dip)
        url_path = "admin/interface_wan?form=wanconfig"
        datas = [urllib.urlencode(kargs)]
        if  self.login():
            for data in datas:
                ret=self.post(url_path,data=data,headers=headers)
            jsondata = demjson.decode(ret.text)
            if jsondata['error_code'] == '0':
                return True
        return False
    def config_wireless(self,kargs=None):
        if not kargs:
            kargs = {'data':'{"method":"set","params":{"radio_id":0,"enable":"on","ssid":"DUT_24G_TEST","ssid_encode":"0","sta_isolation":"off","broadcast":"off","sec_type":"0"}}'}
        else:
            kargs = eval(kargs)
        kargs2= {'data':'{"method":"set","params":{"radio_id":1,"enable":"on","ssid":"DUT_5G_TEST","ssid_encode":"0","sta_isolation":"off","broadcast":"off","sec_type":"0"}}'}
        headers = self.headers
        headers['Referer'] = "http://%s/webpages/index.html" %(self.dip)
        url_path = "admin/wlan_basic?form=basic"
        datas = [urllib.urlencode(kargs2),urllib.urlencode(kargs)]
        if  self.login():
            for data in datas:
                ret=self.post(url_path,data=data,headers=headers)
            jsondata = demjson.decode(ret.text)
            if jsondata['error_code'] == '0':
                return True
        return False
    def config_wireless_5G(self,kargs=None):
        if kargs:
            kargs = eval(kargs)
        else:
            kargs = {'ssid':'DUT_5G_TEST'}
        headers = self.headers
        headers['Referer'] = "http://%s/webpages/index.html" %(self.dip)
        url_path = "admin/wlan_basic?form=basic"
        init_dict={}
        if kargs.has_key('ssid') and kargs.has_key('password'):
            init_dict['data'] = '{"method":"set","params":{"radio_id":1,"enable":"on","ssid":"%s","ssid_encode":"0","sta_isolation":"off","broadcast":"off","sec_type":"1","psk_auth_type":"0","psk_sec_alg":"0","psk_pwd":"%s","psk_update_period":"86400"}}' %(kargs['ssid'],kargs['password'])
        else:
            init_dict['data']='{"method":"set","params":{"radio_id":1,"enable":"on","ssid":"%s","ssid_encode":"0","sta_isolation":"off","broadcast":"off","sec_type":"0"}}' %(kargs['ssid'])
        datas = urllib.urlencode(init_dict)
        if  self.login():
            ret=self.post(url_path,data=datas,headers=headers)
            jsondata = demjson.decode(ret.text)
            if jsondata['error_code'] == '0':
                return True
        return False
    def config_wireless_24G(self,kargs=None):
        if kargs:
            kargs = eval(kargs)
        else:
            kargs = {'ssid':'DUT_24G_TEST'}
        headers = self.headers
        headers['Referer'] = "http://%s/webpages/index.html" %(self.dip)
        url_path = "admin/wlan_basic?form=basic"
        init_dict={}
        if kargs.has_key('ssid') and kargs.has_key('password'):
            init_dict['data'] = '{"method":"set","params":{"radio_id":0,"enable":"on","ssid":"%s","ssid_encode":"0","sta_isolation":"off","broadcast":"off","sec_type":"1","psk_auth_type":"0","psk_sec_alg":"0","psk_pwd":"%s","psk_update_period":"86400"}}' %(kargs['ssid'],kargs['password'])
        else:
            init_dict['data']='{"method":"set","params":{"radio_id":0,"enable":"on","ssid":"%s","ssid_encode":"0","sta_isolation":"off","broadcast":"off","sec_type":"0"}}' %(kargs['ssid'])
        datas = urllib.urlencode(init_dict)
        if  self.login():
            ret=self.post(url_path,data=datas,headers=headers)
            jsondata = demjson.decode(ret.text)
            if jsondata['error_code'] == '0':
                return True
        return False
    def config_channel(self,kargs=None):
        init_dict = {'data':'{"method":"set","params":{"radio_id":"0","channel":"1","hwmode":"4","htmode":"2","txpower":"2","beacon":"100","wmm":"on"}}'}
        bw_dict = {"80":"3","40":"2","20":"1","Auto":"0"}
        if kargs:
            kargs = eval(kargs)
            if int(kargs['channels']) >14:
                init_dict['data'] = '{"method":"set","params":{"radio_id":"1","channel":"%s","hwmode":"3","htmode":"%s","txpower":"2","beacon":"100","wmm":"on"}}' %(kargs['channels'],bw_dict[kargs['bandwidth']])
            else:
                init_dict['data'] = '{"method":"set","params":{"radio_id":"0","channel":"%s","hwmode":"4","htmode":"%s","txpower":"2","beacon":"100","wmm":"on"}}' %(kargs['channels'],bw_dict[kargs['bandwidth']])
        headers = self.headers
        headers['Referer'] = "http://%s/webpages/index.html" %(self.dip)
        url_path = "admin/wlan_advanced?form=adv"
        datas = urllib.urlencode(init_dict)
        if  self.login():
            ret=self.post(url_path,data=datas,headers=headers)
            jsondata = demjson.decode(ret.text)
            if jsondata['error_code'] == '0':
                return True
        return False
#
class AP900I:
    def __init__(self,**kargs):
        self.user = "admin"
        self.password = "123456"
        self.dip = "192.168.0.1"
        self.parser_kargs(**kargs)
        self.s = requests.Session()
        self.login_flag = 0
    def parser_kargs(self,**kargs):
        for key,value in kargs.items():
            setattr(self,key,str(value))
    def getcookies(self,**headers):
        # http://192.168.1.254/data/version.json?_dc=1509346608105&id=10
        now = "%s" %(int(time.time()*1000))
        url = "http://%s/data/version.json?_dc=%s&option=timeout" %(self.dip,now)
        req = self.s.get(url,headers=headers)
        if req.cookies.values():
            self.cookies =  req.cookies
    def logout(self):
        #登陆之前先退出登陆一次
        now = "%s" %(int(time.time()*1000))
        url="http://%s/data/version.json?_dc=%s&option=logout" %(self.dip,now)
        req = self.s.get(url)
        return True
    def login(self):
        headers={'Origin': 'http://%s' %(self.dip), 'Accept-Language': 'zh-CN,zh;q=0.9', 'Accept-Encoding': 'gzip, deflate', 'X-Requested-With': 'XMLHttpRequest', 'Host': self.dip, 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36', 'Connection': 'keep-alive','Referer': 'http://%s/' %(self.dip), 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        #登陆JS在app.js代码smb.user.doLogin中
        #1、现货去Cookies的值 c0a8012100015303
        #2、对Password进行MD5加密 md5("123456")=e10adc3949ba59abbe56e057f20f883e
        #md5("E10ADC3949BA59ABBE56E057F20F883E:c0a8012100015303")
        #D30659729F3B82BFA2933933FEB3EDF4
        #3、把加密的MD5转换成大小在加上Cookies值进行MD5
        #
        #3、然后设置encoded为 用户名:password加密
        #第一步获取Cookies值
        # if self.login_flag:
            # return True
        #每次登陆之前先退出登陆一次
        self.getcookies(**headers)
        cookies = self.cookies.values()[0]
        print "cookies=",cookies
        url = "http://%s/data/version.json" %(self.dip)
        en_password  = self.encprypt(cookies)
        data = {"nonce":cookies,"encoded":"%s:%s" %(self.user,en_password)}
        #解析结果值
        for i in range(0,3):
            req = self.s.post(url,data=data,headers=headers,cookies=self.cookies)
            print "req.text=",req.text
            if not req.text:
                return True
            jsondata = demjson.decode(req.text)
            #先判断是否为首次登陆
            if jsondata.has_key('status'):
                if jsondata['status'] == 0:
                    return True
                elif jsondata['status'] == 4:
                    return self.continue_login(**headers)
        return False
    def continue_login(self,**headers):
        now = "%s" %(int(time.time()*1000))
        url="http://%s/data/loginConfirm.json?_dc=%s" %(self.dip,now)
        cc=self.s.get(url,headers=headers,cookies=self.cookies)
        jsondata = demjson.decode(cc.text)
        print "jsondata=",jsondata
        if cc.status_code == 200:
            return True
        else:
            return False
    def encprypt(self,cookies):
        tmp = md5.md5()
        tmp.update(self.password)
        cc=tmp.hexdigest().upper()
        cc = cc+":"+cookies
        new_md5 = md5.md5()
        new_md5.update(cc)
        encode_text = new_md5.hexdigest().upper()
        print "encode_text=",encode_text
        return encode_text
    def config_wireless_24G(self,kargs=None):
        init_args = {'enable': 'true', 'ssid': 'DUT_24G_TEST','apIsolation': 'false', 'radioID': '0', 'netType': '1', 'securityMode': '0', 'key': '1', 'codeTypetemp': '0', 'ssidBroadcast': 'true', 'option': 'edit'}
        if kargs:
            kargs = eval(kargs)
        else:
            kargs = {}
        if kargs.has_key("ssid"):
            init_args['ssid'] = kargs['ssid']
        if kargs.has_key("password"):
            init_args['securityMode'] = "3"
            init_args['pskVersion'] = "3"
            init_args['pskEncryption'] = "1"
            init_args['pskPassword'] = kargs['password']
            init_args['pskGroupKeyUpdatePeriod'] = "0"
        return self.config_wireless(**init_args)
    def config_wireless_5G(self,kargs=None):
        init_args = {'enable': 'true', 'ssid': 'DUT_5G_TEST', 'apIsolation': 'false', 'radioID': '1', 'netType': '1', 'securityMode': '0', 'key': '1', 'codeTypetemp': '0', 'ssidBroadcast': 'true', 'option': 'edit'}
        if kargs:
            kargs = eval(kargs)
        else:
            kargs = {}
        if kargs.has_key("ssid"):
            init_args['ssid'] = kargs['ssid']
        if kargs.has_key("password"):
            init_args['securityMode'] = "3"
            init_args['pskVersion'] = "3"
            init_args['pskEncryption'] = "1"
            init_args['pskPassword'] = kargs['password']
            init_args['pskGroupKeyUpdatePeriod'] = "0"
        return self.config_wireless(**init_args)
    def config_wireless(self,**kargs):
        headers= {'Origin': 'http://%s' %(self.dip), 'Accept-Language': 'zh-CN,zh;q=0.9', 'Accept-Encoding': 'gzip, deflate', 'X-Requested-With': 'XMLHttpRequest', 'Host': self.dip, 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36', 'Connection': 'keep-alive',  'Referer': 'http://%s/'  %(self.dip), 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        url = "http://%s/data/multiSsid.json" %(self.dip)
        if self.login():
            ret = self.s.post(url,headers=headers,data=kargs,cookies = self.cookies)
            jsondata = demjson.decode(ret.text)
            print "jsondata=",jsondata
            if jsondata['success'] == True:
                self.SaveCfg(**headers)
                return True
        return False
    def config_channel(self,kargs=None):
        headers= {'Origin': 'http://%s' %(self.dip), 'Accept-Language': 'zh-CN,zh;q=0.9', 'Accept-Encoding': 'gzip, deflate', 'X-Requested-With': 'XMLHttpRequest', 'Host': self.dip, 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36', 'Connection': 'keep-alive',  'Referer': 'http://%s/'  %(self.dip), 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        init_args = {'maxRadioClientNum': '100', 'channelWidth': '5', 'dcsTimerInterval': '8', 'reSelectChannel': '0', 'region': '156', 'transPowerValue': '22', 'radioID': '1', 'dcsChanUseThresh': '50', 'enableWmm': 'true', 'beaconInterval': '100', 'transPower': '22', 'mode': '8', 'dcsEnable': '1', 'dcsChSwitchThresh': '20', 'channel': '1'}
        channel_dict = {"36":"1","40":"2","44":"3","48":"4","149":"5","153":"6","157":"7","161":"8","165":"9"}
        if kargs:
            kargs = eval(kargs)
        else:
            kargs = {}
        band_dict = {"20":"2","40":"3",'80':'5'}
        if kargs.has_key("channels"):
            if int(kargs['channels'])<36:
                return self.config_24g_channel(**kargs)
        init_args['channel'] = channel_dict[kargs['channels']]
        init_args['channelWidth'] = band_dict[kargs['bandwidth']]
        urllist = ["http://%s/data/tdma.json" %(self.dip),"http://%s/data/wirelessAdv.json" %(self.dip)]
        if self.login():
            for url in urllist:
                ret = self.s.post(url,headers=headers,data=init_args,cookies = self.cookies)
                if init_args.has_key("reSelectChannel"):
                    init_args.pop('reSelectChannel')
            jsondata = demjson.decode(ret.text)
            print "jsondata=",jsondata
            if jsondata.has_key('errCode'):
                if jsondata['errCode'] == 0:
                    self.SaveCfg(**headers)
                    return True
            # self.SaveCfg(**headers)
        return False
    def config_24g_channel(self,**kargs):
        headers= {'Origin': 'http://%s' %(self.dip), 'Accept-Language': 'zh-CN,zh;q=0.9', 'Accept-Encoding': 'gzip, deflate', 'X-Requested-With': 'XMLHttpRequest', 'Host': self.dip, 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36', 'Connection': 'keep-alive',  'Referer': 'http://%s/'  %(self.dip), 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        init_args = {'maxRadioClientNum': '100', 'channelWidth': '3', 'dcsTimerInterval': '8', 'reSelectChannel': '0', 'region': '156', 'transPowerValue': '20', 'radioID': '0', 'dcsChanUseThresh': '50', 'enableWmm': 'true', 'beaconInterval': '100', 'transPower': '20', 'mode': '4', 'dcsEnable': '1', 'dcsChSwitchThresh': '20', 'apIsolationEnable': 'false', 'channel': '1'}
        band_dict = {"20":"2","40":"3"}
        init_args['channel'] = kargs['channels']
        init_args['channelWidth'] = band_dict[kargs['bandwidth']]
        urllist = ["http://%s/data/tdma.json" %(self.dip),"http://%s/data/wirelessAdv.json" %(self.dip)]
        if self.login():
            for url in urllist:
                ret = self.s.post(url,headers=headers,data=init_args,cookies = self.cookies)
                if init_args.has_key("reSelectChannel"):
                    init_args.pop('reSelectChannel')
            jsondata = demjson.decode(ret.text)
            print "jsondata=",jsondata
            if jsondata.has_key('errCode'):
                if jsondata['errCode'] == 0:
                    self.SaveCfg(**headers)
                    return True
        return False
    def SaveCfg(self,**headers):
        now = "%s" %(int(time.time()*1000))
        url = "http://%s/data/saveChanges.json?_dc=%s" %(self.dip,now)
        ret = self.s.get(url,headers=headers,cookies = self.cookies)
        jsondata = demjson.decode(ret.text)
        if jsondata['success'] == True:
            # self.logout()
            return True
        else:
            return False
if __name__ == "__main__":
    kargs = {'user':'admin','pwd':'123456','dip':'192.168.0.1'}
    tp = AP900I(**kargs)
    # tp.login()
    # tp.reset()
    # tp.login("123456", "123456")
    c1= '{"ssid":"DUT_24G_TEST","password":"1234567890"}'
    c2= '{"ssid":"DUT_5G_TEST","password":"1234567890"}'
    # tp.config_wireless_24G(c1)
    # tp.config_wireless_5G(c2)
    c3='{"channels":"10","bandwidth":"40"}'
    tp.config_channel(c3)   
    # tp.config_wan()
    c4='{"channels":"36","bandwidth":"20"}'
    tp.config_channel(c4)
    # tp.config_channel(c1)
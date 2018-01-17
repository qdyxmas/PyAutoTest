#!/usr/bin/python
#coding=utf-8
import time,io,sys,os,re
import serial
from socket import *
from telnetlib import Telnet
import paramiko
import subprocess
try: 
    import xml.etree.cElementTree as ET 
except ImportError: 
    import xml.etree.ElementTree as ET 
class ktClass(object):
    def __init__(self,type="ssh",host="192.168.20.2",username="root",password="tendatest",**kargs):
        self.host = host
        self.username = username
        self.password = password
        self.rootdir = "/var/tendatest/TDT"
        if type == "telnet":
            self.t = self.telnet_init()
            self.type = "telnet"
        elif type == "ssh":
            self.t = self.ssh_init()
            self.type = "ssh"
        elif type.startswith("com"):
            self.t = self.serial_init(**kargs)
            self.type = "com"
        elif  type == "adb":
            self.type = "adb"
        self.login()
    def telnet_init(self,**kargs):
        t=Telnet()
        t.open(host=self.host, port=23)
        return t
    def serial_init(self,**kargs):
        init_kargs = {}
        init_kargs['brate']= self.parserdict("brate","115200",**kargs)
        init_kargs['port']=self.parserdict('port',"COM1",**kargs)
        s = serial.Serial(port=init_kargs['port'], baudrate=init_kargs['brate'], bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=None, xonxoff=1, rtscts=0, writeTimeout=None, dsrdtr=None)
        return s
    def ssh_init(self,**kargs):
        s=paramiko.SSHClient() 
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
        s.connect(hostname=self.host,username=self.username,password=self.password,allow_agent=True)
        return s
        
    def adb_init(self,**kargs):
        return 
    def shell(self, args):
        """
        执行adb shell命令
        :param args:参数
        :return:
        """
        cmd = """adb shell  su -c '%s' """ % (str(args))
        print "cmd=",cmd
        return os.popen(cmd)
    def adb_wifi(self, power):
        """
        开启/关闭wifi
        pass: 需要root权限
        :return:
        """
        if not self.root():
            print('The device not root.')
            return
        if power:
            self.shell('su -c svc wifi enable').read().strip()
        else:
            self.shell('su -c svc wifi disable').read().strip()
    def adb_wifi_config(self,ssid,password):
        if password:
            network = """network={
            ssid="%s"
            psk="%s"
            key_mgmt=WPA-PSK
            priority=1
        }
        """ %(ssid,password)
        else:
            network = """network={
            ssid="%s"
            key_mgmt=WPA-PSK
            priority=1
        }
        """ %(ssid)
        cmdlist = ["busybox sed -i ':1;N;$ s#network={.*}##;b1' /data/misc/wifi/wpa_supplicant.conf"]
        cmdlist.append("""busybox echo '%s' >>/data/misc/wifi/wpa_supplicant.conf""" %(network))
        cmdlist.append("busybox killall wpa_supplicant")
        cmdlist.append("svc wifi disable")
        cmdlist.append("svc wifi enable")
        cmdlist.append("exit")
        pipe = subprocess.Popen("adb shell su root", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        code = pipe.communicate("\n".join(cmdlist) + "\n")
    def setIp(self,kargs='{}'):
        #初始默认字典
        init_default_dict = {"iface":"eth1","ip":"","mask":"","gateway":"","dns":"","mac":"","mtu":""}
        #命令行参数字典
        cfg_opt_dict = {"iface":"eth1","ip":"","mask":"netmask ","mac":"hw ether ","mtu":"mtu "}
        opt_dict = {"iface":"eth1","ip":"","mask":"netmask ","mac":"hw ether ","mtu":"mtu "}
        
        kargs = self.init_args(kargs,**init_default_dict)
        for k,v in cfg_opt_dict.iteritems():
            if v.endswith(" "):
                cfg_opt_dict[k]=v+kargs[k]
            else:
                cfg_opt_dict[k]=kargs[k]
        print "cfg_opt_dict=",cfg_opt_dict
        cmd = ["ifconfig %s" %(kargs['iface'])]
        for k,v in cfg_opt_dict.iteritems():
            if v != opt_dict[k]:
                cmd.append(v)
        self.sendCmd(" ".join(cmd))
        if kargs['gateway']:
            self.sendCmd("ip route replace default via %s dev %s" %(kargs['gateway'],kargs['iface']))
        if kargs['dns']:
            self.sendCmd("""echo #>/etc/resolv.conf""")
            dnslist = kargs['dns'].split(",")
            for dns in dnslist:
                self.sendCmd("""echo "nameserver %s" >>/etc/resolv.conf """ %(dns))
        return True
    def getIp(self,kargs='{}'):
        init_default_dict = {"iface":"eth1","ip":"","mask":"","gateway":"","dns":"","mac":"","mtu":"","dmac":""}
        kargs=eval(kargs)
        
        retdict = {"iface":kargs['iface']}
        ret = self.sendCmd("ifconfig %s" %(kargs['iface']))
        macinfo = re.findall("(HWaddr.*)",ret)
        ipinfo = re.findall("(inet addr:[0-9.]+)",ret)
        maskinfo = re.findall("(Mask:[0-9.]+)",ret)
        mtuinfo = re.findall("(MTU:[0-9]+)",ret)
        if macinfo:
            retdict['mac'] = macinfo[0].strip().split(" ")[-1]
        if ipinfo:
            retdict['ip'] = ipinfo[0].strip().split(":")[-1]
        if maskinfo:
            retdict['mask'] = maskinfo[0].strip().split(":")[-1]
        if mtuinfo:
            retdict['mtu'] = mtuinfo[0].strip().split(":")[-1]
        ret = self.sendCmd("route|grep default")
        gwinfo = re.findall(r"default\s+[0-9.]+",ret)
        if gwinfo:
            retdict['gateway']=re.split("\s+",gwinfo[0])[-1]
        if retdict.has_key("gateway"):
            ret = self.sendCmd("cat /proc/net/arp|grep %s" %(retdict['gateway']))
            if ret:
                retdict['gmac'] = re.split("\s+",ret)[3]
        # for k,v in retdict.iteritems():
            # if kargs.has_key(k):
                # kargs[k] = v
        return retdict
    def pppoeSerCfg(self,kargs='{}'):
        u"""
            配置Pppoe服务器函数
            auth:ppp认证方式
            user:拨号时用户名
            pwd:拨号时密码
        """
        init_default_dict = {"auth":"chap","user":["tenda"],"pwd":["tenda"],"lip":"10.10.10.1","rip":"10.10.10.10","num":"1","iface":"eth1","padot":"0","dns":"202.96.134.133,202.96.128.86","mtu":"","mru":"","mppe":"","servername":"","repadr":"","mode":"add"}
        pppoe_options_dict = {"auth":"-auth ","dns":"--dns ","mtu":"--mtu ","mru":"-mru ","mppe":"--mppe "}
        init_pppoe_options_dict = {"auth":"-auth ","dns":"--dns ","mtu":"--mtu ","mru":"-mru ","mppe":"--mppe "}
        
        pppoeserver_options_dict = {"lip":"-L ","rip":"-R ","num":"-N ","iface":"-I ","padot":"-t ","servername":"-S ","repadr":"-a"}
        init_pppoeserver_options_dict = {"lip":"-L ","rip":"-R ","num":"-N ","iface":"-I ","padot":"-t ","servername":"-S ","repadr":""}
        kargs = self.init_args(kargs,**init_default_dict)
        if kargs['mode'] == "add":
            self.sendCmd("""echo -e '#'> /etc/ppp/chap-secrets""")
            self.sendCmd("""echo -e '#'> /etc/ppp/pap-secrets""")
        for index,value in enumerate(kargs['user']):
            self.sendCmd("""echo -e '"%s" * "%s" *'>> /etc/ppp/chap-secrets""" %(value,kargs['pwd'][index]))
            self.sendCmd("""echo -e '"%s" * "%s" *'>> /etc/ppp/pap-secrets"""%(value,kargs['pwd'][index]))
        
        #处理pppoe-config参数
        for k,v in pppoe_options_dict.iteritems():
            pppoe_options_dict[k] = v+kargs[k]
        cmd_pppoeconf = ["%s/script/config_PppoeSerCfg.sh" %(self.rootdir)]
        for k,v in pppoe_options_dict.iteritems():
            if v != init_pppoe_options_dict[k]:
                if k == 'dns':
                    dnslst = v.strip("--dns ").split(",")
                    for dns in dnslst:
                        cmd_pppoeconf.append("--dns "+dns)
                else:
                    cmd_pppoeconf.append(v)
        self.sendCmd(" ".join(cmd_pppoeconf))
        
        #处理pppoe-server参数
        for k,v in pppoeserver_options_dict.iteritems():
            if k == "repadr":
                if kargs[k] != "off":
                    pppoeserver_options_dict[k]=''
            else:
                pppoeserver_options_dict[k]=v+kargs[k]
        cmd_pppoeserver = ["%s/bin/pppoe-server" %(self.rootdir)]
        for k,v in pppoeserver_options_dict.iteritems():
            if v != init_pppoeserver_options_dict[k]:
                cmd_pppoeserver.append(v)
        self.sendCmd(" ".join(cmd_pppoeserver))
        #开启pppoe-server服务器
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax | grep pppoe-server | grep -v grep")
            if re.search("pppoe-server",ret):
                return True
        return False
    def pptpSerCfg(self,kargs='{}'):
        #rip 21.1.1.100或者21.1.1.100-200
        init_default_dict = {"auth":"chap","user":["tenda"],"pwd":["tenda"],"lip":"21.1.1.1","rip":"21.1.1.100","iface":"eth1","dns":"202.96.134.133,202.96.128.86",'cf':"/etc/pptpd.conf","pptpopt":"/etc/ppp/options.pptpd","mppe":"","mode":"add","mtu":"","mru":""}
        pptp_options_dict = {"auth":"-auth ","dns":"--dns ","mtu":"--mtu ","mru":"-mru ","mppe":"--mppe ","lip":"--localip ","rip":"--remoteip ","cf":"-o ","pptpopt":" --pppopt "}
        init_pptp_options_dict = {"auth":"-auth ","dns":"--dns ","mtu":"--mtu ","mru":"-mru ","mppe":"--mppe ","lip":"--localip ","rip":"--remoteip ","cf":"-o ","pptpopt":" --pppopt "}
        
        kargs = self.init_args(kargs,**init_default_dict)
        if kargs['mode'] == "add":
            self.sendCmd("""echo -e '#'> /etc/ppp/chap-secrets""")
            self.sendCmd("""echo -e '#'> /etc/ppp/pap-secrets""")
        for index,value in enumerate(kargs['user']):
            self.sendCmd("""echo -e '"%s" * "%s" *'>> /etc/ppp/chap-secrets""" %(value,kargs['pwd'][index]))
            self.sendCmd("""echo -e '"%s" * "%s" *'>> /etc/ppp/pap-secrets"""%(value,kargs['pwd'][index]))
        #配置pptp参数
        for k,v in pptp_options_dict.iteritems():
            pptp_options_dict[k] = v+kargs[k]
        cmd_pptpconf = ["%s/script/config_PptpSerCfg.sh" %(self.rootdir)]
        for k,v in pptp_options_dict.iteritems():
            if v != init_pptp_options_dict[k]:
                if k == 'dns':
                    dnslst = v.strip("--dns ").split(",")
                    for dns in dnslst:
                        cmd_pptpconf.append("--dns "+dns)
                else:
                    cmd_pptpconf.append(v)
        self.sendCmd(" ".join(cmd_pptpconf))
        #开启pptp服务器
        self.sendCmd("%s/bin/pptpd -c %s -l 0.0.0.0" %(self.rootdir,kargs['cf']))
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax|grep pptpd|grep -v grep")
            if re.search(r"pptpd",ret):
                return True
        return False
    def l2tpSerCfg(self,kargs='{}'):
        #rip 21.1.1.100或者21.1.1.100,21.1.1.200
        init_default_dict = {"auth":"chap","user":["tenda"],"pwd":["tenda"],"lip":"22.1.1.1","rip":"22.1.1.100","iface":"eth1","dns":"202.96.134.133,202.96.128.86",'cf':"/etc/xl2tpd/xl2tpd.conf","pptpopt":"/etc/ppp/options.xl2tpd","mppe":"","mode":"add","mtu":"","mru":""}
        l2tp_options_dict = {"auth":"-auth ","dns":"--dns ","mtu":"--mtu ","mru":"-mru ","mppe":"--mppe ","lip":"--localip ","rip":"--remoteip ","cf":"-o ","pptpopt":" --pppopt "}
        init_l2tp_options_dict = {"auth":"-auth ","dns":"--dns ","mtu":"--mtu ","mru":"-mru ","mppe":"--mppe ","lip":"--localip ","rip":"--remoteip ","cf":"-o ","pptpopt":" --pppopt "}
        
        kargs = self.init_args(kargs,**init_default_dict)
        if kargs['mode'] == "add":
            self.sendCmd("""echo -e '#'> /etc/ppp/chap-secrets""")
            self.sendCmd("""echo -e '#'> /etc/ppp/pap-secrets""")
        for index,value in enumerate(kargs['user']):
            self.sendCmd("""echo -e '"%s" * "%s" *'>> /etc/ppp/chap-secrets""" %(value,kargs['pwd'][index]))
            self.sendCmd("""echo -e '"%s" * "%s" *'>> /etc/ppp/pap-secrets"""%(value,kargs['pwd'][index]))
        #配置pptp参数
        for k,v in l2tp_options_dict.iteritems():
            l2tp_options_dict[k] = v+kargs[k]
        cmd_l2tpconf = ["%s/script/config_L2tpSerCfg.sh" %(self.rootdir)]
        for k,v in l2tp_options_dict.iteritems():
            if v != init_l2tp_options_dict[k]:
                if k == 'dns':
                    dnslst = v.strip("--dns ").split(",")
                    for dns in dnslst:
                        cmd_l2tpconf.append("--dns "+dns)
                else:
                    cmd_l2tpconf.append(v)
        self.sendCmd(" ".join(cmd_l2tpconf))
        #开启pptp服务器
        self.sendCmd("%s/bin/xl2tpd -c %s -D >/dev/null 2>&1 &" %(self.rootdir,kargs['cf']))
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax|grep xl2tpd|grep -v grep")
            if re.search(r"xl2tpd",ret):
                return True
        return False
    def ftpSerCfg(self,kargs='{}'):
        init_default_dict = {"port":"21","rootdir":"/var/ftp","cf":"/etc/vsftpd/vsftpd.conf","file":"testfile","data":"ABCDEFGHIJKLMNTEST"}
        ftp_opt_dict =  {"port":"--port ","rootdir":"--rdir ","cf":"-o ","file":"--filename ","data":"--data "}
        init_ftp_opt_dict =  {"port":"--port ","rootdir":"--rdir ","cf":"-o ","file":"--filename ","data":"--data "}
        kargs = self.init_args(kargs,**init_default_dict)
        for k,v in ftp_opt_dict.iteritems():
            ftp_opt_dict[k] = v+kargs[k]
        cmd_ftpopt = ["%s/script/config_FtpSerCfg.sh" %(self.rootdir)]
        for k,v in ftp_opt_dict.iteritems():
            if v != init_ftp_opt_dict[k]:
                cmd_ftpopt.append(v)
        self.sendCmd(" ".join(cmd_ftpopt))
        #开启vsftpd服务器
        self.sendCmd("killall -9 vsftpd")
        self.sendCmd("%s/bin/vsftpd" %(self.rootdir))
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax | grep vsftpd|grep -v grep")
            if re.search("vsftpd",ret):
                return True
        return False
    def httpSerCfg(self,kargs='{}'):
        init_default_dict = {"port":"80","rootdir":"/var/www","cf":"/etc/httpd/conf/httpd.conf","subdir":"index.htm","data":"ABCDEFGHIJKLMNTEST"}
        ftp_opt_dict =  {"port":"--port ","rootdir":"--rdir ","cf":"-o ","subdir":"--subdir ","data":"--data "}
        init_ftp_opt_dict =  {"port":"--port ","rootdir":"--rdir ","cf":"-o ","subdir":"--subdir ","data":"--data "}
        kargs = self.init_args(kargs,**init_default_dict)
        for k,v in ftp_opt_dict.iteritems():
            ftp_opt_dict[k] = v+kargs[k]
        cmd_httpopt = ["%s/script/config_HttpSerCfg.sh" %(self.rootdir)]
        for k,v in ftp_opt_dict.iteritems():
            if v != init_ftp_opt_dict[k]:
                cmd_httpopt.append(v)
        self.sendCmd(" ".join(cmd_httpopt))
        #开启vsftpd服务器
        self.sendCmd("killall -9 httpd")
        self.sendCmd("%s/bin/apachectl -k start" %(self.rootdir))
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax | grep httpd|grep -v grep")
            if re.search("httpd",ret):
                return True
        return False
    def dhcpSerCfg(self,kargs='{}'):
        init_default_dict = {"pool":"","lease":"60","gw":"","dns":"8.8.8.8","mask":"","cf":"/tmp/dhcpd.conf","iface":"eth1","lf":"/var/db/dhcpd.leases","adopt":"","delopt":"","chkopt":"","chklen":"","relet":"","noack":"","mac":"","alert":"","of":"/var/tendatest/TDRouter2/tmp/log_dhcpc.txt","dellog":"0"}
        cfg_option_dict = {"pool":"--iprange ","lease":"--lease ","gw":"--routers ","dns":"--dns ","mask":"--netmask ","cf":"-o "}
        init_cfg_option_dict = {"pool":"--iprange ","lease":"--lease ","gw":"--routers ","dns":"--dns ","mask":"--netmask ","cf":"-o "}
        kargs = self.init_args(kargs,**init_default_dict)
        for k,v in cfg_option_dict.iteritems():
            cfg_option_dict[k]=v+kargs[k]
            
        cmdcfg = ["%s/script/config_DhcpSerCfg.sh" %(self.rootdir)]
        for k,v in cfg_option_dict.iteritems():
            if v != init_cfg_option_dict[k]:
                cmdcfg.append(v)
        self.sendCmd(" ".join(cmdcfg))
        
        cmd_option_dict = {"adopt":"-addop ","delopt":"-delop ","chkopt":"-checkop ","chklen":"-checklen ","relet":"-relet ","noack":"-noack ","mac":"-mac ","alert":"-alarm "}
        init_cmd_option_dict = {"adopt":"-addop ","delopt":"-delop ","chkopt":"-checkop ","chklen":"-checklen ","relet":"-relet ","noack":"-noack ","mac":"-mac ","alert":"-alarm "}
        cmd = ["%s/bin/dhcpd -cf %s -lf %s %s" %(self.rootdir,kargs['cf'],kargs['lf'],kargs['iface'])]
        for k,v in cmd_option_dict.iteritems():
            cmd_option_dict[k] = v+kargs[k]
            if cmd_option_dict[k] != init_cmd_option_dict[k]:
                cmd.append(cmd_option_dict[k])
        self.sendCmd(" ".join(cmd))
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax |grep dhcpd|grep -v grep")
            if re.search("dhcpd",ret):
                return True
        return False
    def dnsSerCfg(self,kargs='{}'):
        init_default_dict = {"dns":"","urlip":"","cf":"/var/named"}
        kargs = self.init_args(kargs,**init_default_dict)
        cmdopt = ["%s/script/config_DnsSerCfg.sh -d %s" %(self.rootdir,kargs['cf'])]
        dnslst = kargs['dns'].split(",")
        for index,dns in enumerate(dnslst):
            cmdopt.append("--s%s %s" %(index+1,dns))
        for url in kargs['urlip'].split(","):
            cmdopt.append("--url %s" %(url))
        self.sendCmd(" ".join (cmdopt))
        self.sendCmd("%s/bin/named -c %s/named.conf" %(self.rootdir,kargs['cf']))
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax | grep named |grep -v grep")
            if re.search("named",ret):
                return True
        return False
    def tftpSerCfg(self,kargs='{}'):
        init_default_dict = {"rootdir":"/var/lib/tftpboot","downfile":"tftptest","data":"tftptestfile"}
        kargs = self.init_args(kargs,**init_default_dict)
        self.sendCmd('echo "%s"> %s/%s' %(kargs['data'],kargs['rootdir'],kargs['downfile']))
        self.sendCmd("service xinetd start")
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("netstat -anlup")
            if re.search("xinetd",ret):
                return True
        return False
    def ntpSerCfg(self,kargs='{}'):
        init_default_dict = {"enable":"1","time":"2014-01-01 00:00:00","cf":"ntp.conf","rf":"/var/run/ntpd.pid"}
        kargs = self.init_args(kargs,**init_default_dict)
        self.sendCmd("date -s '%s'" %(kargs['time']))
        if kargs['enable'] == "1":
            cmd = "%s/bin/ntpd -u ntp:ntp -p %s -g -c %s/conf/%s >/dev/null 2>&1 &" %(self.rootdir,kargs['rf'],self.rootdir,kargs['cf'])
            self.sendCmd(cmd)
        else:
            self.sendCmd("killall -9 ntpd")
            return True
        for x in xrange(5):
            time.sleep(1)
            ret = self.sendCmd("ps ax |grep ntpd|grep -v grep")
            if re.search("ntpd",ret):
                return True
                
        return False
    def pktSend(self,kargs='{}'):
        #flag = 1按需分片 2不允许分片
        init_default_dict = {"dip":"","dport":"60000","pro":"tcp","iface":"","sport":"","sip":"","num":"","size":"","flag":"","loss":0.1,"expemss":"","expe":"pass"}
        option_dict = {"dport":"-p ","iface":"-I ","sport":"-P ","sip":"-i ","num":"-c ","size":"-s ","flag":"-F "}
        init_option_dict = {"dport":"-p ","iface":"-I ","sport":"-P ","sip":"-i ","num":"-c ","size":"-s ","flag":"-F "}
        kargs = self.init_args(kargs,**init_default_dict)
        for k,v in option_dict.iteritems():
            option_dict[k] = v+kargs[k]
        #处理udp或者tcp
        mapdict = {"tcp":"-t ","udp":"-u "}
        cmd_option = ["%s/bin/pksend %s" %(self.rootdir,kargs['dip'])]
        for k,v in option_dict.iteritems():
            if v != init_option_dict[k]:
                cmd_option.append(v)
        cmd = "%s %s" %(" ".join(cmd_option),mapdict[kargs['pro']])
        self.sendCmd("ip route flush cache")
        self.sendCmd("echo 0 >/proc/sys/net/ipv4/tcp_timestamps")
        ret = self.sendCmd(cmd)
        tsret = "fail"
        result = False
        if re.search("ntransmitted",ret):
            retlst =  map(lambda x:float(x),re.findall(r"([0-9]+)",ret))
            # print "retlst=",retlst
            if len(retlst) >=6:
                result = (retlst[0]-retlst[1])/retlst[0] < kargs['loss']
                # print "result=",result
            if kargs['expemss']:
                result = float(kargs['expemss']) == retlst[4] and float(kargs['expemss']) == retlst[5]
        self.sendCmd("echo 1 >/proc/sys/net/ipv4/tcp_timestamps")
        if result:
            tsret = "pass"
        if tsret == kargs['expe']:
            return True
        else:
            return False
    def sshLogin(self,kargs='{}'):
        init_default_dict = {"ip":"","user":"","pwd":"","cmd":"ifconfig","expe":"pass"}
        kargs = self.init_args(kargs,**init_default_dict)
        cmd = "%s/script/sshlogin.sh %s %s %s %s" %(self.rootdir,kargs['user'],kargs['pwd'],kargs['cmd'],kargs['ip'])
        ret = self.sendCmd(cmd)
        result = "pass"
        if re.search("inet addr:%s" %(kargs['ip']),ret):
            result = "pass"
        elif re.search("Connection refused" %(kargs['ip']),ret):
            result = "fail"
        else:
            pass
        if kargs['expe'] == result:
            return True
        else:
            return False
    def telnetLogin(self,kargs='{}'):
        init_default_dict = {"ip":"","user":"","pwd":"","cmd":"ifconfig","expe":"pass"}
        kargs = self.init_args(kargs,**init_default_dict)
        cmd = "%s/script/telnetlogin.sh %s %s %s %s" %(self.rootdir,kargs['user'],kargs['pwd'],kargs['cmd'],kargs['ip'])
        ret = self.sendCmd(cmd)
        result = "pass"
        if re.search("inet addr:%s" %(kargs['ip']),ret):
            result = "pass"
        elif re.search("Connection refused" %(kargs['ip']),ret):
            result = "fail"
        else:
            pass
        if kargs['expe'] == result:
            return True
        else:
            return False
    #tftp 客户端 http客户端 ftp客服端 dhclient pptp客户端 l2tp客户端 pppoe客户端
    def tftpCli(self,kargs='{}'):
        init_default_dict = {"ip":"","port":"69","dfile":"tftptest","lfile":"/tmp/tftptest","data":"tftptestfile","expe":"pass"}
        kargs = self.init_args(kargs,**init_default_dict)
        cmd = "%s/bin/tftp %s %s -c get %s %s" %(self.rootdir,kargs['ip'],kargs['port'],kargs['dfile'],kargs['lfile'])
        self.sendCmd("rm -rf %s" %(kargs['lfile']))
        for x in xrange(3):
            self.sendCmd(cmd)
            time.sleep(2)
            ret = self.sendCmd("cat %s" %(kargs['lfile']))
            if re.search(kargs['data'],ret):
                result = "pass"
            else:
                result = "fail"
            if kargs["expe"] == result:
                return True
        else:
            return False
    def httpCli(self,kargs='{}'):
        init_default_dict = {"url":"","port":"80","dfile":"index.htm","lfile":"/tmp/www","data":"ABCDEFGHIJKLMNTEST","expe":"pass","timeout":"3","reconnum":"3"}
        cft_option_dict = {"url":"--url  ","dfile":"--file ","port":"--port ","timeout":"--timeout ","reconnum":"--reconnum ","lfile":"--outdir "}
        init_cft_option_dict = {"url":"--url  ","dfile":"--file ","port":"--port ","timeout":"--timeout ","reconnum":"--reconnum ","lfile":"--outdir "}
        kargs = self.init_args(kargs,**init_default_dict)
        for k,v in cft_option_dict.iteritems():
            cft_option_dict[k] = v+kargs[k]
        cmd = ["%s/script/http_downfile.sh" %(self.rootdir)]
        for k,v in cft_option_dict.iteritems():
            if v != init_cft_option_dict[k]:
                cmd.append(v)
        for x in xrange(3):
            self.sendCmd("rm -rf %s/%s" %(kargs['lfile'],kargs['dfile']))
            self.sendCmd(" ".join(cmd))
            ret = self.sendCmd("cat %s/%s"%(kargs['lfile'],kargs['dfile']))
            result = "fail"
            if re.search(kargs['data'],ret):
                result = "pass"
            if result == kargs['expe']:
                return True
            time.sleep(1)
        return False
    def ftpCli(self,kargs='{}'):
        init_default_dict = {"ip":"","port":"21","user":"ftp","pwd":"ftp","dfile":"testfile","lfile":"/tmp/ftp","data":"ABCDEFGHIJKLMNTEST","expe":"pass","mode":"0"}
        cft_option_dict = {"ip":"--ip  ","dfile":"--file ","port":"--port ","user":"--user ","pwd":"--passwd ","lfile":"--outdir ","mode":"--mode "}
        init_cft_option_dict = {"ip":"--ip  ","dfile":"--file ","port":"--port ","user":"--user ","pwd":"--passwd ","lfile":"--outdir ","mode":"--mode "}
        kargs = self.init_args(kargs,**init_default_dict)
        for k,v in cft_option_dict.iteritems():
            cft_option_dict[k] = v+kargs[k]
        cmd = ["%s/script/ftp_downfile.sh" %(self.rootdir)]
        for k,v in cft_option_dict.iteritems():
            if v != init_cft_option_dict[k]:
                cmd.append(v)
        for x in xrange(3):
            self.sendCmd("rm -rf %s/%s" %(kargs['lfile'],kargs['dfile']))
            self.sendCmd(" ".join(cmd))
            ret = self.sendCmd("cat %s/%s"%(kargs['lfile'],kargs['dfile']))
            result = "fail"
            if re.search(kargs['data'],ret):
                result = "pass"
            if result == kargs['expe']:
                return True
            time.sleep(1)
        return False
    def pppoeCli(self,kargs='{}'):
        init_default_dict = {"auth":"chap","iface":"eth1","user":"tenda","pwd":"tenda","mppe":"","mode":"add","unit":"1","expe":"pass"}
        
        kargs = self.init_args(kargs,**init_default_dict)
        if kargs['mode'] == "add":
            self.sendCmd("""echo -e '#' > /etc/ppp/chap-secrets""")
            self.sendCmd("""echo -e '#' > /etc/ppp/pap-secrets""")
        self.sendCmd("""echo -e '"%s" * "%s" *' >> /etc/ppp/chap-secrets""" %(kargs['user'],kargs['pwd']))
        self.sendCmd("""echo -e '"%s" * "%s" *' >> /etc/ppp/pap-secrets""" %(kargs['user'],kargs['pwd']))
        #处理认证时参数
        pppoecfg = """ETH=%s
                    USER=%s
                    DNSTYPE=NOCHANGE
                    PEERDNS=no
                    DEFAULTROUTE=yes
                    CONNECT_TIMEOUT=30
                    CONNECT_POLL=2
                    CLAMPMSS=1412
                    LCP_INTERVAL=12
                    LCP_FAILURE=8""" %(kargs['iface'],kargs['user'])
        self.sendCmd("""echo -e '%s' > /etc/ppp/pppoe.conf""" %(pppoecfg))
        #配置/etc/ppp/options参数
        # time.sleep(0.5)
        self.sendCmd("""echo -e "lock" > /etc/ppp/options""")
        self.sendCmd("""echo -e "unit %s" >> /etc/ppp/options""" %(kargs['unit']))
        self.sendCmd("""echo -e "require-%s" >> /etc/ppp/options""" %(kargs['auth']))
        if kargs['mppe']:
            if kargs['mppe'] == "both":
                self.sendCmd("""echo -e "require-mppe" >> /etc/ppp/options""")
            elif kargs['mppe'] == "40" or kargs['mppe'] == "128":
                self.sendCmd("""echo -e "require-mppe-%s" >> /etc/ppp/options"""%(kargs['mppe']))
        
        #开启连接
        cmd = """/usr/sbin/pppd pty "/usr/sbin/pppoe -p .pppoe -I %s -T  -U  -m 1412"    noipdefault noauth default-asyncmap defaultroute hide-password nodetach mtu 1492 mru 1492 noaccomp nodeflate nopcomp novj novjccomp user %s lcp-echo-interval 12 lcp-echo-failure 8 >/dev/null 2>&1 &""" %(kargs['iface'],kargs['user'])
        self.sendCmd(cmd)
        result = "fail"
        for x in xrange(15):
            ret = self.sendCmd("ifconfig")
            if re.search("ppp%s"%(kargs['unit']),ret):
                result = "pass"
                break
            time.sleep(3)
        if kargs['expe'] == result:
            return True
        else:
            return False
    def l2tpCli(self,kargs='{}'):
        init_default_dict = {"desc":"l2tp","ip":"","user":"tenda","pwd":"tenda","auth":"chap","mppe":"","cf":"/etc/xl2tpd/xl2tpd.conf","mode":"add","flag":"1","unit":"1","expe":"pass"}
        kargs = self.init_args(kargs,**init_default_dict)
        if kargs['flag'] == "0":
            self.sendCmd("""echo 'd %s' >/var/run/xl2tpd/l2tp-control""" %(kargs['desc']))
            return True
        if kargs['mode'] == "add":
            self.sendCmd("""echo -e '#' > /etc/ppp/chap-secrets""")
            self.sendCmd("""echo -e '#' > /etc/ppp/pap-secrets""")
        self.sendCmd("""echo -e '"%s" * "%s" *' >> /etc/ppp/chap-secrets""" %(kargs['user'],kargs['pwd']))
        self.sendCmd("""echo -e '"%s" * "%s" *' >> /etc/ppp/pap-secrets""" %(kargs['user'],kargs['pwd']))
        cfg_option_dict = {"desc":"--decr ","ip":"--serip ","user":"--user ","pwd":"--pwd ","auth":"--auth ","mppe":"--mppe ","cf":"-o ","unit":"--unit "}
        cmd = ["%s/script/config_L2tpCliConf.sh" %(self.rootdir)]
        for k,v in cfg_option_dict.iteritems():
            cfg_option_dict[k] = v+kargs[k]
            if v != cfg_option_dict[k]:
                cmd.append(cfg_option_dict[k])
        self.sendCmd(" ".join(cmd))
        result = "fail"
        self.sendCmd("""echo 'c %s' > /var/run/xl2tpd/l2tp-control"""%(kargs['desc']))
        for x in xrange(15):
            ret = self.sendCmd("ifconfig")
            if re.search("ppp%s"%(kargs['unit']),ret):
                result = "pass"
                break
            time.sleep(3)
        if kargs['expe'] == result:
            return True
        else:
            return False
    def pktRecv(self,kargs='{}'):
        init_default_dict = {"sip":"","ipver":"","sport":"60000","pro":"tcp","num":"","size":""}
        option_dict = {"sport":"-P ","num":"-c ","size":"-s "}
        init_option_dict = {"sport":"-P ","num":"-c ","size":"-s "}
        mapdict = {"tcp":"-t","udp":"-u","all":"-u -t"}
        kargs = self.init_args(kargs,**init_default_dict)
        cmd_cfg = ["%s/bin/pkrecv %s" %(self.rootdir,kargs['sip'])]
        print "kargs=",kargs
        for k,v in option_dict.iteritems():
            option_dict[k]=v+kargs[k]
        for k,v in option_dict.iteritems():
            if v != init_option_dict[k]:   
                cmd_cfg.append(v)
        precmd = " ".join(cmd_cfg)
        if kargs['pro'] == "all":
            self.sendCmd("%s -t >/dev/null 2>&1 &" %(precmd))
            self.sendCmd("%s -t >/dev/null 2>&1 &" %(precmd))
        else:
            self.sendCmd("%s %s >/dev/null 2>&1 &" %(precmd,mapdict[kargs['pro']]))
        for x in xrange(4):
            time.sleep(1)
            ret = self.sendCmd("ps ax | grep pkrecv|grep -v grep")
            if re.search("pkrecv",ret):
                return True
        return False
    def upnpMap(self,kargs='{}'):
        init_default_dict = {"lip":"","wport":"9999","lport":"9999","pro":"all"}
        kargs = self.init_args(kargs,**init_default_dict)
        cmd = "%s/bin/upnpc-static -a %s %s %s " %(self.rootdir,kargs['lip'],kargs['lport'],kargs['wport'])
        if kargs['pro'] == "all":
            self.sendCmd(cmd+" tcp")
            self.sendCmd(cmd+" udp")
        else:
            self.sendCmd(cmd+kargs['pro'])
        return True
    def upnpChk(self,kargs='{}'):
        kargs=eval(kargs)
        init_default_dict = {"modelname":"","modelnumber":"","url":"","manufacturer":""}
        
        ret = self.sendCmd("%s/bin/upnpc-static -P" %(self.rootdir))
        urlinfo = re.search("(desc: .*)",ret)
        url = urlinfo.group().split(" ")[-1]
        filename = url.split("/")[-1]
        self.sendCmd("wget %s -P /tmp/" %(url))
        allinfo = self.sendCmd("cat /tmp/%s" %(filename))
        root = ET.fromstring(allinfo)
        factdict = {}
        factdict['friendlyname'] = root[1][1].text
        factdict['manufacturer'] = root[1][2].text
        factdict['modelname'] = root[1][4].text
        factdict['modelnumber'] = root[1][5].text
        factdict['url'] = root[1][-1].text
        for k,v in kargs.iteritems():
            if v != factdict[k]:
                print "keys={%s} expe=%s fact=%s" %(k,v,factdict[k])
                return False
        return True
    def encapPing(self,kargs='{}'):
        init_default_dict = {"dip":"192.168.0.1","iface":"eth1","sip":"","smask":"","smac":"","rip":"","size":"64","num":"5","flood":"1","flag":"0","loss":"10","expe":"pass"}
        
        cfg_option_dict = {"iface":"-I ","sip":"--sip ","smask":"--smask ","smac":"--smac ","rip":"--rip ","size":"-s ","num":"-c "}
        init_cfg_option_dict = {"iface":"-I ","sip":"--sip ","smask":"--smask ","smac":"--smac ","rip":"--rip ","size":"-s ","num":"-c "}
        kargs = self.init_args(kargs,**init_default_dict)
        #第一步先获取得到默认参数
        cmd = ["%s/bin/encapping %s" %(self.rootdir,kargs['dip'])]
        for k,v in cfg_option_dict.iteritems():
            cfg_option_dict[k] = v+kargs[k]
            if cfg_option_dict[k] != init_cfg_option_dict[k]:
                cmd.append(cfg_option_dict[k])
        if kargs['flag'] != "0":
            cmd.append("-F")
        if kargs['flood'] == "1":
            cmd.append("-f")
        ret = self.sendCmd(" ".join(cmd))
        lossper=re.search("([0-9]+%)",ret)
        lossper = float(lossper.group().strip("%"))
        result = "pass"
        if lossper>float(kargs['loss']):
            result = "fail"
        if result == kargs["expe"]:
            return True
        else:
            return False
    def ping(self,kargs='{}'):
        init_default_dict = {"dip":"192.168.0.1","iface":"eth1","size":"64","flood":"0","flag":"0","expe":"pass","maxerr":"10","maxsuc":"5"}
        
        cfg_option_dict = {"iface":"-I ","size":"-s "}
        init_cfg_option_dict = {"iface":"-I ","size":"-s "}
        kargs = self.init_args(kargs,**init_default_dict)
        cmd = ["ping %s -c 1" %(kargs['dip'])]
        for k,v in cfg_option_dict.iteritems():
            cfg_option_dict[k] = v+kargs[k]
            if cfg_option_dict[k] != init_cfg_option_dict[k]:
                cmd.append(cfg_option_dict[k])
        if kargs['flag'] != "0":
            cmd.append(" -M do")
        if kargs['flood'] == "1":
            cmd.append("-f")
        maxerr = int(kargs['maxerr'])
        maxsuc = int(kargs['maxsuc'])
        sumnum = maxerr+maxsuc
        factsuc = 0
        facterr = 0
        result = "fail"
        self.sendCmd("ip route flush cache")
        for x in xrange(sumnum):
            ret = self.sendCmd(" ".join(cmd))
            print ret
            if re.search("ttl=",ret):
                factsuc = factsuc + 1
            else:
                facterr = facterr + 1
            if factsuc >= maxsuc:
                result = "pass"
                break
            time.sleep(0.5)
        if result == kargs["expe"]:
            return True
        else:
            return False
    def dnsInvalid(self,kargs='{}'):
        u"""
            使用iptables对53端口进行过滤
        """
        init_default_dict = {"dns":""}
        kargs = self.init_args(kargs,**init_default_dict)
        if kargs['dns']:
            for dns in kargs['dns'].split(","):
                self.sendCmd("iptables -t filter -A INPUT -s %s -p udp --dport 53 -j DROP"%(dns))
        else:
            self.sendCmd("iptables -t filter -F")
        return True
    def arpSend(self,kargs='{}'):
        u"""arpSend---发送arp数据包"""
        # sip-表示源IP地址 smac-表示源Mac地址 
        # type= 1表示arp请求  2表示相应
        # time  表示发包时间长度 num 表示发包个数
        init_default_dict = {"sip":"","smac":"","dip":"","dmac":"","type":"1","time":"1","num":"1000","macincr":"0","iface":"eth1","expe":"pass"}
        cfg_option_dict = {"sip":"-sip ","dip":"-dip ","smac":"-smac ","dmac":"-dmac ","type":"-type ","num":"-num ","time":"-time "}
        init_cfg_option_dict = {"sip":"-sip ","dip":"-dip ","smac":"-smac ","dmac":"-dmac ","type":"-type ","num":"-num ","time":"-time "}
        kargs = self.init_args(kargs,**init_default_dict)
        cmdlst = ["%s/bin/arpsend " %(self.rootdir)]
        for k,v in cfg_option_dict.iteritems():
            if k in ['smac','dmac']:
                kargs[k] = re.sub("([-:])","",kargs[k])
            cfg_option_dict[k] = v+kargs[k]
            if cfg_option_dict[k] != init_cfg_option_dict[k]:
                cmdlst.append(cfg_option_dict[k])
        if kargs['macincr'] != "0":
            cmdlst.append("-chmac")
        cmdlst.append(kargs['iface'])
        
        self.sendCmd(" ".join(cmdlst))
        return True
    def getTime(self):
        ret = self.sendCmd("""date +"%F %T" """)
        return ret
    def nslookup(self,kargs='{}'):
        init_default_dict = {"url":"","serip":"192.168.0.1","expeip":"","expe":"pass"}
        kargs = self.init_args(kargs,**init_default_dict)
        cmd = "nslookup %s %s" %(kargs['url'],kargs['serip'])
        ret = self.sendCmd(cmd)
        pos  = ret.find("Name:")
        result = "fail"
        if pos != -1:
            fact = re.search("(([0-9]+.){3}([0-9]+))",ret[pos:])
            factip = fact.group()
            if factip == kargs['expeip']:
                result = "pass"
        if result == kargs['expe']:
            return True
        else:
            return False
    def U12Cfg(self,kargs='{}'):
        init_default_dict = {"iface":"wlan0"}
        kargs = self.init_args(kargs,**init_default_dict)
        if password:
            network = """network={
            ssid="%s"
            psk="%s"
            key_mgmt=WPA-PSK
            priority=1
        }
        """ %(ssid,password)
        else:
            network = """network={
            ssid="%s"
            priority=1
        }
        """ %(ssid)
        cmdlist = ["sed -i ':1;N;$ s#network={.*}##;b1' /etc/wpa_supplicant/wpa_supplicant.conf"]
        cmdlist.append("""echo '%s' >> /etc/wpa_supplicant/wpa_supplicant.conf""" %(network))
        cmdlist.append("killall wpa_supplicant")
        cmdlist.append("wpa_supplicant -d -Dwext -iwlan0 -c/etc/wpa_supplicant/wpa_supplicant.conf 2>&1 >>/dev/null &")
        # pipe = subprocess.Popen("adb shell su root", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        for cmd in cmdlist:
            self.sendCmd(cmd)
        return True
        
        
    def packetCapture(self,kargs='{}'):
        #tcpdump开启抓包
        init_default_dict = {"iface":"eth1","filter":"",'result':"/tmp/packet.pcap"}
        kargs = self.init_args(kargs,**init_default_dict)
        
        cmd = "tcpdump -i %s %s -w %s  >/dev/null 2>&1 &"  %(kargs['iface'],kargs['filter'],kargs['result'])
        self.sendCmd("killall -2 tcpdump")
        self.sendCmd(cmd)
        for x in xrange(5):
            ret = self.sendCmd("ps ax | grep -v grep | grep tcpdump")
            if re.search("tcpdump",ret):
                return True
            time.sleep(1)
        return False
    def parserPacket(self,kargs='{}'):
        #tshark解析数据包是否包含字段进行匹配
        #filter = ip.src=1.1.1.1,ip.dst=1.1.1.2
        #num 表示匹配filter的次数
        init_default_dict = {"filter":"",'result':"/tmp/packet.pcap","num":"1",'expe':"pass"}
        kargs = self.init_args(kargs,**init_default_dict)
        retlst = kargs['filter'].split(",")
        keylst = []
        valuelst = ""
        for i in retlst:
            k,v = i.split("=",1)
            keylst.append(k)
            valuelst = valuelst+v+" "
        cmd = ["tshark -r %s -T fields" %(kargs['result'])]
        for key in keylst:
            cmd.append("-e %s" %(key))
        self.sendCmd("killall -2 tcpdump")
        ret = self.sendCmd(" ".join(cmd))
        result = "fail"
        num = int(kargs['num'])
        matchnum = 0
        for i in ret.split("\n"):
            #i表示解析的每一行 只有同一行匹配所有的valuelst即为pass
            factstr = " ".join(re.split("[ \t]+",i))
            if factstr.strip() == valuelst.strip():
                matchnum = matchnum + 1
            if matchnum >= num:
                result = "pass"
                break
        if kargs['expe'] == result:
            return True
        else:
            return False
    def init_args(self,args,**kargs):
        retdict =eval(args)
        for k,v in kargs.iteritems():
            if not retdict.has_key(k):
                retdict[k] = v
        return retdict
    def parserdict(self,key,value,**kargs):
        #如果kargs字典中无key 则返回value
        if kargs.has_key(key):
            return kargs[key]
        else:
            return value
    def login(self):
        #登陆函数
        #串口一般为Fireitup
        #telnet 一般为root Fireitup
        #ssh 一般为root tendatest
        #adb 无密码
        cmds=[self.username,self.password]
        for cmd in cmds:
            if cmd:
                self.sendCmd(cmd)
        return True
    def sendCmd(self,cmd):
        if self.type == "ssh":
            print "cmd=",cmd
            stdin,stdout,sterr = self.t.exec_command(cmd)
            # stdout.flush()
            results=stdout.read()  
            return results
            # self.t.close())
        elif self.type == "telnet":
            self.t.write(cmd+"\n")
            time.sleep(0.3) ;#很重要
            return self.t.read_some()
        elif self.type == "com":
            self.t.write(cmd+"\n")
            time.sleep(0.3) ;#很重要
            return self.read_cominfo()
        elif self.type == "adb":
            pipe = subprocess.Popen("adb shell su root", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            cmdlst = [cmd,'exit']
            code = pipe.communicate("\n".join(cmdlst) + "\n")
            retstr = ""
            for i in code:
                retstr = retstr+str(i)+"\n"
            return retstr
    def read_cominfo(self):
        buffer=''
        while True:
            if self.t.inWaiting():
                data=self.t.read(1)
                buffer=buffer+data
            else:
                break
        return buffer
    def close(self):
        self.t.close()
class ks():
    def __init__(self,**kargs):
        brate=38400
        port="COM1"
        if kargs.has_key('brate'):
            brate=kargs['brate']
        if kargs.has_key('port'):
            port=kargs['port']
        self.serial = serial.Serial(port=port, baudrate=brate, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=None, xonxoff=1, rtscts=0, writeTimeout=None, dsrdtr=None)
    def config_rssi(self,num):
        cmd=""
        self.serial.write(cmd)
    def sendcmd(self,cmd):
        cmd=cmd+"\n"
        # cmd=self.str2bin(cmd)
        self.serial.write(cmd)
        time.sleep(0.5)
    def read_cominfo(self):
        buffer=''
        while True:
            if self.serial.inWaiting():
                data=self.serial.read(1)
                buffer=buffer+data
            else:
                break
        return buffer
if __name__ == "__main__":
    kt_obj = ktClass(type="ssh",host="192.168.20.2",username="root",password="tendatest")
    # kt_obj = kt(type="ssh",host="192.168.20.2",username="root",password="tendatest")
    ipdict = {"iface":"eth1","ip":"192.168.3.35","mask":"255.255.255.0","gateway":"192.168.3.1","dns":"192.168.3.1","mtu":"1450","mac":"00:ab:cd:11:22:33","dns":"223.5.5.5"}
    init_default_dict = {"auth":"chap","user":["tenda"],"pwd":["tenda"],"lip":"10.10.10.1","rip":"10.10.10.10","num":"1","iface":"eth1","padot":"0","dns":"202.96.134.133,202.96.128.86","mtu":"","mru":"","mppe":"","servername":"","repadr":"","mode":"add"}
    pptp_dict = {"auth":"chap","user":["test"],"pwd":["test"],"lip":"21.1.1.1","rip":"21.1.1.100","iface":"eth1","dns":"202.96.134.133,202.96.128.86",'cf':"/etc/pptpd.conf","pptpopt":"/etc/ppp/options.pptpd","mppe":"","mode":"add"}
    l2tp_dict = {"auth":"chap","user":["test"],"pwd":["test"],"lip":"22.1.1.1","rip":"22.1.1.100","iface":"eth1","dns":"202.96.134.133,202.96.128.86","mppe":"","mode":"add"}
    ftpdict = {"port":"21","rootdir":"/var/ftp","cf":"/etc/vsftpd/vsftpd.conf","file":"testfile","data":"ABCDEFGHIJKLMNTEST"}
    httpdict = {"port":"80","rootdir":"/var/www","cf":"/etc/httpd/conf/httpd.conf","subdir":"index.htm","data":"ABCDEFGHIJKLMNTEST"}
    dnsdict = {"dns":"192.168.20.2","urlip":"www.baidu.com#1.1.1.1,www.tenda.com#2.2.2.2","cf":"/var/named"}
    # code= kt_obj.dnsSerCfg(str(dnsdict))
    pkrecvdict = {"sip":"192.168.20.2","sport":"6000","pro":"tcp","num":"","size":""}
    pksenddict= {"dip":"192.168.20.2","dport":"6000","pro":"tcp","iface":"","sport":"","sip":"","num":"","size":"","flag":"1","loss":0.1,"expemss":"1455","expe":"pass"}
    dhcpd_dict = {"pool":"192.168.20.3,192.168.20.10","lease":"60","gw":"192.168.20.2","dns":"8.8.8.8","mask":"255.255.255.0","cf":"/tmp/dhcpd.conf","iface":"eth0","lf":"/var/db/dhcpd.leases","adopt":"","delopt":"","chkopt":"","chklen":"","relet":"","noack":"","mac":"","alert":"","of":"/var/tendatest/TDRouter2/tmp/log_dhcpc.txt","dellog":"0"}
    # code = kt_obj.pktRecv(str(pkrecvdict))
    upnpdict = {"lip":"192.168.3.105","wport":"10000","lport":"10000","pro":"all"}
    # upnpdict = {"lip":"192.168.3.105","wport":"10000","lport":"10000","pro":"all"}
    upnpchk_dict = {"modelname":"Tenda","modelnumber":"Tenda","url":"http://192.168.3.1/","manufacturer":"HF"}
    pingdict={"dip":"192.168.3.1","iface":"eth1","size":"64","maxsuc":"5","maxerr":"30","expe":"pass"}
    sshdict = {"ip":"192.168.3.1","user":"root","pwd":"Fireitup","cmd":"ifconfig","expe":"pass"}
    httpdict = {"ip":"192.168.20.2"}
    # kt_obj.sendCmd("""echo lock > /etc/ppp/options""")
    # kt_obj.sendCmd("""echo "unit 1" >> /etc/ppp/options""")
    # kt_obj.sendCmd("""echo "require-chap" >> /etc/ppp/options""")
    l2tpclidict={"auth":"mschap","iface":"eth1","user":"tenda","pwd":"tenda","mppe":"both","unit":"1","expe":"pass"}
    l2tpclidict={"desc":"l2tp","ip":"192.168.20.3","user":"tenda","pwd":"tenda","auth":"mschap-v2","mppe":"both","mode":"add","expe":"pass"}
    arpsenddict = {"sip":"192.168.3.2","smac":"00:11:22:33:55:44","dip":"192.168.3.1","dmac":"00:11:22:33:55:ab","type":"2","time":"1","num":"10","iface":"eth1"}
    # code = kt_obj.arpSend(str(arpsenddict))
    nslookupdict = {'url':"www.tenda.com.cn",'expeip':"182.92.168.49","serip":"192.168.3.1"}
    # print kt_obj.nslookup(str(nslookupdict))
    parserPacketdict = {'filter':'bootp.option.dhcp=1,ip.src=0.0.0.0,ip.dst=255.255.255.255'}
    packetCapturedict = {"filter":"udp port 67"}
    kt_obj.packetCapture(str(packetCapturedict))
    kt_obj.sendCmd("dhclient eth1")
    code = kt_obj.parserPacket(str(parserPacketdict))
    print code
    # code = kt_obj.ntpSerCfg()
    # print code
    # print  kt_obj.sendCmd("ps")

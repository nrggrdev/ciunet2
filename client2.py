# echo_client.py
import pickle
import socket, sys
import time
import threading
from influxdb import InfluxDBClient
import configparser
import distutils.util

l1=len(f"{0:2d}{0:20d}".encode())
l0=len(f"<#START>".encode())
l3=len(f"<#END>".encode())

import os

class tireslipClient(threading.Thread):
    def __init__(self,config,cwd='.'):
        threading.Thread.__init__(self)
        self.cwd=cwd
        if not os.path.exists(self.cwd):
            os.makedirs(self.cwd)
        windowPath=os.path.join(cwd,'window')
        if not os.path.exists(windowPath):
            os.makedirs(windowPath)

        self.useAverage=bool(distutils.util.strtobool(config['average']))
        self.updateinterval=int(config['updateinterval'])
        self.averageinterval=int(config['averageinterval'])
        self.timeout=int(config['timeout'])
        self.dbHost = config['host']
        self.dbPort=int(config['port'])
        self.dbName=config['database']
        self.measuremnet=config['measurement']
        self.tire=config['measurement']
        self.creepFile=os.path.join(self.cwd,config['creep_file'])
        self.OPC_creepFile=os.path.join(self.cwd,config['opc_file'])
        d=os.path.dirname(self.creepFile)
        print(d)
        if not os.path.exists(d):
            print (f'{d} missing, creating')
            os.makedirs(d)

        self.dbClient = InfluxDBClient(host=self.dbHost, port=self.dbPort, database=self.dbName)


    def run(self):
        while True:
            self.tic()
            time.sleep(self.updateinterval)
            print('>'
                  'tic')


    def tic(self):
        if self.useAverage:
            query_where = f'select mean(*) from {self.measuremnet} where time>now()-{self.averageinterval}s group by id'
        else:
            query_where = f'select last(*) from {self.measuremnet} where time>now()-{self.timeout}s group by id'
        result = self.dbClient.query(query_where)

        query_where = f'select last(*) from tireslip_status  group by id '
        result1 = self.dbClient.query(query_where)

        data = (list(result.get_points(measurement='tireslip_status')))
        data1 = (list(result1.get_points(measurement='tireslip_status')))

        self.writeCreepFile(data=data, data1=data1)

    def writeCreepFile(self,data,data1):
        print (data)
        print (data1)
        lines=[]
        opc_lines=[]
        line1="#ID Position Seconds  rpm     EC Clearance Slip     St\n"
        line2="{} {}  mm Slip Clearance\n".format(1,len(data)-1)
        lines.append(line1)
        opc_lines.append(line1)
        lines.append(line2)
        opc_lines.append(line2)
        if self.useAverage:
            prefix='mean'
        else:
            prefix='last'
        for i,datai in enumerate(data):
            position=data1[i][f'last_pos']
            interval=datai[f'{prefix}_period']/1000000
            rpm=datai[f'{prefix}_rpm']
            result1=datai[f'{prefix}_slip']
            result2=datai[f'{prefix}_clearance']
            statuscode=data1[i][f'last_tirecode']
            errorcode=data1[i][f'last_status']
            line="{:2}{:8.2f}{:8.3f}{:8.3f}{:2.0f}{:8.3f}{:8.3f}{:2.0f}\n".format(i,position,interval,rpm,errorcode,result1,result2,statuscode)
            line2="{:2}{:8.2f}{:8.3f}{:8.3f}{:2.0f}{:8.3f}{:8.3f}{:2.0f}\n".format(i,position,interval,rpm,errorcode,result2,result1,statuscode)
            lines.append(line)
            opc_lines.append(line2)
        print(lines)

        with open(self.creepFile,"w")as f:
            f.writelines(lines)
        with open(self.OPC_creepFile,"w")as f:
            f.writelines(opc_lines)

class tcemClient(threading.Thread):
    def __init__(self,config,cwd='.'):
        threading.Thread.__init__(self)
        self.config=config
        self.cwd = cwd
        self.ciunetHost = config['host']
        self.ciunetPort=int(config['port'])

        if not os.path.exists(self.cwd):
            os.makedirs(self.cwd)

    def run(self):
        while True:
            try:
                print(self.ciunetHost)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ciunetHost,self.ciunetPort))
                print (f'{time.time()}: connecting')
            except Exception as e:
                print(111)
                print(f'connect failed: {e}')
                time.sleep(1)
            try:
                while True:
                    received = sock.recv(l0)
                    if received=="<#START>".encode():
                        d=sock.recv(l1)
                        l2a,l2b = [int(i) for i in (d).split()]#len of data
                        received = sock.recv(l2a)
                        print(received)
                        fn=received.decode()
                        dfn=os.path.join(self.cwd,(fn))
                        received = sock.recv(l2b)
                        while l2b> len(received):
                            l2bb=l2b-len(received)
                            received2 = sock.recv(l2bb)
                            received+=received2

                        x=pickle.loads(received)
                        print(type(x))
                        print(dfn)

                        if type(x)==type(str()):
                            opentype='w'
                        else:
                            opentype='wb'
                        with open(dfn,opentype) as f:
                            data=x
                            f.write(data)
                        sock.recv(l3)
            except Exception as e:
                print("111",'connection lost',e,"111")
                time.sleep(1)

if __name__=="__main__":
    cp =configparser.ConfigParser()
    cp.read('config.ini')
    cwd=cp['tcem']['basepath']

    tcem=tcemClient(config=cp['ciunet'],cwd=cwd)
    tcem.start()

   # e#tireslip=tireslipClient(config=cp['tireslip'],cwd=cwd)
   # tireslip.start()
import traceback
import math
import numpy
from configparser import ConfigParser
from influxdb import InfluxDBClient, DataFrameClient
import sys
import os
import time
from threading import Timer
from datetime import datetime, timedelta
from distutils.util import strtobool
import pandas
import os.path
import logging
from PyQt5 import QtCore
import shutil
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class kiln(QtCore.QObject):
    def __init__(self,config):
        QtCore.QObject.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        print(config)
        config.filename='config/config.ini'
        self.config=config
        influxConfig=config["database"]
        host = influxConfig[ 'host']
        database = influxConfig['name']
        port = int(influxConfig[ 'port'])
        self.host=host
        self.port=port
        self.database=database

        tireslipConfig=config['tireslip']
        self.timeout=int(tireslipConfig["timeout"])
        self.filename=tireslipConfig["filename"]
        try:
            self.opcFilename=tireslipConfig["opcFilename"]
        except:
            self.opcFilename="tirecr.opc"
        c=config["kiln"]["tcem"]
        i=c["ciu_index"]
        fn =os.path.join(c["tcempath"],f"ciu{i}","Tire")
        if not os.path.exists(fn):
            os.makedirs(fn)
        self.filename=os.path.join(fn,self.filename)
        self.opcFilename=os.path.join(fn,self.opcFilename)

        self.influx_online = False
        dbClient = DataFrameClient(host=host, port=port, database=database,timeout=1)
        self.dbClient=dbClient
        try:
            self.dbClient.ping()
            self.influx_online=True
            self.logger.info("connected to influx")
        except Exception as e:
            self.influx_online=False
            self.logger.warning("not connected to influx")

        if self.influx_online:
            self.dbClient2 = InfluxDBClient(host=host, port=port, database=database)

        self.config=config
        self.logger.info("gear created")

        self.gear=gear(tireslipConfig["gear"],self.influx_online,self.dbClient)
        tireNr=0

        self.tires=[]
        while True:
            tireName=f"tire{tireNr}"
            if not tireName in tireslipConfig:
                break
            tp='single'
            try:
                if tireslipConfig[tireName]['type']=='double':tp='double'
            except:
                pass
            if tp=='single':
                t=tire(tireslipConfig[tireName],self.influx_online,self.dbClient,tireName,parent=self)
            if tp=='double':
                t=tireDouble(tireslipConfig[tireName],self.influx_online,self.dbClient,tireName,parent=self)

            self.tires.append(t)
            self.logger.info(f"tire {tireNr} created as type {tp}")

            tireNr+=1
        tireName = f"movement"
        if tireName in tireslipConfig:
            t = horizontalSensor(tireslipConfig[tireName], self.influx_online, self.dbClient, tireName,parent=self)
            self.tires.append(t)
            self.logger.info(f"tire {tireName} created")
            self.horizontalSensor=t
            self.mover=t


        tireName = f"movement3eck"
        if tireName in tireslipConfig:
            t = horizontalSensor3eck(tireslipConfig[tireName], self.influx_online, self.dbClient, tireName,parent=self)
            self.mover=t
            self.tires.append(t)
            self.logger.info(f"tire {tireName} created")
            self.horizontalSensor=t



        if self.influx_online:
            try:
                self.dbClient.create_database(database)
            except:
                pass
        self.startTime=time.time()
        self.lastTic=self.startTime
        self.runtime=0
        self.writeTireFile()
        self.timeoutTimer=QtCore.QTimer()
        self.timeoutTimer.setInterval(self.timeout*1000)
        self.timeoutTimer.setSingleShot(False)
        self.timeoutTimer.timeout.connect(self.tic)
        self.timeoutTimer.start()
        self.deamon = RepeatTimer(30, self.checkInfluxOnline)
        self.deamon.daemon=True
#        self.deamon.setDaemon(True)
        self.deamon.start()

    def updateConfigb(self,child):
        self.logger.info(f'update config and backup: {child.name}')
        d = datetime.now()
        bd = (d.strftime("config_backup.Y%YM%mD%d_%H%M%S"))
        import os.path
        configDir = "config"
        shutil.copytree(configDir, bd)
        #self.config[child.name]=child.config
        self.config.write()
    def getMovement(self):
        try:
            dpos,pos=self.horizontalSensor.get_Position()
        except:
            self.logger.warning('could not get movement values')
            return None
        return dpos,pos
    def updateConfig(self,child):
        self.logger.info(f'update config: {child.name}')
        print(f'update config: {child.name}')
        d = datetime.now()
        self.config.write()

    def updateHP0(self,P0):
        try:
            self.horizontalSensor.setP0(P0)
        except:pass

    def updateHP1(self,P1):
        try:
            self.horizontalSensor.setP1(P1)
        except:pass


    def checkInfluxOnline(self):
#        dbClient = DataFrameClient(host=self.host, port=self.port, database=self.database, timeout=1)
#        self.dbClient = dbClient
        lastOnline=self.influx_online
        try:
            self.dbClient.ping()
            self.influx_online = True
            self.logger.debug("connected to influx")
        except Exception as e:
            self.influx_online = False
            self.logger.warning("not connected to influx")
        if self.influx_online==lastOnline:
            return
        self.logger.info(f"influx connection changed >> online:{self.influx_online}")
        self.logger.info("influx connection changed")

        if self.influx_online:
            try:
                self.dbClient.create_database(self.database)
            except:
                pass
        self.gear.updateInfluxStatus(online=self.influx_online)
        for t in self.tires:
            t.updateInfluxStatus(online=self.influx_online)

    def receiver(self,data,software_timeout):
        try:

            self.tic(software_timeout)
        except Exception as e:
            traceback.format_exc()
            print (e)
    def tic(self,software_timeout=False):
        self.logger.debug("tic")
        try:
            try:
                self.gear.tic(software_timeout)
                self.logger.info("gear tic")

            except Exception as e:
                print(traceback.format_exc())
                print (e)
            try:
                a,e=self.gear.getLastinterval()
                s=self.gear.isStable()
                print (a,e,'a,e')
            except Exception as exx:
                print('****####', exx)


                traceback.print_exc()

            print('tires: ',self.tires)
            for t in self.tires:
                print(t.name)
                try:
                    t.tic(stable=s,anfang=a,ende=e,interval=self.gear.interval,gearR=self.gear.r)
                except Exception as exx:
                    print('****',exx)
                    traceback.print_exc()

                self.logger.info(f"tire {t.name} tic")

            self.write2Influx()
            self.logger.info("write2influx")

            self.writeTireFile()
            self.logger.info("write2tirefile")
        except Exception as e:
            print( 'tireslip tic failed')
            print(e)
            self.logger.warning("tireslip tic failed")
            self.logger.warning(e)

    def write2Influx(self):
        data=[]
        if self.gear.error==1:
            return
        data.append(self.gear.buildJSON())
        if self.gear.isStable():
            for t in self.tires:
                try:

                    if t.error==0:
                        data.append(t.buildJSON())
                except Exception as e:
                    self.logger.warning('write2influx /json : ',t.name,e)
                    print(e)
        try:
            print(data)
            self.dbClient2.write_points(data)
        except Exception as e:
            self.logger.warning('write2influx / write_pints', e)

            print(e)

    def writeTireFile(self,opc=False):
        lines=[]
        lines_opc=[]
        line="#ID Position Seconds  rpm     EC Slip Clearance     St\n"
        lines.append(line)
        lines_opc.append(line)
        line="{} {}  mm Slip Clearance\n".format(1,len(self.tires))
        lines.append(line)
        lines_opc.append(line)

        rpm=0
        result1 = 0
        result2 = 0
        errorcode=0
        statuscode=0

        v = self.gear.getRPM()
        if v is None:
            errorcode = 1
            interval = -1
            rpm=-1
        else:
            rpm, interval=v
            interval=interval/1000000
        position = self.gear.pos
        line = "{:2}{:8.2f}{:8.3f}{:8.3f}{:2.0f}{:8.3f}{:8.3f}{:2.0f}\n".format(0, position, interval, rpm,
                                                                                errorcode, result2, result1, statuscode)
        lines.append(line)
        lines_opc.append(line)

        rpm=0
        result1 = 0
        result2 = 0
        errorcode=0
        statuscode=0

        for i,t in enumerate(self.tires):
            errorcode = 0
            statuscode = 0
            if not t.show :continue

            if self.influx_online:
                try:
                    v=t.getValues()
                except:
                    v=None
            else: v=None
            if v is None:
                errorcode=1
                result1=-1
                result2=-1
                interval=-1
            else:
                result2,result1,interval=t.getValues()
                interval = interval / 1000000

            position=t.pos
            line="{:2}{:8.2f}{:8.3f}{:8.3f}{:2.0f}{:8.3f}{:8.3f}{:2.0f}\n".format(i+1,position,interval,rpm,errorcode,result2,result1,statuscode)
            line_opc="{:2}{:8.2f}{:8.3f}{:8.3f}{:2.0f}{:8.3f}{:8.3f}{:2.0f}\n".format(i+1,position,interval,rpm,errorcode,result1,result2,statuscode)
            lines.append(line)
            lines_opc.append(line_opc)
            print (lines)
        with open(self.filename,"w")as f:
            f.writelines(lines)
        with open(self.opcFilename,"w")as f:
            f.writelines(lines_opc)


class Xkiln_unused(object):
    def __init__(self):
        cf = ConfigParser()
        configName = 'tireslip.ini'
        configName = os.path.join('./config/', configName)
        print (configName)
        cf.read(configName)
        config=cf
        host = config.get('database', 'host')
        database = config.get('database', 'database')
        port = config.getint('database', 'port')
        self.influx_online = False
        dbClient = InfluxDBClient(host=host, port=port, database=database)
        self.dbClient=dbClient
        try:
            self.dbClient.ping()
            self.influx_online=True
        except Exception as e:
            self.influx_online=False
        self.config=config
        self.tires=[]
        self.rpm=0
        self.ticinterval=self.config.getint('general','interval')
        if self.influx_online:
            print ('influx ok'*80)
            self.dbClient.create_database(database)
            self.tires=self.getTires()
            self.deamon=RepeatTimer(self.ticinterval,self.tic)
            self.deamon.setDaemon(True)
            self.deamon.start()
        self.startTime=time.time()
        self.lastTic=self.startTime
        self.runtime=0

    def writeRawValue(self,value,rising=True, channel=0,scanner=1):
        if rising:
            postfix='rising'
        else:
            postfix='falling'


        js = {"time": datetime.utcnow(),
              "measurement": "tireslip_raw",
              "tags": {
                  "id": channel,
                  "scanner": scanner,
              },
              "fields": {
                  f"timeestamp_{postfix}":value
              }
              }
        if self.influx_online:
            self.dbClient.write_points(js)

    def getTires(self):
        i=0
        tires=[]
        while self.config.has_section(f'Tire{i}'):
            t=tire(config=self.config[f'Tire{i}'],dbClient=self.dbClient,id=f'Tire{i}')
            tires.append(t)
            i+=1
            t.writeStatus(ok=False)
        return tires

    def tic(self):
        try:
            gear_ok=False
            print ('tireslip tic')

            self.runtime=time.time()-self.startTime
            trigger=self.tires[0].trigger
            if trigger:
                data=self.tires[0].getRPM()
                self.tires[0].nextRound()
                print (data)
                if len (data)==3:
                    gear_ok=True
                    gear_rpm,gear_interval,gear_std=data
                    if gear_std>0.1:
                        print('rpm deviation to big, instable')

            for t in self.tires:
                t.tic()

                if t==self.tires[0] and trigger:
                    print ('GEAR',gear_ok)
                    t.writeStatus(ok=True,tirecode=0)
                    continue

                t.getRPM()
                if gear_ok and t!=self.tires[0]:
                    t.getTireslip(rotation=gear_interval)
                else :
                    t.writeStatus(ok=False)
            self.lastTic=time.time()
        except Exception as e:
            print (e)

class timeValueFilter(object):
    def __init__(self, config):
        host = config['host']
        database = config['name']
        port = int(config['port'])
        self.influx_online = False
        dbClient = InfluxDBClient(host=host, port=port, database=database)
        self.dbClient = dbClient
        try:
            self.dbClient.ping()
            self.influx_online = True
        except Exception as e:
            print(e)
            self.influx_online = False
        self.config = config
        self.tires = []
        #        self.ticinterval=self.config.getint('general','interval')
        if self.influx_online:
            print('influx ok' * 80)
            self.dbClient.create_database(database)
            #            self.tires=self.getTires()
            self.deamon=RepeatTimer(self.ticinterval,self.tic)
            self.deamon.setDaemon(True)
            self.deamon.start()
        self.startTime = time.time()
        self.lastTic = self.startTime
        self.runtime = 0

    def tic(self):
        try:
            gear_ok=False
            print ('tireslip tic')

            self.runtime=time.time()-self.startTime
            trigger=self.tires[0].trigger
            if trigger:
                data=self.tires[0].getRPM()
                self.tires[0].nextRound()
                print (data)
                if len (data)==3:
                    gear_ok=True
                    gear_rpm,gear_interval,gear_std=data
                    if gear_std>0.1:
                        print('rpm deviation to big, instable')

            for t in self.tires:
                t.tic()

                if t==self.tires[0] and trigger:
                    print ('GEAR',gear_ok)
                    t.writeStatus(ok=True,tirecode=0)
                    continue

                t.getRPM()
                if gear_ok and t!=self.tires[0]:
                    t.getTireslip(rotation=gear_interval)
                else :
                    t.writeStatus(ok=False)
            self.lastTic=time.time()
        except Exception as e:
            print (e)

class rawWriter(QtCore.QObject):
    def __init__(self,config):

        QtCore.QObject.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        host = config[ 'host']
        database = config['name']
        port = int(config[ 'port'])
        self.influx_online = False
        dbClient = InfluxDBClient(host=host, port=port, database=database,timeout=1)
        self.dbClient=dbClient
        try:
            self.dbClient.ping()
            self.influx_online=True
        except Exception as e:
            print(e)
            self.influx_online=False
        self.config=config
        self.tires=[]
#        self.ticinterval=self.config.getint('general','interval')
        if self.influx_online:
            print ('influx ok'*80)
            try:

                self.dbClient.create_database(database)
            except:
                pass
            #            self.tires=self.getTires()
            # self.deamon=RepeatTimer(self.ticinterval,self.tic)
            # self.deamon.setDaemon(True)
            # self.deamon.start()
        self.startTime=time.time()
        self.lastTic=self.startTime
        self.runtime=0

    def writeRawValue(self,data):
        print ('raw tireslip',data)
        self.logger.info(f'raw tireslip: {data}')
        try:
            rising, rawChannel, channel, value=data
        except Exception as e:
            self.logger.warning(f'raw tireslip write failed; data:{data}; error:{e}')

            print(e)
            return
        if rising:
            postfix='rising'
        else:
            postfix='falling'


        js = [{"time": datetime.utcnow(),
              "measurement": "tireslip_raw",
              "tags": {
                  "id": channel,
              },
              "fields": {
                  f"timeestamp_{postfix}":value
              }
              },]
        try:
            if self.influx_online:
                self.dbClient.write_points(js)
        except Exception as e:
            print(e)

class tireDouble(object):
    def __init__(self,config,influxOnline,dbClient,name,parent=None):
        self.parent=parent
        self.config=config
        self.name=name
        self.influxOnline=influxOnline
        self.dbClient=dbClient
        self.src1=config["src1"]
        self.src2=config["src2"]
        self.pos = float(self.config["x"])
        self.r = float(self.config["r"])
        self.average_interval = int(self.config["average_interval"])
        self.average_rotations = int(self.config["average_rotations"])
        self.minSlip = float(self.config["minSlip"])
        self.mininterval = float(self.config["mininterval"])*1000000
        self.maxSlip = float(self.config["maxSlip"])
        self.U=2*self.r*math.pi
        self.std=99.0
        self.period=0.0
        self.error=1
        self.status=0
        self.show=True
        try:
            self.show=strtobool(self.config["show"])
        except:
            pass
        try:
            self.minAlarmSlip = float(self.config["minAlarmSlip"])
        except Exception as e:
            self.minAlarmSlip=0
            self.config["minAlarmSlip"]=self.minAlarmSlip
        try:
            self.maxAlarmSlip = float(self.config["maxAlarmSlip"])
        except Exception as e:
            self.maxAlarmSlip=self.maxSlip
            self.config["maxAlarmSlip"]=self.maxAlarmSlip
    def updateInfluxStatus(self,online=True):
        self.influxOnline=online
    def getValues(self):
        if not self.influxOnline:
            return None
        nResults=0
        query_rising = f"select mean(*) from tireslip where id='{self.src1}' and time>now()-{self.average_interval}s ORDER BY time DESC "  # LIMIT {self.average_rotations}'
        data = self.dbClient.query(query_rising)
        slip=0
        clearance=0
        interval=0
        self.error=0
        if len(data)!=0:
            data=(data)["tireslip"]
            slip=(data[f"mean_slip"].iloc[-1])
            clearance=(data[f"mean_clearance"].iloc[-1])
            interval=(data[f"mean_interval"].iloc[-1])
            nResults+=1

        query_rising = f"select mean(*) from tireslip where id='{self.src2}' and time>now()-{self.average_interval}s ORDER BY time DESC "  # LIMIT {self.average_rotations}'
        data = self.dbClient.query(query_rising)
        if len(data)!=0:
            data=(data)["tireslip"]
            if nResults==1:
                slip=min((data[f"mean_slip"].iloc[-1]),slip)
                clearance=min((data[f"mean_clearance"].iloc[-1]),clearance)
                interval=min((data[f"mean_interval"].iloc[-1]),interval)
            else:
                slip = (data[f"mean_slip"].iloc[-1])
                clearance = (data[f"mean_clearance"].iloc[-1])
                interval = (data[f"mean_interval"].iloc[-1])

            nResults+=1
        if nResults>0:
            self.slip=slip
            self.clearance=clearance
            self.r_slip=self.slip/self.U
            self.r_clearance=self.clearance/self.U
            self.interval=interval
            self.error=0
            self.rpm=60000000/self.interval
            alarm = 0
            if self.maxAlarmSlip < self.slip:
                alarm = 1
            if self.slip < self.minAlarmSlip:
                alarm += 2
            self.status = alarm

            return slip,clearance,interval
        else:
            self.error=1
            return None
    def tic(self,stable,anfang,ende,interval,gearR=0):
        pass
    def buildJSON(self):
        print('tire json')
        js = {"time": datetime.utcnow(),
               "measurement": "tireslip",
               "tags": {
                   "id": self.name,
               },
               "fields": {
                   "interval": self.interval,
                   "rpm": self.rpm,
                   "error": self.error,
                   "slip":self.slip,
                   "r_slip":self.r_slip,
                   "clearance":self.clearance,
                   "r_clearance":self.r_clearance
               }
               }
        return js


class tire(object):
    def __init__(self,config,influxOnline,dbClient,name,parent=None):
        self.parent=parent
        self.config=config
        self.name=name
        self.influxOnline=influxOnline
        self.dbClient=dbClient
        self.channel = self.config["channel"]
        self.pos = float(self.config["x"])
        self.r = float(self.config["r"])
        try:
            self.r2 = float(self.config["r2"])
        except:
            self.r2=self.r
        self.average_interval = int(self.config["average_interval"])
        self.average_rotations = int(self.config["average_rotations"])
        self.minSlip = float(self.config["minSlip"])
        self.maxSlip = float(self.config["maxSlip"])

        try:
            self.minAlarmSlip = float(self.config["minAlarmSlip"])
        except Exception as e:
            self.minAlarmSlip=0
            self.config["minAlarmSlip"]=self.minAlarmSlip
        try:
            self.maxAlarmSlip = float(self.config["maxAlarmSlip"])
        except Exception as e:
            self.maxAlarmSlip=self.maxSlip
            self.config["maxAlarmSlip"]=self.maxAlarmSlip

        self.mininterval = float(self.config["mininterval"])*1000000
        self.rising =strtobool(self.config["rising"])
        self.show=True
        try:
            self.show=strtobool(self.config["show"])
        except:
            pass
        self.falling =strtobool(self.config["falling"])
        self.U=2*self.r*math.pi
        self.std=99.0
        self.period=0.0
        self.error=1
        self.status=0
        self.parent.updateConfig(self)
    def updateInfluxStatus(self,online=True):
        self.influxOnline=online

    def getValues(self):
        query_rising = f"select mean(*) from tireslip where id='{self.name}' and time>now()-{self.average_interval}s ORDER BY time DESC "  # LIMIT {self.average_rotations}'
        if not self.influxOnline:
            return None
        data = self.dbClient.query(query_rising)
        if len(data)==0:
            return None


        data=(data)["tireslip"]
        slip=(data[f"mean_slip"].iloc[-1])
        clearance=(data[f"mean_clearance"].iloc[-1])
        interval=(data[f"mean_interval"].iloc[-1])
        return slip,clearance,interval

    def buildJSON(self):
        js = {"time": datetime.utcnow(),
               "measurement": "tireslip",
               "tags": {
                   "id": self.name,
               },
               "fields": {
                   "interval": self.interval,
                   "rpm": self.rpm,
                   "error": self.error,
                   "slip":self.slip,
                   "r_slip":self.r_slip,
                   "clearance":self.clearance,
                   "r_clearance":self.r_clearance
               }
               }
        return js

    def tic(self,stable,anfang,ende,interval,gearR=0):
        f=1
#        if gearR>0:
#            f=gearR/self.r
#            interval=interval/f
        f=self.r2/self.r
        interval=interval/f


        if not stable:
            print(" warning : not stable")
            self.error=1
            self.status=0
            return
        data=None
        if self.rising:
            data_rising=self.selectData(anfang,ende,interval,rising=True)
            data=data_rising
        if self.falling:
            data_falling=self.selectData(anfang,ende,interval,rising=False)
            if data is None:
                data=data_falling
                print("no data")
            else:
                d1=data
                data=[d1,data_falling]
                data=pandas.concat(data)
                print('tik ok')
                #data=data.append(data_falling)
        if data is None:
            self.error=1
            self.status=0
            return

        try:
            self.timestamp=data["timestamp"]
            self.interval=data["interval"].mean()*f
            self.rpm=data["rpm"].mean()/f
            self.slip=data["slip"].mean()*f
            self.r_slip=data["r_slip"].mean()
            self.clearance=data["clearance"].mean()*f
            self.r_clearance=data["r_clearance"].mean()
            self.error=0
        except Exception as e:
            self.error=1

        # self.slip=(data["interval"][-1]-interval[-1])*self.U/interval[-1]
        # self.r_slip=(data["interval"][-1]-interval[-1])*2*math.pi/interval[-1]
        # self.clearance=(data["interval"][-1]-interval[-1])*self.r/interval[-1]
        # self.r_clearance=(data["interval"][-1]-interval[-1])/interval[-1]

    def selectData(self,  anfang, ende, interval,rising=True):
        if anfang> ende:
            return  None
        if rising:
            edge = "rising"
        else:
            edge ="falling"
        query = f"select timeestamp_{edge} as timestamp from tireslip_raw where id='{self.channel}' and time > now()-{self.average_interval}s"  # LIMIT {self.average_rotations}'
        if self.influxOnline:
            data = self.dbClient.query(query)
        else: return None
        if len(data) == 0:
            return None

        data = data['tireslip_raw']
        data = data[data.index > anfang - pandas.Timedelta(seconds=5 + 2 * interval / 1000000)]
        data = data[data.index <= ende]
        if len(data) == 0:
            return None
#        data = data[data["timestamp"].diff() > self.mininterval]
        data = data[(data["timestamp"].diff() > self.mininterval) | (data["timestamp"].diff() < 0)]


        if len(data) == 0:
            return None

        data['end'] = data.index
        data['interval'] = (data['timestamp'].diff())
        data.loc[data.interval < 0, 'interval'] += 4294967295

        data['rpm'] = 60000000 / data['interval']
        data['start'] = data['end'].shift(1)
        data["slip"]=(data["interval"][-1]-interval)*self.U/interval
        data["r_slip"]=(data["interval"][-1]-interval)*2*math.pi/interval
        data["clearance"]=(data["interval"][-1]-interval)*self.r/interval
        data["r_clearance"]=(data["interval"][-1]-interval)/interval
        pandas.set_option("display.max_rows", None, "display.max_columns", None)
        d1 = (data.iloc[-1])


        dd1=pandas.DataFrame([d1])
        alarm=0
        if self.maxAlarmSlip<d1['slip']:
            alarm=1
        if d1['slip']<self.minAlarmSlip:
            alarm+=2
        self.status=alarm


        if self.minSlip<d1['slip']<self.maxSlip:
            return dd1
        else:
            return None
        return d1.to_frame().reset_index()
        return d1.to_frame()



class horizontalSensor3eck(object):
    def __init__(self,config,influxOnline,dbClient,name,parent=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config=config
        self.parent=parent
        self.name=name
        self.influxOnline=influxOnline
        self.dbClient=dbClient
        self.channel = self.config["channel"]
        self.pos = float(self.config["x"])
        self.average_interval = int(self.config["average_interval"])
        self.average_rotations = int(self.config["average_rotations"])
#        self.minPos = float(self.config["minPos"])
        self.mininterval = float(self.config["mininterval"])*1000000
#        self.maxPos = float(self.config["maxPos"])
        self.Pos0 = float(self.config["Pos0"])
        self.Pos1 = float(self.config["Pos1"])
        self.minPos = float(self.config["minPos"])
        self.maxPos = float(self.config["maxPos"])
        try:
            self.minAlarm = float(self.config["minAlarm"])
        except:
            self.minAlarm = self.minPos
            self.config["minAlarm"]=self.minAlarm
        try:
            self.maxAlarm = float(self.config["maxAlarm"])
        except:
            self.maxAlarm = self.maxPos
            self.config["maxAlarm"]=self.maxAlarm

        self.Pos0_faktor = float(self.config["Pos0_faktor"])
        self.Pos1_faktor = float(self.config["Pos1_faktor"])

        self.rising =strtobool(self.config["rising"])
        self.falling =strtobool(self.config["falling"])
        self.std=99.0
        self.period=0.0
        self.error=1
        self.status=0

        self.show = True
        try:
            self.show = strtobool(self.config["show"])
        except:
            pass
    def updateConfig(self):
        print('update '*80)
        self.config['Pos0']=self.Pos0
        try:
            self.config['Pos1']=self.Pos1
            self.config['Pos0']=self.Pos0
            self.config['Pos0_faktor']=self.Pos0_faktor
            self.config['Pos1_faktor']=self.Pos1_faktor
        except Exception as e:
            print(e)
        print(self.config)
        self.parent.updateConfigb(self)

    def setP0(self,pos):

        self.Pos0=pos
#        try:
        #            if self.interval1>self.interval2:
        #        f=self.interval2/self.interval1
        #    else:
        #        f=self.interval1/self.interval2
        try:
            self.Pos0_faktor=self.f
        except Exception as e :
            print(e)
        #        except:
        #   pass
        print('P00')
        self.updateConfig()

    def setP1(self,pos):
        self.Pos1=pos
        try:
            self.Pos1_faktor = self.f
        except Exception as e:
            print(e)
        self.updateConfig()

    def updateInfluxStatus(self,online=True):
        self.influxOnline=online
    def getValues(self):
        query_rising = f"select mean(*) from tireslip where id='{self.name}' and time>now()-{self.average_interval}s ORDER BY time DESC "  # LIMIT {self.average_rotations}'
        self.logger.debug(f'getvalues:query={query_rising}')
        if not self.influxOnline:
            return None
        data = self.dbClient.query(query_rising)
        if len(data)==0:
            return None


        data=data["tireslip"]
        self.logger.debug(f'getvalues:result={data}')
#        self.logger.debug(f'getvalues:result={data[f"mean_position"]}')
#        self.logger.debug(f'getvalues:result={data[f"mean_position"]}')
#        self.logger.debug(f'getvalues:result={data[f"mean_interval"]}')

        r_position=(data[f"mean_r_position"].iloc[-1])
        d_position=(data[f"mean_d_position"].iloc[-1])
        position=(data[f"mean_d_position"].iloc[-1])
        interval=(data[f"mean_interval"].iloc[-1])
        self.logger.debug(f'getvalues:result={r_position}|{d_position}|{interval}')

        return d_position,r_position,interval
    def get_Position(self):
        values=self.getValues()
        if values!=None:
            dpos,rpos,interval=values
            pos=dpos+self.Pos0
            return dpos, pos
        else:
            return None

    def buildJSON(self):
        try:
            js = {"time": datetime.utcnow(),
                   "measurement": "tireslip",
                   "tags": {
                       "id": self.name,
                   },
                   "fields": {
                       "interval": self.interval,
                       "interval1": self.interval1,
                       "interval2": self.interval2,
                       "f": self.f,
                       "rpm": self.rpm,
                       "error": self.error,
                       "position":self.position,
                       "r_position":self.r_position,
                       "d_position":self.d_position
                   }
                   }
            self.logger.info(js)
        except Exception as e:
            self.logger.warning('buidlJSON', e)
        print(js)
        return js

    def tic(self,stable,anfang,ende,interval,gearR=0):
        self.logger.info(f"tic: stable {stable}")


        if not stable:
            print(" warning : not stable")
            self.error=1
            self.status=0
            return
#        data=None
#        data = data['tireslip_raw']
#        data = data[data.index > anfang - pandas.Timedelta(seconds=5 + 2 * interval / 1000000)]

        try:
            try:
                query_rising = f"select timeestamp_rising as x from tireslip_raw where id='{self.channel}' and time>now()-{self.average_interval}s "  # LIMIT {self.average_rotations}'
                #dfy = pandas.DataFrame(self.dbClient.query(query_rising))
                dfy = self.dbClient.query(query_rising)
                self.logger.info(query_rising)
                self.logger.info(dfy)

                dfy=dfy['tireslip_raw']
                self.logger.info(dfy)

#                dfy.set_index('time', inplace=True)


                query_rising = f"select timeestamp_falling as x from tireslip_raw where id='{self.channel}' and time>now()-{self.average_interval}s "  # LIMIT {self.average_rotations}'
                #dfx = pandas.DataFrame(self.dbClient.query(query_rising))
                dfx = self.dbClient.query(query_rising)
                dfx=dfx['tireslip_raw']

 #               dfx.set_index('time', inplace=True)

#                query_rising = f"select timeestamp_rising as y, timeestamp_falling as x from tireslip_raw where id='{self.channel}' and time>now()-{self.average_interval}s "  # LIMIT {self.average_rotations}'

#                self.logger.warning(f"3eck X: {query_rising}")
                #df = pandas.DataFrame(self.dbClient.query(query_rising, chunked=True, chunk_size=10000).get_points())
#                df = pandas.DataFrame(self.dbClient.query(query_rising))
            except Exception as e:
                self.logger.warning(f"3eck X: {e}")

 #               df=df['tireslip_raw']
 #           try:

#                df.set_index('time', inplace=True)
#            except Exception as e:
#                self.logger.warning(f"3eck: {e}")
            try:
#                dfy = (df['y'])
#                dfy.dropna(inplace=True)
#                dfx = (df['x'])
#                dfy = dfy.rename('x')
#                dfx = dfx.rename('x')
#                dfx.dropna(inplace=True)
                dfxy = pandas.concat([dfx, dfy])
                dfxy.sort_index(inplace=True)
                dfxy.dropna(inplace=True)
#                dfxy = dfxy.to_frame()
                dfxy['interval'] = dfxy.diff()
            except Exception as e:
                self.logger.warning(f"3eck A: {e}")
            try:
                dfxy['interval'] = pandas.to_numeric(dfxy['interval'])
                dfxy.dropna(inplace=True)
                #dfxy['interval'] = pandas.to_numeric(dfxy['interval'])
                dfxy.loc[dfxy.interval < 0].interval += 4294967295
                interval1 = (dfxy[::2].interval.mean())
                interval2 = (dfxy[1::2].interval.mean())
#                    xxx=interval1
#                    interval1=interval2
#                    interval2=xxx
                interval=interval1+interval2

            except Exception as e:
                self.logger.warning(f"3eck A: {e}")
#
            #            self.timestamp=data["timestamp"]
            self.interval=interval
            if interval1 > interval2:
                self.interval1=interval2
                self.interval2=interval1
            else:
                self.interval1=interval1
                self.interval2=interval2

            self.f=self.interval1/self.interval2

            self.rpm=60000000/interval
            self.d_position=(self.Pos1 - self.Pos0) / (self.Pos1_faktor - self.Pos0_faktor) * (self.f - self.Pos0_faktor)
            self.r_position=self.d_position / (self.Pos1 - self.Pos0)
            self.position=self.d_position+self.Pos0

            self.error=0
            alarm = 0
            if self.maxAlarm <self.position:
                alarm = 1
            if self.position < self.minAlarm:
                alarm += 2
            self.status = alarm

        except Exception as e:
            self.error=1
            self.status=0

            self.logger.info(f"could not build movement data: {e}")

            self.error=1

        # self.slip=(data["interval"][-1]-interval[-1])*self.U/interval[-1]
        # self.r_slip=(data["interval"][-1]-interval[-1])*2*math.pi/interval[-1]
        # self.clearance=(data["interval"][-1]-interval[-1])*self.r/interval[-1]
        # self.r_clearance=(data["interval"][-1]-interval[-1])/interval[-1]

    def selectData(self,  anfang, ende, interval,rising=True):
        if anfang> ende:
            return  None
        if rising:
            edge = "rising"
        else:
            edge ="falling"
        query = f"select timeestamp_{edge} as timestamp from tireslip_raw where id='{self.channel}' and time > now()-{self.average_interval}s"  # LIMIT {self.average_rotations}'
        self.logger.debug(f"raw_query: {query}")
        if self.influxOnline:
            data = self.dbClient.query(query)
        else: return None
        if len(data) == 0:
            return None
        return data

        data = data['tireslip_raw']
        data = data[data.index > anfang - pandas.Timedelta(seconds=5 + 2 * interval / 1000000)]
        data = data[data.index <= ende]
        if len(data) == 0:
            return None
#        data = data[data["timestamp"].diff() > self.mininterval]
        data = data[(data["timestamp"].diff() > self.mininterval) | (data["timestamp"].diff() < 0)]
        self.logger.debug(f"filtered rawdata:{data}")


        if len(data) == 0:
            self.logger.info(f"no raw data")
            print(f"no raw data")

            return None


        data['end'] = data.index
        data['interval'] = (data['timestamp'].diff())
        data.loc[data.interval < 0, 'interval'] += 4294967295
        try:
            interval1=data['interval'][::2]
            interval1.dropna(inplace=True)

            interval2=data['interval'][1::2]
            interval2.dropna(inplace=True)
            if (not len(interval1)>0):return None
            if (not len(interval2)>0):return None
        except:
            return None

        interval=interval1 +interval2
        print(f'interval1: {interval1}')
        print(f'interval2: {interval2}')
        if len(interval1) > len(interval2):
            interval1 = interval1[len(interval1)-len(interval2):]
        if len(interval2) > len(interval1):
            interval2 = interval2[len(interval2)-len(interval1):]

        self.logger.debug(f'interval1n: {interval1}')
        self.logger.debug(f'interval2n: {interval2}')
        if interval1.iloc[-1]>interval2.iloc[-1]:
            dir12=True
        else:
            dir12=False
        if dir12:
            int1=interval1.to_numpy()
            int2=interval2.to_numpy()
        else:
            int2=interval1.to_numpy()
            int1=interval2.to_numpy()
        print(int1,int2)
        ndata={}
        ndata["interval1"]=int1[-1]
        ndata["interval2"]=int2[-1]
        ndata["interval"]=ndata["interval1"]+ndata["interval2"]
        ndata["rpm"]=60000000/ndata['interval']
        ndata["f"]=ndata['interval1']/ndata['interval2']
        ndata['d_position'] = (self.Pos1 - self.Pos0) / (self.Pos1_faktor - self.Pos0_faktor) * (ndata['f'] - self.Pos0_faktor)
        ndata['r_position'] = ndata['d_position'] / (self.Pos1 - self.Pos0)
        ndata['position'] = ndata['d_position'] + self.Pos0
        self.logger.debug(ndata)
        if self.minPos<ndata['position']<self.maxPos:
            ndata=pandas.DataFrame([ndata])
            return ndata
        else:
            self.logger.info(f"kiln Position{ndata['position']} not in allowed range")

#        ndata = (ndata.iloc[[-1]])
        self.logger.debug(ndata)
        ndata = ndata[self.minPos<ndata['position']<self.maxPos]
        if ndata.empty:
            return None
        else:
            self.logger.debug(f'final data: {ndata}')

            return ndata

        if self.minPos<ndata['position']<self.maxPos:
            return ndata
        else:
            return None

        interval1['interval1']=int1
        interval1['interval2']=int2
        interval1['interval']=interval1['interval1']+interval1['interval2']
        interval1['rpm']=60000000/interval1['interval']
        interval1['f']=interval1['interval1']/interval1['interval2']
        interval1['d_position'] = (self.Pos1 - self.Pos0) / (self.Pos1_faktor - self.Pos0_faktor) * (interval1['f'] - self.Pos0_faktor)
        interval1['r_position']=interval1['d_position'] / (self.Pos1 - self.Pos0)
        interval1['position']=interval1['d_position']+self.Pos0
        print('final: ',interval1)
        i1=interval1.copy()
        d1 = (i1.iloc[-1])


        dd1=pandas.DataFrame([d1])
        print(dd1)
        return dd1
        return interval1.mean()
        f=interval1/interval2
        if numpy.any(f<1):
            f=1/f
        interval = interval1 + interval2
        print(f'interval: {interval}')
        #        interval=interval[-1]
#        interval1=interval1[-1]
#        interval2=interval2[-1]
        rpm=60000000/interval
        timestamp=data['timestamp'][1::2]
        faktor=f
        d_position = (self.Pos1 - self.Pos0) / (self.Pos1_faktor - self.Pos0_faktor) * (f - self.Pos0_faktor)
        r_position = d_position / (self.Pos1 - self.Pos0)
        position = self.Pos0 + d_position

        x=pandas.DataFrame()
        x['timestamp']=timestamp
        x['rpm']=rpm
        x['faktor']=faktor
        x['interval']=interval
        x['interval1']=interval1
        x['interval2']=interval2
        x['d_position']=d_position
        x['r_position']=r_position
        x['position']=position
        x.set_index('timestamp')

        pandas.set_option("display.max_rows", None, "display.max_columns", None)
        d1 = (x.iloc[-1])
        print(f'd1!!!!!!!!!!!!!!!{d1}')
        print(f'x!!!!!!!!!!!!!!!{x}')


        #dd1=pandas.DataFrame([d1])
        if 0<=d1['r_position']<=1:
            return x
        else:
            return None
        return d1.to_frame().reset_index()
        return d1.to_frame()

class horizontalSensor(object):
    def __init__(self,config,influxOnline,dbClient,name,parent=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config=config
        self.parent=parent
        self.name=name
        self.influxOnline=influxOnline
        self.dbClient=dbClient
        self.channel = self.config["channel"]
        self.pos = float(self.config["x"])
        self.average_interval = int(self.config["average_interval"])
        self.average_rotations = int(self.config["average_rotations"])
#        self.minPos = float(self.config["minPos"])
        self.mininterval = float(self.config["mininterval"])*1000000
#        self.maxPos = float(self.config["maxPos"])
        self.Pos0 = float(self.config["Pos0"])
        self.Pos1 = float(self.config["Pos1"])
        self.minPos = float(self.config["minPos"])
        self.maxPos = float(self.config["maxPos"])
        try:
            self.minAlarm = float(self.config["minAlarm"])
        except:
            self.minAlarm = self.minPos
            self.config["minAlarm"]=self.minAlarm
        try:
            self.maxAlarm = float(self.config["maxAlarm"])
        except:
            self.maxAlarm = self.maxPos
            self.config["maxAlarm"]=self.maxAlarm

        self.Pos0_faktor = float(self.config["Pos0_faktor"])
        self.Pos1_faktor = float(self.config["Pos1_faktor"])

        self.rising =strtobool(self.config["rising"])
        self.falling =strtobool(self.config["falling"])
        self.std=99.0
        self.period=0.0
        self.error=1
        self.status=0

        self.show = True
        try:
            self.show = strtobool(self.config["show"])
        except:
            pass
    def updateConfig(self):
        print('update '*80)
        self.config['Pos0']=self.Pos0
        try:
            self.config['Pos1']=self.Pos1
            self.config['Pos0']=self.Pos0
            self.config['Pos0_faktor']=self.Pos0_faktor
            self.config['Pos1_faktor']=self.Pos1_faktor
        except Exception as e:
            print(e)
        print(self.config)
        self.parent.updateConfigb(self)

    def setP0(self,pos):

        self.Pos0=pos
#        try:
        #            if self.interval1>self.interval2:
        #        f=self.interval2/self.interval1
        #    else:
        #        f=self.interval1/self.interval2
        try:
            self.Pos0_faktor=self.f
        except Exception as e :
            print(e)
        #        except:
        #   pass
        print('P00')
        self.updateConfig()

    def setP1(self,pos):
        self.Pos1=pos
        try:
            self.Pos1_faktor = self.f
        except Exception as e:
            print(e)
        self.updateConfig()

    def updateInfluxStatus(self,online=True):
        self.influxOnline=online
    def getValues(self):
        query_rising = f"select mean(*) from tireslip where id='{self.name}' and time>now()-{self.average_interval}s ORDER BY time DESC "  # LIMIT {self.average_rotations}'
        self.logger.debug(f'getvalues:query={query_rising}')
        if not self.influxOnline:
            return None
        data = self.dbClient.query(query_rising)
        if len(data)==0:
            return None


        data=data["tireslip"]
        self.logger.debug(f'getvalues:result={data}')
#        self.logger.debug(f'getvalues:result={data[f"mean_position"]}')
#        self.logger.debug(f'getvalues:result={data[f"mean_position"]}')
#        self.logger.debug(f'getvalues:result={data[f"mean_interval"]}')

        r_position=(data[f"mean_r_position"].iloc[-1])
        d_position=(data[f"mean_d_position"].iloc[-1])
        position=(data[f"mean_d_position"].iloc[-1])
        interval=(data[f"mean_interval"].iloc[-1])
        self.logger.debug(f'getvalues:result={r_position}|{d_position}|{interval}')

        return d_position,r_position,interval

    def buildJSON(self):
        js = {"time": datetime.utcnow(),
               "measurement": "tireslip",
               "tags": {
                   "id": self.name,
               },
               "fields": {
                   "interval": self.interval,
                   "interval1": self.interval1,
                   "interval2": self.interval2,
                   "f": self.f,
                   "rpm": self.rpm,
                   "error": self.error,
                   "position":self.position,
                   "r_position":self.r_position,
                   "d_position":self.d_position
               }
               }
        print(js)
        return js

    def tic(self,stable,anfang,ende,interval,gearR=0):
        self.logger.info(f"tic: stable {stable}")


        if not stable:
            print(" warning : not stable")
            self.error=1
            self.status=0
            return
        data=None
        try:
            if self.rising:
                data_rising=self.selectData(anfang,ende,interval,rising=True)
                self.logger.debug(f'rising_data: {data_rising}')
                data=data_rising
            if self.falling:
                data_falling=self.selectData(anfang,ende,interval,rising=False)
                self.logger.debug(f'falling_data: {data_falling}')

                if data is None:
                    data=data_falling
                else:
#                    data=data.append(data_falling)
                    data_con=pandas.concat((data, data_falling))


                    self.logger.debug(f'complete_data: {data_con}')
                    data=data_con.mean()
                    self.logger.debug(f'average data: {data}')

            if data is None:
                self.error=1
                self.status=0
                self.logger.info(f"tic: no data")

                return
        except Exception as e:
            self.logger.warning(e)

        try:

            self.logger.debug(f'complete_data: {data}')
#            self.timestamp=data["timestamp"]
            self.interval=data["interval"]
            self.interval1=data["interval1"]
            self.interval2=data["interval2"]
            self.f=data["f"]
            self.rpm=data["rpm"]
            self.d_position=data["d_position"]
            self.r_position=data["r_position"]
            self.position=data["position"]
            self.error=0
            alarm = 0
            if self.maxAlarm < data['position']:
                alarm = 1
            if data['position'] < self.minAlarm:
                alarm += 2
            self.status = alarm

        except Exception as e:
            self.logger.info(f"could not build movement data: {e}")

            self.error=1

        # self.slip=(data["interval"][-1]-interval[-1])*self.U/interval[-1]
        # self.r_slip=(data["interval"][-1]-interval[-1])*2*math.pi/interval[-1]
        # self.clearance=(data["interval"][-1]-interval[-1])*self.r/interval[-1]
        # self.r_clearance=(data["interval"][-1]-interval[-1])/interval[-1]

    def selectData(self,  anfang, ende, interval,rising=True):
        if anfang> ende:
            return  None
        if rising:
            edge = "rising"
        else:
            edge ="falling"
        query = f"select timeestamp_{edge} as timestamp from tireslip_raw where id='{self.channel}' and time > now()-{self.average_interval}s"  # LIMIT {self.average_rotations}'
        self.logger.debug(f"raw_query: {query}")
        if self.influxOnline:
            data = self.dbClient.query(query)
        else: return None
        if len(data) == 0:
            return None

        data = data['tireslip_raw']
        data = data[data.index > anfang - pandas.Timedelta(seconds=5 + 2 * interval / 1000000)]
        data = data[data.index <= ende]
        if len(data) == 0:
            return None
#        data = data[data["timestamp"].diff() > self.mininterval]
        data = data[(data["timestamp"].diff() > self.mininterval) | (data["timestamp"].diff() < 0)]
        self.logger.debug(f"filtered rawdata:{data}")


        if len(data) == 0:
            self.logger.info(f"no raw data")
            print(f"no raw data")

            return None


        data['end'] = data.index
        data['interval'] = (data['timestamp'].diff())
        data.loc[data.interval < 0, 'interval'] += 4294967295
        try:
            interval1=data['interval'][::2]
            interval1.dropna(inplace=True)

            interval2=data['interval'][1::2]
            interval2.dropna(inplace=True)
            if (not len(interval1)>0):return None
            if (not len(interval2)>0):return None
        except:
            return None

        interval=interval1 +interval2
        print(f'interval1: {interval1}')
        print(f'interval2: {interval2}')
        if len(interval1) > len(interval2):
            interval1 = interval1[len(interval1)-len(interval2):]
        if len(interval2) > len(interval1):
            interval2 = interval2[len(interval2)-len(interval1):]

        self.logger.debug(f'interval1n: {interval1}')
        self.logger.debug(f'interval2n: {interval2}')
        if interval1.iloc[-1]>interval2.iloc[-1]:
            dir12=True
        else:
            dir12=False
        if dir12:
            int1=interval1.to_numpy()
            int2=interval2.to_numpy()
        else:
            int2=interval1.to_numpy()
            int1=interval2.to_numpy()
        print(int1,int2)
        ndata={}
        ndata["interval1"]=int1[-1]
        ndata["interval2"]=int2[-1]
        ndata["interval"]=ndata["interval1"]+ndata["interval2"]
        ndata["rpm"]=60000000/ndata['interval']
        ndata["f"]=ndata['interval1']/ndata['interval2']
        ndata['d_position'] = (self.Pos1 - self.Pos0) / (self.Pos1_faktor - self.Pos0_faktor) * (ndata['f'] - self.Pos0_faktor)
        ndata['r_position'] = ndata['d_position'] / (self.Pos1 - self.Pos0)
        ndata['position'] = ndata['d_position'] + self.Pos0
        self.logger.debug(ndata)
        if self.minPos<ndata['position']<self.maxPos:
            ndata=pandas.DataFrame([ndata])
            return ndata
        else:
            self.logger.info(f"kiln Position{ndata['position']} not in allowed range")

#        ndata = (ndata.iloc[[-1]])
        self.logger.debug(ndata)
        ndata = ndata[self.minPos<ndata['position']<self.maxPos]
        if ndata.empty:
            return None
        else:
            self.logger.debug(f'final data: {ndata}')

            return ndata

        if self.minPos<ndata['position']<self.maxPos:
            return ndata
        else:
            return None

        interval1['interval1']=int1
        interval1['interval2']=int2
        interval1['interval']=interval1['interval1']+interval1['interval2']
        interval1['rpm']=60000000/interval1['interval']
        interval1['f']=interval1['interval1']/interval1['interval2']
        interval1['d_position'] = (self.Pos1 - self.Pos0) / (self.Pos1_faktor - self.Pos0_faktor) * (interval1['f'] - self.Pos0_faktor)
        interval1['r_position']=interval1['d_position'] / (self.Pos1 - self.Pos0)
        interval1['position']=interval1['d_position']+self.Pos0
        print('final: ',interval1)
        i1=interval1.copy()
        d1 = (i1.iloc[-1])


        dd1=pandas.DataFrame([d1])
        print(dd1)
        return dd1
        return interval1.mean()
        f=interval1/interval2
        if numpy.any(f<1):
            f=1/f
        interval = interval1 + interval2
        print(f'interval: {interval}')
        #        interval=interval[-1]
#        interval1=interval1[-1]
#        interval2=interval2[-1]
        rpm=60000000/interval
        timestamp=data['timestamp'][1::2]
        faktor=f
        d_position = (self.Pos1 - self.Pos0) / (self.Pos1_faktor - self.Pos0_faktor) * (f - self.Pos0_faktor)
        r_position = d_position / (self.Pos1 - self.Pos0)
        position = self.Pos0 + d_position

        x=pandas.DataFrame()
        x['timestamp']=timestamp
        x['rpm']=rpm
        x['faktor']=faktor
        x['interval']=interval
        x['interval1']=interval1
        x['interval2']=interval2
        x['d_position']=d_position
        x['r_position']=r_position
        x['position']=position
        x.set_index('timestamp')

        pandas.set_option("display.max_rows", None, "display.max_columns", None)
        d1 = (x.iloc[-1])
        print(f'd1!!!!!!!!!!!!!!!{d1}')
        print(f'x!!!!!!!!!!!!!!!{x}')


        #dd1=pandas.DataFrame([d1])
        if 0<=d1['r_position']<=1:
            return x
        else:
            return None
        return d1.to_frame().reset_index()
        return d1.to_frame()



class gear(object):
    def __init__(self,config,influxOnline,influxClient):
        self.config=config
        self.data=[]
        self.channel = self.config["channel"]
        self.pos = float(self.config["x"])
        self.r = float(self.config["r"])
        self.mininterval = float(self.config["mininterval"])*1000000
        self.average_interval = int(self.config["average_interval"])
        self.average_rotations = int(self.config["average_rotations"])
        self.rising =strtobool(self.config["rising"])
        self.falling =strtobool(self.config["falling"])
        self.minRPM=float(self.config["minRPM"])
        self.maxRPM=float(self.config["maxRPM"])
        self.sigmaMax=float(self.config["sigmaMax"])
        self.U=2*self.r*math.pi
        self.std=99.0
        self.rpm=-1.0
        self.interval=0.0
        self.influxOnline=influxOnline
        self.dbClient=influxClient
        self.error=1
        self.status=0
        self.softwaretimeout=True
    def updateInfluxStatus(self,online=True):
        self.influxOnline=online

    def buildJSON(self):
        js = {"time": datetime.utcnow(),
               "measurement": "tireslip",
               "tags": {
                   "id": "gear",
               },
               "fields": {
                   "interval": self.interval,
                   "rpm":self.rpm,
                   "std":self.std,
                   "error":self.error

               }
               }
        return js

    def getRPM(self):
        query_rising = f"select last(rpm) as rpm,last(interval) as interval from tireslip where id='gear' and time>now()-{self.average_interval}s ORDER BY time DESC "  # LIMIT {self.average_rotations}'
        try:
            if self.influxOnline:
                data = self.dbClient.query(query_rising)
            else: return None
        except:
            return None
        if len(data)==0:
            return None


        data=(data)["tireslip"]
        rpm=(data["rpm"].iloc[-1])
        interval=(data["interval"].iloc[-1])
#        interval=(data[f"n_interval"].iloc[-1])

        return rpm,interval



    def isStable(self):
        print(self.rpm,self.std)
        try:
            return (self.minRPM<self.rpm.min())and (self.rpm.max()<self.maxRPM)and(self.std<self.sigmaMax)and self.softwaretimeout
        except:
            return False
    def getLastinterval(self):
        start=stop=-1
        if len(self.data)>0:
            d=self.data.iloc[-1]
            start_new,stop_new=d['start'],d['end']
            if stop_new>start_new:
                start=start_new
                stop=stop_new
        return start,stop


    def selectData(self,edge="rising"):
        print ('gear select data')
        query_rising = f"select timeestamp_{edge} as timestamp from tireslip_raw where id='{self.channel}' and time>now()-{self.average_interval}s ORDER BY time DESC "  # LIMIT {self.average_rotations}'
        if self.influxOnline:
            data = self.dbClient.query(query_rising)
        else: return None
        if len(data)==0: return None
        data=data['tireslip_raw']
        #data[data["timestamp"].diff() <0]+=2**32-1
        #data = data[data["timestamp"].diff() > self.mininterval]
        data['timestamp']=pandas.to_numeric(data['timestamp'])
        data = data[(data["timestamp"].diff() > self.mininterval)|(data["timestamp"].diff() <0)]
        if len(data)==0: return None
        data['end'] = data.index
        data['interval'] = (data['timestamp'].diff())
        data['interval']=pandas.to_numeric(data['interval'])
        #data[data['interval']<0]['interval1']=data[data['interval']<0]['interval']+4294967295
        #data[data['interval']>0]['interval1']=data[data['interval']>0]['interval']+1
        #print (data)
        #data['interval']=data['interval1']
#        data[data['interval']<0]['interval']+=4294967295
        data.loc[data.interval < 0, 'interval'] += 4294967295
        data['rpm'] = 60000000 / data['interval']
        data['start'] = data['end'].shift(1)
        data=data.iloc[-self.average_rotations:]
        self.rpm=data['rpm']
        self.interval=data['interval']
        print ('gear.rpm', self.rpm)
        if self.minRPM<self.rpm.mean()<self.maxRPM:
            return data
        else:
            return None

    def tic(self,softwaretimeout=False):
        if not self.influxOnline:
            self.std=99
            self.period=-1
            self.rpm=-1
            self.error = 1
            self.status = 0
            self.interval=-1
            self.softwaretimeout=softwaretimeout
        data=None

        if self.rising:
            self.dataRising=self.selectData(edge="rising")
            print ('gear rising')

        if self.falling:
            self.dataFalling=self.selectData(edge="falling")
            print('gear falling')

            if data is None:
                data=self.dataFalling
                print('gear merge')

            else:
                d1=data
                data=[d1,self.dataRising]
                data=pandas.concat(data)
#                data=data.append(self.dataRising)
                print('gear merge')

        if data is None:
            self.rpm=-1
            self.interval=-1

            self.std=99
            self.error=1
            return
        data.sort_index()
        self.data=data
        self.rpm=data['rpm'].mean()
        if len(data['rpm'])==1:
            self.std=0
        else:
            self.std=data['rpm'].std()
        self.std=numpy.nan_to_num(self.std)
        self.interval=data['interval'].mean()
        self.error=0




class Xtire2_unused(object):
    def __init__(self,dbClient,config,id):
        self.id=id
        self.dbClient=dbClient
        self.config=config
        self.r = self.config.getfloat( 'r')
        self.pos = self.config.getfloat( 'pos')
        self.U=2*self.r*math.pi
        self.client=dbClient
        self.timeout=self.config.getint('timeout')
        self.average=bool(self.config.get('tireslip','average')=='True')
        self.trigger=False
        self.rising_edge=bool(config['rising_edge'])
        self.minimum_interval=int(self.config.getfloat('minimum_interval')*1000000)
        self.minimum_slip=(self.config.getfloat('min_slip'))
        self.maximum_slip=(self.config.getfloat('max_slip'))
        self.minimum_slip_alarm=(self.config.getfloat('min_slip_alarm'))
        self.maximum_slip_alarm=(self.config.getfloat('max_slip_alarm'))
        self.maximum_std=(self.config.getfloat('max_std'))
        self.scanner=(self.config.getint('scanner'))
        self.channel=(self.config.getint('channel'))
        self.last_trigger_time=0
        self.last_status_time=0
        self.slip=0.0
        self.clearance=0.0
        self.std=-1.0
        self.rpm=0.0
        self.period=0.0


    def nextRound(self):
        self.trigger=False
    def tic(self):
        if self.rising_edge:
            query_where = f'select timestamp_rising as timestamp from tireslip_raw where channel=$channel and scanner=$scanner and time>now()-{self.timeout}s'
        else:
            query_where = f'select timestamp_falling as timestamp from tireslip_raw where id=$id and time>now()-{self.timeout}s'
        bind_params = {'channel': self.channel,'scanner': self.scanner}
        result = self.dbClient.query(query_where, bind_params=bind_params)
        result=list(result.get_points())
        if len(result)==0:
            print (f'{self.id}: missing raw intervals ')
            return
        data=pandas.DataFrame.from_dict(result)
        data=data.set_index('time')
        data2=data.diff(periods=1).dropna()
        data2=data2.rename(columns={'timestamp':'interval'})
        data2 = data2[data2['interval']>self.minimum_interval]
        #
        data=pandas.concat([data, data2], axis=1,join='inner').reindex(data2.index)

        data=data.drop(columns=['interval',])
        data2=data.diff(periods=1).dropna()
        data2=data2.rename(columns={'timestamp':'interval'})
        data2 = data2[data2['interval']>self.minimum_interval]

        data=data.rename(columns={'timestamp':'mbed_timestamp'})
        data=pandas.concat([data, data2], axis=1,join='inner').reindex(data2.index)

         #data=pandas.concat([data, data2], axis=1).reindex(data.index).dropna()
        data['rpm']=60*1000000/data['interval']

        query_where = f'select time_raw from tireslip_interval where id=$id and time>now()-{self.timeout}s'
        bind_params = {'id': self.id}
        result = self.dbClient.query(query_where, bind_params=bind_params)
        result=list(result.get_points())
        data_exits=pandas.DataFrame.from_dict(result)
#        print (type(data.index[1]))
        data=data.reset_index()
#        data=data.drop(columns=['time',])


#        data.index.to_pydatetime()
#        data.index = pandas.to_datetime(data.index)
#        data.index=data.index.to_pydatetime()

##        data.index=data.index.round('ms')
 #       data.index.set
 #       print(type(data.index[1]))
  #      print(data)

        #        , time_precision = 'n'
        d=(data.to_dict(orient='split'))['data']
        json_body=[]
        for di in d:
            try:
                #print (data_exits.loc[data_exits['time_raw'] == di[0]])
                dx= (data_exits['time_raw'] == di[0])
                if dx.any():
                    continue
                else:self.trigger=True
                self.last_trigger_time=time.time()
            except Exception as e:
                print(e)
            js = {"time": datetime.utcnow(),
                  "measurement": "tireslip_interval",
                  "tags": {
                      "id": self.id
                  },
                  "fields": {
                      "time_raw": di[0],
                      "timestamp": di[1],
                      "interval": di[2],
                      "rpm": di[3],
                  }
                  }
            json_body.append(js)

#        print (d)

        self.dbClient.write_points(json_body)
#        self.dbClient.write_points(data,
#        database = 'kiln1', measurement = 'raw')
#        print ('data exists:',data_exits)

        pass


    def getRPM(self):

        if not self.average:
            query_where = f'select LAST(*) from tireslip_interval where id=$id and time> now() - {self.timeout}s '
        else:
            query_where = f'select MEAN(*) from tireslip_interval where id=$id and time> now() - {self.timeout}s'

        bind_params = {'id': self.id}
        result = self.dbClient.query(query_where, bind_params=bind_params)
        result = list(result.get_points())
#        print (f'rpm {self.id}: {result}')
        status=0
        if len(result)==0:
            status=1
            print (f'{self.id}: no rpm')


        if status!=0:
            return (-1,-1,-1)



        if not self.average:
            rpm= result[0]['last_rpm']
            period= result[0]['last_interval']
            average=False
        else:
            rpm= result[0]['mean_rpm']
            period= result[0]['mean_interval']
            average=True

        std=self.getStd(interval=self.timeout)
        self.rpm=rpm
        return rpm, period, std


    def writeStatus(self,ok=False,tirecode=3):
        rpm,period,std=self.getRPM()
        self.period=period

        if ok:
            status=0


        else:
            status=1
            self.slip=0.0
            self.clearance=0.0
            self.interval=-1
            self.period=-1
            self.rpm=-1.0

        if status!=0 and self.last_status_time>time.time()-self.timeout:
            return
        json_body = []
        js = {"time": datetime.utcnow(),
              "measurement": "tireslip_status",
              "tags": {
                  "id": self.id
              },
              "fields": {
                  "status": status,
                  'tirecode':tirecode,
                  'pos':self.pos,
                  'slip':self.slip,
                  'clearance':self.clearance,
                  'std':self.std,
                  'rpm':self.rpm,
                  'period':int(self.period)
              }
              }
        json_body.append(js)

        #        print (d)
        print (json_body)
        self.dbClient.write_points(json_body)
        self.last_status_time=time.time()



    def getHorizontalMovementSingle(self):
        if self.average:
            query_where = f'select MEAN(*) from tireslip_raw where id=$id and time> now() - {self.timeout}s'
        else:
            query_where = f'select LAST(*) from tireslip_raw where id=$id and time> now() - {self.timeout}s'


        bind_params = {'id': self.id}
        result = self.dbClient.query(query_where, bind_params=bind_params)
        result = list(result.get_points())
        #        print (f'rpm {self.id}: {result}')
        status = 0
        if len(result) == 0:
            status = 1
            print(f'{self.id}: no signals found')

        if status != 0:
            return (-1,)

        if not self.average:
            t_rising = result[0]['last_timestamp_rising']
            t_falling = result[0]['last_timestamp_falling']
        else:
            t_rising = result[0]['mean_timestamp_rising']
            t_falling = result[0]['mean_timestamp_falling']

        std = self.getStd(interval=self.timeout)
        self.rpm = rpm
        return rpm, period, std

    def getTireslip(self,rotation):
        rpm,period,std=self.getRPM()
        print (self.id ,' period-interval', period-rotation)

        slip_interval=period-rotation
        slip=self.U*(period-rotation)/rotation
        clearance=self.r*(period-rotation)/rotation
        relative=(period-rotation)/rotation
        relative_rotation=rotation/period
        has_slip=True
        if slip<self.minimum_slip or slip>self.maximum_slip:
            print ('slip measurement impossible due to unallowed values')
            print(self.id,self.minimum_slip,self.maximum_slip,slip)
            has_slip=False
        if std>self.maximum_std:
            print ('slip measurement impossible due to high variations')
            has_slip=False
        print(f'slip {self.id}: {slip}')
        json_body=[]
        if not has_slip:
            js = {"time": datetime.utcnow(),
                  "measurement": "tireslip",
                  "tags": {
                      "id": self.id
                  },
                  "fields": {
                      "rotation_interval": int(rotation),
                      "period": int(period),
                      "period_std": std,
                      "rpm": rpm,
                      "slip_interval": int(slip_interval),
                      "relative_rotation": relative_rotation,
                      "pos":self.pos
                  }
                  }
        else:
            js = {"time": datetime.utcnow(),
                  "measurement": "tireslip",
                  "tags": {
                      "id": self.id
                  },
                  "fields": {
                      "rotation_interval": int(rotation),
                      "period": int(period),
                      "period_std":float(std),
                      "rpm":rpm,
                      "slip_interval":int(slip_interval),
                      "relative_rotation":relative_rotation,
                      "relative_slip":relative,
                      "slip":slip,
                      "clearance":clearance,
                      "pos":self.pos
                  }
                  }

        json_body.append(js)
        self.dbClient.write_points(json_body)
        tirecode=0
        if slip<self.minimum_slip_alarm:
            tirecode+=2
        if slip>self.maximum_slip_alarm:
            tirecode+=1
        self.slip=slip
        self.clearance=clearance
        self.rpm=rpm
        self.std=std
        self.period=period
        if self.id!='Tire0':
            self.writeStatus(ok=has_slip,tirecode=tirecode)
        else:
            self.writeStatus(ok=has_slip,tirecode=tirecode)


        return

    def getStd(self,interval=30):

        query_where = f'select STDDEV(rpm) from tireslip_interval where id=$id and time> now() - {interval}s'

        bind_params = {'id': self.id}
        result = self.dbClient.query(query_where, bind_params=bind_params)
        result = list(result.get_points())
        print (f'sigma  {self.id}: {result}')

        if len(result)==0:
            print (f'{self.id}: no rpm')
            return -1
        return result[0]['stddev']



#        data_exits = pandas.DataFrame.from_dict(result)
    #

if __name__=="__main__":
    import configobj

    configobj
    config=configobj.ConfigObj("../config/config.ini")
    config=configobj.ConfigObj(r"D:\pythonprojekts\CIU-NET5000\config\config.ini")
    print(config)
    k=kiln(config)
    k.tic()

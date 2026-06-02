import logging
import time
import threading
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import Qt

from python_util import util as util


class DisplayLabel(QtWidgets.QLabel):
    def __init__(self, tooltip, source, formatter):
        super().__init__()
        self.setTextFormat(QtCore.Qt.PlainText)
        self.setToolTip(tooltip)
        self.source = source
        self.formatter = formatter

class labelState(QtWidgets.QWidget):
#class labelState(QtWidgets.QRadioButton):
    finished=QtCore.pyqtSignal()
    triggerChange=QtCore.pyqtSignal(object)
    def __init__(self,desc,timeout=1,interval=10):
        super(labelState, self).__init__()
        self.red=QtGui.QPixmap('icon/red.png').scaledToHeight(20)
        self.grey=QtGui.QPixmap('icon/grey.png').scaledToHeight(20)
        self.desc=desc
        self.timeout=timeout
        self.timer=QtCore.QTimer()
        self.timer.start()
        l=QtWidgets.QHBoxLayout()
        l.setSpacing(0)
        l.setContentsMargins(0,0,0,0)
        self.setLayout(l)
        #self.textLabel=QtWidgets.QLabel()
        self.textLabel=QtWidgets.QCheckBox()
        self.textLabel.stateChanged.connect(self.triggerChange.emit)
        self.textLabel.setText(self.desc)
        self.led=QtWidgets.QLabel()
        self.led.setPixmap(self.grey)
        self.layout().addWidget(self.textLabel)
        self.layout().addWidget(self.led)
        self.graph=miniPlot(self,interval=interval)
        self.layout().addWidget(self.graph)
        #self.layout().addItem(QtWidgets.QSpacerItem(10,20,QtWidgets.QSizePolicy.Expanding))
        self.graph.finished.connect(self.finish)
#        self.setFixedHeight(20)
#        self.setStyleSheet('background-color: green')
        self.timer.timeout.connect(self.reset)
        self.blink()
    def setInterval(self,value):
        try:
            self.graph.setInterval(value)
        except Exception as e:
            print(e)

    def check(self, state=True):
        self.textLabel.setChecked(state)
    @property
    def checked(self):
        return self.textLabel.checkState()

    def finish(self):
        self.running=False
        self.finished.emit()

    def blink(self,edge=False,ts=0):
        print('blink')
        self.led.setPixmap(self.red)
        self.timer.start(self.timeout*1000)
        self.graph.addData(edge,ts)

    def reset(self):
        self.led.setPixmap(self.grey)

    def start(self,ts):
        self.running=True
        self.graph.start(ts)
import numpy
class miniPlot(QtWidgets.QLabel):
    finished= QtCore.pyqtSignal()
    def __init__(self,parent,interval):
        super(miniPlot, self).__init__(parent)
        self.firsttimestamp=0
        self.lasttimestamp=0
        self.huelle=False
#        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding))
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                 QtWidgets.QSizePolicy.Fixed))
        self.timer=QtCore.QTimer()
        self.gotData=False
        self.timer.setSingleShot(True)
        self.dt=100
        self.lastpos=0
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update_timeout)
#        self.timer.start()
        self.lastData=1
        self.newData=1
        self.h=20
        self.T=interval
        self.w=800
        self.w=self.width()

        self.dp=self.w/self.T
        self.dpt=self.dp/1000.0
        self.pos=0
        self.setFixedHeight(self.h)
#        self.setFixedWidth(self.w)
        self.data=numpy.zeros((200,100),dtype=numpy.bool_)
        self.pixi=QtGui.QPixmap(self.w,self.h)
        self.pixi.fill(QtCore.Qt.white)
        self.setPixmap(self.pixi)
        self.lastpos=self.w
        self.newline=False
        self.lastpos1=0
        self.timoutl=0
        #qimg=self.pixmap().toImage()
        #size=self.pixmap().size()
        #h = size.width()
        #w = size.height()

        #byte_str = qimg.data#.tobytes()
        #img = numpy.frombuffer(byte_str, dtype=numpy.uint8).reshape((w, h, 4))
    def setInterval(self,T=10):
        self.timer.stop()
        self.T=T
        self.dp = self.w / self.T
        self.dpt = self.dp / 1000.0
        self.pos = 0
        self.lastpos=0
        self.pixi = QtGui.QPixmap(self.w, self.h)
        self.pixi.fill(QtCore.Qt.white)
        self.setPixmap(self.pixi)
        self.finished.emit()

    def resizeEvent(self, event):
        #self.timer.stop()
        self.w = self.width()

        self.dp = self.w / self.T
        self.dpt = self.dp / 1000.0
        self.pos = 0
        self.setFixedHeight(self.h)
        #        self.setFixedWidth(self.w)
        self.data = numpy.zeros((200, 100), dtype=numpy.bool_)
        self.pixi = QtGui.QPixmap(self.w, self.h)
        self.pixi.fill(QtCore.Qt.white)
        self.setPixmap(self.pixi)

#        self.finished.emit()
    def start(self,ts):
        print (f'start:{time.time()}')
        if not self.gotData:
            print("nodata "*80 )
            return
        self.newline=True
        self.lastPlot=time.time()
        self.firstPlot=time.time()
        self.timer.stop()
        self.p=QtGui.QPainter()
        self.p.begin(self.pixi)
        self.p.setPen(QtCore.Qt.white)
#        self.p.setPen(QtCore.Qt.black)
#        self.p.drawRect(0, 0, self.w, self.h)
#        self.p.fillRect(QtCore.QRect( 0,0, self.w, self.h),QtCore.Qt.white)
#        self.p.drawLine(self.lastpos, 0, self.lastpos, self.h-1)
        self.p.setPen(QtCore.Qt.blue)
        self.p.drawLine(self.pos, self.lastData*(self.h-1), self.w, self.lastData*(self.h-1))
        self.p.end()
        self.lastPlot=0
        self.lastPlot=time.time()
#        self.w=self.width()
#        self.dp=self.w/self.T
#        self.dpt=self.dp/1000.0
#        self.pixi=QtGui.QPixmap(self.w,self.h)

        if not self.huelle:
            self.p.fillRect(QtCore.QRect(0, 0, 10, self.h), QtCore.Qt.white)
        self.dx=0
        self.timoutl=0
        self.pos=0
        self.timer.start()
        self.firstPlot=time.time()
        self.firsttimestamp=ts

    def update_timeout(self):
        t=time.time()
        self.newline=False

        try:
            self.p.begin(self.pixi)

            self.p.setPen(QtCore.Qt.white)
            #self.p.drawLine(self.lastpos1, 1, self.lastpos1, self.h-2)

            y0 = self.lastData * (self.h - 1)

            self.timoutl+=self.dt
            dx=round(self.timoutl*self.dpt)
            dx=int((t-self.lastPlot)*1000*self.dpt)
            self.lastpos1=self.pos+dx+1

            if not self.huelle:
                self.p.fillRect(QtCore.QRect(self.pos + 1, 0, dx+10, self.h), QtCore.Qt.white)
            self.p.setPen(QtCore.Qt.blue)
            self.p.drawLine(self.pos, y0,self.pos+dx, y0)
            self.p.setPen(QtCore.Qt.red)
            self.p.drawLine(self.pos+dx+ 1, 1, self.pos +dx + 1, self.h-2)
            self.p.end()
            self.setPixmap(self.pixi)
        except Exception as e:
            print(e)
        if dx+self.pos >=self.w:
            self.finished.emit()
        else:
            dt=int((time.time()-t)*1000)
            self.timer.start(self.dt-dt)
    def updatePlot(self,timestamp=0):
        self.lastPlot=time.time()
        self.timoutl=0
        # if self.newline:
        #     self.firsttimestamp=timestamp
        #     self.lasttimestamp=self.firsttimestamp
        #     self.newline=False
        #     #self.lastpos=0
        #     self.pos=0
        #     self.timer.start()
        #     return

        ddt=timestamp-self.firsttimestamp

        self.lasttimestamp=timestamp
        self.newline=False
        t=time.time()
        if timestamp==0:
            print ('timer update')
            dt=(t-self.firstPlot)*1000.0
        else:
            dt=ddt*1000.0

        dx=dt*self.dpt

        dx=min(dx,self.w)
#        print(dx,dt,self.dpt)
        prelast=self.lastpos
        self.lastpos=self.pos
        self.pos=round(dx)
        if self.lastpos>=self.w:
#            self.pos=0
            print('finish')
            self.timer.stop()
            self.finished.emit()
            return
        self.p=QtGui.QPainter()
        try:
            self.p.begin(self.pixi)
            y0=self.lastData*(self.h-1)
            y1=self.newData*(self.h-1)
            self.lastData=self.newData
            self.p.setPen(QtCore.Qt.white)
            #self.p.drawLine(self.lastpos+1,1,self.lastpos+1,self.h-2)

            if not self.huelle:
                self.p.fillRect(QtCore.QRect(self.lastpos+1, 0, self.pos-self.lastpos+50, self.h), QtCore.Qt.white)

            #            self.p.setPen(QtCore.Qt.blue)
            self.p.setPen(QtCore.Qt.blue)
#            self.p.drawLine(self.lastpos+1,y0,self.lastpos+1,y0)
            self.p.drawLine(self.lastpos,y0,self.pos,y0)
            self.p.drawLine(self.pos,y0,self.pos,y1)
#            self.pos+=1
            self.p.setPen(QtCore.Qt.red)
#            self.p.drawLine(self.pos,y0,self.pos,y1)
            self.p.drawLine(self.pos+1,1,self.pos+1,self.h-2)

            self.p.end()
            self.setPixmap(self.pixi)
        except Exception as e:
            print(e)
        self.timer.start()
        pass
    def addData(self,edge,timestamp):
        try:
            self.newData=not self.lastData
            if edge:
                self.newData=1
            else:
                self.newData=0
            self.gotData=True
        except Exception as e:
            print(e)
        try:
            self.updatePlot(timestamp)
        except Exception as e:
            print(e)




class ledPanel(QtWidgets.QGroupBox):
    def __init__(self, parent,receiver,title='trigger',desc='channel',timeout=1,channels=8):
        super(ledPanel, self).__init__(title, parent)
        self.triggers=set()
        self.interval=30
        self.titlename=title
        self.setTitle(f'{self.titlename} - [{self.interval}s]' )
        self.receiver=receiver
        self.receiver.signalNewTimeData.connect(self.checkData)
        self.desc=desc
        self.timeout=timeout
        self.leds=[]
        self.channels=channels
        l=QtWidgets.QVBoxLayout()
        l.setSpacing(0)
        l.setContentsMargins(0,0,0,0)
        self.setLayout(l)
        self.charttime=0
        self.synctime=0
    #    self.setStyleSheet( 'border: 0;margin:0; background: white; ')
        for i in range(self.channels):
            led=labelState(desc=f'{self.desc} {i}',timeout=self.timeout,interval=self.interval)
            led.triggerChange.connect(self.registerTrigger)
            self.leds.append(led)
            led.finished.connect(self.sync)
            self.layout().addWidget(led)
#        self.leds[0].check(True)
        self.timeslide=QtWidgets.QSlider(orientation=Qt.Qt.Horizontal)
        self.timeslide.setMinimum(5)
        self.timeslide.setMaximum(15*60)
        self.layout().addWidget(self.timeslide)
        self.timeslide.setValue(self.interval)
        self.timeslide.valueChanged.connect(self.setInterval)
        self.starting=False
        self.start()

    def setInterval(self,value):
        print(value)
        old_interval=self.interval
        self.interval=value
        self.setTitle(f'{self.titlename} - [{value}s]' )
        for led in self.leds:
            try:
                print(led)

                led.setInterval(value)
            except Exception as e:
                print(e)
                self.interval=old_interval
                for led in self.leds:
                    try:
                        print(led)

                        led.setInterval(value)
                    except Exception as e:
                        print(e)

    def start(self):
        self.starting=True
        return
        for led in self.leds:
            led.start()

    def sync(self):
        all_done=True
        for led in self.leds:
            if led.running:
                all_done=False
                break
        if all_done:
            self.start()
            self.synctime=time.time()

    def registerTrigger(self,state):
        print (state,self.sender())
        led_index= (self.leds.index(self.sender()))
        if state>0:self.triggers.add(led_index)
        else:self.triggers.remove(led_index)
        print(self.triggers)



    def startLeds(self,ts):
        for led in self.leds:
            led.start(ts)
            self.synctime=time.time()
    def checkData(self,data):
        if (time.time()-self.synctime)>(self.interval+10):
            self.starting=True
        try:
            if self.starting:
#                print ('starting')
                #print(data)

                if ((data[0]==False)and (data[1] in self.triggers)):
                    self.startLeds(data[2])
                    self.starting=False
        except Exception as e:
            print(e)
        try:
            if not self.starting:
                self.leds[data[1]].blink(edge=data[0],ts=data[2])
        except Exception as e:
            print(e)
#        print (data)
        #        self.leds[data[1]].graph.update()
        return
        for led in self.leds:
            led.graph.update()

class analogPlot(QtWidgets.QGroupBox):
    def __init__(self,parent,scanner):
        QtWidgets.QGroupBox.__init__(self,parent=parent)
        self.layout=QtWidgets.QHBoxLayout()
#        self.control=plotControll(self)
#        self.layout.addWidget(self.control)
        self.plot=plotWidget(self,scanner)
        self.layout.addWidget(self.plot)
        self.setLayout(self.layout)



class scanlinePlot(QtWidgets.QGroupBox):
    def __init__(self,parent,scanner):
        QtWidgets.QGroupBox.__init__(self,parent=parent)
        self.layout=QtWidgets.QHBoxLayout()
        self.control=plotControll(self)
        self.layout.addWidget(self.control)
        self.plot=liveblot(self,scanner)
        self.layout.addWidget(self.plot)
        self.setLayout(self.layout)

        self.control.trigger.connect(self.plot.trigger)
        self.control.setVideoMode.connect(self.plot.setVideomode)
        self.control.SignalSetFOV.connect(self.plot.setFOV)
        self.control.setStatusMode.connect(self.plot.setStatusMode)

class plotControll(QtWidgets.QWidget):
    trigger=QtCore.pyqtSignal()
    setVideoMode=QtCore.pyqtSignal(object)
    SignalSetFOV=QtCore.pyqtSignal(object)
    setStatusMode=QtCore.pyqtSignal(object)
    def __init__(self,parent):
        QtWidgets.QWidget.__init__(self,parent=parent)
        self.layout=QtWidgets.QVBoxLayout()
        self.xGroup=QtWidgets.QGroupBox('Scanline')
        self.xGroup.setLayout(QtWidgets.QVBoxLayout())
        self.Button360=QtWidgets.QRadioButton('360')
        self.ButtonFOV=QtWidgets.QRadioButton('FOV')
        self.ButtonDark=QtWidgets.QRadioButton('Dark')
        self.xGroup.layout().addWidget(self.ButtonFOV)
        self.xGroup.layout().addWidget(self.Button360)
        self.xGroup.layout().addWidget(self.ButtonDark)
        self.layout.addWidget(self.xGroup)

        self.yGroup=QtWidgets.QGroupBox('Videobits')
        self.yGroup.setLayout(QtWidgets.QVBoxLayout())
        self.Button16Bit=QtWidgets.QRadioButton('16 Bit')
        self.Button14Bit=QtWidgets.QRadioButton('14 BIt')
        self.Button12Bit=QtWidgets.QRadioButton('12 Bit')
        self.ButtonStatusBit1=QtWidgets.QCheckBox('Bit 15')
        self.ButtonStatusBit2=QtWidgets.QCheckBox('Bit 14')
        self.ButtonStatusBit3=QtWidgets.QCheckBox('Bit 13')
        self.ButtonStatusBit4=QtWidgets.QCheckBox('Bit 12')
        self.yGroup.layout().addWidget(self.Button16Bit)
        self.yGroup.layout().addWidget(self.Button14Bit)
        self.yGroup.layout().addWidget(self.Button12Bit)
        self.layout.addWidget(self.yGroup)

        self.StatusGroup=QtWidgets.QGroupBox('Statusbits')
        self.StatusGroup.setLayout(QtWidgets.QVBoxLayout())

        self.StatusGroup.layout().addWidget(self.ButtonStatusBit1)
        self.StatusGroup.layout().addWidget(self.ButtonStatusBit2)
        self.StatusGroup.layout().addWidget(self.ButtonStatusBit3)
        self.StatusGroup.layout().addWidget(self.ButtonStatusBit4)
        self.layout.addWidget(self.StatusGroup)


        self.refreshGroup=QtWidgets.QGroupBox('Refresh')
        self.refreshGroup.setLayout(QtWidgets.QVBoxLayout())
        self.checkboxTimeout=QtWidgets.QCheckBox('timeout')
        self.checkboxTrigger=QtWidgets.QCheckBox('trigger')
        self.buttonTrigger=QtWidgets.QPushButton('manual')
        self.buttonTrigger.clicked.connect(self.trigger.emit)

        self.refreshGroup.layout().addWidget(self.checkboxTimeout)
        self.refreshGroup.layout().addWidget(self.checkboxTrigger)
        self.refreshGroup.layout().addWidget(self.buttonTrigger)
        self.layout.addWidget(self.refreshGroup)


        self.setLayout(self.layout)
        self.ButtonFOV.setChecked(True)
        self.Button14Bit.setChecked(True)
        self.Button12Bit.clicked.connect(self.set12BitVideo)
        self.Button14Bit.clicked.connect(self.set14BitVideo)
        self.Button16Bit.clicked.connect(self.set16BitVideo)
        self.ButtonFOV.clicked.connect(self.setFOV)
        self.Button360.clicked.connect(self.set360)
        self.ButtonDark.clicked.connect(self.setDark)
        self.ButtonStatusBit1.stateChanged.connect(self.setStatusBits)
        self.ButtonStatusBit2.stateChanged.connect(self.setStatusBits)
        self.ButtonStatusBit3.stateChanged.connect(self.setStatusBits)
        self.ButtonStatusBit4.stateChanged.connect(self.setStatusBits)

    def set12BitVideo(self):
        self.setVideoMode.emit(12)

    def set14BitVideo(self):
        self.setVideoMode.emit(14)

    def set16BitVideo(self):
        self.setVideoMode.emit(16)

    def setFOV(self):
        self.SignalSetFOV.emit(0)

    def set360(self):
        self.SignalSetFOV.emit(1)

    def setDark(self):
        self.SignalSetFOV.emit(2)

    def setStatusBits(self):
        i=0
        if self.ButtonStatusBit1.isChecked():
            print ('Hallo')
            i=1
        i=i<<1
        if self.ButtonStatusBit2.isChecked():
            i+=1
        i=i<<1
        if self.ButtonStatusBit3.isChecked():
            i+=1
        i=i<<1
        if self.ButtonStatusBit4.isChecked():
            i+=1
        self.setStatusMode.emit(i)
        print('status: ',i)


class liveblot(QtWidgets.QWidget):


    def __init__(self,parent,scanner):
        QtWidgets.QWidget.__init__(self,parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                 QtWidgets.QSizePolicy.Expanding))
#        self.c=plotControll(self)
        self.datalen=12000
        self.lock = threading.Lock()
        self.vidmax=0
        self.scanner=scanner
#deaktivate liveplot
        self.scanner.receiver.signalGotLine.connect(self.setData)
#        self.setFixedHeight(160)
#        self.setFixedWidth(240)
        self.setMinimumHeight(200)

        self.videomask12= int('0000 1111 1111 1111'.replace(" ", ""), 2)
        self.videomask14= int('0011 1111 1111 1111'.replace(" ", ""), 2)
        self.videomask16= int('1111 1111 1111 1111'.replace(" ", ""), 2)

        self.statusmask1 = int('1000 0000 0000 0000'.replace(" ", ""), 2)
        self.statusmask2 = int('0100 0000 0000 0000'.replace(" ", ""), 2)
        self.statusmask3 = int('0010 0000 0000 0000'.replace(" ", ""), 2)
        self.statusmask4 = int('0001 0000 0000 0000'.replace(" ", ""), 2)
        self.videomask=self.videomask14
        self.vidmask=numpy.ones(self.width(),dtype=int)*self.videomask
        print (self.videomask)
        self.start=0
        self.mode=0
        self.minVid=None
        self.maxVid=None
        self.view=self.datalen/3
        self.f=round(self.view/self.width())
        self.offset=800
        self.profileCurser=-1
        self.statusbitmode=0
        self.statuslines=[]
        self.statuslinesY=[]
        self.ready2plot=False

    def setStatusMode(self,mode):
        self.statusbitmode=mode

    def setVideomode(self,mode):
        if mode==12:
            self.videomask=self.videomask12
        elif mode==14:
            self.videomask = self.videomask14
        elif mode==16:
            self.videomask = self.videomask16
        self.trigger()
        print ('Videomode', mode)
    def trigger(self):
        self.minVid=None
        self.maxVid=None
        self.vidmax=0

    def resizeEvent(self, event):
        self.trigger()
        self.f=int(self.view/self.width()+1)
        l=round(self.view/self.f)
#        l=1000
        self.vidmask=numpy.ones(l,dtype=int)


    def setFOV(self,l):
        self.mode=l
        if l==0:
            self.view=int(self.datalen/3)
            self.f=(self.view/400)
            self.start=0
        elif l==1:
            self.view=self.datalen
            self.f=(self.view/400)
            self.start=0

        elif l==2:
            self.view=int(self.datalen/3*2)
            self.f=(self.view/400)
            self.start=int(self.view/2)
        self.f=int(self.f)
        self.f=max(self.f,1)

        #print(f'setFOV: {self.f} {self.view}')
        self.trigger()
#        self.f=int(self.view/self.width()+1)
        l=round(self.view/self.f)
        self.vidmask=numpy.ones(l,dtype=int)
        self.trigger()

    def preparePlot(self):
        self.bits = True
        self.lock.acquire()
        data=numpy.copy(self.data)
        self.lock.release()
        try:
            #            self.lock.acquire()
            # video=(data.video_data)[:self.view:self.f][0:len(self.vidmask)]

            video = data[self.start:self.view+self.start:self.f][0:len(self.vidmask)]
            #            print (len(video), self.width())
            vid = numpy.copy(numpy.array(video))
            vid = vid.astype(int)
            #            print (vid.dtype,self.vidmask.dtype)
            #            print(self.videomask)
            statuslinesY = []
            b = 1
            if self.bits:
                for i in range(4):
                    b1 = self.statusbitmode & b
                    #  print('/'*80)
                    #  print(b1,b,self.statusbitmode)

                    if b1 > 0:
                        bb = b1 << 12
                        vid_status = numpy.bitwise_and(vid, self.vidmask * bb)
                        statuslinesY.append(self.height() - (numpy.right_shift(vid_status, 12 + i) * 20 + i * 30 + 10))
                    b = b << 1
            vid = numpy.bitwise_and(vid, self.vidmask * self.videomask) - self.offset
            vidmax = max(vid)  # /self.height()
            if self.vidmax == 0:
                self.vidmax = vidmax
            else:
                self.vidmax = max(self.vidmax, vidmax)
            vidmax = self.vidmax / self.height()

            vidmin = max(vid)
            vid = vid / vidmax
            vid = self.height() - vid
            vid = vid.astype(int)
            if self.minVid is None:
                self.minVid = vid
            else:
                self.minVid = numpy.maximum(vid, self.minVid)
            if self.maxVid is None:
                self.maxVid = vid
            else:
                self.maxVid = numpy.minimum(vid, self.maxVid)

            l = len(video)
            # x=range(l),l
            x = numpy.linspace(0, self.width(), l, dtype=int)
            statuslines = []
            if self.bits:
                for line in (statuslinesY):
                    data = numpy.vstack((x, line)).T
                    line = QtGui.QPolygon()
                    for p in data:
                        line.append(QtCore.QPoint(*p))
                    statuslines.append(line)

            data = numpy.vstack((x, vid)).T
            datamin = numpy.vstack((x, self.minVid)).T
            datamax = numpy.vstack((x, self.maxVid)).T
            line = QtGui.QPolygon()
            minline = QtGui.QPolygonF()
            maxline = QtGui.QPolygonF()

            for p in data:
                line.append(QtCore.QPoint(*p))
            self.line = line
            for p in datamin:
                minline.append(QtCore.QPoint(*p))
            #            self.minline=minline
            for p in datamax[::-1]:
                minline.append(QtCore.QPoint(*p))
#            self.maxline = minline

            self.repaint()
        except Exception as e:
            print(e)
            print('ÄÄÄÄÄÄ')
            return
        finally:
            pass
        self.lock.acquire()
        self.statuslines=statuslines
        self.maxline = minline
        self.lock.release()
        self.ready2plot=True

    #
    # self.lock.release()


    def setData(self,data):
        self.bits=True
        datalen=len(data.video_data)
        if datalen!= self.datalen:
            self.datalen=datalen
            self.setFOV(self.mode)
        self.data=numpy.copy(data.video_data)
#        self.preparePlot()
        self.t=threading.Thread(target=self.preparePlot)
        self.t.daemon=True
        self.t.run()
#        self.t.start()
        return
        try:
#            self.lock.acquire()
            #video=(data.video_data)[:self.view:self.f][0:len(self.vidmask)]
            video=(data.video_data)[:self.view:self.f][0:len(self.vidmask)]
#            print (len(video), self.width())
            vid=numpy.copy(numpy.array(video))
            vid = vid.astype(int)
#            print (vid.dtype,self.vidmask.dtype)
#            print(self.videomask)
            statuslinesY=[]
            b = 1
            if self.bits:
                for i in range(4):
                    b1=self.statusbitmode&b
                  #  print('/'*80)
                  #  print(b1,b,self.statusbitmode)

                    if b1>0:
                        bb=b1<<12
                        vid_status=numpy.bitwise_and(vid,self.vidmask*bb)
                        statuslinesY.append(self.height()-(numpy.right_shift(vid_status,12+i)*20+i*30+10))
                    b=b<<1

            vid=numpy.bitwise_and(vid,self.vidmask*self.videomask) -self.offset
            vidmax = max(vid)  # /self.height()
            if self.vidmax==0:
                self.vidmax=vidmax
            else:
                self.vidmax=max(self.vidmax,vidmax)
            vidmax=self.vidmax/self.height()

            vidmin=max(vid)
            vid=vid/vidmax
            vid=self.height()-vid
            vid=vid.astype(int)
            if self.minVid is None:
                self.minVid=vid
            else:
                self.minVid=numpy.maximum(vid,self.minVid)
            if self.maxVid is None:
                self.maxVid=vid
            else:
                self.maxVid=numpy.minimum(vid,self.maxVid)

            l=len(video)
            #x=range(l),l
            x=numpy.linspace(0,self.width(),l,dtype=int)
            self.statuslines=[]
            if self.bits:
                for line in (statuslinesY):
                    data = numpy.vstack((x, line)).T
                    line=QtGui.QPolygon()
                    for p in data:
                        line.append(QtCore.QPoint(*p))
                    self.statuslines.append(line)

            data= numpy.vstack((x, vid)).T
            datamin= numpy.vstack((x, self.minVid)).T
            datamax= numpy.vstack((x, self.maxVid)).T
            line=QtGui.QPolygon()
            minline=QtGui.QPolygonF()
            maxline=QtGui.QPolygonF()

            for p in data:
                line.append(QtCore.QPoint(*p))
            self.line=line
            for p in datamin:
                minline.append(QtCore.QPoint(*p))
#            self.minline=minline
            for p in datamax[::-1]:
                minline.append(QtCore.QPoint(*p))
            self.maxline=minline

            self.repaint()
        except Exception as e:
            print(e)
        finally:
            pass
#
            #self.lock.release()
    def mouseMoveEvent(self,event) :
        self.profileCurser=event.pos().x()

    def paintData(self,painter):
        painter.begin(self)
        painter.setPen(QtCore.Qt.black)
#        painter.drawPolygon(self.line)
        try:
            painter.setPen(QtCore.Qt.red)
#            painter.drawPolygon(self.maxline)
            painter.setPen(QtCore.Qt.blue)
#            painter.drawPolyline(self.minline)
            self.brush=QtGui.QBrush(QtCore.Qt.gray)
            path =QtGui.QPainterPath()
            path.addPolygon(self.maxline)
            painter.fillPath(path, self.brush);
            painter.setPen(QtCore.Qt.black)
            painter.drawPolyline(self.line)
            if self.profileCurser>0:
                painter.setPen(QtCore.Qt.red)
                painter.drawLine(self.profileCurser,0,self.profileCurser,self.height())
            p=QtGui.QPen()
            p.setColor(QtGui.QColor(0x9999ff))
            p.setWidth(2)
            painter.setPen(p)
#            painter.setPen(QtCore.Qt.blue)
            if self.bits:
                for line in self.statuslines:
                    painter.drawPolyline(line)

        except Exception as e:
            print('xx',e)
        painter.end()
        #self.update()
#        self.p.drawPolyline(self.lastpos+1,1,self.lastpos+1,self.h-2)


    def paintEvent(self, event):
        if self.ready2plot:

            painter = QtGui.QPainter(self)
            self.paintData(painter)
class plotWidget(QtWidgets.QWidget):
    def __init__(self,parent,scanner):
        QtWidgets.QWidget.__init__(self,parent=parent)
        self.len=800
        self.values=numpy.zeros((6,self.len))
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                 QtWidgets.QSizePolicy.Expanding))
        self.scanner=scanner
        self.setMinimumHeight(200)
        self.ready2plot=False
        self.plotting=False
        self.polys=[]
        self.prepare=False
        self.data=[]
        self.lastData=0
        self.scanner.receiver.signalNewAnalogData.connect(self.setData)


    def xyzf(self):
#        print(len(self.data))
        if len(self.data)==0:return
        self.ready2plot=False
        self.prepare=True
        try:

            data = self.data
            l=len(data)
#            print(l)
#            print(data)
            for pos,item in enumerate(data):
                for i in range(6):
                    self.values[i,pos]=item[i]
            self.values=numpy.roll(self.values,-l)
            self.data=[]
            self.ready2plot=False
            polys = []
            for i in range(6):
                poly = QtGui.QPolygon()
                for n,v in enumerate(self.values[i]):
                    p=QtCore.QPoint(n,200-int(v*200))
                    poly.append(p)
                polys.append(poly)
            self.polys=polys
            self.ready2plot=True
            self.update()

        except Exception as e:
            print(e)
        self.prepare=False
    def setData(self,data):
        self.data.append(data)
        if (len(self.data)<50):
            return
        if not self.prepare:
            try:
                if self.t.is_alive():
                    print('thread still running')
                    return
            except Exception as e:
                print(e)
            try:
                self.t=threading.Thread(target=self.xyzf)
                self.prepare = True

                self.t.daemon=True
                self.t.run()

            except Exception as e:
                print(e)
    def paintData(self,painter):
        if self.ready2plot:
#            if self.plotting:return
            if painter.isActive():
                print('painter still active')
                return
            painter.begin(self)
            painter.setPen(QtCore.Qt.black)
            for i,poly in enumerate(self.polys):
                painter.setPen(QtGui.QColor(i*40,255-i*40,120-i*20))
                painter.drawPolyline(poly)
            painter.end()

    def paintEvent(self, event):
        print('paintevent',event)
        if self.ready2plot:
            if not self.plotting:
                self.plotting=True
                painter = QtGui.QPainter()
                self.paintData(painter)
        self.plotting=False
class LabelCollection:
    def __init__(self):
        super().__init__()
        self.labels = []
        self.layout = QtWidgets.QFormLayout()
        self.setLayout(self.layout)

    @util.assert_equal_thread()
    def update_data(self):
        for l in self.labels:
            try:
                v = l.source(self)
                l.setText(l.formatter.format(v))
            except Exception:
                l.setText(self.tr("N/A"))

    def add_label(self, desc, tooltip, source, formatter="{}"):
        label = DisplayLabel(tooltip=tooltip, source=source, formatter=formatter)
        self.labels.append(label)
        self.layout.addRow(desc, label)

class ReceiverInfo(QtWidgets.QGroupBox, LabelCollection):
    def __init__(self, title, receiver, parent):
        super(ReceiverInfo, self).__init__(title, parent)
        self.receiver = receiver
        self.add_label(self.tr("Received Datagrams"),
                       self.tr("Number of received UDP datagrams."),
                       lambda self: self.receiver.received_datagrams,
                       "{:n}")
        self.add_label(self.tr("Received Lines"),
                       self.tr("Number of successfully received lines."),
                       lambda self: self.receiver.receivedLines,
                       "{:n}")
        self.add_label(self.tr("Rejected Lines"),
                       self.tr("Number of rejected lines."),
                       lambda self: "{:n} ({:.2f}%)".
                       format(self.receiver.rejectedLines,
                              self.receiver.rejectedLines / (self.receiver.receivedLines + self.receiver.rejectedLines) * 100.0))
        self.add_label(self.tr("Scanner Online status"),
                       self.tr("Reiceiver operation state 'scanner online'."),
                       lambda self: "{:n} ({:.2f}%)".
                       format(self.receiver.rejectedLines,
                              self.receiver.rejectedLines / (self.receiver.receivedLines + self.receiver.rejectedLines) * 100.0))


class ScannerBox(QtWidgets.QGroupBox, LabelCollection):
    def __init__(self, title, scanner, parent):
        super(ScannerBox, self).__init__(title, parent)
        self.scanner = scanner
        self.add_label(self.tr("Index"),
                       self.tr("Scanner display index."),
                       lambda self: "{}".
                       format(self.scanner.displayIndex))
        self.add_label(self.tr("Model"),
                       self.tr("Scanner Model."),
                       lambda self: "{}".
                       format(self.scanner.model))
        self.add_label(self.tr("S/N"),
                       self.tr("Scanner serial number."),
                       lambda self: "{}".
                       format(self.scanner.serial))
        self.add_label(self.tr("last_trigger"),
                       self.tr("last_trigger."),
                       lambda self: "{}".
                       format(self.scanner.last_trigger))
        self.add_label(self.tr("next_to_last_trigger"),
                       self.tr("next_to_last_trigger."),
                       lambda self: "{}".
                       format(self.scanner.next_to_last_trigger))
        self.add_label(self.tr("next_to_next_last_trigger"),
                       self.tr("next_to_next_last_trigger."),
                       lambda self: "{}".
                       format(self.scanner.next_to_next_last_trigger))
        self.add_label(self.tr("timed out"),
                       self.tr("is the scanner timed out."),
                       lambda self: "{}".
                       format(self.scanner.timeOutStatus))


class ScanlineWidget(QtWidgets.QWidget):
    def __init__(self, scanner, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.layout = QtWidgets.QHBoxLayout()

        self.scannerplot = liveblot(self, scanner)
        self.layout.addWidget(self.scannerplot)

        self.setLayout(self.layout)


class ScannerInfo1(QtWidgets.QWidget):
    def __init__(self, scanner, parent,config):
        super().__init__(parent)
        print ('scannerinfo',config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.layout = QtWidgets.QVBoxLayout()
        self.scannerinfo=ScannerInfo(scanner=scanner,parent=self)
        self.layout.addWidget(self.scannerinfo)
        if 'plottireslip' in config:
            self.ledPanel=ledPanel(parent=self,title='tireslip',receiver=scanner.receiver)
            self.layout.addWidget(self.ledPanel)
        if 'plotscanline'in config:
            self.scannerplot = scanlinePlot(self, scanner)
            self.layout.addWidget(self.scannerplot)
        if 'plotanalogvalues'in config:
            self.analogplot = analogPlot(self, scanner)
            self.layout.addWidget(self.analogplot)

        self.setLayout(self.layout)

class ScannerInfo(QtWidgets.QWidget):
    def __init__(self, scanner, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.layout = QtWidgets.QHBoxLayout()
        self.receiver_box = ReceiverInfo(self.tr("Receiver Info"), scanner.receiver, self)
        self.layout.addWidget(self.receiver_box)
        
        self.scanner_box = ScannerBox(self.tr(scanner.type), scanner, self)
        self.layout.addWidget(self.scanner_box)
#        self.ledPanel=ledPanel(parent=self,title='tireslip',receiver=scanner.receiver)
#        self.layout.addWidget(self.ledPanel)
#        self.scannerplot=liveblot(self,scanner)
#        self.layout.addWidget(self.scannerplot)

        self.setLayout(self.layout)
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.update_data)

        QtCore.QMetaObject.invokeMethod(self.update_timer, "start")

    @QtCore.pyqtSlot()
    @util.noexcept
    def update_data(self):
        try:
            self.receiver_box.update_data()
            self.scanner_box.update_data()
        except Exception:
            self.logger.debug("Problem updating data", exc_info=True)

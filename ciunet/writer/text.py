import os
import logging
from collections import OrderedDict
import json
import datetime
import configparser
import time

from Qt import QtCore
import numpy

from python_util import util as util
from ciunet.processing.ComposedImageView import ComposedImageViewer


class TextWriter(QtCore.QObject):
    tireslip_max_file_age = 300.0

    def __init__(self, composed_image, config, kiln, parent):
        super().__init__(parent)
        print (type(config))
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kiln = kiln
        self.composed_image = composed_image
        self.source_type=str(config['source_type'])
        self.image_viewer = ComposedImageViewer(config.get("image", {}), composed_image, self)
        self.active = config.get("active", False)
        self.filename_timestamp = config.get("filename_timestamp", False)
        self.text_filename = str(config["dest"])
        self.text_filename = os.path.abspath(self.text_filename)
        self.tireslip_filename = str(config["tireslip_filename"])
        self.tireslip_filename = os.path.abspath(self.tireslip_filename)
        self.num_tire_sensors = int(config.get("num_tire_sensor", 4))
        self.horizontal_sensor = int(config.get("horizontal_sensor", -1))
        self.indent = int(config.get("indent", -1))
        if self.indent <= 0:
            self.indent = None
        self.scanner_status_data = {}
        self.kiln.signalGotStatusData.connect(self.getStatusData)

    @QtCore.Slot(object, object)
    @util.noexcept
    def getStatusData(self, data, host):
        for scanner in self.kiln.scanners:
            scanner_ip = scanner.receiver.ip.toString()
            if host != scanner_ip:
                continue
            self.scanner_status_data[scanner.name] = data

    def parse_tireslip_tire(self, cp, fp, tirenum):
        section_data = None
        section = "Tire{}".format(tirenum)
        options_to_read = [("Position", "position", float),
                           ("Interval", "interval", float),
                           ("RPM", "rpm", float),
                           ("Result1", "result1", lambda x: float(x) / 1000.0),  # result in m!
                           ("Result2", "result2", lambda x: float(x) / 1000.0)]  # result in m!
        if cp.has_section(section):
            section_data = OrderedDict()
            for src_name, dest_name, transform in options_to_read:
                if cp.has_option(section, src_name):
                    section_data[dest_name] = transform(cp.get(section, src_name))
            if section == "Tire0":
                section = "Gear"
            section_data["name"] = section
        return section_data

    def parse_tireslip_data(self, filename):
        if time.time() - os.path.getmtime(filename) > self.tireslip_max_file_age:
            raise RuntimeError('Tireslip file too old.')
        with open(filename, "r") as f:
            cp = configparser.ConfigParser()
            cp.read_file(f)
            tireslip_data = []
            horizontal_data = None

            for i in range(self.num_tire_sensors):
                d = self.parse_tireslip_tire(cp, f, i)
                if d is not None:
                    tireslip_data.append(d)
            if self.horizontal_sensor >= 0:
                horizontal_data = self.parse_tireslip_tire(cp, f, self.horizontal_sensor)
            return (tireslip_data, horizontal_data)

    def parse_tireslip_data_influx(self):
        tireslip_data=[]
        tsc=self.kiln.tireslip_calculator
        v = tsc.gear.getRPM()
        if v is None:
            return
            interval = -1
            rpm=-1
        else:
            rpm, interval=v
            interval=interval/1000000
        position = tsc.gear.pos
        json_data={}
        json_data['name']='gear'
        json_data['result1']=0
        json_data['result2']=0
        json_data['rpm']=rpm
        json_data['interval']=interval
        json_data['position']=position

        tireslip_data.append(json_data)

        for t in (tsc.tires):
            try:
                v=t.getValues()
                if v==None:
                    continue

                position=t.pos
                name=t.name
                json_data = {}
                json_data['name'] = name
                r=t.getValues()
                if not r is None:
                    slip, clearance, interval = r
                    slip = slip / 1000.0
                    clearance = clearance / 1000.0
                    interval = interval / 1000000

                    json_data['result1'] = slip
                    json_data['result2'] = clearance
    #                json_data['rpm'] = rpm
                    json_data['interval'] = interval
                json_data['position'] = position
                tireslip_data.append(json_data)
            except:
                pass
        return tireslip_data

    def build_data(self):
        if not self.kiln.all_scanner_ok():
            self.logger.warning('scandata not valid!!!!! Error 375')
            return

        now = util.datetime_helper.current_local_time()
        data = OrderedDict()
        data["description"] = "{} image output file".format(QtCore.QCoreApplication.applicationName())
        data["application_version"] = QtCore.QCoreApplication.applicationVersion()
        data["time"] = str(now)
        data["timestamp"] = now.timestamp()
        kiln = OrderedDict()
        try:
            kiln["name"] = self.kiln.description.decode()
        except Exception as e:
            self.logger.warning("Cannot add kiln name: {}".format(e))
#         try:
#             kiln["rpm"] = self.kiln.rpm
#         except Exception as e:
#             self.logger.warning("Cannot add kiln rpm: {}".format(e))
        try:
            kiln["rpm"] = self.kiln.rpm
        except Exception as e:
            self.logger.warning("Cannot add kiln rpm: {}".format(e))
        try:
            kiln["pos_left"] = self.kiln.kiln_start
            kiln["pos_right"] = self.kiln.kiln_end
        except Exception as e:
            self.logger.warning("Cannot add kiln start/end: {}".format(e))

        try:
            if self.source_type=='statusfile':
                tireslip_data, horizontal_data = self.parse_tireslip_data(self.tireslip_filename)
                kiln["tireslip"] = tireslip_data
                kiln["horizontal_movement"] = horizontal_data["result1"]
                kiln["horizontal_position"] = horizontal_data["result2"]
            else:
                tireslip_data = self.parse_tireslip_data_influx()
                try:
                    tsc = self.kiln.tireslip_calculator
                    dpos, pos = tsc.getMovement()
                    kiln["horizontal_movement"] = dpos
                    kiln["horizontal_position"] = pos
                except Exception as e:
                    self.logger.info(f'could not get horizontal movement data: {e}')

                kiln["tireslip"] = tireslip_data

        except Exception as e:
            self.logger.warning("Cannot add tireslip data: {}".format(e))
        data["kiln"] = kiln

        image_data = self.image_viewer.image
        try:
            img = OrderedDict()
            img["width"] = self.image_viewer.width
            img["height"] = self.image_viewer.height
            img["data"] = numpy.round(image_data, 2).tolist()

            data["image"] = img
        except Exception as e:
            self.logger.warning("Cannot add image: {}".format(e))

        profiles = {}
        filters = [("min", numpy.nanmin),
                   ("max", numpy.nanmax),
                   ("mean", numpy.nanmean)
                   ]
        for name, filter_ in filters:
            try:
                profile = filter_(image_data, axis=0)
#                if  numpy.min(profile) < 0.1:
#                    self.logger.info('Medas text file not written')
#                    print ('Medas text file not written')
#                    return None

                profiles[name] = numpy.round(profile, 2).tolist()
            except Exception as e:
                self.logger.warning("Cannot add profile: {}".format(e))
        data["profiles"] = profiles


        try:
            status_data = OrderedDict()
            for key, d in self.scanner_status_data.items():
                try:
                    scanner_data = OrderedDict()
                    scanner_data["TSS1"] = d["digital_ins"]["p33"]["value"]
                    scanner_data["TSS2"] = d["digital_ins"]["p34"]["value"]
                    status_data[key] = scanner_data
                except Exception as e:
                    self.logger.debug("Cannot add status data for scanner {}: {}".format(key, e))
            data["status_data"] = status_data
        except Exception as e:
            self.logger.debug("Cannot add status data: {}".format(e))

        return data

    def write_text_file(self, data):
        if data is None:
            return
        text_filename = self.text_filename
        if self.filename_timestamp:
            head, tail = os.path.splitext(self.text_filename)
            timestamp = datetime.datetime.now().timestamp()
            text_filename = "".join([head, "_{}".format(int(timestamp)), tail])
        dir_path = os.path.dirname(text_filename)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with util.save_file.open_savefile(text_filename, 'w') as file:
            json.dump(data, file, indent=self.indent)

    def save_image(self):
        if not self.active:
            return
        self.logger.info("Writing textual output file.")
        try:
            data = self.build_data()
            self.write_text_file(data)
        except:
            self.logger.info('creating json file failed')

    @QtCore.Slot()
    @util.noexcept
    def registerTrigger(self):
        self.save_image()

import datetime
import logging
import warnings
from collections import deque
import itertools
import threading

from Qt import QtCore
import numpy
from scipy import interpolate

from python_util import util as util

# Safety limit
MAX_LINES = 72000  # 1h at 20Hz


def to_numpy_int32(value: int):
    return value
    """Convert a python integer representing a 32bit unsigned integer value to a numpy.int32 number"""
    return numpy.int64(value)#.astype(numpy.int32)


def to_numpy_uint32(value: int):
    return value
    """Convert a python integer representing a 32bit unsigned integer value to a numpy.uint32 number"""
    with warnings.catch_warnings():
        # Suppress warnings about all-NAN slices
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return numpy.uint32(value).astype(numpy.uint32)


class SingleImage(QtCore.QObject):
    """composed image per scanner"""
    def __init__(self, parent, sensor_name, vertical_offset, reverse_vertical, width, height,
                 vertical_interpolation_mode, image_reset_value, extrapolate):
        super().__init__(parent)
        self.logger = logging.getLogger("{}_{}".format(self.__class__.__name__, sensor_name))
        self.image_reset_value = image_reset_value
        self.name=sensor_name
        self.vertical_offset = vertical_offset  # vertical offset as angle (degree)
        self.reverse_vertical = reverse_vertical
        self.vertical_interpolation_mode = vertical_interpolation_mode
        self.extrapolate = extrapolate
        self.width = width
        self.height = height
        self.last_trigger = None
        self.next_to_last_trigger = None
        self.next_to_next_last_trigger = None
        self.top = -self.vertical_offset
        self.bottom = 360.0 - self.vertical_offset
        if self.reverse_vertical:
            self.top, self.bottom = self.bottom, self.top
        self.dest_y = numpy.linspace(self.top, self.bottom, self.height)
        self.lines_lock = threading.Lock()
        self.lines = deque(maxlen=MAX_LINES)
        self.logger.debug("w={}, h={}".format(width, height))
        self.num_raw_lines = 0
        self.data = numpy.empty((self.height, self.width), dtype=float)

    def clear(self):
#        import sys
#        sys.exit(0)
        self.logger.debug("Clear.")

        self.data = numpy.empty((self.height, self.width), dtype=float)

        self.lines.clear()
        self.num_raw_lines = 0

    @QtCore.Slot(object)
    @util.noexcept
    def trigger_changed(self, sensor):
        """register a change in trigger timestamps of the associated sensor"""
        self.logger.debug("trigger changed for sensor={}".format(sensor.name))

        self.last_trigger = sensor.last_trigger
        self.next_to_last_trigger = sensor.next_to_last_trigger
        self.next_to_next_last_trigger = sensor.next_to_next_last_trigger
        self.logger.debug("last_trigger={} ntlast_trigger={} ntnlast_trigger={}".
                          format(self.last_trigger, self.next_to_last_trigger, self.next_to_next_last_trigger))

        # Extrapolate last interval back in time to next to last interval

        if self.next_to_next_last_trigger is None:
            if self.last_trigger is not None and self.next_to_last_trigger is not None:
                #self.next_to_next_last_trigger = to_numpy_uint32(self.next_to_last_trigger) - (to_numpy_uint32(self.last_trigger) - to_numpy_uint32(self.next_to_last_trigger))
                self.next_to_next_last_trigger = (self.next_to_last_trigger) - ((self.last_trigger) - (self.next_to_last_trigger))
                self.logger.info("Artifically set next_to_next_last_trigger to calculated time {}".format(self.next_to_next_last_trigger))

        if sensor.last_trigger is None:
            return
        if sensor.next_to_last_trigger is None:
            return

        num_lines_before = len(self.lines)
        try:
            if num_lines_before == 0:
#                self.blackout(sensor)
                self.clear()
                self.lines.clear()
                return
        except Exception as e:
            print(f"-------------------{e}----------------")

        #            return
        with self.lines_lock:
            self.logger.debug("Before: First line in buffer t={}; last t={}".
                              format(self.lines[0].time_usec, self.lines[-1].time_usec))
#
            try:
                with numpy.errstate(over='ignore'):
                    # Check if we have "old" unordered lines in our buffer.
                    # This may be caused by a DaLi-NETA receiver reset, causing its
                    # internal timer to be reset, and making existing line timestamps
                    # invalid.
                    # In this case, clear line buffer.

                    next(line for line in self.lines
                         #if to_numpy_int32(self.lines[-1].time_usec) - to_numpy_int32(line.time_usec) < -10 ** 6)
                         if self.lines[-1].time_usec - line.time_usec < 0)
                    self.logger.warning("Detected time-unordered lines entries. Clearing lines.")
                    self.lines.clear()
            except StopIteration:
                pass

            # Removes all lines before self.next_to_next_last_trigger
            # problems on the edges.
            def old_line(line):
                if self.next_to_next_last_trigger is None:
                    return False
                with numpy.errstate(over='ignore'):
                    #dt = to_numpy_int32(line.time_usec) - to_numpy_int32(self.next_to_next_last_trigger)
                    dt = (line.time_usec) - (self.next_to_next_last_trigger)
                    if dt < (-10 ** 6):
                        return True
                return False
            while len(self.lines):
                if old_line(self.lines[0]):
                    self.lines.popleft()
                else:
                    break
            num_lines_after = len(self.lines)
            self.logger.debug("Removed {} lines. ( before={} after={})".
                              format(num_lines_before - num_lines_after, num_lines_before, num_lines_after))
            if not len(self.lines):
                return
            self.logger.debug("After: First line in buffer t={}; last t={}".
                              format(self.lines[0].time_usec, self.lines[-1].time_usec))

            # Calculate angles for lines
            for line in self.lines:
                with numpy.errstate(over='ignore'):
                    #too_old = to_numpy_int32(line.time_usec) - to_numpy_int32(self.next_to_last_trigger)
                    too_old = (line.time_usec) - (self.next_to_last_trigger)
                    too_old1 = (line.time_usec) - (self.next_to_last_trigger)
                    if too_old!= too_old1:
                        print ('python too old', too_old1)

                        print('numpy too old', too_old)

                    if too_old < 0:
                        if self.next_to_next_last_trigger is not None:
                            # lines are from the last trigger interval. We should have calculated most positions
                            # already, but have not gotten all lines during that time. So recalculate all positions
                            new_pos = self.calculate_vertical_positions(self.next_to_next_last_trigger,
                                                                        self.next_to_last_trigger, [line])
                            line.vertical_position = new_pos[0] - 360.0
                        continue
                    # Lines after next_to_last_trigger should not yet have a position assigned
                    too_new = (line.time_usec) - (self.last_trigger)
                    if too_new > 0:
                        continue
                    pos = self.calculate_vertical_positions(self.next_to_last_trigger,
                                                            self.last_trigger, [line])

                    line.vertical_position = pos[0]
            self.logger.debug("Calculated angles for lines.")

    def add_line(self, line, _sensor):
        with self.lines_lock:
            self.lines.append(line)

    def _interpolate_scipy(self, source_x, values, dest_x):
        f = interpolate.interp1d(source_x,
                                 values,
                                 kind=self.vertical_interpolation_mode,
                                 bounds_error=False,
                                 fill_value=("extrapolate" if self.extrapolate else self.image_reset_value))
        return f(dest_x)

    @staticmethod
    def calculate_vertical_positions(start, end, lines):
#        for l in lines:
#            print(l.time_usec)
#            print((l.time_usec-start)/(end-start)*360)
        """Build vertical source_y values by transforming time-stamps relative to trigger times into angles."""
        with numpy.errstate(over='ignore'):
            # Make sure to use numpy.int32 values in each step for correct overflow calculation
#            start, end = to_numpy_int32(start), to_numpy_int32(end)

            #time_values = numpy.array([line.time_usec for line in lines], dtype=numpy.int64)#.astype(numpy.int32)
            time_values = numpy.array([line.time_usec for line in lines])#.astype(numpy.int32)
            #adjusted_time_values = (time_values - start).astype(numpy.int64)
            overflows=int(time_values[0]/4294967295)
            if end < start:
                end+=4294967295
#            time_values-=overflows*4294967295
            adjusted_time_values = (time_values - start)
#            if end < start:
#                print (start,end,end+2**32-1,end+2**32-1-start, adjusted_time_values / (end - start) * 360.0,adjusted_time_values / (end - +2**32-1-start) * 360.0)

#                end+=2**32-1
#                print (start,end, )
            vertical_positions = (adjusted_time_values / (end - start) * 360)


            """
            print ("@"*80)
            print(end<start)
            print (vertical_positions,adjusted_time_values,time_values)
            print (end-start,end, start)
            """
            return vertical_positions


    def interpolate(self, vertical_positions, values, data):
        if numpy.sum(numpy.isnan(vertical_positions)) != 0:
            self.logger.debug("Vertical Positions: {}".format(vertical_positions))
            raise ValueError("invalid vertical positions detected.")
        if self.vertical_interpolation_mode == "nearest":
            self.logger.debug("Using nearest vertical interpolation.")
            interpolation_table = numpy.array([numpy.abs(x - vertical_positions).argmin() for x in self.dest_y])
#            print ("interpolate")
#            print (interpolation_table.tolist())
            # self.logger.debug("Calculated interpolation table: {}".format(interpolation_table))
            # Interpolate each row
            data = numpy.take(values, interpolation_table, axis=0)
        else:
            # Interpolate each row
            for i in range(self.width):
                row_data = values[:, i]
                interpolated_data = self._interpolate_scipy(vertical_positions, row_data, self.dest_y)
                data[:, i] = interpolated_data
        return data

    def checklines(self):
        remove_lines=[]
        try:
            print ("==============================================================================")
            print (self.lines[0].time_usec,self.lines[-1].time_usec,self.last_trigger,self.next_to_last_trigger,self.next_to_next_last_trigger)
            t=self.lines[-1].time_usec
            print (t-self.last_trigger,t-self.next_to_last_trigger,t-self.next_to_next_last_trigger)
            print ("==============================================================================")
        except:
            return

        for i,l in enumerate(self.lines):
            if l.vertical_position==None:
                remove_lines.append(l)
                continue
            if self.lines[i+1].vertical_position==None:
                remove_lines.append(l)
                continue
            if i>= len(self.lines):
                break
            if l.vertical_position>=self.lines[i+1].vertical_position:
                remove_lines.append(l)

        for l in remove_lines:

            self.lines.remove(l)

    def compose(self, data):
        """compose current image"""
#        self.checklines()
        lines = list(self.lines)

        self.logger.debug("Composing SingleImage. Usable lines: {}".format(len(lines)))
        try:
            self.logger.debug("First line in buffer t={}; last t={}".format(lines[0].time_usec, lines[-1].time_usec))
        except:
            self.logger.debug(f"{len(lines)} lines")
        vertical_positions = numpy.hstack([line.vertical_position for line in lines])
        vertical_positions = vertical_positions.astype(float)

        self.logger.debug("{}".format(vertical_positions))
        start = numpy.nanargmin(vertical_positions)
        end = numpy.nanargmax(vertical_positions)
        self.logger.debug("vertical positions min={} (i={}) max={} (i={})".
                          format(numpy.nanmin(vertical_positions), start, numpy.nanmax(vertical_positions), end))
        if start > end:
            print (self.name,self.next_to_last_trigger,self.next_to_next_last_trigger,self.last_trigger)
            print (numpy.min(vertical_positions),numpy.max(vertical_positions))
#            for line in self.lines:
#                print (line.vertical_position,line.time_usec,line.segments[0].block2,line.segments[0].block_time_usec)
        lines2remove=[]
        ll=None
#        print (self.lines)
        v=-360
        for  l in self.lines:

#            print(l, l.vertical_position)
            if l.vertical_position==None:
                continue
            if v>=360:
                break

            if l.vertical_position<-360:
                lines2remove.append(l)
                continue
            else:
                if (ll!=None) :
                    if ll.vertical_position>l.vertical_position:
                        lines2remove.append(ll)
            ll=l
            v = l.vertical_position
        for l in lines2remove:
                self.lines.remove(l)
 #               print (f'remove{l}')
                self.logger.debug(f'remove{l}')
        vertical_positions = vertical_positions[start:end]
        if len(vertical_positions) == 0:
            return 0, None

        # Stack all data into a big array
        values = numpy.vstack([line.data for line in deque(itertools.islice(lines, int(start), int(end)))])
        data = self.interpolate(vertical_positions, values, data)

        with warnings.catch_warnings():
            # Suppress warnings about all-NAN slices
            warnings.simplefilter("ignore", category=RuntimeWarning)
            num_raw_lines = numpy.abs(end - start)
        self.logger.debug("Num raw lines used: {}".format(num_raw_lines))
#        data[data==numpy.nan]=self.image_reset_value
        return num_raw_lines, data

    def get_data(self):
        data = self.data
        data[:] = numpy.nan#self.image_reset_value
        num_raw_lines = 0
        if not len(self.lines):
            self.logger.info("No lines available.")
            return 0, data
        if not self.last_trigger:
            self.logger.info("No last_trigger available.")
            return 0, data
        if not self.next_to_last_trigger:
            self.logger.info("No next_to_last_trigger available.")
            return 0, data
        if self.last_trigger == self.next_to_last_trigger:
            self.logger.warning("last and next to last kiln trigger equal.")
            return 0, data
        try:
            num_raw_lines, data = self.compose(data)
        except ValueError as e:
            self.logger.info("Could not yet compose image: {}".format(e))
            self.logger.debug("Could not yet compose image.", exc_info=True)
        except Exception:
            self.logger.warning("Could not compose image.", exc_info=True)
        return num_raw_lines, data


class ComposedImage(QtCore.QObject):
    """Thermal image consisting of one SingleImage per sensor"""
    signal_image_updates = QtCore.Signal()

    def __init__(self, config, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._rawlines = 0
        self.empty = True
        self._full_data = None
        self.images = {}
        self.width = int(config["width"])
        self.blackies=0
        self.ungleich=0
        self.blacks=[]
        if self.width <= 0:
            raise ValueError("Image width must be positive.")
        self.height = int(config["height"])
        if self.height <= 0:
            raise ValueError("Image height must be positive.")

        self.horizontal_interpolation_mode = config["horizontal_interpolation_mode"]
        supported_interpolations = ["linear", "nearest"]
        experimental_interpolations = ["zero", "slinear", "quadratic", "cubic"]
        try:
            self.horizontal_interpolation_mode = int(self.horizontal_interpolation_mode)
        except ValueError:
            if self.horizontal_interpolation_mode in experimental_interpolations:
                self.logger.warning("Using experimental horizontal interpolation mode '{}'.".
                                    format(self.horizontal_interpolation_mode))
            if self.horizontal_interpolation_mode not in supported_interpolations+experimental_interpolations:
                raise ValueError("Unsupported Horizontal interpolation mode '{}'. Valid options: {}".
                                 format(self.horizontal_interpolation_mode,
                                        supported_interpolations+experimental_interpolations))

        self.vertical_interpolation_mode = str(config["vertical_interpolation_mode"])
        if self.vertical_interpolation_mode not in ("linear", "nearest"):
            raise ValueError("Vertical interpolation mode needs to be 'linear' or 'nearest'")

        self.image_reset_value = float(config["image_reset_value"])
        if self.image_reset_value < 0:
            self.image_reset_value = numpy.nan

        self.vertical_extrapolate = config.get("vertical_extrapolate", "False")

        self.logger.debug("ComposedImage: w={} h={}".format(self.width, self.height))

    def get_num_rawlines(self):
        return self._rawlines

    def get_full_data(self):
        return self._full_data

    def image_empty(self):
        return self._full_data is None

    def init_sensors(self, kiln):
        for i, sensor in kiln.sensors.items():
            if not sensor.hasLinedata:
                continue
            img = SingleImage(self, sensor.name, sensor.vertical_offset, sensor.reverse_vertical, self.width,
                              self.height, self.vertical_interpolation_mode, self.image_reset_value,
                              self.vertical_extrapolate)
            sensor.signal_got_trigger.connect(img.trigger_changed, QtCore.Qt.QueuedConnection)
            self.images[i] = img
            sensor.sigConvertedLine.connect(self.addLine)
        self.__defaultMergeFunc = numpy.nanmax
        self.empty = True

    def blackout(self, sensor):
        self.logger.debug("Blackout sensor={}.".format(sensor))
        self.images[sensor.index].clear()
        #self.num_sources = len(kiln.sensors)
        #self.images = {}

    @property
    def alive(self):
        try:
            return (datetime.datetime.now() - self.__lastUpdate).total_seconds() < self.__aliveTimeout
        except Exception as _e:
            return False

    @QtCore.Slot()
    def trigger(self):
        pass

    def clear(self):
        self.logger.debug("Clear.")
        for img in self.images.values():
            img.clear()

    def build_data(self):
        """
        Collpase the scanner dimension of the image.
        By default, use maximum filter.
        """
        def accu(iterable):
            sum_ = 0
            for it in iterable:
                sum_ += it
            return sum_
        image_data = [image.get_data() for image in self.images.values()]

        lines =-1

        black=False
        ungleich=0
        for d in image_data:
#            print (type(d))
##            print(d)
 #           print (d[0],(numpy.nanmax(d[1])))
            if lines==-1:
                lines=d[0]
            if d[0]==0:
                black=True
                continue
            f=lines/d[0]
            if 0.9<f<1.1:
                print('ungleich')
                ungleich+=1

        if ungleich>0:
            self.ungleich+=1
        else:
            self.ungleich=0
        if black:
            self.logger.warning('ERROR 374')
            self.blackies+=1
        else :
            self.blackies=0
        if 0<self.blackies<5:
            return
        if 0<self.ungleich<3:
            return

#            self.clear()
#            return
        self._full_data = [data.copy() for _num_raw_lines, data in image_data]
        num_raw_lines = [num_raw_lines for num_raw_lines, _data in image_data]
        self._rawlines = accu(num_raw_lines)

    @QtCore.Slot()
    @util.noexcept
    def update_image(self):
        self.logger.debug("Updating image.")
        self.time = util.datetime_helper.current_local_time()
        if self.empty:
            self.logger.debug("Image empty, returning.")
#            return
        self.build_data()
        self.signal_image_updates.emit()

    @QtCore.Slot(object, object)
    def addLine(self, line, scanner):
        """
        :type line: convertedLine
        """
        try:
            self.empty = False
            self.images[scanner.index].add_line(line, scanner)
            self.__lastUpdate = datetime.datetime.now()
        except Exception as e:
            self.logger.error("Could not add line to image: {}".format(e), exc_info=True)


if __name__ == '__main__':
    # Test vertical position calculation
    class Line:
        def __init__(self, time_usec):
            self.time_usec = time_usec
    # test 32bit int overflow scenario
    length = [2 ** 32 - 200, 76, 500, 800, 1270, 2000]
    data = [Line(t) for t in length]
    start = 2 ** 32 - 100
    end = 1270
    r = SingleImage.calculate_vertical_positions(start, end, data)

    # check overflow ignoring
    start = 2
    end = 2 ** 31 + 1
    r = SingleImage.calculate_vertical_positions(start, end, data)

import numpy


class RawLine(object):
    def __init__(self, segment,oldData=None, validate_line_sync=True):
        super().__init__()
        self.line_id = segment.line_id
        self.data = None
        if oldData!=None:
            self.data=oldData
#            old_data = numpy.array(old_data)
#            data = numpy.hstack([segment.data for segment in self.segments])
#            data = numpy.hstack([old_data, data])
#            data = data.astype(dtype=int)
        self.rawLen=0
        self.supercount=0
        self.mergecount=0
        self.segments = []
        self.is_complete = False
        self.cached_video_data = None
        self.validate_line_sync = validate_line_sync
        self.add(segment)
        self.ls=None

    @property
    def time_usec(self):
        """timestamp associated with this line."""
        # Define this as the block_time of the first segment == timestamp of the first pixel
#        if self.segments[0].block2!=self.segments[0].block_time_usec:
#            print (self.segments[0].block2,self.segments[0].block_time_usec,self.segments[0].time_offset)
        #return self.segments[0].block2
        return self.segments[0].block_time_usec

    @property
    def length(self):
        return len(self.data)

    @property
    def _intermediate_length(self):
        sum_ = 0
        for segment in self.segments:
            sum_ += segment.num_data_words
        return sum_

    @property
    def last_segment(self):
        if len(self.segments):
            return self.segments[-1]
        return None

    def add(self, segment,merge=False):
        if merge:
            self.supercount+=len(self.segments)
            self.mergecount+=1

        if len(self.segments)==0:self.first_id=segment.block_id
        if len(self.segments):
            last_segment = self.segments[-1]
            if segment.line_id != last_segment.line_id+self.mergecount:
                raise RuntimeError("Skipped {} raw line(s). {} != {} id{}!={}".format(segment.line_id - last_segment.line_id, last_segment.line_id, segment.line_id, last_segment.global_block_id, segment.global_block_id))
            x=0
            if merge:
                x=self.supercount
            if (segment.block_id+x - last_segment.block_id) != 1:
                raise RuntimeError("Non-consequtive segment. {} <> {}({})".format(last_segment, segment,x))

            if segment.video_bits != last_segment.video_bits:
                raise RuntimeError("Non-equal Video_Bits_per_Word.")
#            if self.validate_line_sync and len(self.segments)+self.first_id != segment.block_id:
            if self.validate_line_sync and len(self.segments) != segment.block_id+self.supercount:
                if segment.no_data():
                    raise RuntimeError("Segment contains no data. Please check DATA fiber optic line.")
#                pass
                raise RuntimeError("Entering segment with invalid block_id into segment list. {} != {} comp={} id={}".format(len(self.segments), segment.block_id, self.is_complete, segment.global_block_id))

        #            if self.validate_line_sync and len(self.segments) != segment.block_id:
#                if segment.no_data():
#                    raise RuntimeError("Segment contains no data. Please check DATA fiber optic line.")
#                raise RuntimeError("Entering segment with invalid block_id into segment list. {} != {} comp={} id={}".format(len(self.segments), segment.block_id, self.is_complete, segment.global_block_id))
        self.segments.append(segment)

    def complete(self,old_data):
        """compose segment data when line is complete"""
        old_data=numpy.array(old_data)
        data = numpy.hstack([segment.data for segment in self.segments])
        data = numpy.hstack([old_data,data])
        data=data.astype(dtype=int)
#        data = numpy.array(old_data).flatten()+data.flatten()
        #self.data = numpy.hstack([segment.data for segment in self.segments])
        self.rawLen=len(data)
        mark=0x4000
        #print(data)
        data2=data & mark

        data2=data2[1:] - data2[:-1]
        #print(data2)
        #print('linesync: ',numpy.where(data2!=0))
        self.ls=numpy.where(data2 != 0)
        self.oversize=False
        if len(data)>12000:
            self.rest=data[12000:]
            data=data[0:12000]
            self.oversize=True
        else:
            self.rest=[]
        xvals = numpy.linspace(0, 12000,len(data))
        xtvals = numpy.linspace(0,12000, 12000)
        self.data=numpy.interp(xtvals, xvals, data)
        self.data=data.astype(dtype=int)
        self.is_complete = True

    def add2(self, segment, merge=False):
        if len(self.segments) == 0: self.first_id = segment.block_id
        if self.segments[-1].block_id+1!=segment.block_id:
            raise ValueError('missed package')
        self.data = numpy.hstack([self.data, segment.data])
        self.data = self.data.astype(dtype='uint16')
        self.segments.append(segment)


    def complete2(self, old_data):
        """compose segment data when line is complete"""
        old_data = numpy.array(old_data)
        data = numpy.hstack([segment.data for segment in self.segments])
        data = numpy.hstack([old_data, data])
        data = data.astype(dtype=int)
        #        data = numpy.array(old_data).flatten()+data.flatten()
        # self.data = numpy.hstack([segment.data for segment in self.segments])
        self.rawLen = len(data)
        mark = 0x4000
        # print(data)
        data2 = data & mark

        data2 = data2[1:] - data2[:-1]
        # print(data2)
        # print('linesync: ',numpy.where(data2!=0))
        self.ls = numpy.where(data2 != 0)
        self.oversize = False
        if len(data) > 12000:
            self.rest = data[12000:]
            data = data[0:12000]
            self.oversize = True
        else:
            self.rest = []
        xvals = numpy.linspace(0, 12000, len(data))
        xtvals = numpy.linspace(0, 12000, 12000)
        self.data = numpy.interp(xtvals, xvals, data)
        self.data = data.astype(dtype=int)
        self.is_complete = True

    @property
    def video_data(self):
        if self.cached_video_data is None:
            bits = self.segments[-1].video_bits
            self.cached_video_data = numpy.bitwise_and(self.data, ((1 << bits) - 1))
        return self.cached_video_data

    @property
    def status_data(self):
        bits = self.segments[-1].video_bits
        return numpy.bitwise_and(self.raw_data, ~((1 << bits) - 1))

    @property
    def fov_length(self):
        """ Assumes that FoV ends on the first non-zero status_data pixel"""
        return numpy.argmax(self.status_data > 1)

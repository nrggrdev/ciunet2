class ConvertedLine:
    def __init__(self, time_usec):
        self.time_usec = time_usec
        self.vertical_position = None


class ConvertedLineWithGenerator(ConvertedLine):
    @property
    def data(self):
        try:
            self._data = next(self.generator)
        except StopIteration:
            pass
        return self._data

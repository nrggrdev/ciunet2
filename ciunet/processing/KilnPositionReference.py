import numpy


class KilnPositionReference:
    """
    Tracks a raw digital value at a given kiln position over one kiln rotation.

    The aggregation method controls how values from multiple scan lines are combined:
    - 'max': track the maximum (default, original behaviour)
    - 'min': track the minimum
    - 'avg': compute the mean across all samples in the window
    """

    def __init__(self, kiln_position, window, method='max'):
        """
        :param kiln_position: Centre of the reference window in kiln length units (m / ft).
        :param window:        Full width of the window in the same units.
        :param method:        Aggregation over one rotation: 'max', 'min', or 'avg'.
        """
        self.kiln_position = float(kiln_position)
        self.window = float(window)
        self.method = method
        self._committed_value = numpy.nan
        # per-rotation accumulators
        self._current_max = numpy.nan
        self._current_min = numpy.nan
        self._current_sum = 0.0
        self._current_count = 0

    # ------------------------------------------------------------------
    def update(self, raw_data, geo_transformator):
        """Update accumulator with one raw FOV scan line."""
        try:
            data_length = len(raw_data)
            target_positions, real_positions = geo_transformator._get_target_positions(data_length)
            real_data = raw_data[real_positions].astype(float)
            low = self.kiln_position - self.window / 2.0
            high = self.kiln_position + self.window / 2.0
            mask = (target_positions >= low) & (target_positions <= high)
            if mask.any():
                vals = real_data[mask]
                valid = vals[~numpy.isnan(vals)]
                if len(valid) == 0:
                    return
                if self.method == 'max':
                    val = float(numpy.max(valid))
                    if numpy.isnan(self._current_max) or val > self._current_max:
                        self._current_max = val
                elif self.method == 'min':
                    val = float(numpy.min(valid))
                    if numpy.isnan(self._current_min) or val < self._current_min:
                        self._current_min = val
                elif self.method == 'avg':
                    self._current_sum += float(numpy.sum(valid))
                    self._current_count += len(valid)
        except Exception:
            pass

    def on_trigger(self):
        """Commit the rotation-accumulated value and reset the accumulator."""
        if self.method == 'max':
            if not numpy.isnan(self._current_max):
                self._committed_value = self._current_max
            self._current_max = numpy.nan
        elif self.method == 'min':
            if not numpy.isnan(self._current_min):
                self._committed_value = self._current_min
            self._current_min = numpy.nan
        elif self.method == 'avg':
            if self._current_count > 0:
                self._committed_value = self._current_sum / self._current_count
            self._current_sum = 0.0
            self._current_count = 0

    # ------------------------------------------------------------------
    @property
    def value(self):
        """Aggregated raw digital value from the last complete rotation.

        Returns ``numpy.nan`` until at least one full rotation has been observed.
        """
        return self._committed_value

import numpy


class KilnPositionReference:
    """
    Tracks the maximum raw digital value at a given kiln position over one kiln rotation.

    Used in [temperature] section to derive P1_dig / P2_dig from a physically meaningful
    location on the kiln instead of a fixed analog-channel angle.  On each scan line the
    raw FOV data is mapped to kiln coordinates via the scanner's GeoTransformator; the
    maximum value inside the configured window is accumulated.  When an external trigger
    (= one full kiln rotation) arrives, the accumulated maximum is committed and the
    accumulator is reset.
    """

    def __init__(self, kiln_position, window):
        """
        :param kiln_position: Centre of the reference window in kiln length units (m / ft).
        :param window:        Full width of the window in the same units.
        """
        self.kiln_position = float(kiln_position)
        self.window = float(window)
        self._committed_max = numpy.nan
        self._current_max = numpy.nan

    # ------------------------------------------------------------------
    def update(self, raw_data, geo_transformator):
        """Update accumulator with one raw FOV scan line.

        :param raw_data:         1-D array of raw digital values in FOV-pixel space
                                 (same data that is passed to temperature conversion).
        :param geo_transformator: GeoTransformator instance of the owning scanner.
        """
        try:
            data_length = len(raw_data)
            target_positions, real_positions = geo_transformator._get_target_positions(data_length)
            real_data = raw_data[real_positions].astype(float)
            low = self.kiln_position - self.window / 2.0
            high = self.kiln_position + self.window / 2.0
            mask = (target_positions >= low) & (target_positions <= high)
            if mask.any():
                val = float(numpy.nanmax(real_data[mask]))
                if numpy.isnan(self._current_max) or val > self._current_max:
                    self._current_max = val
        except Exception:
            pass

    def on_trigger(self):
        """Commit the rotation-accumulated maximum.

        Call this once per kiln rotation trigger.  The committed value becomes
        available via :attr:`value` and the accumulator is reset for the next
        rotation.
        """
        if not numpy.isnan(self._current_max):
            self._committed_max = self._current_max
        self._current_max = numpy.nan

    # ------------------------------------------------------------------
    @property
    def value(self):
        """Maximum raw digital value from the last complete rotation.

        Returns ``numpy.nan`` until at least one full rotation has been observed.
        """
        return self._committed_max

import logging

import numpy
from scipy import interpolate
from scipy import optimize


def scanner_geometry_conversion(x, args):
    """Geometrical equation we are trying to solve. See GeometrischeSkalierungScanner.jpeg"""
    l, h, θ = x
    return [y - l - h * numpy.tan(numpy.radians(φ - θ)) for φ, y in args]


class GeoTransformator:
    def __init__(self, kiln, target_pixel, fov_angle, geometry_config, mask, interpolation_mode):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Creating new geometrical converter. config={}".format(geometry_config))
        self.mask = mask
        self.kiln_start = kiln.kiln_start
        self.kiln_end = kiln.kiln_end
        self.interpolation_points = numpy.arange(kiln.kiln_start, kiln.kiln_end, kiln.length / target_pixel)
        self.interpolation_mode = interpolation_mode
        self.interpolate = self._interpolate_scipy
        valid_modes = ("tilt", "3point")
        self.mode = geometry_config.get("mode", "tilt")
        if self.mode not in valid_modes:
            raise ValueError("Invalid geometry mode {} not in {}.".format(self.mode, valid_modes))

        self.fov_angle = fov_angle
        if self.fov_angle > 360.0:
            raise ValueError("Fov angle must be <= 360 degree.")
        self.phiWH = fov_angle / 2.0
        self.cached_positions = {}
        self.tilt = float(geometry_config["tilt"])
        if numpy.abs(self.tilt) >= 90.0:
            raise ValueError("Tilt must be lower than +-90.0degree.")

        if self.mode == "3point":
            self.build_3point_geometry(geometry_config)
        elif self.mode=="tilt":
            self.build_tilt_geometry(geometry_config)
        else:
            self.build_raw()

        self.logger.info("l={} h={} tilt={}".format(self.l, self.h, self.tilt))
        self.logger.info("pos for q={} is {}.".format(self.phiWH, self._transform_scanner_to_kiln_coords(numpy.array([self.phiWH]))))

    def buid_raw(self):
        self.fov

    def build_tilt_geometry(self, geometry_config):
        """
        Calculate scanner geometry with 2 reference points + tilt
        Solve y = l + h * tan(phi-tilt) for l and h by hand
        """
        self.logger.info("Doing tilt  geometry.")
        φ1 = float(geometry_config["phi1"])
        if φ1 < 0.0 or φ1 > self.fov_angle:
            self.logger.warning("Phi1 outside of FOV.")
        φ2 = float(geometry_config["phi2"])
        if φ2 < 0.0 or φ2 > self.fov_angle:
            self.logger.warning("Phi2 outside of FOV.")
        y1 = float(geometry_config["pass1"])
        y2 = float(geometry_config["pass2"])

        # Adjusted angle 1 between passpoint1 and perpendicular
        q1 = φ1 - self.phiWH - self.tilt
        if numpy.abs(q1) >= 90.0:
            raise ValueError("Phi1 must be on the kiln axis")

        # Adjusted angle 2 between passpoint2 and perpendicular
        q2 = φ2 - self.phiWH - self.tilt
        if numpy.abs(q2) >= 90.0:
            raise ValueError("Phi2 must be on the kiln axis")

        # length of perpendicular line from scanner onto kiln
        self.h = (y2 - y1) / (numpy.tan(numpy.radians(q2)) - numpy.tan(numpy.radians(q1)))

        # position of perpendicular on the kiln
        self.l = y1 - numpy.tan(numpy.radians(q1)) * self.h
        self.logger.info("q1={} q2={}".format(q1, q2))

    def build_3point_geometry(self, geometry_config):
        """
        Calculate scanner geometry with 3 reference points
        Use numerical solver to solve equation y = l + h * tan(φ - θ)
        with φ  being the scan angle, θ  being the tilt and y the position on the kiln
        l is the position of the perpendicular on the kiln, and h the length of the perpendicular.
        """
        self.logger.info("Doing 3 Point geometry.")
        reference_points = []
        for i in range(1, 4):
            phi = float(geometry_config["phi{}".format(i)]) - self.phiWH
            y = float(geometry_config["pass{}".format(i)])
            reference_points.append((phi, y))
        x0 = (50, 60, self.tilt)
        try:
            r = optimize.fsolve(scanner_geometry_conversion, x0, reference_points)
        except RuntimeWarning as e:
            raise RuntimeWarning("Problem when calculating 3point scanner geometry: {}".format(e)) from e
        self.l, self.h, self.tilt = r
        if numpy.abs(self.tilt) >= 90.0:
            raise ValueError("Calculated tilt of {:.2f}degree exceeds limt of +-90.0degree.".format(self.tilt))

    def _transform_scanner_to_kiln_coords(self, angles):
        """Transform from scanner coordinates (angles) to kiln coordinates"""
        adjusted_angles = angles - self.phiWH - self.tilt

        # exclude angles going outside of the real kiln axis.
        adjusted_angles[numpy.abs(adjusted_angles) >= 90.0] = numpy.nan

        return self.l + numpy.tan(numpy.radians(adjusted_angles)) * self.h

    def _interpolate_numpy(self, dest_x, source_x, source_y, mode):
        """Interpolate data. returns dest_y"""
        return numpy.interp(dest_x, source_x, source_y, left=numpy.nan, right=numpy.nan)

    def _interpolate_scipy(self, dest_x, source_x, source_y, mode):
        """Interpolate data. returns dest_y"""
        f = interpolate.interp1d(source_x, source_y, kind=mode, bounds_error=False)
        return f(dest_x)

    def _get_target_positions(self, data_length):
        """Calculate kiln positions for each scanner pixel. Includes caching for performance improvement."""
        if data_length in self.cached_positions:
            return self.cached_positions[data_length]

        # angle position for each data point. assume linear distribution
        scan_angles = numpy.linspace(0, self.fov_angle, num=data_length)

        # calculate kiln position for each data point
        positions = self._transform_scanner_to_kiln_coords(scan_angles)

        # Go through some hoops to remove NAN positions values (scanner pixels which do not land on the kiln axis) before interpolating.
        real_positions = numpy.invert(numpy.isnan(positions))
        target_positions = positions[real_positions]

        # put into cache
        self.cached_positions[data_length] = (target_positions, real_positions)
        return (target_positions, real_positions)

    def _get_fov_target_positions(self, data_length, fov_angle):
        """Map FoV to 120deg FoV pixels at linear space on kiln between kiln start and end"""
        fov_factor =1# fov_angle / 120.0
        v = numpy.linspace(self.kiln_start, (self.kiln_end - self.kiln_start) * fov_factor + self.kiln_start, num=data_length)
        return v

    def get_data_position(self, data, fov_mode, fov_angle):
        if not fov_mode:
            target_positions, real_positions = self._get_target_positions(len(data))
            data = data[real_positions]  # remove NAN positions from data
        else:
            target_positions = self._get_fov_target_positions(len(data), fov_angle)
        return data, target_positions

    def convert(self, data, fov_mode, fov_angle):
        """Convert fov_data with scanner coordinates to kiln coordinates and interpolate """
        adjusted_data, target_positions = self.get_data_position(data, fov_mode, fov_angle)

        # now use the calculated positions to do linear interpolation onto the destination positions 
        v = self.interpolate(dest_x=self.interpolation_points,
                                source_x=target_positions,
                                source_y=adjusted_data,
                                mode=self.interpolation_mode)
        v[numpy.invert(self.mask)] = numpy.nan
        return v

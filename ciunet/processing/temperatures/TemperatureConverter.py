import numpy
import logging
import math

from PyQt5 import QtCore

from python_util import util as util
from daq_net.daq import Temperature
from .VignettationTransformer import VignettationTransformer


class TemperatureConverter(QtCore.QObject):
    def __init__(self, config, scanner, parent):
        super().__init__(parent=parent)
        self.tempfit='exp'
        if "window_transmission_table" in config:
            self.window_transmission_vignetting = VignettationTransformer(str(config["window_transmission_table"]))
        else:
            self.window_transmission_vignetting = 1.0
        self.use_window_transmission = util.str2bool(config["use_window_transmission"])
        self.τw = float(config["window_transmission"])

        self.logger = logging.getLogger(self.__class__.__name__)
        self.scanner = scanner
        self.temperature_unit = Temperature.unit[config["temp_unit"]]
        self.mode = str(config["temperatureTransformationMode"])
        self.temperature_lower_limit = float(config.get("temperature_lower_limit", -1.0))
        self.log_conversion_table = str(config.get("log_conversion_table", "logs/{}_temperature.log".format(scanner.name)))
        if self.temperature_lower_limit < 0.0:
            self.check_clamping = lambda x: x
        else:
            self.check_clamping = self.clamp_temperature
        self.dPhi = 0.0
        self.live_references_valid = False
        self.B = float(config["B"])
        self.C = float(config["C"])
        self.L = float(config["non_linearity_constant"])
        self.ε0 = float(config["ε0"])
        self.τa = float(config["τa"])
        self.window_temperature = Temperature.celsiusToKelvin(float(config["window_temperature"]))
        self.window_calibration_temperature = Temperature.celsiusToKelvin(float(config["window_calibration_temperature"]))
        self.surroundings_temperature = Temperature.celsiusToKelvin(float(config["surroundings_temperature"]))
        self.atmospheric_temperature = Temperature.celsiusToKelvin(float(config["atmospheric_temperature"]))
        self.Φs = self.get_phi(self.surroundings_temperature)
        self.Φa = self.get_phi(self.atmospheric_temperature)
        self.Φw = self.get_phi(self.window_temperature)
        self.Φwcalib = self.get_phi(self.window_calibration_temperature)

        self.slave = False          # default; may be overridden in initializeReferences
        self.P1_kiln_ref = None    # KilnPositionReference for P1 dig, if configured
        self.P2_kiln_ref = None    # KilnPositionReference for P2 dig, if configured

        if self.mode == "parameters":
            self.initializeParametersMode(config)
        elif self.mode == "withReferences":
            self.initializeReferences(config)
        elif self.mode == "withSingleReference":
            self.initializeSingleReference(config)
        elif self.mode == "withReferencesLinear":
            self.initializeReferences(config,mode='linear')
            self.mode = "withReferences"
        else:
            raise UserWarning("Invalid temperatureTransformationMode: {}".format(self.mode))
        self.update_references()

    def initializeParametersMode(self, config):
        """Initialize config for parameter mode"""
        self.A = float(config["A"])
        self.u0 = float(config["u0"])
        self.dPhi = 0.0
        self.live_references_valid = True

    def initializeReferences(self, config, mode='exp'):
        """Initialize config for reference-mode"""
        self.tempfit = mode
        self.A = self.u0 = numpy.nan
        self.m = numpy.nan
        self.b = numpy.nan
        self.dPhi = 0.0

        self.P1_temp_static = util.str2bool(config["P1_temp_static"])
        if self.P1_temp_static:
            self.P1_temp = Temperature.convert(self.temperature_unit, Temperature.Kelvin, float(config["P1_temp"]))
            if self.P1_temp < 0.0:
                raise ValueError("Invalid P1 temp < 0 Kelvin.")
        else:
            P1_temp_reference_str = str(config["P1_temp_source"])
            self.P1_temp_reference_index = self.scanner.temperatureManager.find(P1_temp_reference_str)
            if self.P1_temp_reference_index < 0:
                raise ValueError("P1_temp_reference not found")

        self.P2_temp_static = util.str2bool(config["P2_temp_static"])
        if self.P2_temp_static:
            self.P2_temp = Temperature.convert(self.temperature_unit, Temperature.Kelvin, float(config["P2_temp"]))
            if self.P2_temp < 0.0:
                raise ValueError("Invalid P2 temp < 0 Kelvin.")
        else:
            P2_temp_reference_str = str(config["P2_temp_source"])
            self.P2_temp_reference_index = self.scanner.temperatureManager.find(P2_temp_reference_str)
            if self.P2_temp_reference_index < 0:
                raise ValueError("P2_temp_reference not found")

        self.P1_dig_static = util.str2bool(config["P1_dig_static"])
        self.P1_dig_factor = float(config.get("P1_dig_factor", 1.0))
        if self.P1_dig_static:
            self.P1_static_value = float(config["P1_dig"])
        if not  self.P1_dig_static:
            P1_live_reference_str = str(config["P1_live_reference"])
            self.P1_live_reference_index = self.scanner.multiplexedValuesManager.find(P1_live_reference_str)
            if self.P1_live_reference_index < 0:
                raise ValueError("P1_live_reference not found")

        self.P2_dig_static = util.str2bool(config["P2_dig_static"])
        self.P2_dig_factor = float(config.get("P2_dig_factor", 1.0))
        if self.P2_dig_static:
            self.P2_static_value = float(config["P2_dig"])
        if not self.P2_dig_static:

            P2_live_reference_str = str(config["P2_live_reference"])
            self.P2_live_reference_index = self.scanner.multiplexedValuesManager.find(P2_live_reference_str)
            if self.P2_live_reference_index < 0:
                raise ValueError("P2_live_reference not found")

        self.p1_emission = float(config.get("P1_emission", 1.0))
        self.p2_emission = float(config.get("P2_emission", 1.0))

        # Kiln-position-based reference points (optional)
        # When P1_ref_position is set, the max digital value at that kiln position
        # over one full rotation is used as P1_dig instead of a static value or analog channel.
        # When slave=True, P1_temp / P2_temp are taken from the non-slave scanners'
        # temperature output at those same positions.
        self.slave = util.str2bool(str(config.get("slave", "False")))
        from ..KilnPositionReference import KilnPositionReference
        p1_pos = config.get("P1_ref_position", None)
        if p1_pos is not None:
            p1_method = str(config.get("P1_ref_method", "max")).lower()
            self.P1_kiln_ref = KilnPositionReference(float(p1_pos),
                                                     float(config.get("P1_ref_window", 0.5)),
                                                     method=p1_method)
        p2_pos = config.get("P2_ref_position", None)
        if p2_pos is not None:
            p2_method = str(config.get("P2_ref_method", "max")).lower()
            self.P2_kiln_ref = KilnPositionReference(float(p2_pos),
                                                     float(config.get("P2_ref_window", 0.5)),
                                                     method=p2_method)

        # Setup update QTimer
        live_reference_update_interval = float(config["live_reference_update_interval"])
        self.reference_invalidator_timer = QtCore.QTimer(self)
        self.reference_invalidator_timer.setInterval(int(live_reference_update_interval * 1000))
        self.reference_invalidator_timer.timeout.connect(self.invalidate_references)
        self.reference_invalidator_timer.start()

    def initializeSingleReference(self, config):
        """Initialize config for reference-mode"""
        self.B = float(config["B"])
        self.C = float(config["C"])
        self.A = float(config["A"])
        self.u0 = numpy.nan
        self.dPhi = 0.0

        self.P1_temp_static = util.str2bool(config["P1_temp_static"])
        if self.P1_temp_static:
            self.P1_temp = Temperature.convert(self.temperature_unit, Temperature.Kelvin, float(config["P1_temp"]))
            if self.P1_temp < 0.0:
                raise ValueError("Invalid P1 temp < 0 Kelvin.")
        else:
            P1_temp_reference_str = str(config["P1_temp_source"])
            self.P1_temp_reference_index = self.scanner.temperatureManager.find(P1_temp_reference_str)
            if self.P1_temp_reference_index < 0:
                raise ValueError("P1_temp_reference not found")

        self.P1_dig_static = util.str2bool(config["P1_dig_static"])
        self.P1_dig_factor = float(config.get("P1_dig_factor", 1.0))
        if self.P1_dig_static:
            self.P1_static_value = float(config["P1_dig"])
        else:
            P1_live_reference_str = str(config["P1_live_reference"])
            self.P1_live_reference_index = self.scanner.multiplexedValuesManager.find(P1_live_reference_str)
            if self.P1_live_reference_index < 0:
                raise ValueError("P1_live_reference not found")

        self.p1_emission = float(config.get("P1_emission", 1.0))

        # Setup update QTimer
        live_reference_update_interval = float(config["live_reference_update_interval"])
        self.reference_invalidator_timer = QtCore.QTimer(self)
        self.reference_invalidator_timer.setInterval(live_reference_update_interval * 1000)
        self.reference_invalidator_timer.timeout.connect(self.invalidate_references)
        self.reference_invalidator_timer.start()

    @QtCore.pyqtSlot()
    def invalidate_references(self):
        self.logger.debug("Invalidating reference values.")
        self.live_references_valid = False

    def update_single_reference(self):
        if self.P1_dig_static:
            P1_dig = self.P1_static_value
        else:
            P1_dig = self.scanner.multiplexedValuesManager.getValue(self.P1_live_reference_index)
            print("MASKE fuer INTERNE REF 1")

            a=~0x7000
            P1_dig=P1_dig&a
        P1_dig *= self.P1_dig_factor

        if self.P1_temp_static:
            P1_temp = self.P1_temp
        else:
            P1_temp = self.scanner.temperatureManager.getValue(self.P1_temp_reference_index)

        if P1_temp < 0.0:
            raise ValueError("P1_temp < 0 Kelvin.")

        p1_rad = Temperature.temperatureToRadiation(self.B, self.C, P1_temp)
        self.u0 = P1_dig - p1_rad * self.A * self.p1_emission * self.transmission
        self.dPhi = 0.0
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("References used to recalculate temperature calibration.u0={}; p1_dig={}, p1_temp={}C p1_rad={}".
                              format(self.u0, P1_dig, Temperature.kelvinToCelsius(P1_temp), p1_rad))

    @util.noexcept
    def update_log_conversion_table(self):
        if self.tempfit=="linear":
            return
        digits = numpy.arange(0, 2 ** 12, dtype=numpy.int16)
        digits_adjusted = digits.astype(float)
        values = self.convert(None, digits_adjusted)
        Φ0 = self.Φ0(None, digits_adjusted)
        ΔΦ = self.ΔΦ()
        data_combined = [(digits[i], values[i], Φ0[i]+ΔΦ, ΔΦ,  ΔΦ * 100.0 / (Φ0[i]+ΔΦ)) for i in range(len(values))]
        #output = numpy.column_stack((data_combined.flatten(), data_combined.flatten()))
        with open(self.log_conversion_table, "wb") as f:
            f.write("Digits; Temperature(K); Φ0+ΔΦ; ΔΦ; ΔΦ/(Φ0+ΔΦ)*100% {}\n".format(self).encode("utf-8"))
            numpy.savetxt(f, data_combined, delimiter="; ", fmt=("%d", "%.2f", "%.10f", "%.10f", "%.4f"))  # , fmt, delimiter, newline, header, footer, comments)

    def update_two_references(self):
        """Update two-point calibration. Returns True on success, False if not ready yet."""
        sname = self.scanner.name

        # --- P1 digital value ---
        # P1_dig_static takes priority over the kiln-position accumulator so that
        # a fixed reference value (e.g. cold body) can be used even in slave mode.
        if self.P1_dig_static:
            P1_dig = self.P1_static_value * self.P1_dig_factor
        elif self.P1_kiln_ref is not None:
            P1_dig_raw = self.P1_kiln_ref.value
            if numpy.isnan(P1_dig_raw):
                self.logger.info("[%s] REF: P1 dig not ready yet (no complete rotation at %.2fm)",
                                 sname, self.P1_kiln_ref.kiln_position)
                return False
            P1_dig = P1_dig_raw * self.P1_dig_factor
        else:
            try:
                P1_dig = self.scanner.multiplexedValuesManager.getValue(self.P1_live_reference_index)
                a=0x7000
                ai=int(P1_dig)&a
                P1_dig=P1_dig-ai
            except Exception as e:
                self.logger.warning("[%s] REF: P1 dig read failed: %s", sname, e)
                return False
            P1_dig *= self.P1_dig_factor

        # --- P2 digital value ---
        if self.P2_dig_static:
            P2_dig = self.P2_static_value * self.P2_dig_factor
        elif self.P2_kiln_ref is not None:
            P2_dig_raw = self.P2_kiln_ref.value
            if numpy.isnan(P2_dig_raw):
                self.logger.info("[%s] REF: P2 dig not ready yet (no complete rotation at %.2fm)",
                                 sname, self.P2_kiln_ref.kiln_position)
                return False
            P2_dig = P2_dig_raw * self.P2_dig_factor
        else:
            try:
                P2_dig = self.scanner.multiplexedValuesManager.getValue(self.P2_live_reference_index)
                a=0x7000
                ai=int(P2_dig)&a
                P2_dig=P2_dig-ai
            except Exception as e:
                self.logger.warning("[%s] REF: P2 dig read failed: %s", sname, e)
                return False
            P2_dig *= self.P2_dig_factor

        # --- P1 temperature ---
        if self.slave and self.P1_kiln_ref is not None:
            P1_temp = self.scanner.kiln.get_temperature_at_position(
                self.P1_kiln_ref.kiln_position, self.P1_kiln_ref.window)
            if P1_temp is None or numpy.isnan(P1_temp):
                self.logger.info("[%s] REF (slave): P1 temp at %.2fm not available from master scanners",
                                 sname, self.P1_kiln_ref.kiln_position)
                return False
            self.logger.info("[%s] REF (slave): P1 at %.2fm — dig=%.0f, master_temp=%.1f°C",
                             sname, self.P1_kiln_ref.kiln_position, P1_dig,
                             Temperature.kelvinToCelsius(P1_temp))
        elif self.P1_temp_static:
            P1_temp = self.P1_temp
        else:
            P1_temp = self.scanner.temperatureManager.getValue(self.P1_temp_reference_index)

        # --- P2 temperature ---
        if self.slave and self.P2_kiln_ref is not None:
            P2_temp = self.scanner.kiln.get_temperature_at_position(
                self.P2_kiln_ref.kiln_position, self.P2_kiln_ref.window)
            if P2_temp is None or numpy.isnan(P2_temp):
                self.logger.info("[%s] REF (slave): P2 temp at %.2fm not available from master scanners",
                                 sname, self.P2_kiln_ref.kiln_position)
                return False
            self.logger.info("[%s] REF (slave): P2 at %.2fm — dig=%.0f, master_temp=%.1f°C",
                             sname, self.P2_kiln_ref.kiln_position, P2_dig,
                             Temperature.kelvinToCelsius(P2_temp))
        elif self.P2_temp_static:
            P2_temp = self.P2_temp
        else:
            P2_temp = self.scanner.temperatureManager.getValue(self.P2_temp_reference_index)

        if P1_temp < 0.0:
            raise ValueError("P1_temp < 0 Kelvin.")
        if P2_temp < 0.0:
            raise ValueError("P2_temp < 0 Kelvin.")

        # Enforce P2 is always the higher-temperature reference
        if P2_temp < P1_temp:
            P1_temp, P2_temp = P2_temp, P1_temp
            P1_dig, P2_dig = P2_dig, P1_dig
            self.logger.info("[%s] REF: P1/P2 swapped — P2 is now the higher reference "
                             "(%.1f°C > %.1f°C)",
                             sname, Temperature.kelvinToCelsius(P2_temp),
                             Temperature.kelvinToCelsius(P1_temp))

        if self.tempfit == 'linear':
            if P1_dig == P2_dig:
                self.logger.warning("[%s] REF: P1_dig == P2_dig (%.0f) — cannot compute linear calibration",
                                    sname, P1_dig)
                return False
            self.m = (P1_temp - P2_temp) / (P1_dig - P2_dig)
            self.b = P1_temp - self.m * P1_dig
            self.logger.info("[%s] REF: linear calibration updated — "
                             "P1(dig=%.0f, %.1f°C) P2(dig=%.0f, %.1f°C) → m=%.6f, b=%.2fK",
                             sname, P1_dig, Temperature.kelvinToCelsius(P1_temp),
                             P2_dig, Temperature.kelvinToCelsius(P2_temp),
                             self.m, self.b)
            return True

        p1_rad = Temperature.temperatureToRadiation(self.B, self.C, P1_temp)
        p2_rad = Temperature.temperatureToRadiation(self.B, self.C, P2_temp)
        self.A = Temperature.A_from_references(P1_dig, p1_rad, P2_dig, p2_rad, self.p1_emission, self.p2_emission, self.τa)
        self.u0 = Temperature.calculate_digital_offset_from_references(P1_dig, p1_rad, P2_dig, p2_rad)
        self.dPhi = 0.0
        self.logger.info("[%s] REF: exp calibration updated — "
                         "P1(dig=%.0f, %.1f°C) P2(dig=%.0f, %.1f°C) → A=%.6g, u0=%.2f",
                         sname, P1_dig, Temperature.kelvinToCelsius(P1_temp),
                         P2_dig, Temperature.kelvinToCelsius(P2_temp),
                         self.A, self.u0)
        return True

    def update_kiln_position_references(self, raw_data, geo_transformator):
        """Feed a raw FOV scan line into the kiln-position reference accumulators."""
        if self.P1_kiln_ref is not None:
            self.P1_kiln_ref.update(raw_data, geo_transformator)
        if self.P2_kiln_ref is not None:
            self.P2_kiln_ref.update(raw_data, geo_transformator)

    def on_kiln_trigger(self):
        """Commit accumulated maxima on kiln rotation trigger and invalidate cached calibration."""
        changed = False
        if self.P1_kiln_ref is not None:
            self.P1_kiln_ref.on_trigger()
            changed = True
        if self.P2_kiln_ref is not None:
            self.P2_kiln_ref.on_trigger()
            changed = True
        if changed:
            self.live_references_valid = False

    def update_references(self):
        """Update reference data and recalculate A and u0"""
        try:
            if self.live_references_valid:
                return
            if self.mode == "withReferences":
                if not self.update_two_references():
                    return  # not ready yet — will retry on next call
            elif self.mode == "withSingleReference":
                self.update_single_reference()
            self.live_references_valid = True
            self.update_log_conversion_table()
        except Exception:
            self.logger.exception("failure to update references")

    @property
    def offset(self):
        return self.u0

    def clamp_temperature(self, d):
        d = numpy.nan_to_num(d)
        d[d < self.temperature_lower_limit] = self.temperature_lower_limit
        return d

    def __str__(self):
        return "TempConverter(mode={}, A={}, B={}, C={}, u0={}, ε0={}, τa={}, dPhi={} Φs={} Φa={} Φw={} Φwcalib={} τw={})". \
                format(self.mode, self.A, self.B, self.C, self.u0, self.ε0, self.τa, self.dPhi, self.Φs, self.Φa, self.Φw,
                       self.Φwcalib, self.τw)

    def get_phi(self, temperature):
        return Temperature.temperatureToRadiation(self.B, self.C, temperature)

    def ΔΦ(self):
        """ΔΦ"Radiation Offset" i.e. stray radiation from object surroundings, atmosphere and window."""
        return self.Φs * (1.0 - self.ε0) / self.ε0 +\
                self.Φa * (1.0 - self.τa) / (self.u0 - self.τa) +\
                (self.Φw - self.Φwcalib) * (1.0 - self.τw) / (self.τw * self.u0 * self.τa)

    def Φ0(self, fov_angle, data ):
        with numpy.errstate(all="ignore"):
            data = data.astype(float)
            data -= self.u0 / (1 - self.L * (data - self.u0))

            # Adjust vignetting
            if fov_angle:
                # In this case, τw is a array containing the transmission for each pixel, with angle-based adjustements
                angle_dependent_window_transmission = self.window_transmission_vignetting.convert(fov_angle, data)
            else:
                # Without fov_angle, eg. for log output, use a fixed value of 1.0
                angle_dependent_window_transmission = 1.0

            if self.use_window_transmission:
                window_transmission = self.τw
            else:
                window_transmission = 1.0
            window_transmission *= angle_dependent_window_transmission
            return data / (self.A * self.ε0 * self.τa * window_transmission) - self.ΔΦ()

    def convert(self, fov_angle, data):
        """Convert digital data to temperatue in Kelvin"""
        # Remove digital offset
        with numpy.errstate(all="ignore"):
            # Convert to temperatures [Kelvin]
            if self.tempfit=='linear':
                t= self.clamp_temperature(data*self.m+self.b)
                return t

            return self.clamp_temperature(self.B / numpy.log((1.0 / self.Φ0(fov_angle, data) + 1) / self.C))

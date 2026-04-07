import unittest
from daq_net.daq import Temperature


class TestTemperatureBasics(unittest.TestCase):
    def test_kelvin_to_celsius(self):
        self.assertEqual(Temperature.kelvinToCelsius(0), -273.15)
        self.assertEqual(Temperature.kelvinToCelsius(273.15), 0)

    def test_kelvin_to_farenheit(self):
        self.assertAlmostEqual(Temperature.kelvinToFarenheit(0), -459.67)
        self.assertAlmostEqual(Temperature.kelvinToFarenheit(273.15), 32)

    def test_convert(self):
        Temperature.convert(Temperature.Kelvin, Temperature.Celsius, 0)
        Temperature.convert(Temperature.Kelvin, Temperature.Farenheit, 0)
        with self.assertRaises(ValueError):
            Temperature.convert(Temperature.Kelvin, 199, 0)
        with self.assertRaises(ValueError):
            Temperature.convert(Temperature.Kelvin, Temperature.RAW, 0)


class TestTemperaturePlanck(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        # CS17-034-R0A.8H170906A.I9948.A17-037.PTFN-WestAsia-IR.PB170918.pdf
        self.A = -103110
        self.B = 3760
        self.C = -0.42
        self.u0 = 204.69
        self.r1_temp = Temperature.celsiusToKelvin(75)
        self.r1_dig = 209.7
        self.r2_temp = Temperature.celsiusToKelvin(250)
        self.r2_dig = 390
        self.emission = 1
        self.transmission = 1
        self.dPhi = 0

    def _test_planck(self, digits, temperature_celsius):
        calculated_temperature = Temperature.dig2Temp(digits,
                                                      self.A,
                                                      self.B,
                                                      self.C,
                                                      self.u0,
                                                      self.emission,
                                                      self.transmission,
                                                      self.dPhi)
        calculated_temperature = Temperature.kelvinToCelsius(calculated_temperature)
        self.assertAlmostEqual(calculated_temperature, temperature_celsius, delta=0.1)

    def test_planck_1(self):
        self._test_planck(209.7, 75)

    def test_planck_2(self):
        self._test_planck(390, 250)

    def test_planck_3(self):
        self._test_planck(3400, 599.21)

    def _test_references(self, r1_temp, r1_dig, r1_emission, r2_temp, r2_dig, r2_emission, B, C, A, u0, transmission):
        r1_rad = Temperature.temperatureToRadiation(B, C, r1_temp)
        r2_rad = Temperature.temperatureToRadiation(B, C, r2_temp)
        calculated_A = Temperature.A_from_references(r1_dig, r1_rad, r2_dig, r2_rad, r1_emission, r2_emission, transmission)
        calculated_u0 = Temperature.calculate_digital_offset_from_references(r1_dig, r1_rad, r2_dig, r2_rad)
        self.assertAlmostEqual(A, calculated_A, delta=1)
        self.assertAlmostEqual(u0, calculated_u0, delta=0.01)

    def test_references_1(self):
        self._test_references(self.r1_temp, self.r1_dig, 1.0, self.r2_temp, self.r2_dig, 1.0,
                              self.B, self.C, self.A, self.u0, self.transmission)
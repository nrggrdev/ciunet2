import numpy


Kelvin = 0
Celsius = 1
Farenheit = 2
RAW = 3
unit = {"C": Celsius, "F": Farenheit, "K": Kelvin, "R": RAW}
text = {Kelvin: "K", Celsius: "C", Farenheit: "F", RAW: "R"}
full_text = {Kelvin: "Kelvin", Celsius: "Celsius", Farenheit: "Farenheit", RAW: "Raw"}
short_text = {Kelvin: "K", Celsius: "°C", Farenheit: "°F", RAW: "R"}
celsiusNP = -273.15


def temperatureToRadiation(B, C, temp):
    return 1.0 / (C * numpy.exp(B / temp) - 1.0)


def calculate_digital_offset_from_references(dig_ref1, rad_ref1, dig_ref2, rad_ref2):
    return (dig_ref1 * rad_ref2 - dig_ref2 * rad_ref1) / (rad_ref2 - rad_ref1)


def A_from_references(dig_ref1, rad_ref1, dig_ref2, rad_ref2, emission1, emission2, transmission):
    return (dig_ref2 - dig_ref1) / ((rad_ref2 * emission2 - rad_ref1 * emission1) * transmission)


def dig2Temp_after_offset(data, A, B, C, emission, transmission, dPhi):
    """Transform digital values after offset to temperature in Kelvin"""
    with numpy.errstate(all="ignore"):
        Phi = data / (A * emission * transmission) - dPhi
        return B / numpy.log((1.0 / Phi + 1) / C)

def dig2Temp(data, A, B, C, u0, emission, transmission, dPhi):
    """Transform digital values after offset to temperature in Kelvin"""
    data = numpy.subtract(data, u0)
    return dig2Temp_after_offset(data, A, B, C, emission, transmission, dPhi)


def celsiusToKelvin(data):
    return numpy.subtract(data, celsiusNP)


def kelvinToCelsius(data, celsiusNP=celsiusNP):
    return numpy.add(data, celsiusNP)


def celsiusToFarenheit(data):
    return numpy.add(numpy.multiply(data, 1.8), 32)


def farenheitToCelsius(data):
    return numpy.subtract(numpy.divide(data, 1.8), 32)


def kelvinToFarenheit(data):
    return celsiusToFarenheit(kelvinToCelsius(data))


def farenheitToKelvin(data):
    return celsiusToKelvin(farenheitToCelsius(data))


def temperatureToKelvin(unit_source, data):
    if unit_source == Celsius:
        return celsiusToKelvin(data)
    elif unit_source == Farenheit:
        return farenheitToKelvin(data)
    elif unit_source == Kelvin:
        return data
    raise ValueError("Invalid Temperature Unit")


def kelvinToTemperature(unit_dest, data):
    if unit_dest == Celsius:
        return kelvinToCelsius(data)
    elif unit_dest == Farenheit:
        return kelvinToFarenheit(data)
    elif unit_dest == Kelvin:
        return data
    raise ValueError("Invalid Temperature Unit")


def convert(unit_source, unit_dest, data):
    if unit_source == unit_dest:
        return data
    return kelvinToTemperature(unit_dest, temperatureToKelvin(unit_source, data))



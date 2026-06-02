"""
Testmuster-Generatoren fuer den Scanner-Simulator.

Jede Funktion liefert ein 1D-uint16-Array der Laenge ``length`` (Digit-Werte
einer FoV-Linie, 0..2**video_bits-1). ``t`` ist der fortlaufende Linienindex,
womit zeitliche Bewegung erzeugt werden kann.
"""

import numpy


def _clip(values, video_bits):
    maxval = (1 << video_bits) - 1
    return numpy.clip(values, 0, maxval).astype("uint16")


def gradient(length, t, video_bits=14, **_):
    """Horizontaler Verlauf von kalt nach warm, langsam driftend."""
    base = numpy.linspace(2000, 9000, length)
    drift = 1000.0 * numpy.sin(t / 30.0)
    return _clip(base + drift, video_bits)


def chessboard(length, t, video_bits=14, h_freq=16, v_freq=8,
               low=2000, high=9000, **_):
    """Schachbrett: wechselnde Bloecke entlang FoV und ueber Zeit."""
    x = (numpy.arange(length) * h_freq // length) % 2
    y = (t * v_freq // 100) % 2
    cells = numpy.where((x ^ y) == 0, high, low)
    return _clip(cells, video_bits)


def stripes(length, t, video_bits=14, n_marks=5, low=2500, high=11000, **_):
    """
    Ruhiger Hintergrund mit scharfen, festen vertikalen Markern.

    Ideal, um im Geometrie-Tool Referenzpunkte (Passpunkte) wiederzuerkennen:
    die Marker liegen bei konstanten Bruchteilen des FoV.
    """
    data = numpy.full(length, low, dtype=float)
    # leichter Bauch (Ofenkoerper)
    x = numpy.linspace(-1, 1, length)
    data += 1500.0 * numpy.exp(-(x ** 2) / 0.3)
    for k in range(1, n_marks + 1):
        pos = int(length * k / (n_marks + 1))
        w = max(2, length // 200)
        data[max(0, pos - w):pos + w] = high
    return _clip(data, video_bits)


def kiln(length, t, video_bits=14, low=2200, body=7000, **_):
    """
    Realistischeres Ofenbild: warmer Ofenkoerper (gewoelbt) auf kaltem
    Hintergrund, mit einem langsam wandernden heissen Fleck.
    """
    x = numpy.linspace(-1.0, 1.0, length)
    profile = body * numpy.exp(-(x ** 2) / 0.5) + low
    # wandernder Hotspot
    spot_pos = (numpy.sin(t / 25.0) * 0.6)
    profile += 4000.0 * numpy.exp(-((x - spot_pos) ** 2) / 0.005)
    # etwas Rauschen
    profile += numpy.random.normal(0, 40, length)
    return _clip(profile, video_bits)


PATTERNS = {
    "gradient": gradient,
    "chessboard": chessboard,
    "stripes": stripes,
    "kiln": kiln,
}

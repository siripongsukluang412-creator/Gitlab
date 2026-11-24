"""Tests for the dependency-free SVG chart renderer."""

import unittest

import svg_plots as plots


FREQ = [1, 10, 100, 1e3, 1e4, 1e5, 1e6]
GAIN = [-20, -3, 5, 6, 6, 5, -3]
PHASE = [-170, -175, -180, -180, -180, -181, -185]
TIME = [0, 0.00025, 0.0005, 0.00075, 0.001]
VIN = [0, 0.01, 0, -0.01, 0]
VOUT = [0, -0.02, 0, 0.02, 0]


class TestBode(unittest.TestCase):
    def test_renders_axes_units_and_two_traces(self):
        svg = plots.bode_svg(FREQ, GAIN, PHASE)

        self.assertIn("<svg", svg)
        self.assertIn("Frequency (Hz)", svg)
        self.assertIn("Gain (dB)", svg)
        self.assertIn("Phase (°)", svg)
        self.assertIn("1k", svg)
        self.assertIn("10k", svg)
        self.assertGreaterEqual(svg.count("<polyline"), 2)

    def test_renders_without_none_labels(self):
        svg = plots.bode_svg(FREQ, GAIN, PHASE)
        self.assertNotIn("None", svg)


class TestTransient(unittest.TestCase):
    def test_renders_time_and_voltage_axes(self):
        svg = plots.transient_svg(TIME, VIN, VOUT)

        self.assertIn("<svg", svg)
        self.assertIn("Time (ms)", svg)
        self.assertIn("Voltage (mV)", svg)
        self.assertIn("Vin", svg)
        self.assertIn("Vout", svg)
        self.assertEqual(svg.count("<polyline"), 2)

    def test_downsamples_long_waveforms(self):
        n = 5000
        time = [i / n for i in range(n)]
        vin = [0.01 * (i % 2) for i in range(n)]
        vout = [-0.02 * (i % 2) for i in range(n)]

        svg = plots.transient_svg(time, vin, vout)

        points = svg.count(" ")
        self.assertLess(points, 20000)


if __name__ == "__main__":
    unittest.main()

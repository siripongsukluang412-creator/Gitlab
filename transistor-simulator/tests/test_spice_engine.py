"""Tests for the ngspice adapter (netlist, run, parse).

Run with: py -m unittest discover -s tests -t . -v
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import spice_engine as se


PARAMS = se.CircuitParams(
    vcc=12.0,
    r1=100_000.0,
    r2=22_000.0,
    rc=2_200.0,
    re=1_000.0,
    beta=100.0,
    amp=10e-3,
    freq=1e3,
)

OP_RAW = """Title: * CE test
Plotname: Operating Point
Flags: real
No. Variables: 13
No. Points: 1
Variables:
\t0\tv(vcc)\tvoltage
\t1\ti(@q1[ib])\tcurrent
\t2\ti(@q1[ic])\tcurrent
\t3\ti(@q1[ie])\tcurrent
\t4\tv(@q1[vbe])\tvoltage
\t5\tv(@q1[vce])\tvoltage dims=0
\t6\tv(base)\tvoltage
\t7\tv(coll)\tvoltage
\t8\tv(emit)\tvoltage
\t9\tv(in)\tvoltage
\t10\tv(out)\tvoltage
\t11\ti(vcc)\tcurrent
\t12\ti(vin)\tcurrent
Values:
 0\t1.200000000000000e+01
\t1.191895272144118e-05
\t1.278192757271984e-03
\t-1.290111719182835e-03
\t6.596583592043330e-01
\t0.000000000000000e+00
\t1.949112053392557e+00
\t9.189410182055312e+00
\t1.289453694188224e+00
\t0.000000000000000e+00
\t0.000000000000000e+00
\t-1.378049705804569e-03
\t0.000000000000000e+00
"""

AC_DAT = """ frequency       gdb             gph
 1.00000000e+00  1.00000000e+00 -3.00000000e+00
 1.00000000e+01  5.00000000e+00 -3.14159000e+00
 1.00000000e+02  5.00000000e+00  3.14159000e+00
 1.00000000e+03  4.00000000e+00  3.00000000e+00
 1.00000000e+04  1.00000000e+00  2.00000000e+00
"""

TRAN_DAT = """ time            v(in)           v(out)
 0.00000000e+00  0.00000000e+00  0.00000000e+00
 2.50000000e-04  1.00000000e-02 -2.00000000e-02
 5.00000000e-04  0.00000000e+00  0.00000000e+00
 7.50000000e-04 -1.00000000e-02  2.00000000e-02
 1.00000000e-03  0.00000000e+00  0.00000000e+00
"""


class TestValidation(unittest.TestCase):
    def test_transient_requires_positive_amplitude(self):
        _, errors = se.validate_source("tran", "0", "1000")
        self.assertIn("amplitude", errors)

    def test_transient_rejects_out_of_range_frequency(self):
        _, errors = se.validate_source("tran", "10e-3", "1e9")
        self.assertIn("frequency", errors)

    def test_transient_accepts_valid_source(self):
        values, errors = se.validate_source("tran", "10e-3", "1e3")
        self.assertEqual(errors, {})
        self.assertAlmostEqual(values["amplitude"], 10e-3)
        self.assertAlmostEqual(values["frequency"], 1e3)

    def test_op_does_not_require_source_values(self):
        values, errors = se.validate_source("op", "", "")
        self.assertEqual(errors, {})
        self.assertEqual(values["amplitude"], 0.0)
        self.assertEqual(values["frequency"], 0.0)


class TestFindNgspice(unittest.TestCase):
    def test_env_override_is_used_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "ngspice_con.exe"
            fake.write_text("stub", encoding="utf-8")
            with mock.patch.dict(os.environ, {"NGSPICE_BIN": str(fake)}):
                self.assertEqual(se.find_ngspice(), str(fake))

    def test_missing_env_override_is_ignored(self):
        with mock.patch.dict(os.environ, {"NGSPICE_BIN": r"C:\does\not\exist.exe"}):
            found = se.find_ngspice()
            self.assertTrue(found is None or Path(found).is_file())

    def test_parse_version_reads_banner(self):
        banner = "******\n** ngspice-41 : Circuit level simulation program\n******\n"
        self.assertEqual(se.parse_version(banner), "ngspice-41")


class TestNetlist(unittest.TestCase):
    def test_op_netlist_has_reference_components(self):
        text = se.build_netlist(PARAMS, "op")
        for fragment in (
            "VCC vcc 0",
            "R1 vcc base",
            "R2 base 0",
            "RC vcc coll",
            "RE emit 0",
            "CIN in base",
            "COUT coll out",
            "RL out 0",
            "Q1 coll base emit QNPN",
            ".model QNPN NPN",
            "SIN(0",
            "op\nwrite op.raw",
        ):
            self.assertIn(fragment, text)

    def test_ac_netlist_requests_bode_vectors(self):
        text = se.build_netlist(PARAMS, "ac")
        self.assertIn("ac dec", text)
        self.assertIn("wrdata ac.dat", text)
        self.assertIn("gdb", text)
        self.assertIn("gph", text)

    def test_tran_netlist_uses_operating_point_initial_conditions(self):
        text = se.build_netlist(
            PARAMS,
            "tran",
            ic={"base": 1.949, "emit": 1.289, "coll": 9.189},
        )
        self.assertIn(".ic v(base)=1.949", text)
        self.assertIn("v(emit)=1.289", text)
        self.assertIn("v(coll)=9.189", text)
        self.assertIn("uic", text)
        self.assertIn("wrdata tran.dat", text)

    def test_netlist_values_are_si_numbers(self):
        text = se.build_netlist(PARAMS, "op")
        self.assertIn("100000", text)  # 100 kΩ
        self.assertIn("22000", text)  # 22 kΩ


class TestParsers(unittest.TestCase):
    def test_parse_op_raw_reads_node_and_device_values(self):
        data = se.parse_op_raw(OP_RAW)

        self.assertAlmostEqual(data["vb"], 1.949112053392557, places=9)
        self.assertAlmostEqual(data["ve"], 1.289453694188224, places=9)
        self.assertAlmostEqual(data["vc"], 9.189410182055312, places=9)
        self.assertAlmostEqual(data["vce"], 7.899956487867088, places=9)
        self.assertAlmostEqual(data["ic"], 1.278192757271984e-03, places=12)
        self.assertAlmostEqual(data["ie"], 1.290111719182835e-03, places=12)
        self.assertEqual(data["region"], "active")
        self.assertEqual(data["warnings"], [])

    def test_parse_op_raw_reports_saturation(self):
        text = OP_RAW.replace(
            " 0\t1.200000000000000e+01",
            " 0\t1.200000000000000e+01",
        )
        # coll below emit -> negative VCE
        text = text.replace(
            "9.189410182055312e+00",
            "1.250000000000000e+00",
        )
        data = se.parse_op_raw(text)
        self.assertEqual(data["region"], "saturation")
        self.assertTrue(data["warnings"])

    def test_parse_ac_dat_converts_phase_to_degrees_and_unwraps(self):
        data = se.parse_ac_dat(AC_DAT)

        self.assertEqual(len(data["frequency_hz"]), 5)
        self.assertAlmostEqual(data["midband_gain_db"], 5.0)
        self.assertAlmostEqual(data["phase_deg"][1], -180.0, places=3)
        self.assertAlmostEqual(data["phase_deg"][2], -180.0, places=3)
        self.assertLess(data["phase_deg"][3], -180.0)
        self.assertAlmostEqual(data["f_low_hz"], 10.0)
        self.assertAlmostEqual(data["f_high_hz"], 10_000.0)

    def test_parse_tran_dat_computes_peak_to_peak_gain_and_inversion(self):
        data = se.parse_tran_dat(TRAN_DAT)

        self.assertAlmostEqual(data["vin_pp"], 0.02)
        self.assertAlmostEqual(data["vout_pp"], 0.04)
        self.assertAlmostEqual(data["gain_pp"], 2.0)
        self.assertTrue(data["inverted"])


@unittest.skipUnless(se.find_ngspice(), "ngspice is not installed")
class TestRealNgspice(unittest.TestCase):
    def test_real_op_matches_analytical_reference(self):
        run = se.run_simulation(PARAMS, "op")
        data = run["data"]

        self.assertIn("ngspice", run["engine"])
        self.assertAlmostEqual(data["vb"], 1.9422, delta=0.10)
        self.assertAlmostEqual(data["ve"], 1.2422, delta=0.10)
        self.assertAlmostEqual(data["vc"], 9.2943, delta=0.15)
        self.assertAlmostEqual(data["vce"], 8.0522, delta=0.20)
        self.assertEqual(data["region"], "active")


if __name__ == "__main__":
    unittest.main()

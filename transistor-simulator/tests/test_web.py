import unittest
from unittest import mock

import spice_engine as se
from app import app


FAKE_OP = {
    "analysis": "op",
    "engine": "ngspice-41",
    "model": se.MODEL_DESCRIPTION,
    "netlist": "* reference CE\nVCC vcc 0 DC 12\nR1 vcc base 100000\n.op\n.end\n",
    "log": "No. of Data Rows : 1",
    "duration_s": 0.12,
    "workdir": "C:/tmp/op",
    "data": {
        "vb": 1.9491,
        "ve": 1.28945,
        "vc": 9.18941,
        "vce": 7.89996,
        "ib": 11.919e-6,
        "ic": 1.27819e-3,
        "ie": 1.29011e-3,
        "region": "active",
        "warnings": [],
    },
}

FAKE_AC = {
    "analysis": "ac",
    "engine": "ngspice-41",
    "model": se.MODEL_DESCRIPTION,
    "netlist": "* reference CE\n.ac dec 30 1 100meg\n.end\n",
    "log": "No. of Data Rows : 301",
    "duration_s": 0.21,
    "workdir": "C:/tmp/ac",
    "data": {
        "frequency_hz": [10.0, 100.0, 1e3, 1e4, 1e5],
        "gain_db": [4.70, 4.85, 4.86, 4.86, 4.80],
        "phase_deg": [-170.0, -180.0, -180.0, -180.0, -175.0],
        "midband_gain_db": 4.86,
        "midband_frequency_hz": 1e3,
        "f_low_hz": 10.0,
        "f_high_hz": 1e5,
    },
}

FAKE_TRAN = {
    "analysis": "tran",
    "engine": "ngspice-41",
    "model": se.MODEL_DESCRIPTION,
    "netlist": "* reference CE\n.tran 5u 5m\n.end\n",
    "log": "No. of Data Rows : 1011",
    "duration_s": 0.31,
    "workdir": "C:/tmp/tran",
    "data": {
        "time_s": [0.0, 0.25e-3, 0.5e-3, 0.75e-3, 1e-3],
        "vin_v": [0.0, 0.01, 0.0, -0.01, 0.0],
        "vout_v": [0.0, -0.035, 0.0, 0.035, 0.0],
        "vin_pp": 0.02,
        "vout_pp": 0.07,
        "gain_pp": 3.5,
        "inverted": True,
        "initial_conditions": {"base": 1.949, "emit": 1.289, "coll": 9.189},
    },
}


def form(**overrides):
    data = {
        "vcc": "12", "vcc_unit": "V",
        "r1": "47", "r1_unit": "kΩ",
        "r2": "10", "r2_unit": "kΩ",
        "rc": "2.2", "rc_unit": "kΩ",
        "re": "1", "re_unit": "kΩ",
        "beta": "100",
        "vbe": "0.7", "vbe_unit": "V",
    }
    data.update(overrides)
    return data


class TestWeb(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_index_renders_form_and_empty_results(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        for text in (
            "BJT DC Bias Web App",
            "Input Parameters",
            "Circuit: Common-Emitter Amplifier",
            "DC Bias Results",
            "Calculate DC Bias",
        ):
            self.assertIn(text, html)

    def test_valid_post_shows_operating_point(self):
        response = self.client.post("/", data=form())
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("12.9 µA", html)
        self.assertIn("1.29 mA", html)
        self.assertIn("1.30 mA", html)
        self.assertIn("7.87 V", html)
        self.assertIn("Active region approximation OK", html)

    def test_units_are_converted_to_base_units(self):
        in_kilo_ohms = self.client.post("/", data=form()).get_data(as_text=True)
        in_ohms = self.client.post(
            "/",
            data=form(
                r1="47000", r1_unit="Ω",
                r2="10000", r2_unit="Ω",
                rc="2200", rc_unit="Ω",
                re="1000", re_unit="Ω",
            ),
        ).get_data(as_text=True)

        self.assertIn("12.9 µA", in_kilo_ohms)
        self.assertIn("12.9 µA", in_ohms)

    def test_millivolt_unit_is_converted(self):
        html = self.client.post(
            "/", data=form(vcc="12000", vcc_unit="mV", vbe="700", vbe_unit="mV")
        ).get_data(as_text=True)

        self.assertIn("12.9 µA", html)

    def test_invalid_input_returns_400_and_message(self):
        response = self.client.post("/", data=form(r1="0"))
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("R_1 must be greater than 0", html)

    def test_non_numeric_input_returns_400(self):
        response = self.client.post("/", data=form(vcc="abc"))
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("V_CC must be a number", html)

    def test_cutoff_region_is_reported(self):
        html = self.client.post(
            "/", data=form(r1="100", r2="1")
        ).get_data(as_text=True)

        self.assertIn("Cutoff region", html)

    def test_saturation_region_is_reported(self):
        html = self.client.post(
            "/", data=form(rc="10")
        ).get_data(as_text=True)

        self.assertIn("Saturation region", html)


class TestLab04SpiceWeb(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def _post(self, **overrides):
        data = form(**overrides)
        data.setdefault("analysis", "analytical")
        return self.client.post("/", data=data)

    def test_index_offers_analysis_tabs_and_source_inputs(self):
        response = self.client.get("/?mode=divider&analysis=ac")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        for text in (
            "Analytical DC",
            "SPICE DC (.op)",
            "SPICE AC (.ac)",
            "SPICE Transient (.tran)",
            "V_in amplitude",
            "Frequency",
        ):
            self.assertIn(text, html)

    def test_analytical_page_never_shows_spice_claims(self):
        html = self.client.get("/").get_data(as_text=True)

        self.assertNotIn("SPICE simulation", html)
        self.assertNotIn("Bode plot", html)

    def test_spice_op_renders_provenance_and_engine(self):
        with mock.patch("app.spice_engine.run_simulation", return_value=FAKE_OP) as run:
            response = self._post(analysis="op")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("SPICE simulation", html)
        self.assertIn("ngspice-41", html)
        self.assertIn("Analytical model", html)
        self.assertIn("1.28 mA", html)  # I_C from the SPICE data
        self.assertIn("Operating Point", html)
        run.assert_called_once()

    def test_spice_ac_renders_bode_chart_and_cutoffs(self):
        with mock.patch("app.spice_engine.run_simulation", return_value=FAKE_AC):
            response = self._post(analysis="ac")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Bode plot", html)
        self.assertIn('<svg class="chart"', html)
        self.assertIn("Midband gain", html)
        self.assertIn("4.86 dB", html)
        self.assertIn("Frequency (Hz)", html)

    def test_spice_tran_renders_waveform_and_source_summary(self):
        with mock.patch("app.spice_engine.run_simulation", return_value=FAKE_TRAN):
            response = self._post(
                analysis="tran", amplitude="10", amplitude_unit="mV",
                frequency="1", frequency_unit="kHz",
            )
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Time (ms)", html)
        self.assertIn("Vin", html)
        self.assertIn("Vout", html)
        self.assertIn("inverted", html.lower())

    def test_source_units_are_converted_to_si_for_ngspice(self):
        captured = {}

        def fake_run(params, analysis, timeout=45.0):
            captured["params"] = params
            captured["analysis"] = analysis
            return FAKE_TRAN

        with mock.patch("app.spice_engine.run_simulation", side_effect=fake_run):
            self._post(
                analysis="tran", amplitude="20", amplitude_unit="mV",
                frequency="2", frequency_unit="kHz",
            )

        self.assertEqual(captured["analysis"], "tran")
        self.assertAlmostEqual(captured["params"].amp, 0.020)
        self.assertAlmostEqual(captured["params"].freq, 2_000.0)

    def test_spice_is_rejected_for_non_divider_bias_modes(self):
        response = self._post(mode="fixed", rb="470", analysis="op")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("voltage-divider", html)

    def test_transient_requires_positive_amplitude(self):
        with mock.patch("app.spice_engine.run_simulation") as run:
            response = self._post(
                analysis="tran", amplitude="0", amplitude_unit="mV",
                frequency="1", frequency_unit="kHz",
            )
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("amplitude must be greater than 0", html)
        run.assert_not_called()

    def test_transient_rejects_out_of_range_frequency(self):
        with mock.patch("app.spice_engine.run_simulation") as run:
            response = self._post(
                analysis="tran", amplitude="10", amplitude_unit="mV",
                frequency="2000", frequency_unit="kHz",
            )
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Frequency must be between", html)
        run.assert_not_called()

    def test_engine_failure_is_reported_without_a_chart(self):
        with mock.patch(
            "app.spice_engine.run_simulation",
            side_effect=se.SpiceError("ngspice exploded"),
        ):
            response = self._post(analysis="ac")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("SPICE simulation failed", html)
        self.assertIn("ngspice exploded", html)
        self.assertNotIn('<svg class="chart"', html)

    def test_spice_rejects_zero_emitter_resistor(self):
        with mock.patch("app.spice_engine.run_simulation") as run:
            response = self._post(analysis="op", re="0", re_unit="kΩ")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("R_E must be greater than 0", html)
        run.assert_not_called()

    def test_netlist_and_log_are_available_for_audit(self):
        with mock.patch("app.spice_engine.run_simulation", return_value=FAKE_OP):
            html = self._post(analysis="op").get_data(as_text=True)

        self.assertIn("Netlist", html)
        self.assertIn("ngspice log", html)
        self.assertIn("R1 vcc base", html)


if __name__ == "__main__":
    unittest.main()

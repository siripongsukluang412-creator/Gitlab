import unittest

from app import app


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


if __name__ == "__main__":
    unittest.main()

import unittest

from dc_bias import BiasInputs, VCE_SAT, calculate, validate_inputs


TEXTBOOK = BiasInputs(
    vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0, re=1000.0, beta=100.0, vbe=0.7
)


class TestKnownExample(unittest.TestCase):
    """Independent hand calculation, documented in docs/validation.md."""

    def test_textbook_example_values(self):
        result = calculate(TEXTBOOK)

        self.assertAlmostEqual(result.vbb, 2.1052631579, places=9)
        self.assertAlmostEqual(result.rth, 8245.6140350877, places=6)
        self.assertAlmostEqual(result.ib, 1.2863337080e-05, places=14)
        self.assertAlmostEqual(result.ic, 1.2863337080e-03, places=12)
        self.assertAlmostEqual(result.ie, 1.2991970451e-03, places=12)
        self.assertAlmostEqual(result.vce, 7.8708687972, places=9)
        self.assertAlmostEqual(result.ve, 1.2991970451, places=9)
        self.assertAlmostEqual(result.vc, 9.1700658423, places=9)
        self.assertAlmostEqual(result.vb, 1.9991970451, places=9)

    def test_textbook_example_is_active(self):
        result = calculate(TEXTBOOK)
        self.assertEqual(result.region, "active")
        self.assertEqual(result.warnings, ())


class TestRegions(unittest.TestCase):
    def test_cutoff_when_vbb_not_above_vbe(self):
        inputs = BiasInputs(
            vcc=12.0, r1=100000.0, r2=1000.0, rc=2200.0, re=1000.0,
            beta=100.0, vbe=0.7,
        )

        result = calculate(inputs)

        self.assertEqual(result.region, "cutoff")
        self.assertEqual(result.ib, 0.0)
        self.assertEqual(result.ic, 0.0)
        self.assertEqual(result.ie, 0.0)
        self.assertEqual(result.vce, 12.0)
        self.assertEqual(result.ve, 0.0)
        self.assertEqual(result.vc, 12.0)
        self.assertAlmostEqual(result.vb, 12.0 * 1000.0 / 101000.0)
        self.assertTrue(result.warnings)

    def test_saturation_when_vce_below_threshold(self):
        inputs = BiasInputs(
            vcc=12.0, r1=47000.0, r2=10000.0, rc=10000.0, re=1000.0,
            beta=100.0, vbe=0.7,
        )

        result = calculate(inputs)

        self.assertEqual(result.region, "saturation")
        self.assertLess(result.vce, VCE_SAT)
        self.assertTrue(result.warnings)


class TestValidation(unittest.TestCase):
    def base(self, **overrides):
        raw = {
            "vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
            "re": "1000", "beta": "100", "vbe": "0.7",
        }
        raw.update(overrides)
        return raw

    def test_valid_inputs_return_inputs_and_no_errors(self):
        inputs, errors = validate_inputs(self.base())

        self.assertEqual(errors, {})
        self.assertIsNotNone(inputs)
        self.assertAlmostEqual(inputs.vcc, 12.0)
        self.assertAlmostEqual(inputs.beta, 100.0)

    def test_missing_field_is_reported(self):
        _, errors = validate_inputs(self.base(r1=""))

        self.assertIn("r1", errors)
        self.assertTrue(errors["r1"])

    def test_non_numeric_field_is_reported(self):
        _, errors = validate_inputs(self.base(vcc="abc"))

        self.assertIn("vcc", errors)

    def test_zero_or_negative_supply_is_rejected(self):
        for value in ("0", "-1"):
            _, errors = validate_inputs(self.base(vcc=value))
            self.assertIn("vcc", errors)

    def test_zero_divider_resistor_is_rejected(self):
        for field in ("r1", "r2"):
            _, errors = validate_inputs(self.base(**{field: "0"}))
            self.assertIn(field, errors)

    def test_negative_load_resistor_is_rejected(self):
        for field in ("rc", "re"):
            _, errors = validate_inputs(self.base(**{field: "-1"}))
            self.assertIn(field, errors)

    def test_beta_out_of_range_is_rejected(self):
        for value in ("0", "-5", "10001"):
            _, errors = validate_inputs(self.base(beta=value))
            self.assertIn("beta", errors)

    def test_vbe_out_of_range_is_rejected(self):
        for value in ("-0.1", "2.5"):
            _, errors = validate_inputs(self.base(vbe=value))
            self.assertIn("vbe", errors)

    def test_non_finite_number_is_rejected(self):
        _, errors = validate_inputs(self.base(rc="inf"))

        self.assertIn("rc", errors)


if __name__ == "__main__":
    unittest.main()

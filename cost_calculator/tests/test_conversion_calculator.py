import math
import unittest

from costing.conversion_calculator import calculate_conversion, calculator_config


class ConversionCalculatorTests(unittest.TestCase):
    def test_config_exposes_mode_fields_and_presets(self):
        config = calculator_config()

        self.assertEqual(config["default_mode"], "rectangular")
        self.assertEqual(
            [mode["key"] for mode in config["modes"]],
            ["rectangular", "round", "quantity"],
        )
        self.assertEqual(config["modes"][0]["fields"][0]["key"], "height")
        self.assertEqual(config["default_preset"], "none")

    def test_rectangular_factor(self):
        result = calculate_conversion("rectangular", {"height": 2, "width": 3}, 0.5)

        self.assertEqual(result, {"area": 6.0, "factor": 3.0})

    def test_round_factor_subtracts_hole(self):
        result = calculate_conversion("round", {"diameter": 4, "holeDiameter": 2}, 0.25)

        self.assertAlmostEqual(result["area"], 3 * math.pi)
        self.assertAlmostEqual(result["factor"], 0.75 * math.pi)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown conversion calculator mode"):
            calculate_conversion("triangle", {}, 1)


if __name__ == "__main__":
    unittest.main()

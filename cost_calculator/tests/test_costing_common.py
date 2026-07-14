import unittest

from costing.common import markup_multiplier


class CommonCostingTests(unittest.TestCase):
    def test_zero_markup_multiplier_is_preserved(self):
        self.assertEqual(markup_multiplier(0), 0)

    def test_missing_markup_multiplier_uses_one(self):
        self.assertEqual(markup_multiplier(None), 1.0)


if __name__ == "__main__":
    unittest.main()

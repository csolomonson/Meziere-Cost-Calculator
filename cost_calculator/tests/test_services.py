import unittest
from unittest.mock import patch

import pandas as pd

from web.services import enrich_material_lines_from_child_costs


class MaterialChildCostEnrichmentTests(unittest.TestCase):
    @patch("web.services.get_part_cost")
    def test_current_child_cost_keeps_current_source_and_exact_run(self, mock_get_part_cost):
        mock_get_part_cost.return_value = pd.DataFrame([{
            "ucpPartCostID": 42,
            "ucpCostQuantity": 10,
            "ucpUnitRawCost": 7.5,
            "ucpMaterialsRawCost": 75,
            "ucpMachineTimeRawCost": 0,
            "ucpLaborRawCost": 0,
            "ucpExternalOperationsRawCost": 0,
            "ucpAdditionalRawCost": 0,
            "ucpIsCurrent": True,
        }])
        lines = pd.DataFrame([{
            "ucmManufacturedPartCostID": 42,
            "ucmCostSource": "manufactured_history",
            "ucmTotalQuantityRequired": 2,
        }])

        line = enrich_material_lines_from_child_costs(lines).iloc[0]

        self.assertEqual(line["ucmCostSource"], "manufactured_current")
        self.assertTrue(line["ucmManufacturedPartCostIsCurrent"])
        self.assertEqual(line["ucmManufacturedPartCostID"], 42)
        self.assertEqual(line["ucmUnitCost"], 7.5)
        self.assertEqual(line["ucmRawCost"], 15)

    @patch("web.services.get_part_cost")
    def test_manual_override_is_not_replaced_by_a_former_child_cost(self, mock_get_part_cost):
        lines = pd.DataFrame([{
            "ucmManufacturedPartCostID": 42,
            "ucmCostSource": "manual_override",
            "ucmUnitCost": 9.25,
            "ucmRawCost": 18.5,
            "ucmTotalQuantityRequired": 2,
        }])

        line = enrich_material_lines_from_child_costs(lines).iloc[0]

        mock_get_part_cost.assert_not_called()
        self.assertEqual(line["ucmCostSource"], "manual_override")
        self.assertEqual(line["ucmUnitCost"], 9.25)
        self.assertEqual(line["ucmRawCost"], 18.5)


if __name__ == "__main__":
    unittest.main()

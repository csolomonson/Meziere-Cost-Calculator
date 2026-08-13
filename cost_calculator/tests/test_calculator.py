import unittest
from unittest.mock import patch

import pandas as pd

from costing import calculator, operations
from tests.costing_fixtures import (
    COST_QUANTITY,
    PART_ID,
    REVISION_ID,
    wpbbc01u_part_df,
)


class WPBBC01UCostRunTests(unittest.TestCase):
    @patch("costing.calculator.get_part")
    @patch("costing.calculator.build_material_cost_lines")
    @patch("costing.calculator.build_operation_cost_lines")
    def test_wpbbc01u_full_cost_run_summarizes_operations_and_one_material(
        self, mock_operation_lines, mock_material_lines, mock_part
    ):
        operation_lines = operations.update_internal_costs(
            pd.DataFrame([
                {
                    "ucoCostQuantity": COST_QUANTITY,
                    "ucoQuantityPerAssembly": 1.0,
                    "ucoBatchSize": 1,
                    "ucoAdditionalCostPerPart": 0.0,
                    "ucoAdditionalCostTotal": 0.0,
                    "ucoAdditionalCostMarkup": 1.15,
                    "ucoSetupLaborRate": 25.0,
                    "ucoSetupTimeHours": 0.25,
                    "ucoBatchResetLaborRate": 25.0,
                    "ucoBatchResetTimeHours": 0.0,
                    "ucoLaborMarkup": 1.15,
                    "ucoCycleTimeHours": 0.025,
                    "ucoBatchIdleTimeHours": 0.0,
                    "ucoMachineOccupiedHourlyCost": 5.0,
                    "ucoMachineRunningHourlyCost": 20.0,
                    "ucoMachineCostMarkup": 1.15,
                    "ucoExternalCost": 0.0,
                    "ucoExternalOperationMarkup": 1.25,
                },
                {
                    "ucoCostQuantity": COST_QUANTITY,
                    "ucoQuantityPerAssembly": 1.0,
                    "ucoBatchSize": 1,
                    "ucoAdditionalCostPerPart": 0.0,
                    "ucoAdditionalCostTotal": 0.0,
                    "ucoAdditionalCostMarkup": 1.15,
                    "ucoSetupLaborRate": 25.0,
                    "ucoSetupTimeHours": 0.0,
                    "ucoBatchResetLaborRate": 25.0,
                    "ucoBatchResetTimeHours": 0.0,
                    "ucoLaborMarkup": 1.15,
                    "ucoCycleTimeHours": 0.0,
                    "ucoBatchIdleTimeHours": 0.0,
                    "ucoMachineOccupiedHourlyCost": 0.0,
                    "ucoMachineRunningHourlyCost": 0.0,
                    "ucoMachineCostMarkup": 1.15,
                    "ucoExternalCost": 8125.0,
                    "ucoExternalOperationMarkup": 1.25,
                },
            ])
        )
        material_lines = pd.DataFrame([
            {
                "ucmTotalQuantityRequired": COST_QUANTITY,
                "ucmMinimumPurchaseQty": 0.0,
                "ucmUnitCost": 2.75,
                "ucmMaterialMarkup": 1.25,
                "ucmRawCost": 0.0,
                "ucmMarkedUpCost": 0.0,
            }
        ])
        mock_part.return_value = wpbbc01u_part_df()
        mock_operation_lines.return_value = operation_lines
        mock_material_lines.return_value = material_lines

        result = calculator.build_part_cost(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            cost_quantity=COST_QUANTITY,
            costed_by="test",
        )

        summary = result["part_cost"].iloc[0]
        self.assertEqual(summary["ucpPartID"], PART_ID)
        self.assertEqual(len(result["material_lines"]), 1)
        self.assertAlmostEqual(summary["ucpMaterialsRawCost"], 27500.0)
        self.assertAlmostEqual(summary["ucpMachineTimeRawCost"], 6251.25)
        self.assertAlmostEqual(summary["ucpLaborRawCost"], 6.25)
        self.assertAlmostEqual(summary["ucpExternalOperationsRawCost"], 8125.0)
        self.assertAlmostEqual(summary["ucpTotalRawCost"], 41882.5)
        self.assertAlmostEqual(summary["ucpUnitRawCost"], 4.18825)

import assert from "node:assert/strict";
import test from "node:test";

import {
  activeMarkupBreak,
  afterHoursIdleHours,
  manualMaterialCostOverride,
  materialSource,
  materialUsesCurrentCostRun,
  recalcRun,
  valuesEquivalent,
} from "../src/domain/calculations.js";
import {
  formatDurationInput,
  hoursToClock,
  parseDurationInput,
} from "../src/domain/formatting.js";
import { partCostReportUrl } from "../src/domain/reports.js";

const markupBreaks = [
  { breakQty: 1, material: 2, labor: 1.5, machine: 2, external: 1.25, additional: 1.1 },
  { breakQty: 100, material: 3, labor: 2, machine: 2.5, external: 1.5, additional: 1.2 },
];

test("part cost report URLs require a saved positive integer ID", () => {
  assert.equal(partCostReportUrl(42), "/api/reports/part-cost/42");
  assert.equal(partCostReportUrl("42"), "/api/reports/part-cost/42");
  assert.equal(partCostReportUrl(null), "");
  assert.equal(partCostReportUrl(0), "");
});

test("duration parsing and formatting preserve the accepted input contract", () => {
  assert.equal(parseDurationInput("1:30"), 1.5);
  assert.equal(parseDurationInput("1h 15m 30s"), 1.2583333333333333);
  assert.equal(parseDurationInput("not a duration"), null);
  assert.equal(formatDurationInput(1.5), "1h 30m");
  assert.equal(hoursToClock(25.5), "01:30");
});

test("quantity breaks choose the greatest applicable threshold", () => {
  assert.equal(activeMarkupBreak(markupBreaks, 99).breakQty, 1);
  assert.equal(activeMarkupBreak(markupBreaks, 100).breakQty, 100);
});

test("edited-value comparison retains numeric and one-second duration tolerances", () => {
  assert.equal(valuesEquivalent("ucpCostQuantity", "10", 10), true);
  assert.equal(valuesEquivalent("ucoCycleTimeHours", 1, 1 + (0.5 / 3600)), true);
  assert.equal(valuesEquivalent("ucoCycleTimeHours", 1, 1 + (2 / 3600)), false);
});

test("overriding a manufactured unit cost makes the manual value authoritative", () => {
  const source = {
    _id: "material-1",
    ucmBackflush: true,
    ucmIsPurchased: false,
    ucmQtyPerAssembly: 2,
    ucmCostQuantity: 10,
    ucmTotalQuantityRequired: 20,
    ucmUnitCost: 4,
    ucmCostSource: "manufactured_current",
    ucmManufacturedPartCostID: 42,
    ucmManufacturedPartCostIsCurrent: true,
    ucmMaterialsRawCost: 20,
    ucmMachineTimeRawCost: 20,
    ucmLaborRawCost: 20,
    ucmExternalOperationsRawCost: 10,
    ucmAdditionalRawCost: 10,
    ucmMaterialMarkup: 1.25,
  };

  const overridden = manualMaterialCostOverride(source, 7.5);
  const recalculated = recalcRun({ part_cost: { ucpCostQuantity: 10 }, material_lines: [overridden], operation_lines: [] }, markupBreaks);
  const line = recalculated.material_lines[0];

  assert.equal(line.ucmUnitCost, 7.5);
  assert.equal(line.ucmRawCost, 150);
  assert.equal(line.ucmCostSource, "manual_override");
  assert.equal(line.ucmManufacturedPartCostID, null);
  assert.equal(line.ucmManufacturedPartCostIsCurrent, false);
  assert.equal(materialSource(line).label, "Manual unit cost");
  assert.equal(materialUsesCurrentCostRun(line), false);
});

test("current manufactured sources expose their exact saved run", () => {
  assert.equal(materialUsesCurrentCostRun({ ucmCostSource: "manufactured_current", ucmManufacturedPartCostID: 42 }), true);
  assert.equal(materialUsesCurrentCostRun({ ucmCostSource: "manufactured_history", ucmManufacturedPartCostID: 42, ucmManufacturedPartCostIsCurrent: false }), false);
});

test("after-hours idle calculation rolls completion to the next first shift", () => {
  assert.equal(
    afterHoursIdleHours("14:00", 1, {
      firstShiftStart: "06:00",
      firstShiftEnd: "14:30",
      afterHoursIdleMultiplier: 1,
    }),
    15,
  );
});

test("run recalculation preserves the established material and operation totals", () => {
  const recalculated = recalcRun({
    part_cost: { ucpCostQuantity: 10 },
    material_lines: [{
      _id: "material-1",
      ucmBackflush: true,
      ucmIsPurchased: true,
      ucmQtyPerAssembly: 2,
      ucmMinimumPurchaseQty: 6,
      ucmUnitCost: 3,
      ucmMaterialMarkup: 2,
    }],
    operation_lines: [{
      _id: "operation-1",
      ucoQuantityPerAssembly: 1,
      ucoSetupTimeHours: 1,
      ucoCycleTimeHours: 0.5,
      ucoBatchSize: 5,
      ucoBatchResetTimeHours: 0.25,
      ucoBatchIdleTimeHours: 0.25,
      ucoUseAfterHoursIdle: false,
      ucoSetupLaborRate: 20,
      ucoBatchResetLaborRate: 10,
      ucoLaborMarkup: 1.5,
      ucoMachineRunningHourlyCost: 4,
      ucoMachineOccupiedHourlyCost: 2,
      ucoMachineCostMarkup: 2,
      ucoExternalJob: false,
      ucoExternalUnitCost: 0,
      ucoExternalOperationMarkup: 1.25,
      ucoAdditionalCostPerPart: 1,
      ucoAdditionalCostMarkup: 1.1,
    }],
  }, markupBreaks);

  assert.equal(recalculated.material_lines[0].ucmTotalQuantityRequired, 20);
  assert.equal(recalculated.material_lines[0].ucmWasteQuantity, 4);
  assert.equal(recalculated.part_cost.ucpMaterialsRawCost, 72);
  assert.equal(recalculated.part_cost.ucpMaterialsMarkedUpCost, 144);
  assert.equal(recalculated.part_cost.ucpMachineTimeRawCost, 33);
  assert.equal(recalculated.part_cost.ucpLaborRawCost, 22.5);
  assert.equal(recalculated.part_cost.ucpAdditionalRawCost, 10);
  assert.equal(recalculated.part_cost.ucpTotalRawCost, 137.5);
  assert.equal(recalculated.part_cost.ucpTotalMarkedUpCost, 254.75);
  assert.equal(recalculated.part_cost.ucpUnitRawCost, 13.75);
  assert.equal(recalculated.part_cost.ucpUnitMarkedUpCost, 25.475);
});

export const moneyFields = new Set([
  "ucpMaterialsRawCost", "ucpMaterialsMarkedUpCost", "ucpMachineTimeRawCost", "ucpMachineTimeMarkedUpCost",
  "ucpLaborRawCost", "ucpLaborMarkedUpCost", "ucpExternalOperationsRawCost", "ucpExternalOperationsMarkedUpCost",
  "ucpAdditionalRawCost", "ucpAdditionalMarkedUpCost", "ucpTotalRawCost", "ucpTotalMarkedUpCost",
  "ucpUnitRawCost", "ucpUnitMarkedUpCost", "ucpRetailUnitPrice", "ucmUnitCost", "ucmPurchaseUnitCost", "ucmLastPOCost", "ucmRetailUnitPrice", "ucmRawCost", "ucmMarkedUpCost",
  "ucoSetupLaborRate", "ucoBatchResetLaborRate", "ucoMachineRunningHourlyCost", "ucoMachineOccupiedHourlyCost",
  "ucoExternalCost", "ucoExternalUnitCost", "ucoLastPOCost", "ucoAdditionalCostPerPart", "ucoMachineRawCost",
  "ucoMachineMarkedUpCost", "ucoLaborRawCost", "ucoLaborMarkedUpCost", "ucoExternalOperationRawCost",
  "ucoExternalOperationMarkedUpCost", "ucoAdditionalCostRawCost", "ucoAdditionalCostMarkedUpCost", "ucoLineRawCost", "ucoLineMarkedUpCost",
  "ucmMaterialsRawCost", "ucmMaterialsMarkedUpCost", "ucmMachineTimeRawCost", "ucmMachineTimeMarkedUpCost",
  "ucmLaborRawCost", "ucmLaborMarkedUpCost", "ucmExternalOperationsRawCost", "ucmExternalOperationsMarkedUpCost",
  "ucmAdditionalRawCost", "ucmAdditionalMarkedUpCost",
]);

export const numericFields = new Set(["quantity", "ucpCostQuantity", "ucmQtyPerAssembly", "ucmTotalQuantityRequired", "ucmUnitCost", "ucmPurchaseUnitCost", "ucmRetailUnitPrice", "ucmMinimumPurchaseQty", "ucmMaterialMarkup", "ucoQuantityPerAssembly", "ucoSetupTimeHours", "ucoCycleTimeHours", "ucoBatchSize", "ucoBatchResetTimeHours", "ucoBatchIdleTimeHours", "ucoSetupLaborRate", "ucoBatchResetLaborRate", "ucoLaborMarkup", "ucoMachineRunningHourlyCost", "ucoMachineOccupiedHourlyCost", "ucoMachineCostMarkup", "ucoExternalUnitCost", "ucoExternalOperationMarkup", "ucoAdditionalCostPerPart", "ucoAdditionalCostMarkup", "ucoAfterHoursIdleRateMultiplier", "afterHoursIdleMultiplier"]);
export const durationFields = new Set(["ucoSetupTimeHours", "ucoCycleTimeHours", "ucoBatchResetTimeHours", "ucoBatchIdleTimeHours"]);

export const partDefaults = { ucpPartCostID: null, ucpPartID: "", ucpPartRevision: "", ucpPartDescription: "", ucpCostQuantity: 10000, ucpRetailUnitPrice: null, ucpMaterialsRawCost: 0, ucpMaterialsMarkedUpCost: 0, ucpMachineTimeRawCost: 0, ucpMachineTimeMarkedUpCost: 0, ucpLaborRawCost: 0, ucpLaborMarkedUpCost: 0, ucpExternalOperationsRawCost: 0, ucpExternalOperationsMarkedUpCost: 0, ucpAdditionalRawCost: 0, ucpAdditionalMarkedUpCost: 0, ucpTotalRawCost: 0, ucpTotalMarkedUpCost: 0, ucpUnitRawCost: 0, ucpUnitMarkedUpCost: 0, ucpIsCurrent: false };
export const defaultMarkupBreaks = [1, 10, 100, 1000, 10000].map((breakQty) => ({ breakQty, material: 1.25, labor: 1.15, machine: 1.15, external: 1.25, additional: 1.15 }));
export const defaultShiftSettings = { firstShiftStart: "06:00", firstShiftEnd: "14:30", afterHoursIdleMultiplier: 1 };

export const materialFields = [["ucmMaterialID", "Material part number"], ["ucmMaterialDescription", "Material description"], ["ucmBackflush", "Backflushed into cost", "checkbox"], ["ucmIsPurchased", "Purchased material", "checkbox"], ["ucmQtyPerAssembly", "Quantity used per finished part"], ["ucmUnitCost", "Unit material cost"], ["ucmRetailUnitPrice", "Retail unit price"], ["ucmMinimumPurchaseQty", "Purchase quantity increment"], ["ucmMaterialMarkup", "Material markup multiplier"], ["ucmLastPO", "Last purchase order"], ["ucmLastPOCost", "Last PO unit cost"], ["ucmLastPODate", "Last PO date"]];
export const opCommonFields = [["ucoPartOperationLineID", "Operation sequence"], ["ucoWorkCenterID", "Machine / work center"], ["ucoOperationID", "Process code"], ["ucoOperationDescription", "Operation description"], ["ucoQuantityPerAssembly", "Operation quantity per finished part"], ["ucoExternalJob", "Purchased outside operation", "checkbox"]];
export const opInternalFields = [["ucoSetupTimeHours", "Setup time"], ["ucoSetupLaborRate", "Setup labor hourly rate"], ["ucoBatchSize", "Parts per unattended batch"], ["ucoCycleTimeHours", "Cycle time per part"], ["ucoBatchResetTimeHours", "Reset time between batches"], ["ucoBatchIdleTimeHours", "Idle time between batches"], ["ucoUseAfterHoursIdle", "Cost after-hours idle time", "checkbox"], ["ucoBatchResetLaborRate", "Tending labor hourly rate"], ["ucoLaborMarkup", "Labor markup multiplier"], ["ucoMachineRunningHourlyCost", "Machine active hourly cost"], ["ucoMachineOccupiedHourlyCost", "Machine occupied idle hourly cost"], ["ucoMachineCostMarkup", "Machine markup multiplier"], ["ucoAdditionalCostPerPart", "Additional cost per finished part"], ["ucoAdditionalCostMarkup", "Additional cost markup multiplier"]];
export const opExternalFields = [["ucoExternalUnitCost", "Outside service unit cost"], ["ucoExternalOperationMarkup", "Outside service markup multiplier"], ["ucoAdditionalCostPerPart", "Additional cost per finished part"], ["ucoAdditionalCostMarkup", "Additional cost markup multiplier"], ["ucoLastPO", "Last purchase order"], ["ucoLastPOCost", "Last PO unit cost"], ["ucoLastPODate", "Last PO date"]];
export const machineDefaultFields = [["ucoSetupLaborRate", "Setup labor rate"], ["ucoBatchResetLaborRate", "Tending labor rate"], ["ucoMachineRunningHourlyCost", "Active machine rate"], ["ucoMachineOccupiedHourlyCost", "Occupied idle rate"], ["ucoBatchResetTimeHours", "Default reset time"], ["ucoBatchIdleTimeHours", "Default idle time"]];
export const markupDefaults = [["material", "Material", "ucmMaterialMarkup"], ["labor", "Labor", "ucoLaborMarkup"], ["machine", "Machine", "ucoMachineCostMarkup"], ["external", "External", "ucoExternalOperationMarkup"], ["additional", "Additional", "ucoAdditionalCostMarkup"]];
export const machineDefaultKeys = new Set(machineDefaultFields.map(([field]) => field));
export const defaultGlobalMachineDefaults = { ucoSetupLaborRate: 0, ucoBatchResetLaborRate: 0, ucoMachineRunningHourlyCost: 0, ucoMachineOccupiedHourlyCost: 0, ucoBatchResetTimeHours: 0, ucoBatchIdleTimeHours: 0 };

export const costBuckets = [
  { key: "materials", label: "Material", materialRaw: "ucmMaterialsRawCost", materialMarked: "ucmMaterialsMarkedUpCost", operationRaw: null, operationMarked: null, partRaw: "ucpMaterialsRawCost", markup: "material" },
  { key: "machine", label: "Machine", materialRaw: "ucmMachineTimeRawCost", materialMarked: "ucmMachineTimeMarkedUpCost", operationRaw: "ucoMachineRawCost", operationMarked: "ucoMachineMarkedUpCost", partRaw: "ucpMachineTimeRawCost", markup: "machine" },
  { key: "labor", label: "Labor", materialRaw: "ucmLaborRawCost", materialMarked: "ucmLaborMarkedUpCost", operationRaw: "ucoLaborRawCost", operationMarked: "ucoLaborMarkedUpCost", partRaw: "ucpLaborRawCost", markup: "labor" },
  { key: "external", label: "External", materialRaw: "ucmExternalOperationsRawCost", materialMarked: "ucmExternalOperationsMarkedUpCost", operationRaw: "ucoExternalOperationRawCost", operationMarked: "ucoExternalOperationMarkedUpCost", partRaw: "ucpExternalOperationsRawCost", markup: "external" },
  { key: "additional", label: "Additional", materialRaw: "ucmAdditionalRawCost", materialMarked: "ucmAdditionalMarkedUpCost", operationRaw: "ucoAdditionalCostRawCost", operationMarked: "ucoAdditionalCostMarkedUpCost", partRaw: "ucpAdditionalRawCost", markup: "additional" },
];

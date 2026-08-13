import { formatValue, toNumber } from "../../domain/formatting.js";
import { materialHasNoRoute, materialIsManufactured } from "../../domain/calculations.js";

export function findIssues(run) {
  const issues = [];
  const materials = run.material_lines || [], operations = run.operation_lines || [];
  if (!materials.length && operations.some((row) => !row.ucoExternalJob)) issues.push({ kind: "part", id: "part.no-materials", tone: "amber", text: (run.part_cost?.ucpPartID || "This part") + " has manufacturing operations but no material lines." });
  materials.forEach((row) => {
    const name = row.ucmMaterialID || "Material";
    if (row.ucmIsPurchased && !row.ucmLastPO) issues.push({ kind: "material", id: row._id + ".no-po", rowId: row._id, tone: "amber", text: name + " is purchased but has no purchase order history." });
    if (materialHasNoRoute(row)) issues.push({ kind: "material", id: row._id + ".no-route", rowId: row._id, tone: "red", text: name + " is marked manufactured but has no child materials or processes, so its cost should be zero." });
    else if (materialIsManufactured(row) && toNumber(row.ucmUnitCost) === 0) issues.push({ kind: "material", id: row._id + ".zero-cost", rowId: row._id, tone: "amber", text: name + " is manufactured with zero unit cost. It likely needs to be costed as a child." });
    if (toNumber(row.ucmWasteQuantity) > 0) issues.push({ kind: "material", id: row._id + ".waste", rowId: row._id, tone: "blue", text: name + " wastes " + formatValue("ucmWasteQuantity", row.ucmWasteQuantity) + " because of purchase increment." });
  });
  (run.operation_lines || []).forEach((row) => { if (row.ucoExternalJob && !row.ucoLastPO) issues.push({ kind: "operation", id: row._id, tone: "amber", text: (row.ucoOperationDescription || "External operation") + " has no purchase order reference." }); if (!row.ucoExternalJob && toNumber(row.ucoAfterHoursIdleTimeHours) > 0) issues.push({ kind: "operation", id: row._id, tone: "blue", text: (row.ucoOperationDescription || "Operation") + " includes after-hours idle time." }); });
  return issues;
}



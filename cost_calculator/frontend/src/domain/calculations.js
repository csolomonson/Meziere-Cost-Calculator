import {
  costBuckets,
  defaultGlobalMachineDefaults,
  defaultMarkupBreaks,
  defaultShiftSettings,
  durationFields,
  machineDefaultFields,
  markupDefaults,
  materialFields,
  numericFields,
  opCommonFields,
  opExternalFields,
  opInternalFields,
  partDefaults,
} from "./model.js";
import { numberOr, parseTimeHours, toNumber } from "./formatting.js";

export function uid(prefix) { return prefix + Math.random().toString(36).slice(2, 9); }
export function keyFor(row, field) { return row._id + "." + field; }
export function valuesEquivalent(field, value, originalValue) { if ((value === null || value === undefined || value === "") && (originalValue === null || originalValue === undefined || originalValue === "")) return true; if (durationFields.has(field)) return Math.abs(toNumber(value) - toNumber(originalValue)) < (1 / 3600); if (numericFields.has(field)) return Math.abs(toNumber(value) - toNumber(originalValue)) < 0.0000001; if (typeof value === "boolean" || typeof originalValue === "boolean") return Boolean(value) === Boolean(originalValue); return String(value ?? "") === String(originalValue ?? ""); }
export function setEditedForValue(current, key, field, value, originalValue) { const next = new Set(current); if (valuesEquivalent(field, value, originalValue)) next.delete(key); else next.add(key); return next; }
export function machineKey(row) { return row?.ucoWorkCenterID || "Unassigned"; }
export function processTimingFields(process, row) {
  const setup = toNumber(process.xawSetupHours ?? process.xaoSetupHours ?? row.ucoSetupTimeHours);
  const productionStandard = toNumber(process.xawProductionStandard ?? process.xaoProductionStandard);
  return {
    ucoSetupTimeHours: setup,
    ucoCycleTimeHours: productionStandard > 0 ? productionStandard / 60 : toNumber(row.ucoCycleTimeHours),
  };
}
export function materialSource(row) { if (row?.ucmBackflush === false || row?.ucmBackflush === 0) return { label: "Not backflushed", tone: "neutral" }; if (row?.ucmCostSource === "manufactured_current") return { label: "Manufactured current", tone: "green" }; if (row?.ucmCostSource === "manufactured_history") return { label: "Manufactured history", tone: "green" }; if (row?.ucmCostSource === "manufactured_route") return { label: "Manufactured route", tone: "blue" }; if (row?.ucmIsPurchased || row?.ucmCostSource === "purchase_order") return { label: "Purchased", tone: "amber" }; return { label: "Manufactured/internal", tone: "blue" }; }
export function materialIsManufactured(row) { return !row?.ucmIsPurchased && (String(row?.ucmCostSource || "").startsWith("manufactured_") || row?.ucmHasManufacturingDetail || row?.ucmCostSource === "erp_estimate" || row?.ucmCostSource === "manual"); }
export function materialHasNoRoute(row) { return !row?.ucmIsPurchased && row?.ucmHasManufacturingDetail === false && toNumber(row?.ucmManufacturingMaterialCount) === 0 && toNumber(row?.ucmManufacturingOperationCount) === 0; }
export function materialNeedsPartCostUpdate(row) { return !row?.ucmIsPurchased && row?.ucmMaterialID && row?.ucmCostSource === "manufactured_history" && (!row.ucmManufacturedPartCostID || row.ucmManufacturedPartCostIsCurrent === false || row.ucmManufacturedPartCostIsCurrent === 0); }
export function pct(start, duration, day) { const left = Math.max(0, Math.min(24, start - day * 24)); const right = Math.max(0, Math.min(24, start + duration - day * 24)); return { left: left / 24 * 100, width: Math.max(0, (right - left) / 24 * 100) }; }
export function operationTiming(row) {
  const lineQty = toNumber(row.ucoCostQuantity) * numberOr(row.ucoQuantityPerAssembly, 1);
  const batchSize = toNumber(row.ucoBatchSize) || 1;
  const batches = lineQty > 0 ? Math.ceil(lineQty / batchSize) : 0;
  const resets = Math.max(batches - 1, 0);
  const setup = toNumber(row.ucoSetupTimeHours);
  const cycle = lineQty * toNumber(row.ucoCycleTimeHours);
  const reset = resets * toNumber(row.ucoBatchResetTimeHours);
  const batchIdle = resets * toNumber(row.ucoBatchIdleTimeHours);
  return { lineQty, batchSize, batches, resets, setup, cycle, reset, batchIdle, runtime: setup + cycle + reset + batchIdle };
}
export function calendarSegments(row, start, shownDays) {
  const timing = operationTiming(row);
  const visibleStart = Math.min(...shownDays) * 24;
  const visibleEnd = (Math.max(...shownDays) + 1) * 24;
  const resetHours = toNumber(row.ucoBatchResetTimeHours);
  const idleHours = toNumber(row.ucoBatchIdleTimeHours);
  const cycleHours = toNumber(row.ucoCycleTimeHours);
  const segments = [];
  function push(kind, label, left, duration) {
    if (duration <= 0.0001 || left + duration < visibleStart || left > visibleEnd) return;
    segments.push({ kind, label, left, duration });
  }
  push("setup", "Setup", start, timing.setup);
  let cursor = start + timing.setup;
  let remaining = timing.lineQty;
  let rendered = 0;
  const maxSegments = 420;
  for (let batch = 0; batch < timing.batches && rendered < maxSegments; batch += 1) {
    const batchQty = Math.min(timing.batchSize, remaining);
    const cycleDuration = batchQty * cycleHours;
    push("cycle", "Cycle", cursor, cycleDuration);
    rendered += 1;
    cursor += cycleDuration;
    remaining -= batchQty;
    if (batch < timing.batches - 1) {
      push("reset", "Reset", cursor, resetHours);
      rendered += 1;
      cursor += resetHours;
      push("batch-idle", "Between-batch idle", cursor, idleHours);
      rendered += 1;
      cursor += idleHours;
    }
  }
  if (rendered >= maxSegments) {
    return [
      { kind: "setup", label: "Setup", left: start, duration: timing.setup },
      { kind: resetHours || idleHours ? "production-mix" : "cycle", label: resetHours || idleHours ? "Cycle + batch breaks" : "Cycle", left: start + timing.setup, duration: timing.cycle + timing.reset + timing.batchIdle },
    ];
  }
  return segments;
}

export function markRows(rows, prefix, source) {
  return (rows || []).map((row, index) => {
    const normalized = { ...row, _id: row._id || prefix + index, _source: row._source || source };
    if (prefix === "mat") {
      if (normalized.ucmBackflush === undefined || normalized.ucmBackflush === null) normalized.ucmBackflush = true;
      const hasBucketCosts = costBuckets.some((bucket) => toNumber(normalized[bucket.materialRaw]) > 0);
      if (!hasBucketCosts && normalized.ucmRawCost !== undefined) normalized.ucmMaterialsRawCost = toNumber(normalized.ucmRawCost);
    }
    if (prefix === "op") {
      const qty = numberOr(normalized.ucoCostQuantity, 1) * numberOr(normalized.ucoQuantityPerAssembly, 1);
      if (normalized.ucoExternalUnitCost === undefined) normalized.ucoExternalUnitCost = qty ? toNumber(normalized.ucoExternalCost) / qty : toNumber(normalized.ucoLastPOCost);
      if (normalized.ucoUseAfterHoursIdle === undefined) normalized.ucoUseAfterHoursIdle = false;
      if (normalized.ucoStartTime === undefined) normalized.ucoStartTime = "";
      if (normalized.ucoAfterHoursIdleTimeHours === undefined) normalized.ucoAfterHoursIdleTimeHours = 0;
    }
    return normalized;
  });
}
export function activeMarkupBreak(markupBreaks, quantity) { const sorted = [...(markupBreaks || defaultMarkupBreaks)].sort((a, b) => toNumber(a.breakQty) - toNumber(b.breakQty)); return sorted.reduce((chosen, row) => toNumber(quantity) >= toNumber(row.breakQty) ? row : chosen, sorted[0] || {}); }
export function normalizeMarkupBreaks(rows) { const source = rows?.length ? rows : defaultMarkupBreaks; return source.map((row) => ({ breakQty: toNumber(row.breakQty) || 1, material: numberOr(row.material, 1), labor: numberOr(row.labor, 1), machine: numberOr(row.machine, 1), external: numberOr(row.external, 1), additional: numberOr(row.additional, 1) })).sort((a, b) => a.breakQty - b.breakQty); }
export function normalizeOptionalMarkupBreaks(rows) { return rows?.length ? normalizeMarkupBreaks(rows) : []; }
export function markupSettingsFromPayload(settings = {}) { const globalMarkupBreaks = normalizeMarkupBreaks(settings.global_markup_breaks || settings.markup_breaks || []), partMarkupBreaks = normalizeOptionalMarkupBreaks(settings.part_markup_breaks || []), markupBreakScope = settings.markup_break_scope === "part" && partMarkupBreaks.length ? "part" : "global", markupBreaks = markupBreakScope === "part" ? partMarkupBreaks : globalMarkupBreaks; return { markupBreaks, globalMarkupBreaks, partMarkupBreaks, markupBreakScope }; }
export function purchasedQuantity(required, increment, isPurchased) { const step = isPurchased ? toNumber(increment) : 0; return step > 0 && required > 0 ? Math.ceil(required / step) * step : required; }
export function materialUnitBreakdown(row) {
  if (row.ucmIsPurchased || row.ucmCostSource === "purchase_order") {
    return { ucmMaterialsRawCost: toNumber(row.ucmUnitCost), ucmMachineTimeRawCost: 0, ucmLaborRawCost: 0, ucmExternalOperationsRawCost: 0, ucmAdditionalRawCost: 0 };
  }
  const previousRequired = toNumber(row.ucmTotalQuantityRequired) || (toNumber(row.ucmQtyPerAssembly) * (toNumber(row.ucmCostQuantity) || 1));
  const previousBuy = purchasedQuantity(previousRequired, row.ucmMinimumPurchaseQty, row.ucmIsPurchased) || 1;
  const values = costBuckets.reduce((out, bucket) => ({ ...out, [bucket.materialRaw]: toNumber(row[bucket.materialRaw]) }), {});
  if (Object.values(values).some((value) => value > 0)) return Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value / previousBuy]));
  values.ucmMaterialsRawCost = toNumber(row.ucmUnitCost);
  return values;
}
export function partUnitBreakdown(part) {
  const quantity = toNumber(part?.ucpCostQuantity) || 1;
  const values = costBuckets.reduce((out, bucket) => ({ ...out, [bucket.materialRaw]: toNumber(part?.[bucket.partRaw]) / quantity }), {});
  if (!Object.values(values).some((value) => value > 0)) values.ucmMaterialsRawCost = toNumber(part?.ucpUnitRawCost);
  return values;
}
export function lineBreakdownFromUnit(row, unitBreakdown) {
  const required = toNumber(row.ucmQtyPerAssembly) * (toNumber(row.ucmCostQuantity) || 1);
  const buy = purchasedQuantity(required, row.ucmMinimumPurchaseQty, row.ucmIsPurchased);
  return costBuckets.reduce((out, bucket) => ({ ...out, [bucket.materialRaw]: buy * toNumber(unitBreakdown[bucket.materialRaw]) }), {});
}
export function recalcMaterials(rows, quantity, markupBreaks) {
  const activeBreak = activeMarkupBreak(markupBreaks, quantity);
  return markRows(rows, "mat", "erp").map((row) => {
    const required = toNumber(row.ucmQtyPerAssembly) * quantity;
    const buy = purchasedQuantity(required, row.ucmMinimumPurchaseQty, row.ucmIsPurchased);
    const isBackflushed = row.ucmBackflush !== false && row.ucmBackflush !== 0;
    if (!isBackflushed) return { ...row, ucmCostQuantity: quantity, ucmTotalQuantityRequired: required, ucmWasteQuantity: 0, ucmRawCost: 0, ucmMarkedUpCost: 0, ucmMaterialsRawCost: 0, ucmMaterialsMarkedUpCost: 0, ucmMachineTimeRawCost: 0, ucmMachineTimeMarkedUpCost: 0, ucmLaborRawCost: 0, ucmLaborMarkedUpCost: 0, ucmExternalOperationsRawCost: 0, ucmExternalOperationsMarkedUpCost: 0, ucmAdditionalRawCost: 0, ucmAdditionalMarkedUpCost: 0 };
    const unitBreakdown = materialUnitBreakdown(row);
    const next = { ...row, ucmCostQuantity: quantity, ucmTotalQuantityRequired: required, ucmWasteQuantity: Math.max(buy - required, 0) };
    let raw = 0, marked = 0;
    costBuckets.forEach((bucket) => {
      const bucketRaw = buy * toNumber(unitBreakdown[bucket.materialRaw]);
      const fallbackMarkup = bucket.markup === "material" ? row.ucmMaterialMarkup : activeBreak[bucket.markup];
      const markup = numberOr(fallbackMarkup, 1);
      next[bucket.materialRaw] = bucketRaw;
      next[bucket.materialMarked] = bucketRaw * markup;
      raw += next[bucket.materialRaw];
      marked += next[bucket.materialMarked];
    });
    return { ...next, ucmRawCost: raw, ucmMarkedUpCost: marked };
  });
}
export function afterHoursIdleHours(startTime, occupiedHours, shift = defaultShiftSettings) { const occupied = toNumber(occupiedHours); if (occupied <= 0) return 0; const shiftStart = parseTimeHours(shift.firstShiftStart, 6), shiftEndRaw = parseTimeHours(shift.firstShiftEnd, 14.5); let shiftLength = shiftEndRaw - shiftStart; if (shiftLength <= 0) shiftLength += 24; let start = parseTimeHours(startTime, shiftStart); while (start < shiftStart) start += 24; while (start >= shiftStart + 24) start -= 24; const end = start + occupied, day = Math.floor((end - shiftStart) / 24), currentStart = shiftStart + day * 24, currentEnd = currentStart + shiftLength; if (currentStart <= end && end <= currentEnd) return 0; return end < currentStart ? currentStart - end : currentStart + 24 - end; }
export function recalcOperations(rows, quantity, markupBreaks, shift = defaultShiftSettings) {
  return markRows(rows, "op", "erp").map((base) => {
    const row = base;
    const lineQty = quantity * numberOr(row.ucoQuantityPerAssembly, 1), batchSize = toNumber(row.ucoBatchSize) || 1, batches = lineQty > 0 ? Math.ceil(lineQty / batchSize) : 0, resets = Math.max(batches - 1, 0);
    const occupied = toNumber(row.ucoSetupTimeHours) + lineQty * toNumber(row.ucoCycleTimeHours) + resets * (toNumber(row.ucoBatchResetTimeHours) + toNumber(row.ucoBatchIdleTimeHours));
    const idle = row.ucoUseAfterHoursIdle ? afterHoursIdleHours(row.ucoStartTime, occupied, shift) : 0;
    const additionalRaw = lineQty * toNumber(row.ucoAdditionalCostPerPart);
    const laborRaw = toNumber(row.ucoSetupLaborRate) * toNumber(row.ucoSetupTimeHours) + toNumber(row.ucoBatchResetLaborRate) * resets * toNumber(row.ucoBatchResetTimeHours);
    const machineRaw = occupied * toNumber(row.ucoMachineOccupiedHourlyCost) + idle * toNumber(row.ucoMachineOccupiedHourlyCost) * (toNumber(shift.afterHoursIdleMultiplier) || 0) + lineQty * toNumber(row.ucoCycleTimeHours) * toNumber(row.ucoMachineRunningHourlyCost);
    const externalRaw = lineQty * toNumber(row.ucoExternalUnitCost), external = Boolean(row.ucoExternalJob), effectiveLabor = external ? 0 : laborRaw, effectiveMachine = external ? 0 : machineRaw, effectiveIdle = external ? 0 : idle;
    const additionalMarked = additionalRaw * numberOr(row.ucoAdditionalCostMarkup, 1), laborMarked = effectiveLabor * numberOr(row.ucoLaborMarkup, 1), machineMarked = effectiveMachine * numberOr(row.ucoMachineCostMarkup, 1), externalMarked = externalRaw * numberOr(row.ucoExternalOperationMarkup, 1);
    return { ...row, ucoCostQuantity: quantity, ucoBatchTimeHours: lineQty * toNumber(row.ucoCycleTimeHours), ucoAfterHoursIdleTimeHours: effectiveIdle, ucoExternalCost: externalRaw, ucoAdditionalCostRawCost: additionalRaw, ucoAdditionalCostMarkedUpCost: additionalMarked, ucoLaborRawCost: effectiveLabor, ucoLaborMarkedUpCost: laborMarked, ucoMachineRawCost: effectiveMachine, ucoMachineMarkedUpCost: machineMarked, ucoExternalOperationRawCost: externalRaw, ucoExternalOperationMarkedUpCost: externalMarked, ucoLineRawCost: additionalRaw + effectiveLabor + effectiveMachine + externalRaw, ucoLineMarkedUpCost: additionalMarked + laborMarked + machineMarked + externalMarked };
  });
}
export function recalcRun(run, markupBreaks = defaultMarkupBreaks, shift = defaultShiftSettings) { if (!run) return run; const quantity = toNumber(run.part_cost?.ucpCostQuantity) || 1; const materialLines = recalcMaterials(run.material_lines || [], quantity, markupBreaks), operationLines = recalcOperations(run.operation_lines || [], quantity, markupBreaks, shift); const sum = (rows, key) => rows.reduce((total, row) => total + toNumber(row[key]), 0); const bucketTotal = (bucket, kind) => sum(materialLines, bucket["material" + kind]) + (bucket["operation" + kind] ? sum(operationLines, bucket["operation" + kind]) : 0); const materialsRaw = bucketTotal(costBuckets[0], "Raw"), materialsMarked = bucketTotal(costBuckets[0], "Marked"), machineRaw = bucketTotal(costBuckets[1], "Raw"), machineMarked = bucketTotal(costBuckets[1], "Marked"), laborRaw = bucketTotal(costBuckets[2], "Raw"), laborMarked = bucketTotal(costBuckets[2], "Marked"), externalRaw = bucketTotal(costBuckets[3], "Raw"), externalMarked = bucketTotal(costBuckets[3], "Marked"), additionalRaw = bucketTotal(costBuckets[4], "Raw"), additionalMarked = bucketTotal(costBuckets[4], "Marked"); const totalRaw = materialsRaw + machineRaw + laborRaw + externalRaw + additionalRaw, totalMarked = materialsMarked + machineMarked + laborMarked + externalMarked + additionalMarked; return { ...run, material_lines: materialLines, operation_lines: operationLines, part_cost: { ...partDefaults, ...run.part_cost, ucpCostQuantity: quantity, ucpMaterialsRawCost: materialsRaw, ucpMaterialsMarkedUpCost: materialsMarked, ucpMachineTimeRawCost: machineRaw, ucpMachineTimeMarkedUpCost: machineMarked, ucpLaborRawCost: laborRaw, ucpLaborMarkedUpCost: laborMarked, ucpExternalOperationsRawCost: externalRaw, ucpExternalOperationsMarkedUpCost: externalMarked, ucpAdditionalRawCost: additionalRaw, ucpAdditionalMarkedUpCost: additionalMarked, ucpTotalRawCost: totalRaw, ucpTotalMarkedUpCost: totalMarked, ucpUnitRawCost: totalRaw / quantity, ucpUnitMarkedUpCost: totalMarked / quantity } }; }
export function newMaterial(quantity) { return { _id: uid("mat"), _source: "manual", ucmMaterialID: "", ucmMaterialDescription: "", ucmQtyPerAssembly: 1, ucmBackflush: true, ucmIsPurchased: false, ucmCostSource: "manual", ucmLastPO: "", ucmLastPOCost: null, ucmLastPODate: null, ucmRetailUnitPrice: null, ucmUnitCost: 0, ucmPurchaseUnitCost: 0, ucmMaterialPriceMode: "purchase", ucmMinimumPurchaseQty: 1, ucmMaterialMarkup: 1, ucmTotalQuantityRequired: quantity || 1, ucmWasteQuantity: 0, ucmMaterialsRawCost: 0, ucmMaterialsMarkedUpCost: 0, ucmMachineTimeRawCost: 0, ucmMachineTimeMarkedUpCost: 0, ucmLaborRawCost: 0, ucmLaborMarkedUpCost: 0, ucmExternalOperationsRawCost: 0, ucmExternalOperationsMarkedUpCost: 0, ucmAdditionalRawCost: 0, ucmAdditionalMarkedUpCost: 0, ucmRawCost: 0, ucmMarkedUpCost: 0 }; }
export function newOperation(quantity, sequence = "") { return { _id: uid("op"), _source: "manual", ucoPartOperationLineID: sequence, ucoCostQuantity: quantity || 1, ucoQuantityPerAssembly: 1, ucoWorkCenterID: "", ucoOperationID: "", ucoOperationDescription: "", ucoSetupTimeHours: 0, ucoCycleTimeHours: 0, ucoBatchSize: 1, ucoBatchTimeHours: 0, ucoAutomated: false, ucoMachineRunningHourlyCost: 0, ucoMachineOccupiedHourlyCost: 0, ucoMachineCostMarkup: 1, ucoSetupLaborRate: 0, ucoBatchResetTimeHours: 0, ucoBatchIdleTimeHours: 0, ucoUseAfterHoursIdle: false, ucoStartTime: "", ucoBatchResetLaborRate: 0, ucoLaborMarkup: 1, ucoExternalJob: false, ucoLastPO: "", ucoLastPOCost: null, ucoLastPODate: null, ucoExternalUnitCost: 0, ucoExternalOperationMarkup: 1, ucoAdditionalCostPerPart: 0, ucoAdditionalCostMarkup: 1, ucoLineRawCost: 0, ucoLineMarkedUpCost: 0 }; }
export function nextOperationSequence(rows) { const maxSequence = (rows || []).reduce((max, row) => Math.max(max, toNumber(row.ucoPartOperationLineID)), 0); return Math.ceil(maxSequence / 10) * 10 + 10; }
export function buildMachineDefaults(lines) { return (lines || []).reduce((out, row) => { const key = machineKey(row); if (!out[key]) out[key] = {}; machineDefaultFields.forEach(([field]) => { if (out[key][field] === undefined) out[key][field] = toNumber(row[field]); }); return out; }, {}); }
export function buildGlobalMachineDefaults(settings) { if (!settings) return defaultGlobalMachineDefaults; return { ucoSetupLaborRate: toNumber(settings.ucgDefaultLaborHourlyCost), ucoBatchResetLaborRate: toNumber(settings.ucgDefaultLaborHourlyCost), ucoMachineRunningHourlyCost: toNumber(settings.ucgDefaultMachineRunningHourlyCost), ucoMachineOccupiedHourlyCost: toNumber(settings.ucgDefaultMachineOccupiedHourlyCost), ucoBatchResetTimeHours: toNumber(settings.ucgDefaultBatchResetTimeHours), ucoBatchIdleTimeHours: toNumber(settings.ucgDefaultBatchIdleTimeHours) }; }
export function buildSettingsMachineDefaults(settingsRows, lines) { const fromLines = buildMachineDefaults(lines); const fromSettings = (settingsRows || []).reduce((out, row) => ({ ...out, [row.ucmWorkCenterID || "Unassigned"]: { ucoSetupLaborRate: toNumber(row.ucmDefaultLaborHourlyCost), ucoBatchResetLaborRate: toNumber(row.ucmDefaultLaborHourlyCost), ucoMachineRunningHourlyCost: toNumber(row.ucmDefaultMachineRunningHourlyCost), ucoMachineOccupiedHourlyCost: toNumber(row.ucmDefaultMachineOccupiedHourlyCost), ucoBatchResetTimeHours: toNumber(row.ucmDefaultBatchResetTimeHours), ucoBatchIdleTimeHours: toNumber(row.ucmDefaultBatchIdleTimeHours) } }), {}); return { ...fromLines, ...fromSettings }; }
export function buildShiftSettings(settings) { return settings ? { firstShiftStart: settings.ucgDefaultFirstShiftStart || defaultShiftSettings.firstShiftStart, firstShiftEnd: settings.ucgDefaultFirstShiftEnd || defaultShiftSettings.firstShiftEnd, afterHoursIdleMultiplier: numberOr(settings.ucgDefaultAfterHoursIdleRateMultiplier, 1) } : defaultShiftSettings; }
export function lineCostQuantity(row) { return toNumber(row.ucmCostQuantity ?? row.ucoCostQuantity) || 1; }
export function lineRawUnitCost(row) { return toNumber(row.ucmRawCost ?? row.ucoLineRawCost) / lineCostQuantity(row); }
export function lineMarkedUnitCost(row) { return toNumber(row.ucmMarkedUpCost ?? row.ucoLineMarkedUpCost) / lineCostQuantity(row); }
export function materialDefaultsToRow(row, part, defaults) {
  const source = defaults?.source || "erp_estimate";
  const description = part.impShortDescription || part.impPartShortDescription || defaults?.part?.impShortDescription || defaults?.part?.impPartShortDescription || row.ucmMaterialDescription;
  const replacement = {
    ...row,
    ucmMaterialID: part.impPartID,
    ucmMaterialDescription: description,
    ucmCostSource: source,
    ucmIsPurchased: source === "purchase_order",
    ucmUnitCost: toNumber(defaults?.unit_cost) || 0,
    ucmPurchaseUnitCost: defaults?.last_po_purchase_unit_cost ?? (toNumber(defaults?.unit_cost) / (toNumber(defaults?.last_po_conversion_factor) || 1)) ?? 0,
    ucmMaterialPriceMode: defaults?.last_po_purchase_unit_cost ? "purchase" : "inventory",
    ucmMinimumPurchaseQty: defaults?.minimum_purchase_qty ?? (source === "purchase_order" ? 1 : 0),
    ucmLastPO: defaults?.last_po || "",
    ucmLastPOCost: defaults?.last_po_cost ?? null,
    ucmLastPODate: defaults?.last_po_date ?? null,
    ucmRetailUnitPrice: defaults?.retail_unit_price ?? row.ucmRetailUnitPrice ?? null,
    ucmLastPOPurchaseUnitCost: defaults?.last_po_purchase_unit_cost ?? row.ucmLastPOPurchaseUnitCost,
    ucmLastPOConversionFactor: defaults?.last_po_conversion_factor ?? row.ucmLastPOConversionFactor,
    ucmLastPOPurchaseUnit: defaults?.last_po_purchase_unit ?? row.ucmLastPOPurchaseUnit,
    ucmLastPOInventoryUnit: defaults?.last_po_inventory_unit ?? row.ucmLastPOInventoryUnit,
    ucmHasManufacturingDetail: defaults?.has_manufacturing_detail ?? row.ucmHasManufacturingDetail,
    ucmManufacturingMaterialCount: defaults?.manufacturing_material_count ?? row.ucmManufacturingMaterialCount,
    ucmManufacturingOperationCount: defaults?.manufacturing_operation_count ?? row.ucmManufacturingOperationCount,
    ucmMaterialMarkup: defaults?.material_markup ?? row.ucmMaterialMarkup,
    ucmManufacturedPartCostID: defaults?.manufactured_part_cost_id ?? row.ucmManufacturedPartCostID,
    ucmManufacturedPartCostIsCurrent: defaults?.manufactured_part_cost_is_current ?? row.ucmManufacturedPartCostIsCurrent,
  };
  const hasSplit = ["materials", "machine", "labor", "external", "additional"].some((key) => toNumber(defaults?.[key + "_raw_unit_cost"]) > 0);
  if (!hasSplit) return replacement;
  return {
    ...replacement,
    ...lineBreakdownFromUnit(replacement, {
      ucmMaterialsRawCost: defaults.materials_raw_unit_cost,
      ucmMachineTimeRawCost: defaults.machine_raw_unit_cost,
      ucmLaborRawCost: defaults.labor_raw_unit_cost,
      ucmExternalOperationsRawCost: defaults.external_raw_unit_cost,
      ucmAdditionalRawCost: defaults.additional_raw_unit_cost,
    }),
  };
}
export function groupedFields(kind, row) {
  if (kind === "material") {
    return [
      { title: "Identity", note: "What material is being used.", fields: ["ucmMaterialDescription", "ucmBackflush", "ucmIsPurchased"] },
      { title: "Quantity", note: "These drive how much is consumed, bought, and wasted.", fields: ["ucmQtyPerAssembly", "ucmMinimumPurchaseQty"] },
      { title: "Unit cost", note: "ERP, PO, retail, or manufactured-history cost assumptions.", fields: ["ucmUnitCost", "ucmRetailUnitPrice", "ucmMaterialMarkup", "ucmLastPO", "ucmLastPOCost", "ucmLastPODate"] },
    ];
  }
  const purchase = row.ucoExternalJob;
  return [
    { title: "Identity", note: "What step this is and where it runs.", fields: ["ucoPartOperationLineID", "ucoWorkCenterID", "ucoOperationDescription", "ucoQuantityPerAssembly", "ucoExternalJob"] },
    purchase
      ? { title: "Outside service", note: "Only external unit cost and related adders affect this operation.", fields: ["ucoExternalUnitCost", "ucoExternalOperationMarkup", "ucoAdditionalCostPerPart", "ucoAdditionalCostMarkup", "ucoLastPO", "ucoLastPOCost", "ucoLastPODate"] }
      : { title: "Runtime", note: "Changing these often means checking batch size, reset time, and the schedule preview together.", fields: ["ucoSetupTimeHours", "ucoBatchSize", "ucoCycleTimeHours", "ucoBatchResetTimeHours", "ucoBatchIdleTimeHours", "ucoUseAfterHoursIdle"] },
    purchase ? null : { title: "Rates and markup", note: "Right click default-backed machine fields to update that machine default.", fields: ["ucoSetupLaborRate", "ucoBatchResetLaborRate", "ucoLaborMarkup", "ucoMachineRunningHourlyCost", "ucoMachineOccupiedHourlyCost", "ucoMachineCostMarkup", "ucoAdditionalCostPerPart", "ucoAdditionalCostMarkup"] },
  ].filter(Boolean);
}

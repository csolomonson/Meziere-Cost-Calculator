const { useEffect, useMemo, useRef, useState } = React;

const moneyFields = new Set([
  "ucpMaterialsRawCost", "ucpMaterialsMarkedUpCost", "ucpMachineTimeRawCost", "ucpMachineTimeMarkedUpCost",
  "ucpLaborRawCost", "ucpLaborMarkedUpCost", "ucpExternalOperationsRawCost", "ucpExternalOperationsMarkedUpCost",
  "ucpAdditionalRawCost", "ucpAdditionalMarkedUpCost", "ucpTotalRawCost", "ucpTotalMarkedUpCost",
  "ucpUnitRawCost", "ucpUnitMarkedUpCost", "ucmUnitCost", "ucmLastPOCost", "ucmRawCost", "ucmMarkedUpCost",
  "ucoSetupLaborRate", "ucoBatchResetLaborRate", "ucoMachineRunningHourlyCost", "ucoMachineOccupiedHourlyCost",
  "ucoExternalCost", "ucoExternalUnitCost", "ucoLastPOCost", "ucoAdditionalCostPerPart", "ucoMachineRawCost",
  "ucoMachineMarkedUpCost", "ucoLaborRawCost", "ucoLaborMarkedUpCost", "ucoExternalOperationRawCost",
  "ucoExternalOperationMarkedUpCost", "ucoAdditionalCostRawCost", "ucoAdditionalCostMarkedUpCost", "ucoLineRawCost", "ucoLineMarkedUpCost",
]);
const numericFields = new Set(["quantity", "ucpCostQuantity", "ucmQtyPerAssembly", "ucmTotalQuantityRequired", "ucmUnitCost", "ucmMinimumPurchaseQty", "ucmMaterialMarkup", "ucoQuantityPerAssembly", "ucoSetupTimeHours", "ucoCycleTimeHours", "ucoBatchSize", "ucoBatchResetTimeHours", "ucoBatchIdleTimeHours", "ucoSetupLaborRate", "ucoBatchResetLaborRate", "ucoLaborMarkup", "ucoMachineRunningHourlyCost", "ucoMachineOccupiedHourlyCost", "ucoMachineCostMarkup", "ucoExternalUnitCost", "ucoExternalOperationMarkup", "ucoAdditionalCostPerPart", "ucoAdditionalCostMarkup", "ucoAfterHoursIdleRateMultiplier", "afterHoursIdleMultiplier"]);
const durationFields = new Set(["ucoSetupTimeHours", "ucoCycleTimeHours", "ucoBatchResetTimeHours", "ucoBatchIdleTimeHours"]);
const partDefaults = { ucpPartCostID: null, ucpPartID: "", ucpPartRevision: "", ucpPartDescription: "", ucpCostQuantity: 10000, ucpMaterialsRawCost: 0, ucpMaterialsMarkedUpCost: 0, ucpMachineTimeRawCost: 0, ucpMachineTimeMarkedUpCost: 0, ucpLaborRawCost: 0, ucpLaborMarkedUpCost: 0, ucpExternalOperationsRawCost: 0, ucpExternalOperationsMarkedUpCost: 0, ucpAdditionalRawCost: 0, ucpAdditionalMarkedUpCost: 0, ucpTotalRawCost: 0, ucpTotalMarkedUpCost: 0, ucpUnitRawCost: 0, ucpUnitMarkedUpCost: 0, ucpIsCurrent: false };
const defaultMarkupBreaks = [1, 10, 100, 1000, 10000].map((breakQty) => ({ breakQty, material: 1.25, labor: 1.15, machine: 1.15, external: 1.25, additional: 1.15 }));
const defaultShiftSettings = { firstShiftStart: "06:00", firstShiftEnd: "14:30", afterHoursIdleMultiplier: 1 };
const materialFields = [["ucmMaterialID", "Material part number"], ["ucmMaterialDescription", "Material description"], ["ucmQtyPerAssembly", "Quantity used per finished part"], ["ucmUnitCost", "Unit material cost"], ["ucmMinimumPurchaseQty", "Purchase quantity increment"], ["ucmMaterialMarkup", "Material markup multiplier"], ["ucmLastPO", "Last purchase order"], ["ucmLastPOCost", "Last PO unit cost"], ["ucmLastPODate", "Last PO date"]];
const opCommonFields = [["ucoPartOperationLineID", "Operation sequence"], ["ucoWorkCenterID", "Machine / work center"], ["ucoOperationID", "Process code"], ["ucoOperationDescription", "Operation description"], ["ucoQuantityPerAssembly", "Operation quantity per finished part"], ["ucoExternalJob", "Purchased outside operation", "checkbox"]];
const opInternalFields = [["ucoSetupTimeHours", "Setup time"], ["ucoSetupLaborRate", "Setup labor hourly rate"], ["ucoBatchSize", "Parts per unattended batch"], ["ucoCycleTimeHours", "Cycle time per part"], ["ucoBatchResetTimeHours", "Reset time between batches"], ["ucoBatchIdleTimeHours", "Idle time between batches"], ["ucoUseAfterHoursIdle", "Cost after-hours idle time", "checkbox"], ["ucoBatchResetLaborRate", "Tending labor hourly rate"], ["ucoLaborMarkup", "Labor markup multiplier"], ["ucoMachineRunningHourlyCost", "Machine active hourly cost"], ["ucoMachineOccupiedHourlyCost", "Machine occupied idle hourly cost"], ["ucoMachineCostMarkup", "Machine markup multiplier"], ["ucoAdditionalCostPerPart", "Additional cost per finished part"], ["ucoAdditionalCostMarkup", "Additional cost markup multiplier"]];
const opExternalFields = [["ucoExternalUnitCost", "Outside service unit cost"], ["ucoExternalOperationMarkup", "Outside service markup multiplier"], ["ucoAdditionalCostPerPart", "Additional cost per finished part"], ["ucoAdditionalCostMarkup", "Additional cost markup multiplier"], ["ucoLastPO", "Last purchase order"], ["ucoLastPOCost", "Last PO unit cost"], ["ucoLastPODate", "Last PO date"]];
const machineDefaultFields = [["ucoSetupLaborRate", "Setup labor rate"], ["ucoBatchResetLaborRate", "Tending labor rate"], ["ucoMachineRunningHourlyCost", "Active machine rate"], ["ucoMachineOccupiedHourlyCost", "Occupied idle rate"], ["ucoBatchResetTimeHours", "Default reset time"], ["ucoBatchIdleTimeHours", "Default idle time"]];
const markupDefaults = [["material", "Material", "ucmMaterialMarkup"], ["labor", "Labor", "ucoLaborMarkup"], ["machine", "Machine", "ucoMachineCostMarkup"], ["external", "External", "ucoExternalOperationMarkup"], ["additional", "Additional", "ucoAdditionalCostMarkup"]];
const machineDefaultKeys = new Set(machineDefaultFields.map(([field]) => field));
const markupKeys = new Set(markupDefaults.map(([, , field]) => field));
const defaultGlobalMachineDefaults = { ucoSetupLaborRate: 0, ucoBatchResetLaborRate: 0, ucoMachineRunningHourlyCost: 0, ucoMachineOccupiedHourlyCost: 0, ucoBatchResetTimeHours: 0, ucoBatchIdleTimeHours: 0 };

function uid(prefix) { return prefix + Math.random().toString(36).slice(2, 9); }
function toNumber(value) { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : 0; }
function keyFor(row, field) { return row._id + "." + field; }
async function readApiResponse(response) { const text = await response.text(); let payload = {}; if (text) { try { payload = JSON.parse(text); } catch { payload = { detail: text }; } } if (!response.ok) { const detail = payload?.detail; throw new Error(typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : response.statusText || "Request failed"); } return payload; }
function formatValue(key, value) { if (value === null || value === undefined || value === "") return "-"; if (key === "ucoExternalJob") return value ? "External" : "Internal"; if (moneyFields.has(key) && typeof value === "number") return value.toLocaleString(undefined, { style: "currency", currency: "USD" }); if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 5 }); if (typeof value === "boolean") return value ? "Yes" : "No"; return String(value); }
function parseTimeHours(value, fallback) { const text = String(value ?? "").trim(); if (!text) return fallback; if (text.includes(":")) { const [h, m] = text.split(":"); return toNumber(h) + toNumber((m || "0").slice(0, 2)) / 60; } const parsed = Number(text); return Number.isFinite(parsed) ? parsed : fallback; }
function hoursToClock(hours) { const normalized = ((hours % 24) + 24) % 24; const h = Math.floor(normalized); const minutes = Math.round((normalized - h) * 60); return String((h + Math.floor(minutes / 60)) % 24).padStart(2, "0") + ":" + String(minutes % 60).padStart(2, "0"); }
function parseDurationInput(value) { const text = String(value ?? "").trim().toLowerCase(); if (!text) return 0; const colon = text.match(/^(\d+(?:\.\d+)?)(?::(\d+(?:\.\d+)?))?(?::(\d+(?:\.\d+)?))?$/); if (colon && text.includes(":")) return toNumber(colon[1]) + toNumber(colon[2]) / 60 + toNumber(colon[3]) / 3600; let total = 0, matched = false; const units = /(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|m|min|mins|minute|minutes|s|sec|secs|second|seconds)/g; let match; while ((match = units.exec(text))) { matched = true; const unit = match[2][0]; total += unit === "h" ? toNumber(match[1]) : unit === "m" ? toNumber(match[1]) / 60 : toNumber(match[1]) / 3600; } if (matched) return total; const parsed = Number(text); return Number.isFinite(parsed) ? parsed : null; }
function formatDurationInput(hours) { const total = Math.round(toNumber(hours) * 3600); if (!total) return "0m"; const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), s = total % 60; return [[h, "h"], [m, "m"], [s, "s"]].filter(([n]) => n).map(([n, u]) => n + u).join(" "); }
function durationParts(hours) { const total = Math.max(0, Math.round(toNumber(hours) * 3600)); return { h: Math.floor(total / 3600), m: Math.floor((total % 3600) / 60), s: total % 60 }; }
function formatDuration(hours) { const value = toNumber(hours); if (value < 1) return Math.round(value * 60) + " min"; if (value < 24) return value.toFixed(value >= 10 ? 1 : 2).replace(/\.0+$/, "") + " hr"; const days = Math.floor(value / 24); const rest = value - days * 24; return days + " day" + (days === 1 ? "" : "s") + (rest > 0.05 ? " " + formatDuration(rest) : ""); }
function valuesEquivalent(field, value, originalValue) { if ((value === null || value === undefined || value === "") && (originalValue === null || originalValue === undefined || originalValue === "")) return true; if (durationFields.has(field)) return Math.abs(toNumber(value) - toNumber(originalValue)) < (1 / 3600); if (numericFields.has(field)) return Math.abs(toNumber(value) - toNumber(originalValue)) < 0.0000001; if (typeof value === "boolean" || typeof originalValue === "boolean") return Boolean(value) === Boolean(originalValue); return String(value ?? "") === String(originalValue ?? ""); }
function setEditedForValue(current, key, field, value, originalValue) { const next = new Set(current); if (valuesEquivalent(field, value, originalValue)) next.delete(key); else next.add(key); return next; }
function setEditedForFields(current, id, row, originalRow, fields) { return fields.reduce((next, field) => setEditedForValue(next, id + "." + field, field, row?.[field], originalRow?.[field]), new Set(current)); }
function machineKey(row) { return row?.ucoWorkCenterID || "Unassigned"; }
function materialSource(row) { if (row?.ucmCostSource === "manufactured_current") return { label: "Manufactured current", tone: "green" }; if (row?.ucmCostSource === "manufactured_history") return { label: "Manufactured history", tone: "green" }; if (row?.ucmCostSource === "manufactured_route") return { label: "Manufactured route", tone: "blue" }; if (row?.ucmIsPurchased || row?.ucmCostSource === "purchase_order") return { label: "Purchased", tone: "amber" }; return { label: "Manufactured/internal", tone: "blue" }; }
function pct(start, duration, day) { const left = Math.max(0, Math.min(24, start - day * 24)); const right = Math.max(0, Math.min(24, start + duration - day * 24)); return { left: left / 24 * 100, width: Math.max(0, (right - left) / 24 * 100) }; }
function operationTiming(row) {
  const lineQty = toNumber(row.ucoCostQuantity) * (toNumber(row.ucoQuantityPerAssembly) || 1);
  const batchSize = toNumber(row.ucoBatchSize) || 1;
  const batches = lineQty > 0 ? Math.ceil(lineQty / batchSize) : 0;
  const resets = Math.max(batches - 1, 0);
  const setup = toNumber(row.ucoSetupTimeHours);
  const cycle = lineQty * toNumber(row.ucoCycleTimeHours);
  const reset = resets * toNumber(row.ucoBatchResetTimeHours);
  const batchIdle = resets * toNumber(row.ucoBatchIdleTimeHours);
  return { lineQty, batchSize, batches, resets, setup, cycle, reset, batchIdle, runtime: setup + cycle + reset + batchIdle };
}
function calendarSegments(row, start, shownDays) {
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

function markRows(rows, prefix, source) {
  return (rows || []).map((row, index) => {
    const normalized = { ...row, _id: row._id || prefix + index, _source: row._source || source };
    if (prefix === "op") {
      const qty = toNumber(normalized.ucoCostQuantity || 1) * (toNumber(normalized.ucoQuantityPerAssembly) || 1);
      if (normalized.ucoExternalUnitCost === undefined) normalized.ucoExternalUnitCost = qty ? toNumber(normalized.ucoExternalCost) / qty : toNumber(normalized.ucoLastPOCost);
      if (normalized.ucoUseAfterHoursIdle === undefined) normalized.ucoUseAfterHoursIdle = false;
      if (normalized.ucoStartTime === undefined) normalized.ucoStartTime = "";
      if (normalized.ucoAfterHoursIdleTimeHours === undefined) normalized.ucoAfterHoursIdleTimeHours = 0;
    }
    return normalized;
  });
}
function activeMarkupBreak(markupBreaks, quantity) { const sorted = [...(markupBreaks || defaultMarkupBreaks)].sort((a, b) => toNumber(a.breakQty) - toNumber(b.breakQty)); return sorted.reduce((chosen, row) => toNumber(quantity) >= toNumber(row.breakQty) ? row : chosen, sorted[0] || {}); }
function normalizeMarkupBreaks(rows) { const source = rows?.length ? rows : defaultMarkupBreaks; return source.map((row) => ({ breakQty: toNumber(row.breakQty) || 1, material: toNumber(row.material) || 1, labor: toNumber(row.labor) || 1, machine: toNumber(row.machine) || 1, external: toNumber(row.external) || 1, additional: toNumber(row.additional) || 1 })).sort((a, b) => a.breakQty - b.breakQty); }
function purchasedQuantity(required, increment, isPurchased) { const step = isPurchased ? toNumber(increment) : 0; return step > 0 && required > 0 ? Math.ceil(required / step) * step : required; }
function recalcMaterials(rows, quantity, markupBreaks, edited) { return markRows(rows, "mat", "erp").map((row) => { const required = toNumber(row.ucmQtyPerAssembly) * quantity; const buy = purchasedQuantity(required, row.ucmMinimumPurchaseQty, row.ucmIsPurchased); const raw = buy * toNumber(row.ucmUnitCost); return { ...row, ucmCostQuantity: quantity, ucmTotalQuantityRequired: required, ucmWasteQuantity: Math.max(buy - required, 0), ucmRawCost: raw, ucmMarkedUpCost: raw * (toNumber(row.ucmMaterialMarkup) || 1) }; }); }
function afterHoursIdleHours(startTime, occupiedHours, shift = defaultShiftSettings) { const occupied = toNumber(occupiedHours); if (occupied <= 0) return 0; const shiftStart = parseTimeHours(shift.firstShiftStart, 6), shiftEndRaw = parseTimeHours(shift.firstShiftEnd, 14.5); let shiftLength = shiftEndRaw - shiftStart; if (shiftLength <= 0) shiftLength += 24; let start = parseTimeHours(startTime, shiftStart); while (start < shiftStart) start += 24; while (start >= shiftStart + 24) start -= 24; const end = start + occupied, day = Math.floor((end - shiftStart) / 24), currentStart = shiftStart + day * 24, currentEnd = currentStart + shiftLength; if (currentStart <= end && end <= currentEnd) return 0; return end < currentStart ? currentStart - end : currentStart + 24 - end; }
function recalcOperations(rows, quantity, markupBreaks, edited, shift = defaultShiftSettings) {
  return markRows(rows, "op", "erp").map((base) => {
    const row = base;
    const lineQty = quantity * (toNumber(row.ucoQuantityPerAssembly) || 1), batchSize = toNumber(row.ucoBatchSize) || 1, batches = lineQty > 0 ? Math.ceil(lineQty / batchSize) : 0, resets = Math.max(batches - 1, 0);
    const occupied = toNumber(row.ucoSetupTimeHours) + lineQty * toNumber(row.ucoCycleTimeHours) + resets * (toNumber(row.ucoBatchResetTimeHours) + toNumber(row.ucoBatchIdleTimeHours));
    const idle = row.ucoUseAfterHoursIdle ? afterHoursIdleHours(row.ucoStartTime, occupied, shift) : 0;
    const additionalRaw = lineQty * toNumber(row.ucoAdditionalCostPerPart);
    const laborRaw = toNumber(row.ucoSetupLaborRate) * toNumber(row.ucoSetupTimeHours) + toNumber(row.ucoBatchResetLaborRate) * resets * toNumber(row.ucoBatchResetTimeHours);
    const machineRaw = occupied * toNumber(row.ucoMachineOccupiedHourlyCost) + idle * toNumber(row.ucoMachineOccupiedHourlyCost) * (toNumber(shift.afterHoursIdleMultiplier) || 0) + lineQty * toNumber(row.ucoCycleTimeHours) * toNumber(row.ucoMachineRunningHourlyCost);
    const externalRaw = lineQty * toNumber(row.ucoExternalUnitCost), external = Boolean(row.ucoExternalJob), effectiveLabor = external ? 0 : laborRaw, effectiveMachine = external ? 0 : machineRaw, effectiveIdle = external ? 0 : idle;
    const additionalMarked = additionalRaw * (toNumber(row.ucoAdditionalCostMarkup) || 1), laborMarked = effectiveLabor * (toNumber(row.ucoLaborMarkup) || 1), machineMarked = effectiveMachine * (toNumber(row.ucoMachineCostMarkup) || 1), externalMarked = externalRaw * (toNumber(row.ucoExternalOperationMarkup) || 1);
    return { ...row, ucoCostQuantity: quantity, ucoBatchTimeHours: lineQty * toNumber(row.ucoCycleTimeHours), ucoAfterHoursIdleTimeHours: effectiveIdle, ucoExternalCost: externalRaw, ucoAdditionalCostRawCost: additionalRaw, ucoAdditionalCostMarkedUpCost: additionalMarked, ucoLaborRawCost: effectiveLabor, ucoLaborMarkedUpCost: laborMarked, ucoMachineRawCost: effectiveMachine, ucoMachineMarkedUpCost: machineMarked, ucoExternalOperationRawCost: externalRaw, ucoExternalOperationMarkedUpCost: externalMarked, ucoLineRawCost: additionalRaw + effectiveLabor + effectiveMachine + externalRaw, ucoLineMarkedUpCost: additionalMarked + laborMarked + machineMarked + externalMarked };
  });
}
function recalcRun(run, markupBreaks = defaultMarkupBreaks, edited = new Set(), shift = defaultShiftSettings) { if (!run) return run; const quantity = toNumber(run.part_cost?.ucpCostQuantity) || 1; const materialLines = recalcMaterials(run.material_lines || [], quantity, markupBreaks, edited), operationLines = recalcOperations(run.operation_lines || [], quantity, markupBreaks, edited, shift); const sum = (rows, key) => rows.reduce((total, row) => total + toNumber(row[key]), 0); const materialsRaw = sum(materialLines, "ucmRawCost"), materialsMarked = sum(materialLines, "ucmMarkedUpCost"), machineRaw = sum(operationLines, "ucoMachineRawCost"), machineMarked = sum(operationLines, "ucoMachineMarkedUpCost"), laborRaw = sum(operationLines, "ucoLaborRawCost"), laborMarked = sum(operationLines, "ucoLaborMarkedUpCost"), externalRaw = sum(operationLines, "ucoExternalOperationRawCost"), externalMarked = sum(operationLines, "ucoExternalOperationMarkedUpCost"), additionalRaw = sum(operationLines, "ucoAdditionalCostRawCost"), additionalMarked = sum(operationLines, "ucoAdditionalCostMarkedUpCost"); const totalRaw = materialsRaw + machineRaw + laborRaw + externalRaw + additionalRaw, totalMarked = materialsMarked + machineMarked + laborMarked + externalMarked + additionalMarked; return { ...run, material_lines: materialLines, operation_lines: operationLines, part_cost: { ...partDefaults, ...run.part_cost, ucpCostQuantity: quantity, ucpMaterialsRawCost: materialsRaw, ucpMaterialsMarkedUpCost: materialsMarked, ucpMachineTimeRawCost: machineRaw, ucpMachineTimeMarkedUpCost: machineMarked, ucpLaborRawCost: laborRaw, ucpLaborMarkedUpCost: laborMarked, ucpExternalOperationsRawCost: externalRaw, ucpExternalOperationsMarkedUpCost: externalMarked, ucpAdditionalRawCost: additionalRaw, ucpAdditionalMarkedUpCost: additionalMarked, ucpTotalRawCost: totalRaw, ucpTotalMarkedUpCost: totalMarked, ucpUnitRawCost: totalRaw / quantity, ucpUnitMarkedUpCost: totalMarked / quantity } }; }
function newMaterial(quantity) { return { _id: uid("mat"), _source: "manual", ucmMaterialID: "", ucmMaterialDescription: "", ucmQtyPerAssembly: 1, ucmIsPurchased: false, ucmCostSource: "manual", ucmLastPO: "", ucmLastPOCost: null, ucmLastPODate: null, ucmUnitCost: 0, ucmMinimumPurchaseQty: 1, ucmMaterialMarkup: 1, ucmTotalQuantityRequired: quantity || 1, ucmWasteQuantity: 0, ucmRawCost: 0, ucmMarkedUpCost: 0 }; }
function newOperation(quantity) { return { _id: uid("op"), _source: "manual", ucoPartOperationLineID: "", ucoCostQuantity: quantity || 1, ucoQuantityPerAssembly: 1, ucoWorkCenterID: "", ucoOperationID: "", ucoOperationDescription: "", ucoSetupTimeHours: 0, ucoCycleTimeHours: 0, ucoBatchSize: 1, ucoMachineRunningHourlyCost: 0, ucoMachineOccupiedHourlyCost: 0, ucoMachineCostMarkup: 1, ucoSetupLaborRate: 0, ucoBatchResetTimeHours: 0, ucoBatchIdleTimeHours: 0, ucoUseAfterHoursIdle: false, ucoStartTime: "", ucoBatchResetLaborRate: 0, ucoLaborMarkup: 1, ucoExternalJob: false, ucoLastPO: "", ucoLastPOCost: null, ucoLastPODate: null, ucoExternalUnitCost: 0, ucoExternalOperationMarkup: 1, ucoAdditionalCostPerPart: 0, ucoAdditionalCostMarkup: 1, ucoLineRawCost: 0, ucoLineMarkedUpCost: 0 }; }
function buildMachineDefaults(lines) { return (lines || []).reduce((out, row) => { const key = machineKey(row); if (!out[key]) out[key] = {}; machineDefaultFields.forEach(([field]) => { if (out[key][field] === undefined) out[key][field] = toNumber(row[field]); }); return out; }, {}); }
function buildGlobalMachineDefaults(settings) { if (!settings) return defaultGlobalMachineDefaults; return { ucoSetupLaborRate: toNumber(settings.ucgDefaultLaborHourlyCost), ucoBatchResetLaborRate: toNumber(settings.ucgDefaultLaborHourlyCost), ucoMachineRunningHourlyCost: toNumber(settings.ucgDefaultMachineRunningHourlyCost), ucoMachineOccupiedHourlyCost: toNumber(settings.ucgDefaultMachineOccupiedHourlyCost), ucoBatchResetTimeHours: toNumber(settings.ucgDefaultBatchResetTimeHours), ucoBatchIdleTimeHours: toNumber(settings.ucgDefaultBatchIdleTimeHours) }; }
function buildSettingsMachineDefaults(settingsRows, lines) { const fromLines = buildMachineDefaults(lines); const fromSettings = (settingsRows || []).reduce((out, row) => ({ ...out, [row.ucmWorkCenterID || "Unassigned"]: { ucoSetupLaborRate: toNumber(row.ucmDefaultLaborHourlyCost), ucoBatchResetLaborRate: toNumber(row.ucmDefaultLaborHourlyCost), ucoMachineRunningHourlyCost: toNumber(row.ucmDefaultMachineRunningHourlyCost), ucoMachineOccupiedHourlyCost: toNumber(row.ucmDefaultMachineOccupiedHourlyCost), ucoBatchResetTimeHours: toNumber(row.ucmDefaultBatchResetTimeHours), ucoBatchIdleTimeHours: toNumber(row.ucmDefaultBatchIdleTimeHours) } }), {}); return { ...fromLines, ...fromSettings }; }
function buildShiftSettings(settings) { return settings ? { firstShiftStart: settings.ucgDefaultFirstShiftStart || defaultShiftSettings.firstShiftStart, firstShiftEnd: settings.ucgDefaultFirstShiftEnd || defaultShiftSettings.firstShiftEnd, afterHoursIdleMultiplier: toNumber(settings.ucgDefaultAfterHoursIdleRateMultiplier) || 1 } : defaultShiftSettings; }
function lineCostQuantity(row) { return toNumber(row.ucmCostQuantity ?? row.ucoCostQuantity) || 1; }
function lineRawUnitCost(row) { return toNumber(row.ucmRawCost ?? row.ucoLineRawCost) / lineCostQuantity(row); }
function lineMarkedUnitCost(row) { return toNumber(row.ucmMarkedUpCost ?? row.ucoLineMarkedUpCost) / lineCostQuantity(row); }
function fieldLabel(field) { return [...materialFields, ...opCommonFields, ...opInternalFields, ...opExternalFields, ...machineDefaultFields].find(([key]) => key === field)?.[1] || field; }
function materialDefaultsToRow(row, part, defaults) {
  const source = defaults?.source || "erp_estimate";
  const description = part.impShortDescription || part.impPartShortDescription || defaults?.part?.impShortDescription || defaults?.part?.impPartShortDescription || row.ucmMaterialDescription;
  return {
    ...row,
    ucmMaterialID: part.impPartID,
    ucmMaterialDescription: description,
    ucmCostSource: source,
    ucmIsPurchased: source === "purchase_order",
    ucmUnitCost: toNumber(defaults?.unit_cost) || 0,
    ucmMinimumPurchaseQty: defaults?.minimum_purchase_qty ?? (source === "purchase_order" ? 1 : 0),
    ucmLastPO: defaults?.last_po || "",
    ucmLastPOCost: defaults?.last_po_cost ?? null,
    ucmLastPODate: defaults?.last_po_date ?? null,
    ucmMaterialMarkup: defaults?.material_markup ?? row.ucmMaterialMarkup,
    ucmManufacturedPartCostID: defaults?.manufactured_part_cost_id ?? row.ucmManufacturedPartCostID,
  };
}
function groupedFields(kind, row) {
  if (kind === "material") {
    return [
      { title: "Identity", note: "What material is being used.", fields: ["ucmMaterialDescription"] },
      { title: "Quantity", note: "These drive how much is consumed, bought, and wasted.", fields: ["ucmQtyPerAssembly", "ucmMinimumPurchaseQty"] },
      { title: "Unit cost", note: "ERP, PO, or manufactured-history cost assumptions.", fields: ["ucmUnitCost", "ucmMaterialMarkup", "ucmLastPO", "ucmLastPOCost", "ucmLastPODate"] },
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

function Badge({ children, tone = "neutral" }) { return <span className={"badge " + tone}>{children}</span>; }
function CostTrend({ field, value, originalValue, strong = false }) {
  const diff = toNumber(value) - toNumber(originalValue);
  const changed = originalValue !== undefined && Math.abs(diff) >= 0.005;
  const delta = (diff > 0 ? "+" : "-") + formatValue(field, Math.abs(diff));
  const content = <>{formatValue(field, value)}{changed && <span className={"trend-pill " + (diff > 0 ? "up" : "down")} title={(diff > 0 ? "Increased by " : "Decreased by ") + formatValue(field, Math.abs(diff))}>{delta}</span>}</>;
  return strong ? <strong className="cost-trend">{content}</strong> : <span className="cost-trend">{content}</span>;
}
function Button({ children, tone = "primary", ...props }) { return <button {...props} className={(props.className || "") + " button " + tone}>{children}</button>; }
function Stat({ label, value, field }) { return <div className="stat"><span>{label}</span><strong>{formatValue(field || label, value)}</strong></div>; }
function numberDraft(value) { return value === null || value === undefined ? "" : String(value); }
function isCompleteNumber(text) { return text !== "" && text !== "-" && text !== "." && text !== "-." && Number.isFinite(Number(text)); }
const NumberInput = React.forwardRef(function NumberInput({ value, onChange, ...props }, ref) {
  const [draft, setDraft] = useState(numberDraft(value)), [focused, setFocused] = useState(false);
  useEffect(() => { if (!focused) setDraft(numberDraft(value)); }, [value, focused]);
  function change(event) {
    const next = event.target.value;
    setDraft(next);
    if (isCompleteNumber(next)) onChange(Number(next));
  }
  function blur() {
    setFocused(false);
    setDraft(isCompleteNumber(draft) ? numberDraft(Number(draft)) : numberDraft(value));
  }
  return <input {...props} ref={ref} type="text" inputMode="decimal" value={draft} onChange={change} onFocus={(event) => { setFocused(true); setTimeout(() => event.target.select?.(), 0); props.onFocus?.(event); }} onBlur={(event) => { blur(); props.onBlur?.(event); }} />;
});

const DurationInput = React.forwardRef(function DurationInput({ value, onChange, onKeyDown, ...props }, ref) {
  const [draft, setDraft] = useState(formatDurationInput(value)), [focused, setFocused] = useState(false), parts = durationParts(value);
  useEffect(() => { if (!focused) setDraft(formatDurationInput(value)); }, [value, focused]);
  function change(event) {
    const next = event.target.value;
    setDraft(next);
    const parsed = parseDurationInput(next);
    if (parsed !== null) onChange(parsed);
  }
  function blur(event) {
    setFocused(false);
    setDraft(formatDurationInput(parseDurationInput(draft) ?? value));
    props.onBlur?.(event);
  }
  return <div className="duration-box"><input {...props} ref={ref} value={draft} onFocus={(event) => { setFocused(true); setTimeout(() => event.target.select?.(), 0); props.onFocus?.(event); }} onBlur={blur} onChange={change} onKeyDown={onKeyDown} /><div className="duration-readout"><b>{parts.h}</b><small>h</small><b>{String(parts.m).padStart(2, "0")}</b><small>m</small><b>{String(parts.s).padStart(2, "0")}</b><small>s</small></div></div>;
});

function DefaultValueInput({ field, value, onChange }) {
  return durationFields.has(field) ? <DurationInput data-field={field} value={value ?? 0} onChange={onChange} /> : <NumberInput data-field={field} value={value ?? 0} onChange={onChange} />;
}

function Field({ label, value, field, onChange, edited, defaultSourced, onDefaultEdit, onReset, type = "text" }) {
  const isDuration = durationFields.has(field), isNumeric = numericFields.has(field) && !isDuration, inputType = type === "checkbox" ? "checkbox" : "text";
  const [draft, setDraft] = useState(isNumeric ? numberDraft(value) : ""), [focused, setFocused] = useState(false);
  useEffect(() => { if (isNumeric && !focused) setDraft(numberDraft(value)); }, [isNumeric, value, focused]);
  function change(event) {
    if (inputType === "checkbox") return onChange(event.target.checked);
    if (isNumeric) { setDraft(event.target.value); if (isCompleteNumber(event.target.value)) onChange(Number(event.target.value)); return; }
    onChange(event.target.value);
  }
  function blur() { setFocused(false); if (isNumeric) setDraft(isCompleteNumber(draft) ? numberDraft(Number(draft)) : numberDraft(value)); }
  function keyDown(event) { if (event.key !== "Enter") return; event.preventDefault(); const inputs = Array.from(document.querySelectorAll(".focus-screen input")).filter((input) => !input.disabled && input.offsetParent !== null); const index = inputs.indexOf(event.currentTarget); const next = inputs[index + (event.shiftKey ? -1 : 1)]; if (next) { next.focus(); next.select?.(); } }
  function reset(event) { event.preventDefault(); event.stopPropagation(); onReset?.(); }
  return <label className={"field " + (edited ? "changed" : "") + (defaultSourced ? " from-default" : "")} onContextMenu={(event) => { if (onDefaultEdit) { event.preventDefault(); onDefaultEdit(field, value); } }}>
    <span>{label}<span className="field-flags">{defaultSourced && <em>default</em>}{edited && <em className="changed-flag">changed</em>}{edited && onReset && <button className="reset-button" type="button" onMouseDown={reset} onClick={(event) => event.preventDefault()}>Reset</button>}</span></span>
    {isDuration ? <DurationInput data-field={field} value={value} onChange={onChange} onKeyDown={keyDown} /> : <input data-field={field} type={inputType} inputMode={isNumeric ? "decimal" : undefined} checked={inputType === "checkbox" ? Boolean(value) : undefined} value={inputType === "checkbox" ? undefined : isNumeric ? draft : value ?? ""} onChange={change} onFocus={(event) => { setFocused(true); event.target.select?.(); }} onBlur={blur} onKeyDown={keyDown} />}
  </label>;
}

function AutocompleteField({ label, value, field, edited, searchUrl, renderOption, optionValue, onChange, onSelect }) {
  const [query, setQuery] = useState(""), [options, setOptions] = useState([]);
  useEffect(() => { const q = query.trim(); if (q.length < 2) { setOptions([]); return; } const timer = setTimeout(async () => { try { const payload = await readApiResponse(await fetch(searchUrl + encodeURIComponent(q))); setOptions(payload.parts || payload.operations || []); } catch { setOptions([]); } }, 180); return () => clearTimeout(timer); }, [query, searchUrl]);
  function choose(option) { setQuery(""); setOptions([]); onSelect(option); }
  function handleKey(event) {
    if ((event.key === "Enter" || event.key === "ArrowDown") && options[0]) {
      event.preventDefault();
      choose(options[0]);
    }
    if (event.key === "Escape") {
      setQuery("");
      setOptions([]);
    }
  }
  return <label className={"field autocomplete " + (edited ? "changed" : "")}><span>{label}{edited && <em className="changed-flag">changed</em>}</span><input data-field={field} value={value ?? ""} onChange={(event) => { setQuery(event.target.value); onChange(event.target.value); }} onKeyDown={handleKey} onKeyUp={(event) => { if (event.key === "ArrowDown" && options[0]) handleKey(event); }} />{options.length > 0 && <div className="suggestion-menu">{options.map((option, index) => <button type="button" key={optionValue(option) + index} onMouseDown={(event) => event.preventDefault()} onClick={() => choose(option)}>{renderOption(option)}</button>)}</div>}</label>;
}

function StartScreen({ draft, setDraft, loadErp, startBlank, loading, error }) {
  const partRef = useRef(null), qtyRef = useRef(null), [suggestions, setSuggestions] = useState([]);
  useEffect(() => { partRef.current?.focus(); }, []);
  useEffect(() => { const q = draft.part_id.trim(); if (q.length < 2) { setSuggestions([]); return; } const timer = setTimeout(async () => { try { const payload = await readApiResponse(await fetch("/api/parts/search?q=" + encodeURIComponent(q))); setSuggestions(document.activeElement === partRef.current ? payload.parts || [] : []); } catch { setSuggestions([]); } }, 180); return () => clearTimeout(timer); }, [draft.part_id]);
  function update(field, value) { setDraft((current) => ({ ...current, [field]: field === "quantity" ? toNumber(value) : value })); }
  function choose(part) { setDraft((current) => ({ ...current, part_id: part.impPartID, revision_id: part.impPartRevisionID || "" })); setSuggestions([]); qtyRef.current?.focus(); qtyRef.current?.select(); }
  return <main className="start-screen"><section className="start-card"><div><span className="eyebrow">Costing</span><h1>New product cost</h1><p>Part, Enter, quantity, Enter.</p></div><div className="start-form"><label className="field part-search"><span>Part number</span><input ref={partRef} autoComplete="off" value={draft.part_id} onChange={(event) => update("part_id", event.target.value.toUpperCase())} onKeyDown={(event) => { if (event.key === "ArrowDown" && suggestions[0]) { event.preventDefault(); choose(suggestions[0]); } if (event.key === "Enter") { event.preventDefault(); setSuggestions([]); qtyRef.current?.focus(); qtyRef.current?.select(); } }} /></label>{suggestions.length > 0 && <div className="start-suggestions">{suggestions.map((part) => <button type="button" key={part.impPartID} onClick={() => choose(part)}><strong>{part.impPartID}</strong><span>{part.impShortDescription || part.impPartShortDescription || "No description"}</span></button>)}</div>}<label className="field"><span>Revision</span><input autoComplete="off" value={draft.revision_id} onChange={(event) => update("revision_id", event.target.value)} /></label><label className="field"><span>Quantity</span><NumberInput ref={qtyRef} autoComplete="off" value={draft.quantity} onChange={(value) => update("quantity", value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); loadErp(); } }} /></label><Button onClick={() => loadErp()} disabled={loading}>{loading ? "Loading" : "Use ERP + defaults"}</Button><Button tone="secondary" onClick={startBlank}>Start blank</Button>{error && <div className="error-box">{error}</div>}</div></section></main>;
}

function OperationCalendar({ row, shift, onChange }) {
  const start = parseTimeHours(row.ucoStartTime, parseTimeHours(shift.firstShiftStart, 6));
  const timing = operationTiming(row);
  const runtime = timing.runtime;
  const finish = start + runtime;
  const days = Math.max(1, Math.ceil(finish / 24));
  const shownDays = days > 2 ? [0, days - 1] : [0, 1];
  const shiftStart = parseTimeHours(shift.firstShiftStart, 6), shiftEnd = parseTimeHours(shift.firstShiftEnd, 14.5);
  const segments = calendarSegments(row, start, shownDays);
  function setStartFromPointer(event, target = event.currentTarget) {
    const rect = target.getBoundingClientRect();
    const hour = Math.max(0, Math.min(24, ((event.clientX - rect.left) / rect.width) * 24));
    onChange("ucoStartTime", hoursToClock(hour));
  }
  function startDrag(event) {
    if (event.button !== 0) return;
    const target = event.currentTarget;
    event.preventDefault();
    setStartFromPointer(event, target);
    function move(moveEvent) { setStartFromPointer(moveEvent, target); }
    function up() {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    }
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  }
  return <section className="calendar-card"><div className="calendar-head"><div><span className="eyebrow">Schedule preview</span><strong>{formatDuration(runtime)} runtime</strong></div><Badge tone={row.ucoUseAfterHoursIdle ? "amber" : "neutral"}>{row.ucoUseAfterHoursIdle ? formatDuration(row.ucoAfterHoursIdleTimeHours) + " after-hours idle" : "not costed"}</Badge></div>{days > 2 && <div className="middle-note">{days - 2} full day{days - 2 === 1 ? "" : "s"} hidden in the middle</div>}{shownDays.map((day) => <div className="day-row" key={day}><div className="day-label">{day === 0 ? "Start day" : "Finish day"}<span>{day === 0 ? "Drag to set start " + hoursToClock(start) : "Finish " + hoursToClock(finish)}</span></div><div className={"timeline " + (day === 0 ? "draggable" : "")} onMouseDown={day === 0 ? startDrag : undefined}>{Array.from({ length: 25 }).map((_, i) => <i key={i} style={{ left: (i / 24) * 100 + "%" }} />)}<div className="shift-band" style={{ left: (shiftStart / 24) * 100 + "%", width: (((shiftEnd - shiftStart + 24) % 24 || 24) / 24) * 100 + "%" }} />{segments.map((segment, index) => { const pos = pct(segment.left, segment.duration, day); const showLabel = pos.width > 15; return pos.width > 0 && <div key={segment.kind + segment.left + index} className={"bar " + segment.kind} title={segment.label + " - " + formatDuration(segment.duration)} style={{ left: pos.left + "%", width: pos.width + "%" }}>{showLabel ? segment.label : ""}</div>; })}{row.ucoUseAfterHoursIdle && toNumber(row.ucoAfterHoursIdleTimeHours) > 0 && (() => { const pos = pct(finish, toNumber(row.ucoAfterHoursIdleTimeHours), day); return pos.width > 0 && <div className="bar after" style={{ left: pos.left + "%", width: pos.width + "%" }}>{pos.width > 18 ? "After-hours idle" : ""}</div>; })()} {day === 0 && <div className="start-marker" style={{ left: (start / 24) * 100 + "%" }}><b>{hoursToClock(start)}</b></div>}</div></div>)}</section>;
}

function Review({ run, setView, openLine, returnCrumb, onReturnWithUnitCost }) {
  const part = run.part_cost;
  const issueCount = findIssues(run).length;
  return <div className="page-grid review-grid">{returnCrumb && <section className="panel span-2 child-cost-banner"><div><span className="eyebrow">Child cost report</span><h3>Use this marked-up unit cost in {returnCrumb}</h3><p>Marked-up unit cost is {formatValue("ucpUnitMarkedUpCost", part.ucpUnitMarkedUpCost)}. Change the quantity above first if this material will be made in a different batch size.</p></div><Button onClick={() => onReturnWithUnitCost(part.ucpUnitMarkedUpCost)}>Use marked-up cost</Button></section>}<section className="panel span-2"><div className="panel-title"><div><span className="eyebrow">Overview</span><h2>{part.ucpPartID || "Blank cost"} {part.ucpPartRevision && <small>rev {part.ucpPartRevision}</small>}</h2><p>{part.ucpPartDescription || "No description from ERP"}</p></div><Badge tone={issueCount ? "amber" : "green"}>{issueCount ? issueCount + " things to review" : "ready to review"}</Badge></div><div className="stat-grid"><Stat label="Unit raw" field="ucpUnitRawCost" value={part.ucpUnitRawCost} /><Stat label="Unit marked up" field="ucpUnitMarkedUpCost" value={part.ucpUnitMarkedUpCost} /><Stat label="Quantity" field="ucpCostQuantity" value={part.ucpCostQuantity} /><Stat label="Total marked up" field="ucpTotalMarkedUpCost" value={part.ucpTotalMarkedUpCost} /><Stat label="Material raw unit" field="ucpMaterialsRawCost" value={part.ucpMaterialsRawCost / (toNumber(part.ucpCostQuantity) || 1)} /><Stat label="Material marked unit" field="ucpMaterialsMarkedUpCost" value={part.ucpMaterialsMarkedUpCost / (toNumber(part.ucpCostQuantity) || 1)} /><Stat label="Operation raw unit" field="ucpMachineTimeRawCost" value={(part.ucpMachineTimeRawCost + part.ucpLaborRawCost + part.ucpExternalOperationsRawCost + part.ucpAdditionalRawCost) / (toNumber(part.ucpCostQuantity) || 1)} /><Stat label="Operation marked unit" field="ucpMachineTimeMarkedUpCost" value={(part.ucpMachineTimeMarkedUpCost + part.ucpLaborMarkedUpCost + part.ucpExternalOperationsMarkedUpCost + part.ucpAdditionalMarkedUpCost) / (toNumber(part.ucpCostQuantity) || 1)} /></div></section><section className="panel"><div className="panel-title"><h3>Material summary</h3><Button tone="secondary" onClick={() => setView("materials")}>Open</Button></div><div className="stacked-stats"><Stat label="Lines" value={run.material_lines.length} /><Stat label="Raw unit material" field="ucpMaterialsRawCost" value={part.ucpMaterialsRawCost / (toNumber(part.ucpCostQuantity) || 1)} /><Stat label="Marked unit material" field="ucpMaterialsMarkedUpCost" value={part.ucpMaterialsMarkedUpCost / (toNumber(part.ucpCostQuantity) || 1)} /></div></section><section className="panel"><div className="panel-title"><h3>Operation summary</h3><Button tone="secondary" onClick={() => setView("operations")}>Open</Button></div><div className="stacked-stats"><Stat label="Operations" value={run.operation_lines.length} /><Stat label="Raw unit operations" field="ucpMachineTimeRawCost" value={(part.ucpMachineTimeRawCost + part.ucpLaborRawCost + part.ucpExternalOperationsRawCost + part.ucpAdditionalRawCost) / (toNumber(part.ucpCostQuantity) || 1)} /><Stat label="Marked unit operations" field="ucpLaborMarkedUpCost" value={(part.ucpLaborMarkedUpCost + part.ucpMachineTimeMarkedUpCost + part.ucpExternalOperationsMarkedUpCost + part.ucpAdditionalMarkedUpCost) / (toNumber(part.ucpCostQuantity) || 1)} /></div></section><section className="panel span-2"><div className="panel-title"><h3>Needs attention</h3></div><div className="issue-list">{findIssues(run).length ? findIssues(run).map((issue) => <button type="button" key={issue.id} onClick={() => openLine(issue.kind, issue.id)}><Badge tone={issue.tone}>{issue.kind}</Badge><span>{issue.text}</span></button>) : <p>No obvious ERP/default issues found.</p>}</div></section></div>;
}

function LineList({ kind, rows, originalRows = [], onOpen, onAdd, onDelete, onResetLines, onRefreshDefaults, canReset }) {
  const isMaterial = kind === "material";
  const originalById = new Map((originalRows || []).map((row) => [row._id, row]));
  function rowKeyOpen(event, row) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(kind, row._id);
    }
  }
  return <section className="panel full-panel"><div className="panel-title"><div><span className="eyebrow">{isMaterial ? "Materials" : "Operations"}</span><h2>{isMaterial ? "Material costs" : "Operation costs"}</h2></div><div className="focus-actions"><Button tone="secondary" onClick={onRefreshDefaults}>Refresh defaults</Button><Button tone="secondary" onClick={onResetLines} disabled={!canReset}>Reset lines</Button><Button onClick={onAdd}>Add {isMaterial ? "material" : "operation"}</Button></div></div><div className="data-table"><div className="table-head">{isMaterial ? ["Part", "Type", "Description", "Qty/part", "Raw unit", "Marked unit", "Total marked", ""].map((h) => <b key={h}>{h}</b>) : ["Seq", "Machine", "Description", "Type", "Runtime", "Raw unit", "Marked unit", "Total marked", ""].map((h) => <b key={h}>{h}</b>)}</div>{rows.map((row) => { const original = originalById.get(row._id) || {}; return isMaterial ? <div className="table-row" tabIndex="0" key={row._id} onClick={() => onOpen("material", row._id)} onKeyDown={(event) => rowKeyOpen(event, row)}><strong>{row.ucmMaterialID || "New material"}</strong><Badge tone={materialSource(row).tone}>{materialSource(row).label}</Badge><span>{row.ucmMaterialDescription || "-"}</span><span>{formatValue("ucmQtyPerAssembly", row.ucmQtyPerAssembly)}</span><CostTrend field="ucmRawCost" value={lineRawUnitCost(row)} originalValue={original._id ? lineRawUnitCost(original) : undefined} /><CostTrend field="ucmMarkedUpCost" value={lineMarkedUnitCost(row)} originalValue={original._id ? lineMarkedUnitCost(original) : undefined} /><strong>{formatValue("ucmMarkedUpCost", row.ucmMarkedUpCost)}</strong><span className="row-actions"><button type="button" onClick={(event) => { event.stopPropagation(); onDelete("material", row._id); }}>Delete</button></span></div> : <div className="table-row op-row" tabIndex="0" key={row._id} onClick={() => onOpen("operation", row._id)} onKeyDown={(event) => rowKeyOpen(event, row)}><strong>{row.ucoPartOperationLineID || row.ucoOperationID || "New"}</strong><span>{row.ucoWorkCenterID || "-"}</span><span>{row.ucoOperationDescription || "-"}</span><Badge tone={row.ucoExternalJob ? "amber" : "blue"}>{row.ucoExternalJob ? "External" : "Internal"}</Badge><span>{formatDuration(operationTiming(row).runtime)}</span><CostTrend field="ucoLineRawCost" value={lineRawUnitCost(row)} originalValue={original._id ? lineRawUnitCost(original) : undefined} /><CostTrend field="ucoLineMarkedUpCost" value={lineMarkedUnitCost(row)} originalValue={original._id ? lineMarkedUnitCost(original) : undefined} /><strong>{formatValue("ucoLineMarkedUpCost", row.ucoLineMarkedUpCost)}</strong><span className="row-actions"><button type="button" onClick={(event) => { event.stopPropagation(); onDelete("operation", row._id); }}>Delete</button></span></div>; })}</div></section>;
}

function FocusEditor({ kind, row, original, edited, updateRow, resetField, refreshDefaults, removeRow, close, openPO, applyMaterialSuggestion, updateMachineDefault, shift, onCostMaterial, openMaterialHistory }) {
  const isMaterial = kind === "material";
  if (!row) return null;
  const changed = (field) => edited.has(keyFor(row, field));
  const commonProps = (field) => ({ edited: changed(field), onReset: () => resetField(kind, row._id, field) });
  function set(field, value) { updateRow(kind, row._id, field, numericFields.has(field) && !durationFields.has(field) ? toNumber(value) : value); }
  const fields = isMaterial ? materialFields : [...opCommonFields, ...(row.ucoExternalJob ? opExternalFields : opInternalFields)];
  const fieldMap = new Map(fields.map(([field, label, type]) => [field, { label, type }]));
  function renderField(field) {
    if (isMaterial && field === "ucmMaterialID") return null;
    if (!isMaterial && field === "ucoOperationID") return null;
    const meta = fieldMap.get(field);
    if (!meta) return null;
    return <Field key={field} field={field} label={meta.label} value={row[field]} type={meta.type} onChange={(value) => set(field, value)} defaultSourced={!isMaterial && machineDefaultKeys.has(field) && !changed(field)} onDefaultEdit={!isMaterial && machineDefaultKeys.has(field) ? (f, value) => updateMachineDefault(machineKey(row), f, value) : null} {...commonProps(field)} />;
  }
  return <main className="focus-screen">
    <section className="focus-head">
      <Button tone="secondary" onClick={close}>Save and exit</Button>
      <div><span className="eyebrow">{isMaterial ? "Material" : "Operation"}</span><h2>{isMaterial ? row.ucmMaterialID || "New material" : row.ucoOperationDescription || row.ucoOperationID || "New operation"}</h2></div>
      <div className="focus-actions"><Button tone="secondary" onClick={() => refreshDefaults(kind, row._id)}>Refresh defaults</Button>{isMaterial && <Button tone="secondary" onClick={() => openMaterialHistory(row)} disabled={!row.ucmMaterialID}>Cost history</Button>}{isMaterial && <Button tone="secondary" onClick={() => onCostMaterial(row)} disabled={!row.ucmMaterialID}>New child cost</Button>}{(isMaterial && row.ucmIsPurchased) || (!isMaterial && row.ucoExternalJob) ? <Button tone="secondary" onClick={() => openPO(kind, row)}>PO explorer</Button> : null}<Button tone="danger" onClick={() => removeRow(kind, row._id)}>Delete</Button></div>
    </section>
    <section className="focus-layout">
      <div className="edit-panel grouped">
        <div className="source-strip">{isMaterial ? <Badge tone={materialSource(row).tone}>{materialSource(row).label}</Badge> : <Badge tone={row.ucoExternalJob ? "amber" : "blue"}>{row.ucoExternalJob ? "External operation" : "Internal operation"}</Badge>}<Badge>{row._source === "erp" ? "ERP seeded" : "manual"}</Badge></div>
        {isMaterial && <AutocompleteField label="Material part number" field="ucmMaterialID" value={row.ucmMaterialID} edited={changed("ucmMaterialID")} searchUrl="/api/parts/search?q=" optionValue={(part) => part.impPartID} renderOption={(part) => <><strong>{part.impPartID}</strong><span>{part.impShortDescription || part.impPartShortDescription || "No description"}</span></>} onChange={(value) => set("ucmMaterialID", value.toUpperCase())} onSelect={(part) => applyMaterialSuggestion(row._id, part)} />}
        {!isMaterial && <AutocompleteField label="Process code" field="ucoOperationID" value={row.ucoOperationID} edited={changed("ucoOperationID")} searchUrl="/api/operations/search?q=" optionValue={(op) => op.xawWorkCenterID + op.xaoOperationID} renderOption={(op) => <><strong>{op.xaoOperationID || op.xawWorkCenterID}</strong><span>{op.xaoDescription || op.xawDescription || "No description"}</span></>} onChange={(value) => set("ucoOperationID", value)} onSelect={(op) => { set("ucoOperationID", op.xaoOperationID || row.ucoOperationID); set("ucoWorkCenterID", op.xawWorkCenterID || row.ucoWorkCenterID); set("ucoOperationDescription", op.xaoDescription || op.xawDescription || row.ucoOperationDescription); }} />}
        {groupedFields(kind, row).map((group) => <section className="field-group" key={group.title}><div className="group-heading"><h3>{group.title}</h3><p>{group.note}</p></div><div className="group-fields">{group.fields.map(renderField)}</div></section>)}
      </div>
      <div className="calc-panel">
        <h3>Calculated now</h3>
        {isMaterial ? <>
          <Stat label="Required quantity" field="ucmTotalQuantityRequired" value={row.ucmTotalQuantityRequired} />
          <Stat label="Wasted quantity" field="ucmWasteQuantity" value={row.ucmWasteQuantity} />
          <Stat label="Raw cost" field="ucmRawCost" value={row.ucmRawCost} />
          <Stat label="Marked up cost" field="ucmMarkedUpCost" value={row.ucmMarkedUpCost} />
        </> : <>
          <Stat label="Runtime" value={formatDuration(operationTiming(row).runtime)} />
          <Stat label="Labor" field="ucoLaborMarkedUpCost" value={row.ucoLaborMarkedUpCost} />
          <Stat label="Machine" field="ucoMachineMarkedUpCost" value={row.ucoMachineMarkedUpCost} />
          <Stat label="External" field="ucoExternalOperationMarkedUpCost" value={row.ucoExternalOperationMarkedUpCost} />
          <Stat label="Line total" field="ucoLineMarkedUpCost" value={row.ucoLineMarkedUpCost} />
          <OperationCalendar row={row} shift={shift} onChange={set} />
        </>}
        <details><summary>Original ERP/default values</summary><pre>{JSON.stringify(original || {}, null, 2)}</pre></details>
      </div>
    </section>
  </main>;
}

function Settings({ part, markupBreaks, setMarkupBreaks, globalDefaults, setGlobalDefaults, machineDefaults, setMachineDefaults, shift, setShift, refreshAllDefaults }) {
  const [saveState, setSaveState] = useState("");
  function updateBreak(index, field, value) { setMarkupBreaks((rows) => normalizeMarkupBreaks(rows.map((row, i) => i === index ? { ...row, [field]: toNumber(value) } : row))); }
  function removeBreak(index) { setMarkupBreaks((rows) => rows.filter((_, i) => i !== index)); }
  function addBreak() { setMarkupBreaks((rows) => { const lastQty = rows.reduce((max, row) => Math.max(max, toNumber(row.breakQty)), 0); return normalizeMarkupBreaks([...rows, { breakQty: lastQty ? lastQty * 10 : 1, material: 1, labor: 1, machine: 1, external: 1, additional: 1 }]); }); }
  function updateGlobal(field, value) { setGlobalDefaults((current) => ({ ...current, [field]: toNumber(value) })); }
  function updateMachine(machine, field, value) { setMachineDefaults((current) => ({ ...current, [machine]: { ...(current[machine] || {}), [field]: toNumber(value) } })); }
  async function saveSettings() { try { setSaveState("Saving"); await readApiResponse(await fetch("/api/settings/defaults", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_id: part?.ucpPartID || null, revision_id: part?.ucpPartRevision || "", markup_breaks: normalizeMarkupBreaks(markupBreaks), global_defaults: globalDefaults, machine_defaults: machineDefaults, shift_settings: shift }) })); setSaveState("Saved"); } catch (err) { setSaveState(err.message); } }
  const sortedBreaks = normalizeMarkupBreaks(markupBreaks);
  return <div className="page-grid"><section className="panel span-2"><div className="panel-title"><div><span className="eyebrow">Part markup</span><h2>Quantity breaks</h2></div><div className="settings-actions"><Button tone="secondary" onClick={refreshAllDefaults}>Refresh all lines</Button><Button tone="secondary" onClick={addBreak}>Add break</Button><Button onClick={saveSettings}>Save settings</Button>{saveState && <span>{saveState}</span>}</div></div><div className="settings-table"><div className="settings-row head"><b>Quantity starts at</b>{markupDefaults.map(([key, label]) => <b key={key}>{label}</b>)}<b></b></div>{sortedBreaks.map((row, index) => <div className="settings-row" key={index}><NumberInput value={row.breakQty} onChange={(value) => updateBreak(index, "breakQty", value)} />{markupDefaults.map(([key]) => <NumberInput key={key} value={row[key]} onChange={(value) => updateBreak(index, key, value)} />)}<Button tone="danger" onClick={() => removeBreak(index)}>Remove</Button></div>)}</div></section><section className="panel"><div className="panel-title"><h2>Global cost defaults</h2></div><div className="settings-mini">{machineDefaultFields.map(([field, label]) => <Field key={field} label={label} field={field} value={globalDefaults[field] ?? 0} onChange={(value) => updateGlobal(field, value)} />)}</div></section><section className="panel"><div className="panel-title"><h2>Shift calendar</h2></div><div className="settings-mini"><Field label="First shift starts" field="firstShiftStart" value={shift.firstShiftStart} onChange={(value) => setShift((s) => ({ ...s, firstShiftStart: value }))} /><Field label="First shift ends" field="firstShiftEnd" value={shift.firstShiftEnd} onChange={(value) => setShift((s) => ({ ...s, firstShiftEnd: value }))} /><Field label="After-hours idle discount" field="afterHoursIdleMultiplier" value={shift.afterHoursIdleMultiplier} onChange={(value) => setShift((s) => ({ ...s, afterHoursIdleMultiplier: toNumber(value) }))} /></div></section><section className="panel span-2"><div className="panel-title"><h2>Machine defaults</h2></div><div className="machine-table"><div className="machine-row head"><b>Machine</b>{machineDefaultFields.map(([, label]) => <b key={label}>{label}</b>)}</div>{Object.keys(machineDefaults).sort().map((machine) => <div className="machine-row" key={machine}><strong>{machine}</strong>{machineDefaultFields.map(([field]) => <DefaultValueInput key={field} field={field} value={machineDefaults[machine]?.[field] ?? 0} onChange={(value) => updateMachine(machine, field, value)} />)}</div>)}</div></section></div>;
}

function POExplorer({ target, onClose, onApply }) {
  const [rows, setRows] = useState([]), [selected, setSelected] = useState(null), [error, setError] = useState("");
  useEffect(() => { if (!target) return; (async () => { try { setError(""); const params = target.kind === "material" ? "part_id=" + encodeURIComponent(target.row.ucmMaterialID || "") : "part_id=" + encodeURIComponent(target.partId || "") + "&method_operation_id=" + encodeURIComponent(target.row.ucoPartOperationLineID || target.row.ucoOperationID || ""); const payload = await readApiResponse(await fetch("/api/purchase-orders/" + (target.kind === "material" ? "material" : "external-operation") + "?" + params)); setRows(payload.purchase_orders || payload.rows || []); } catch (err) { setError(err.message); } })(); }, [target]);
  if (!target) return null;
  return <div className="modal-backdrop"><section className="po-modal"><header><div><span className="eyebrow">Purchase orders</span><h2>{target.kind === "material" ? target.row.ucmMaterialID : target.row.ucoOperationDescription}</h2></div><Button tone="secondary" onClick={onClose}>Close</Button></header>{error && <div className="error-box">{error}</div>}<div className="po-panes"><div className="po-list">{rows.length ? rows.map((row, index) => <button type="button" key={index} className={selected === row ? "selected" : ""} onClick={() => setSelected(row)} onDoubleClick={() => onApply(row)}><strong>{row.pmlPurchaseOrderID || row.po_id || "-"}</strong><span>{formatValue("ucmLastPOCost", row.pmlPurchaseUnitCostBase ?? row.pmlExtendedCostBase ?? row.unit_cost)}</span><span>{row.pmlDueDate || row.pmlCreatedDate || row.date || ""}</span></button>) : <p>No matching purchase order lines.</p>}</div><div className="po-details"><h3>SQL row details</h3>{selected ? <pre>{JSON.stringify(selected, null, 2)}</pre> : <p>Select a purchase order line.</p>}</div></div></section></div>;
}

function CostHistoryModal({ target, onClose, onUseRun, onUseUnitCost, onCostQuantity, onNewRun, onSetCurrent }) {
  const rows = target?.rows || [];
  const [selected, setSelected] = useState(rows.find((row) => row.ucpIsCurrent) || rows[0] || null);
  useEffect(() => { setSelected(rows.find((row) => row.ucpIsCurrent) || rows[0] || null); }, [target]);
  if (!target) return null;
  const isMaterial = target.kind === "material";
  const title = isMaterial ? target.row.ucmMaterialID : target.partId;
  return <div className="modal-backdrop"><section className="history-modal"><header><div><span className="eyebrow">{isMaterial ? "Material cost history" : "Cost history"}</span><h2>{title}</h2></div><Button tone="secondary" onClick={onClose}>Close</Button></header><div className="history-body"><div className="history-list">{rows.map((row) => <button type="button" key={row.ucpPartCostID} className={selected?.ucpPartCostID === row.ucpPartCostID ? "selected" : ""} onClick={() => setSelected(row)} onDoubleClick={() => isMaterial ? onUseUnitCost(row) : onUseRun(row)}><strong>{formatValue("ucpUnitMarkedUpCost", row.ucpUnitMarkedUpCost)}</strong><span>Qty {formatValue("ucpCostQuantity", row.ucpCostQuantity)}</span><span>{row.ucpDateCosted || ""}</span>{row.ucpIsCurrent ? <Badge tone="green">Current</Badge> : <Badge>Saved</Badge>}</button>)}</div><div className="history-detail">{selected ? <><div className="stat-grid compact"><Stat label="Unit raw" field="ucpUnitRawCost" value={selected.ucpUnitRawCost} /><Stat label="Unit marked up" field="ucpUnitMarkedUpCost" value={selected.ucpUnitMarkedUpCost} /><Stat label="Quantity" field="ucpCostQuantity" value={selected.ucpCostQuantity} /><Stat label="Total" field="ucpTotalMarkedUpCost" value={selected.ucpTotalMarkedUpCost} /></div><div className="history-actions">{isMaterial ? <><Button onClick={() => onUseUnitCost(selected)}>Use unit cost</Button><Button tone="secondary" onClick={() => onCostQuantity(selected)}>Re-cost quantity</Button></> : <Button onClick={() => onUseRun(selected)}>Open as starting point</Button>}<Button tone="secondary" onClick={() => onSetCurrent(selected)}>Make current</Button><Button tone="secondary" onClick={onNewRun}>{isMaterial ? "Start new run" : "Use ERP defaults"}</Button></div>{selected.ucpNotes && <p>{selected.ucpNotes}</p>}</> : <p>No saved costing runs.</p>}</div></div></section></div>;
}

function findIssues(run) {
  const issues = [];
  (run.material_lines || []).forEach((row) => { if (row.ucmIsPurchased && !row.ucmLastPO) issues.push({ kind: "material", id: row._id, tone: "amber", text: (row.ucmMaterialID || "Material") + " has no purchase order reference." }); if (toNumber(row.ucmWasteQuantity) > 0) issues.push({ kind: "material", id: row._id, tone: "blue", text: (row.ucmMaterialID || "Material") + " wastes " + formatValue("ucmWasteQuantity", row.ucmWasteQuantity) + " because of purchase increment." }); });
  (run.operation_lines || []).forEach((row) => { if (row.ucoExternalJob && !row.ucoLastPO) issues.push({ kind: "operation", id: row._id, tone: "amber", text: (row.ucoOperationDescription || "External operation") + " has no purchase order reference." }); if (!row.ucoExternalJob && toNumber(row.ucoAfterHoursIdleTimeHours) > 0) issues.push({ kind: "operation", id: row._id, tone: "blue", text: (row.ucoOperationDescription || "Operation") + " includes after-hours idle time." }); });
  return issues;
}

function Workspace({ run, setRun, original, setOriginal, setMode, draft, onCostMaterial, returnCrumb, onReturnToParent, onReturnWithUnitCost }) {
  const [view, setView] = useState("review"), [focus, setFocus] = useState(null), [edited, setEdited] = useState(() => new Set(run.settings?.editedFromSave || [])), [markupBreaks, setMarkupBreaks] = useState(() => normalizeMarkupBreaks(run.settings?.markupBreaks)), [globalDefaults, setGlobalDefaults] = useState(() => run.settings?.globalDefaults || defaultGlobalMachineDefaults), [shift, setShift] = useState(() => run.settings?.shift || defaultShiftSettings), [machineDefaults, setMachineDefaults] = useState(() => run.settings?.machineDefaults || buildMachineDefaults(run.operation_lines)), [poTarget, setPoTarget] = useState(null), [historyTarget, setHistoryTarget] = useState(null), [saveState, setSaveState] = useState("");
  const recalced = useMemo(() => recalcRun(run, markupBreaks, edited, shift), [run, markupBreaks, edited, shift]);
  useEffect(() => { setRun(recalced); }, [recalced.part_cost.ucpTotalMarkedUpCost]);
  useEffect(() => { setView("review"); setFocus(null); }, [run.part_cost.ucpPartID]);
  function commit(next, nextEdited = edited) { const recalculated = recalcRun(next, markupBreaks, nextEdited, shift); setRun(recalculated); return recalculated; }
  function setQuantity(value) { const next = { ...run, part_cost: { ...run.part_cost, ucpCostQuantity: toNumber(value) || 1 } }; commit(next); }
  function openLine(kind, id) { const rows = kind === "material" ? run.material_lines : run.operation_lines; const row = rows.find((item) => item._id === id); if (row) { setFocus({ kind, id }); setView("focus"); } }
  function addLine(kind) { const row = kind === "material" ? newMaterial(run.part_cost.ucpCostQuantity) : newOperation(run.part_cost.ucpCostQuantity); const next = kind === "material" ? { ...run, material_lines: [...run.material_lines, row] } : { ...run, operation_lines: [...run.operation_lines, row] }; commit(next); setFocus({ kind, id: row._id }); setView("focus"); }
  function updateRow(kind, id, field, value) { const key = kind === "material" ? "material_lines" : "operation_lines"; const originalRows = kind === "material" ? original.material_lines : original.operation_lines; const rows = run[key].map((row) => row._id === id ? { ...row, [field]: value } : row); const changedRow = rows.find((row) => row._id === id); const originalRow = (originalRows || []).find((row) => row._id === id) || {}; const nextEdited = setEditedForValue(edited, id + "." + field, field, changedRow[field], originalRow[field]); setEdited(nextEdited); commit({ ...run, [key]: rows }, nextEdited); }
  function resetField(kind, id, field) { const key = kind === "material" ? "material_lines" : "operation_lines"; const originalRows = kind === "material" ? original.material_lines : original.operation_lines; const source = (originalRows || []).find((row) => row._id === id); if (!source) return updateRow(kind, id, field, kind === "material" ? newMaterial()[field] : newOperation()[field]); updateRow(kind, id, field, source[field]); }
  function removeRow(kind, id) { const key = kind === "material" ? "material_lines" : "operation_lines"; commit({ ...run, [key]: run[key].filter((row) => row._id !== id) }); setView(kind === "material" ? "materials" : "operations"); setFocus(null); }
  function resetLines(kind) {
    const key = kind === "material" ? "material_lines" : "operation_lines";
    const originalRows = original[key] || [];
    const currentById = new Map((run[key] || []).map((row) => [row._id, row]));
    const originalIds = new Set(originalRows.map((row) => row._id));
    const restoredIds = new Set();
    const rows = originalRows.map((row) => {
      if (currentById.has(row._id)) return currentById.get(row._id);
      restoredIds.add(row._id);
      return row;
    });
    const nextEdited = new Set([...edited].filter((keyName) => {
      const id = keyName.split(".")[0];
      return originalIds.has(id) && !restoredIds.has(id);
    }));
    setEdited(nextEdited);
    commit({ ...run, [key]: rows }, nextEdited);
    if (focus?.kind === kind && !rows.some((row) => row._id === focus.id)) setFocus(null);
  }
  function materialDefaultValue(row, field) {
    if (field !== "ucmMaterialMarkup") return row[field];
    if (row.ucmCostSource === "manufactured_history" || row.ucmCostSource === "manufactured_current") return 1;
    return toNumber(activeMarkupBreak(markupBreaks, run.part_cost.ucpCostQuantity).material) || 1;
  }
  function operationDefaultValue(row, field) {
    const markup = markupDefaults.find(([, , markupField]) => markupField === field);
    if (markup) return toNumber(activeMarkupBreak(markupBreaks, run.part_cost.ucpCostQuantity)[markup[0]]) || 1;
    if (!machineDefaultKeys.has(field)) return row[field];
    const machineValue = machineDefaults[machineKey(row)]?.[field];
    return machineValue === undefined || machineValue === null ? toNumber(globalDefaults[field]) : toNumber(machineValue);
  }
  function refreshRowsWithDefaults(nextRun, kind, id = null) {
    const isMaterial = kind === "material", key = isMaterial ? "material_lines" : "operation_lines";
    const fields = isMaterial ? ["ucmMaterialMarkup"] : [...machineDefaultFields.map(([field]) => field), ...markupDefaults.map(([, , field]) => field)];
    const rows = nextRun[key].map((row) => {
      if (id && row._id !== id) return row;
      return fields.reduce((next, field) => edited.has(keyFor(row, field)) ? next : { ...next, [field]: isMaterial ? materialDefaultValue(row, field) : operationDefaultValue(row, field) }, row);
    });
    return { ...nextRun, [key]: rows };
  }
  function refreshDefaults(kind, id = null) { commit(refreshRowsWithDefaults(run, kind, id)); }
  function refreshAllDefaults() { commit(refreshRowsWithDefaults(refreshRowsWithDefaults(run, "material"), "operation")); }
  function lineMembershipChanged(kind) {
    const key = kind === "material" ? "material_lines" : "operation_lines";
    const currentIds = (run[key] || []).map((row) => row._id).sort().join("|");
    const originalIds = (original[key] || []).map((row) => row._id).sort().join("|");
    return currentIds !== originalIds;
  }
  async function applyMaterialSuggestion(id, part) { const row = run.material_lines.find((item) => item._id === id); let defaults = {}; try { defaults = await readApiResponse(await fetch("/api/materials/default?part_id=" + encodeURIComponent(part.impPartID) + "&revision_id=" + encodeURIComponent(part.impPartRevisionID || ""))); } catch { defaults = {}; } const replacement = materialDefaultsToRow(row, part, defaults); const rows = run.material_lines.map((item) => item._id === id ? replacement : item); const originalRow = (original.material_lines || []).find((item) => item._id === id) || {}; let nextEdited = new Set(edited); materialFields.map(([field]) => field).forEach((field) => { nextEdited = setEditedForValue(nextEdited, id + "." + field, field, replacement[field], originalRow[field]); }); setEdited(nextEdited); commit({ ...run, material_lines: rows }, nextEdited); }
  function updateMachineDefault(machine, field, value) { setMachineDefaults((current) => ({ ...current, [machine]: { ...(current[machine] || {}), [field]: toNumber(value) } })); }
  function applyPO(row) { if (!poTarget) return; const id = poTarget.row._id, cost = toNumber(row.pmlPurchaseUnitCostBase ?? row.pmlExtendedCostBase ?? row.unit_cost), poId = row.pmlPurchaseOrderID || row.po_id || "", date = row.pmlDueDate || row.pmlCreatedDate || row.date || ""; if (poTarget.kind === "material") { const rows = run.material_lines.map((item) => item._id === id ? { ...item, ucmLastPO: poId, ucmLastPOCost: cost, ucmLastPODate: date, ucmUnitCost: cost, ucmIsPurchased: true } : item); commit({ ...run, material_lines: rows }); } else { const rows = run.operation_lines.map((item) => item._id === id ? { ...item, ucoLastPO: poId, ucoLastPOCost: cost, ucoLastPODate: date, ucoExternalUnitCost: cost, ucoExternalJob: true } : item); commit({ ...run, operation_lines: rows }); } setPoTarget(null); }
  async function saveWorksheet(makeCurrent = false) { try { setSaveState("Saving"); const payload = await readApiResponse(await fetch("/api/costs/save-run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_cost: { ...run.part_cost, ucpIsCurrent: false }, operation_lines: run.operation_lines, material_lines: run.material_lines, make_current: makeCurrent }) })); const saved = { ...run, part_cost: { ...run.part_cost, ucpPartCostID: payload.part_cost_id, ucpIsCurrent: makeCurrent } }; setRun(saved); setOriginal(JSON.parse(JSON.stringify(saved))); setSaveState(makeCurrent ? "Saved current" : "Saved"); } catch (err) { setSaveState(err.message); } }
  async function openMaterialHistory(row) { try { const payload = await readApiResponse(await fetch("/api/costs/history?part_id=" + encodeURIComponent(row.ucmMaterialID || "") + "&revision_id=")); if ((payload.history || []).length) setHistoryTarget({ kind: "material", row, rows: payload.history }); else onCostMaterial(row); } catch { onCostMaterial(row); } }
  function useMaterialHistoryCost(history) { if (!historyTarget?.row) return; const id = historyTarget.row._id; const rows = run.material_lines.map((item) => item._id === id ? { ...item, ucmUnitCost: toNumber(history.ucpUnitMarkedUpCost), ucmMaterialMarkup: 1, ucmCostSource: "manufactured_history", ucmIsPurchased: false, ucmManufacturedPartCostID: history.ucpPartCostID, ucmLastPO: "", ucmLastPOCost: null, ucmLastPODate: history.ucpDateCosted } : item); commit({ ...run, material_lines: rows }); setHistoryTarget(null); }
  async function setHistoryCurrent(history) { await readApiResponse(await fetch("/api/costs/current", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_cost_id: history.ucpPartCostID }) })); setHistoryTarget((target) => target ? { ...target, rows: target.rows.map((row) => ({ ...row, ucpIsCurrent: row.ucpPartCostID === history.ucpPartCostID })) } : target); }
  const activeRow = focus?.kind === "material" ? run.material_lines.find((row) => row._id === focus.id) : focus?.kind === "operation" ? run.operation_lines.find((row) => row._id === focus.id) : null;
  const originalRow = focus?.kind === "material" ? original.material_lines.find((row) => row._id === focus.id) : focus?.kind === "operation" ? original.operation_lines.find((row) => row._id === focus.id) : null;
  return <div className="workspace">
    <header className={"topbar " + (returnCrumb ? "with-return" : "")}>
      <Button tone="secondary" className="home-icon" onClick={() => setMode("start")}>Home</Button>
      {returnCrumb && <Button tone="secondary" className="return-button" onClick={onReturnToParent}>Back to {returnCrumb}</Button>}
      <div className="part-title"><strong>{run.part_cost.ucpPartID || draft.part_id || "New cost"}</strong><span>{run.part_cost.ucpPartDescription || "Cost worksheet"}</span></div>
      <label className="qty-box"><span>Quantity</span><NumberInput value={run.part_cost.ucpCostQuantity} onChange={setQuantity} /></label>
      <Stat label="Unit raw" field="ucpUnitRawCost" value={run.part_cost.ucpUnitRawCost} />
      <Stat label="Unit marked up" field="ucpUnitMarkedUpCost" value={run.part_cost.ucpUnitMarkedUpCost} />
      <Stat label="Total" field="ucpTotalMarkedUpCost" value={run.part_cost.ucpTotalMarkedUpCost} />
      <div className="save-box"><div><Button tone="secondary" onClick={() => saveWorksheet(false)}>Save</Button><Button onClick={() => saveWorksheet(true)}>Save current</Button></div>{saveState && <span>{saveState}</span>}</div>
      {returnCrumb && <Button className="use-cost-button" onClick={() => onReturnWithUnitCost(run.part_cost.ucpUnitMarkedUpCost)}>Use marked-up cost</Button>}
    </header>
    <nav className="tabs">
      <button className={view === "review" ? "active" : ""} onClick={() => setView("review")}>Review</button>
      <button className={view === "materials" ? "active" : ""} onClick={() => setView("materials")}>Materials</button>
      <button className={view === "operations" ? "active" : ""} onClick={() => setView("operations")}>Operations</button>
      <button className={view === "settings" ? "active" : ""} onClick={() => setView("settings")}>Settings</button>
    </nav>
    {view === "review" && <Review run={run} setView={setView} openLine={openLine} returnCrumb={returnCrumb} onReturnWithUnitCost={onReturnWithUnitCost} />}
    {view === "materials" && <LineList kind="material" rows={run.material_lines} originalRows={original.material_lines} onOpen={openLine} onAdd={() => addLine("material")} onDelete={removeRow} onResetLines={() => resetLines("material")} onRefreshDefaults={() => refreshDefaults("material")} canReset={lineMembershipChanged("material")} />}
    {view === "operations" && <LineList kind="operation" rows={run.operation_lines} originalRows={original.operation_lines} onOpen={openLine} onAdd={() => addLine("operation")} onDelete={removeRow} onResetLines={() => resetLines("operation")} onRefreshDefaults={() => refreshDefaults("operation")} canReset={lineMembershipChanged("operation")} />}
    {view === "settings" && <Settings part={run.part_cost} markupBreaks={markupBreaks} setMarkupBreaks={setMarkupBreaks} globalDefaults={globalDefaults} setGlobalDefaults={setGlobalDefaults} machineDefaults={machineDefaults} setMachineDefaults={setMachineDefaults} shift={shift} setShift={setShift} refreshAllDefaults={refreshAllDefaults} />}
    {view === "focus" && <FocusEditor kind={focus.kind} row={activeRow} original={originalRow} edited={edited} updateRow={updateRow} resetField={resetField} refreshDefaults={refreshDefaults} removeRow={removeRow} close={() => setView(focus.kind === "material" ? "materials" : "operations")} openPO={(kind, row) => setPoTarget({ kind, row, partId: run.part_cost.ucpPartID })} applyMaterialSuggestion={applyMaterialSuggestion} updateMachineDefault={updateMachineDefault} shift={shift} onCostMaterial={onCostMaterial} openMaterialHistory={openMaterialHistory} />}
    <POExplorer target={poTarget} onClose={() => setPoTarget(null)} onApply={applyPO} />
    <CostHistoryModal target={historyTarget} onClose={() => setHistoryTarget(null)} onUseUnitCost={useMaterialHistoryCost} onCostQuantity={(history) => { setHistoryTarget(null); onCostMaterial(historyTarget.row, history.ucpCostQuantity); }} onNewRun={() => { const row = historyTarget.row; setHistoryTarget(null); onCostMaterial(row); }} onSetCurrent={setHistoryCurrent} />
  </div>;
}

function App() {
  const [mode, setModeState] = useState("start"), [draft, setDraft] = useState({ part_id: "", revision_id: "", quantity: 10000 }), [run, setRun] = useState(null), [original, setOriginal] = useState(null), [loading, setLoading] = useState(false), [error, setError] = useState(""), [returnStack, setReturnStack] = useState([]), [startHistory, setStartHistory] = useState(null);
  function setMode(nextMode) {
    if (nextMode === "start") setReturnStack([]);
    setModeState(nextMode);
  }
  async function loadCostRun(partId, revisionId, quantity) {
    const settings = await readApiResponse(await fetch("/api/settings/defaults?part_id=" + encodeURIComponent(partId || "") + "&revision_id=" + encodeURIComponent(revisionId || "")));
    const markupBreaks = normalizeMarkupBreaks(settings.markup_breaks || []);
    const shift = buildShiftSettings(settings.global_defaults);
    const payload = await readApiResponse(await fetch("/api/costs/calculate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_id: partId, revision_id: revisionId || "", quantity: toNumber(quantity) || 1, markup_breaks: markupBreaks }) }));
    const operationLines = markRows(payload.operation_lines || [], "op", "erp");
    const globalDefaults = buildGlobalMachineDefaults(settings.global_defaults);
    return recalcRun({ part_cost: { ...partDefaults, ...(payload.part_cost || {}) }, material_lines: markRows(payload.material_lines || [], "mat", "erp"), operation_lines: operationLines, settings: { markupBreaks, globalDefaults, machineDefaults: buildSettingsMachineDefaults(settings.machine_defaults || [], operationLines), shift } }, markupBreaks, new Set(), shift);
  }
  async function loadSavedCostRun(partCostId) { const payload = await readApiResponse(await fetch("/api/costs/" + encodeURIComponent(partCostId))); const part = payload.part_cost || {}; const settings = await readApiResponse(await fetch("/api/settings/defaults?part_id=" + encodeURIComponent(part.ucpPartID || "") + "&revision_id=" + encodeURIComponent(part.ucpPartRevision || ""))); const markupBreaks = normalizeMarkupBreaks(settings.markup_breaks || []), shift = buildShiftSettings(settings.global_defaults), materialLines = markRows(payload.material_lines || [], "mat", "saved"), operationLines = markRows(payload.operation_lines || [], "op", "saved"), globalDefaults = buildGlobalMachineDefaults(settings.global_defaults); return recalcRun({ part_cost: { ...partDefaults, ...part }, material_lines: materialLines, operation_lines: operationLines, settings: { markupBreaks, globalDefaults, machineDefaults: buildSettingsMachineDefaults(settings.machine_defaults || [], operationLines), shift } }, markupBreaks, new Set(), shift); }
  async function openRun(normalized, nextDraft = draft) { setRun(normalized); setOriginal(JSON.parse(JSON.stringify(normalized))); setDraft(nextDraft); setReturnStack([]); setModeState("workspace"); }
  async function loadErp(forceNew = false) { try { setLoading(true); setError(""); if (!forceNew) { const history = await readApiResponse(await fetch("/api/costs/history?part_id=" + encodeURIComponent(draft.part_id || "") + "&revision_id=" + encodeURIComponent(draft.revision_id || ""))); if ((history.history || []).length) { setStartHistory({ kind: "start", partId: draft.part_id, revisionId: draft.revision_id || "", quantity: draft.quantity, rows: history.history }); return; } } const normalized = await loadCostRun(draft.part_id, draft.revision_id, draft.quantity); await openRun(normalized); } catch (err) { setError(err.message); } finally { setLoading(false); } }
  function startBlank() { const blank = recalcRun({ part_cost: { ...partDefaults, ucpPartID: draft.part_id, ucpPartRevision: draft.revision_id, ucpCostQuantity: toNumber(draft.quantity) || 1 }, material_lines: [], operation_lines: [], settings: { markupBreaks: defaultMarkupBreaks, globalDefaults: defaultGlobalMachineDefaults, machineDefaults: {}, shift: defaultShiftSettings } }); setRun(blank); setOriginal(JSON.parse(JSON.stringify(blank))); setReturnStack([]); setModeState("workspace"); }
  async function costMaterial(material, quantityOverride = null) {
    if (!material?.ucmMaterialID || !run) return;
    try {
      setLoading(true);
      setError("");
      const parent = { run, original, draft, label: run.part_cost.ucpPartID || "parent cost", materialLineId: material._id, materialId: material.ucmMaterialID };
      const quantity = toNumber(quantityOverride) || toNumber(material.ucmTotalQuantityRequired) || toNumber(material.ucmQtyPerAssembly) || 1;
      const normalized = await loadCostRun(material.ucmMaterialID, "", quantity);
      setReturnStack((stack) => [...stack, parent]);
      setDraft({ part_id: material.ucmMaterialID, revision_id: "", quantity });
      setRun(normalized);
      setOriginal(JSON.parse(JSON.stringify(normalized)));
      setModeState("workspace");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  function returnToParent() {
    setReturnStack((stack) => {
      const parent = stack[stack.length - 1];
      if (!parent) return stack;
      setRun(parent.run);
      setOriginal(parent.original);
      setDraft(parent.draft);
      setModeState("workspace");
      return stack.slice(0, -1);
    });
  }
  function returnWithUnitCost(unitCost) {
    setReturnStack((stack) => {
      const parent = stack[stack.length - 1];
      if (!parent) return stack;
      const markedUpUnitCost = toNumber(unitCost);
      const updatedRun = {
        ...parent.run,
        material_lines: (parent.run.material_lines || []).map((line) => line._id === parent.materialLineId ? {
          ...line,
          ucmUnitCost: markedUpUnitCost,
          ucmMaterialMarkup: 1,
          ucmCostSource: "manufactured_current",
          ucmIsPurchased: false,
          ucmLastPO: "",
          ucmLastPOCost: null,
          ucmLastPODate: new Date().toISOString(),
        } : line),
      };
      const normalized = recalcRun(updatedRun, parent.run.settings?.markupBreaks || defaultMarkupBreaks, new Set(parent.run.settings?.editedFromSave || []), parent.run.settings?.shift || defaultShiftSettings);
      setRun(normalized);
      setOriginal(parent.original);
      setDraft(parent.draft);
      setModeState("workspace");
      return stack.slice(0, -1);
    });
  }
  const returnCrumb = returnStack.length ? returnStack[returnStack.length - 1].label : "";
  return <>{mode === "workspace" && run ? <Workspace key={(run.part_cost.ucpPartID || "cost") + "-" + returnStack.length} run={run} setRun={setRun} original={original} setOriginal={setOriginal} setMode={setMode} draft={draft} onCostMaterial={costMaterial} returnCrumb={returnCrumb} onReturnToParent={returnToParent} onReturnWithUnitCost={returnWithUnitCost} /> : <StartScreen draft={draft} setDraft={setDraft} loadErp={loadErp} startBlank={startBlank} loading={loading} error={error} />}<CostHistoryModal target={startHistory} onClose={() => setStartHistory(null)} onUseRun={async (history) => { try { setLoading(true); const normalized = await loadSavedCostRun(history.ucpPartCostID); setStartHistory(null); await openRun(normalized, { part_id: history.ucpPartID, revision_id: history.ucpPartRevision || "", quantity: history.ucpCostQuantity }); } catch (err) { setError(err.message); } finally { setLoading(false); } }} onNewRun={async () => { try { setLoading(true); const target = startHistory; setStartHistory(null); setDraft((current) => ({ ...current, part_id: target.partId, revision_id: target.revisionId, quantity: target.quantity })); const normalized = await loadCostRun(target.partId, target.revisionId, target.quantity); await openRun(normalized, { part_id: target.partId, revision_id: target.revisionId, quantity: target.quantity }); } catch (err) { setError(err.message); } finally { setLoading(false); } }} onSetCurrent={async (history) => { await readApiResponse(await fetch("/api/costs/current", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_cost_id: history.ucpPartCostID }) })); setStartHistory((target) => target ? { ...target, rows: target.rows.map((row) => ({ ...row, ucpIsCurrent: row.ucpPartCostID === history.ucpPartCostID })) } : target); }} /></>;
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);


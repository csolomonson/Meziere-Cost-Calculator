import React, { useEffect, useMemo, useState } from "react";

import { readApiResponse } from "../../api/client.js";
import {
  defaultGlobalMachineDefaults,
  defaultMarkupBreaks,
  defaultShiftSettings,
  costBuckets,
  machineDefaultFields,
  machineDefaultKeys,
  markupDefaults,
  materialFields,
} from "../../domain/model.js";
import {
  numberOr,
  poInventoryUnit,
  poInventoryUnitCost,
  poPurchaseUnit,
  toNumber,
} from "../../domain/formatting.js";
import {
  activeMarkupBreak,
  buildMachineDefaults,
  keyFor,
  lineBreakdownFromUnit,
  manualMaterialCostOverride,
  machineKey,
  materialDefaultsToRow,
  newMaterial,
  newOperation,
  nextOperationSequence,
  normalizeMarkupBreaks,
  normalizeOptionalMarkupBreaks,
  partUnitBreakdown,
  recalcRun,
  setEditedForValue,
} from "../../domain/calculations.js";
import { partCostReportUrl } from "../../domain/reports.js";
import { NumberInput } from "../../components/inputs.jsx";
import { Button, RetailStat, Stat } from "../../components/ui.jsx";
import { CostHistoryModal, JobExplorer, POExplorer } from "../explorers/Explorers.jsx";
import { Settings } from "../settings/Settings.jsx";
import { FocusEditor } from "./FocusEditor.jsx";
import { LineList } from "./LineList.jsx";
import { Review } from "./Review.jsx";

export function Workspace({ run, setRun, original, setOriginal, setMode, draft, onCostMaterial, onOpenMaterialSourceCost, returnCrumb, onReturnToParent, onReturnWithUnitCost, landingFocus, onLandingHandled, initialView }) {
  const [view, setView] = useState(initialView || "review"), [focus, setFocus] = useState(null), [edited, setEdited] = useState(() => new Set()), [markupScope, setMarkupScope] = useState(() => run.settings?.markupBreakScope || "global"), [globalMarkupBreaks, setGlobalMarkupBreaks] = useState(() => normalizeMarkupBreaks(run.settings?.globalMarkupBreaks || run.settings?.markupBreaks)), [partMarkupBreaks, setPartMarkupBreaks] = useState(() => normalizeOptionalMarkupBreaks(run.settings?.partMarkupBreaks)), [markupBreaks, setMarkupBreaks] = useState(() => normalizeMarkupBreaks(run.settings?.markupBreaks)), [globalDefaults, setGlobalDefaults] = useState(() => run.settings?.globalDefaults || defaultGlobalMachineDefaults), [shift, setShift] = useState(() => run.settings?.shift || defaultShiftSettings), [machineDefaults, setMachineDefaults] = useState(() => run.settings?.machineDefaults || buildMachineDefaults(run.operation_lines)), [settingsFocusMachine, setSettingsFocusMachine] = useState(null), [poTarget, setPoTarget] = useState(null), [jobTarget, setJobTarget] = useState(null), [historyTarget, setHistoryTarget] = useState(null), [saveState, setSaveState] = useState("");
  const recalced = useMemo(() => recalcRun(run, markupBreaks, shift), [run, markupBreaks, shift]);
  useEffect(() => { setRun(recalced); }, [recalced.part_cost.ucpTotalMarkedUpCost]);
  useEffect(() => { setView(initialView || "review"); setFocus(null); }, [run.part_cost.ucpPartID]);
  useEffect(() => {
    if (!landingFocus) return;
    const rows = landingFocus.kind === "operation" ? run.operation_lines : run.material_lines;
    if ((rows || []).some((row) => row._id === landingFocus.id)) {
      setFocus({ kind: landingFocus.kind, id: landingFocus.id });
      setView("focus");
    }
    onLandingHandled?.();
  }, [landingFocus]);
  function commit(next) { const recalculated = recalcRun(next, markupBreaks, shift); setRun(recalculated); return recalculated; }
  function setQuantity(value) { const next = { ...run, part_cost: { ...run.part_cost, ucpCostQuantity: toNumber(value) || 1 } }; commit(next); }
  function openLine(kind, id) { const rows = kind === "material" ? run.material_lines : run.operation_lines; const row = rows.find((item) => item._id === id); if (row) { setFocus({ kind, id }); setView("focus"); } }
  function addLine(kind) { const row = kind === "material" ? newMaterial(run.part_cost.ucpCostQuantity) : newOperation(run.part_cost.ucpCostQuantity, nextOperationSequence(run.operation_lines)); const next = kind === "material" ? { ...run, material_lines: [...run.material_lines, row] } : { ...run, operation_lines: [...run.operation_lines, row] }; commit(next); setFocus({ kind, id: row._id }); setView("focus"); }
  function updateRow(kind, id, field, value) { const key = kind === "material" ? "material_lines" : "operation_lines"; const originalRows = kind === "material" ? original.material_lines : original.operation_lines; const rows = run[key].map((row) => row._id === id ? { ...row, [field]: value } : row); const changedRow = rows.find((row) => row._id === id); const originalRow = (originalRows || []).find((row) => row._id === id) || {}; const nextEdited = setEditedForValue(edited, id + "." + field, field, changedRow[field], originalRow[field]); setEdited(nextEdited); commit({ ...run, [key]: rows }); }
  function updateFields(kind, id, values) { const key = kind === "material" ? "material_lines" : "operation_lines"; const originalRows = kind === "material" ? original.material_lines : original.operation_lines; const rows = run[key].map((row) => row._id === id ? { ...row, ...values } : row); const changedRow = rows.find((row) => row._id === id); const originalRow = (originalRows || []).find((row) => row._id === id) || {}; const nextEdited = Object.keys(values).reduce((next, field) => setEditedForValue(next, id + "." + field, field, changedRow[field], originalRow[field]), new Set(edited)); setEdited(nextEdited); commit({ ...run, [key]: rows }); }
  const materialCostSourceFields = ["ucmUnitCost", "ucmCostSource", "ucmIsPurchased", "ucmManufacturedPartCostID", "ucmManufacturedPartCostIsCurrent", ...costBuckets.map((bucket) => bucket.materialRaw)];
  function materialCostValues(row) { return Object.fromEntries(materialCostSourceFields.map((field) => [field, row?.[field]])); }
  function overrideMaterialUnitCost(id, value) {
    const row = run.material_lines.find((item) => item._id === id);
    if (!row) return;
    updateFields("material", id, materialCostValues(manualMaterialCostOverride(row, value)));
  }
  function resetMaterialUnitCost(id) {
    const source = (original.material_lines || []).find((row) => row._id === id) || newMaterial(run.part_cost.ucpCostQuantity);
    updateFields("material", id, materialCostValues(source));
  }
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
    commit({ ...run, [key]: rows });
    if (focus?.kind === kind && !rows.some((row) => row._id === focus.id)) setFocus(null);
  }
  function materialDefaultValue(row, field) {
    if (field !== "ucmMaterialMarkup") return row[field];
    return numberOr(activeMarkupBreak(markupBreaks, run.part_cost.ucpCostQuantity).material, 1);
  }
  function operationDefaultValue(row, field) {
    const markup = markupDefaults.find(([, , markupField]) => markupField === field);
    if (markup) return numberOr(activeMarkupBreak(markupBreaks, run.part_cost.ucpCostQuantity)[markup[0]], 1);
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
  async function applyMaterialSuggestion(id, part) { const row = run.material_lines.find((item) => item._id === id); let defaults = {}; try { defaults = await readApiResponse(await fetch("/api/materials/default?part_id=" + encodeURIComponent(part.impPartID) + "&revision_id=" + encodeURIComponent(part.impPartRevisionID || ""))); } catch { defaults = {}; } const replacement = materialDefaultsToRow(row, part, defaults); const rows = run.material_lines.map((item) => item._id === id ? replacement : item); const originalRow = (original.material_lines || []).find((item) => item._id === id) || {}; let nextEdited = new Set(edited); materialFields.map(([field]) => field).forEach((field) => { nextEdited = setEditedForValue(nextEdited, id + "." + field, field, replacement[field], originalRow[field]); }); setEdited(nextEdited); commit({ ...run, material_lines: rows }); }
  async function updateMaterialPartCost(id) {
    const row = run.material_lines.find((item) => item._id === id);
    if (!row?.ucmMaterialID) return;
    try {
      const defaults = await readApiResponse(await fetch("/api/materials/default?part_id=" + encodeURIComponent(row.ucmMaterialID) + "&revision_id="));
      const replacement = materialDefaultsToRow(row, {
        impPartID: row.ucmMaterialID,
        impPartRevisionID: "",
        impPartShortDescription: row.ucmMaterialDescription,
      }, defaults);
      const rows = run.material_lines.map((item) => item._id === id ? replacement : item);
      const originalRow = (original.material_lines || []).find((item) => item._id === id) || {};
      const trackedFields = ["ucmUnitCost", "ucmCostSource", "ucmManufacturedPartCostID", "ucmLastPODate", "ucmRawCost", "ucmMarkedUpCost"];
      let nextEdited = new Set(edited);
      trackedFields.forEach((field) => { nextEdited = setEditedForValue(nextEdited, id + "." + field, field, replacement[field], originalRow[field]); });
      setEdited(nextEdited);
      commit({ ...run, material_lines: rows });
    } catch (err) {
      setSaveState(err.message || "Could not update material cost.");
    }
  }
  function updateMachineDefault(machine, field, value) { setMachineDefaults((current) => ({ ...current, [machine]: { ...(current[machine] || {}), [field]: toNumber(value) } })); }
  function openMachineSettings(row) {
    const machine = machineKey(row);
    setMachineDefaults((current) => current[machine] ? current : {
      ...current,
      [machine]: machineDefaultFields.reduce((defaults, [field]) => ({ ...defaults, [field]: toNumber(row[field] ?? globalDefaults[field]) }), {}),
    });
    setSettingsFocusMachine({ machine, tick: Date.now() });
    setFocus(null);
    setView("settings");
  }
  function openJobsForRow(row) { if (row.ucoPartOperationLineID !== undefined) { const partId = run.part_cost.ucpPartID || draft.part_id || ""; setJobTarget({ kind: "operation", row, partId, revisionId: run.part_cost.ucpPartRevision || draft.revision_id || "", operationSequence: row.ucoPartOperationLineID, title: (partId || "Current part") + " op " + (row.ucoPartOperationLineID || row.ucoOperationID || "") }); } else setJobTarget({ kind: "material", row }); }
  function applyPO(row) { if (!poTarget) return; const id = poTarget.row._id, cost = poTarget.kind === "material" ? poInventoryUnitCost(row) : toNumber(row.pmlPurchaseUnitCostBase ?? row.pmlExtendedCostBase ?? row.unit_cost), poId = row.pmlPurchaseOrderID || row.po_id || "", date = row.pmlDueDate || row.pmlCreatedDate || row.date || ""; if (poTarget.kind === "material") { const rows = run.material_lines.map((item) => item._id === id ? { ...item, ucmLastPO: poId, ucmLastPOCost: cost, ucmLastPODate: date, ucmUnitCost: cost, ucmPurchaseUnitCost: toNumber(row.pmlPurchaseUnitCostBase ?? cost), ucmMaterialPriceMode: "purchase", ucmIsPurchased: true, ucmCostSource: "purchase_order", ucmLastPOPurchaseUnitCost: row.pmlPurchaseUnitCostBase, ucmLastPOConversionFactor: row.pmlConversionFactor || 1, ucmLastPOPurchaseUnit: poPurchaseUnit(row), ucmLastPOInventoryUnit: poInventoryUnit(row) } : item); commit({ ...run, material_lines: rows }); } else { const rows = run.operation_lines.map((item) => item._id === id ? { ...item, ucoLastPO: poId, ucoLastPOCost: cost, ucoLastPODate: date, ucoExternalUnitCost: cost, ucoExternalJob: true } : item); commit({ ...run, operation_lines: rows }); } setPoTarget(null); }
  async function saveWorksheet(makeCurrent = false) { try { setSaveState("Saving"); const payload = await readApiResponse(await fetch("/api/costs/save-run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_cost: { ...run.part_cost, ucpIsCurrent: false }, operation_lines: run.operation_lines, material_lines: run.material_lines, make_current: makeCurrent }) })); const saved = { ...run, part_cost: { ...run.part_cost, ucpPartCostID: payload.part_cost_id, ucpIsCurrent: makeCurrent } }; setRun(saved); setOriginal(JSON.parse(JSON.stringify(saved))); setSaveState(makeCurrent ? "Saved current" : "Saved"); return saved; } catch (err) { setSaveState(err.message); return null; } }
  async function saveCurrentAndReturn() { const saved = await saveWorksheet(true); if (saved) onReturnWithUnitCost(saved.part_cost); }
  function exitWorksheet() { if (window.confirm("Leave this worksheet? Unsaved changes in this screen will be lost.")) setMode("start"); }
  async function openMaterialHistory(row) { try { const payload = await readApiResponse(await fetch("/api/costs/history?part_id=" + encodeURIComponent(row.ucmMaterialID || "") + "&revision_id=")); setHistoryTarget({ kind: "material", row, rows: payload.history || [] }); } catch (err) { setHistoryTarget({ kind: "material", row, rows: [], message: err.message || "Could not load cost history." }); } }
  function useMaterialHistoryCost(history) { if (!historyTarget?.row) return; const id = historyTarget.row._id; const isCurrent = Boolean(history.ucpIsCurrent); const rows = run.material_lines.map((item) => item._id === id ? { ...item, ...lineBreakdownFromUnit(item, partUnitBreakdown(history)), ucmUnitCost: toNumber(history.ucpUnitRawCost), ucmMaterialMarkup: numberOr(activeMarkupBreak(markupBreaks, run.part_cost.ucpCostQuantity).material, 1), ucmCostSource: isCurrent ? "manufactured_current" : "manufactured_history", ucmIsPurchased: false, ucmManufacturedPartCostID: history.ucpPartCostID, ucmManufacturedPartCostIsCurrent: isCurrent, ucmLastPO: "", ucmLastPOCost: null, ucmLastPODate: history.ucpDateCosted } : item); commit({ ...run, material_lines: rows }); setHistoryTarget(null); }
  async function setHistoryCurrent(history) { await readApiResponse(await fetch("/api/costs/current", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_cost_id: history.ucpPartCostID }) })); setHistoryTarget((target) => target ? { ...target, rows: target.rows.map((row) => ({ ...row, ucpIsCurrent: row.ucpPartCostID === history.ucpPartCostID })) } : target); }
  const activeRow = focus?.kind === "material" ? run.material_lines.find((row) => row._id === focus.id) : focus?.kind === "operation" ? run.operation_lines.find((row) => row._id === focus.id) : null;
  const originalRow = focus?.kind === "material" ? original.material_lines.find((row) => row._id === focus.id) : focus?.kind === "operation" ? original.operation_lines.find((row) => row._id === focus.id) : null;
  const internalReportUrl = partCostReportUrl(run.part_cost.ucpPartCostID, "internal");
  const customerReportUrl = partCostReportUrl(run.part_cost.ucpPartCostID, "customer");
  return <div className="workspace">
    <header className={"topbar " + (returnCrumb ? "with-return" : "")}>
      <Button tone="secondary" className="home-icon" onClick={exitWorksheet}>Exit</Button>
      <div className="part-title"><strong>{run.part_cost.ucpPartID || draft.part_id || "New cost"}</strong><span>{run.part_cost.ucpPartDescription || "Cost worksheet"}</span></div>
      <div className="qty-tools"><label className="qty-box"><span>Quantity</span><NumberInput value={run.part_cost.ucpCostQuantity} onChange={setQuantity} /></label><Button tone="secondary" onClick={() => setJobTarget({ kind: "part", partId: run.part_cost.ucpPartID || draft.part_id, revisionId: run.part_cost.ucpPartRevision || draft.revision_id || "", title: run.part_cost.ucpPartID || draft.part_id || "Current part" })} disabled={!(run.part_cost.ucpPartID || draft.part_id)}>Recent jobs</Button></div>
      <Stat label="Unit raw" field="ucpUnitRawCost" value={run.part_cost.ucpUnitRawCost} />
      <Stat label="Unit marked up" field="ucpUnitMarkedUpCost" value={run.part_cost.ucpUnitMarkedUpCost} />
      <RetailStat part={run.part_cost} />
      <Stat label="Total" field="ucpTotalMarkedUpCost" value={run.part_cost.ucpTotalMarkedUpCost} />
      <div className="save-box"><div>{internalReportUrl ? <><a className="button secondary" href={internalReportUrl} target="_blank" rel="noopener noreferrer" title="Open the detailed internal cost analysis from the last saved version">Internal PDF</a><a className="button secondary" href={customerReportUrl} target="_blank" rel="noopener noreferrer" title="Open the customer-safe cost summary from the last saved version">Customer PDF</a></> : <><Button tone="secondary" disabled title="Save this worksheet before opening its reports">Internal PDF</Button><Button tone="secondary" disabled title="Save this worksheet before opening its reports">Customer PDF</Button></>}{returnCrumb ? <><Button tone="secondary" onClick={onReturnToParent}>Back to parent</Button><Button onClick={saveCurrentAndReturn}>Save current & return</Button></> : <><Button tone="secondary" onClick={() => saveWorksheet(false)}>Save</Button><Button onClick={() => saveWorksheet(true)}>Save current</Button></>}</div>{saveState && <span>{saveState}</span>}</div>
    </header>
    <nav className="tabs">
      <button className={view === "review" ? "active" : ""} onClick={() => setView("review")}>Review</button>
      <button className={view === "materials" ? "active" : ""} onClick={() => setView("materials")}>Materials</button>
      <button className={view === "operations" ? "active" : ""} onClick={() => setView("operations")}>Operations</button>
      <button className={view === "settings" ? "active" : ""} onClick={() => setView("settings")}>Settings</button>
    </nav>
    {view === "review" && <Review run={run} setView={setView} openLine={openLine} returnCrumb={returnCrumb} />}
    {view === "materials" && <LineList kind="material" rows={run.material_lines} originalRows={original.material_lines} onOpen={openLine} onAdd={() => addLine("material")} onDelete={removeRow} onResetLines={() => resetLines("material")} onRefreshDefaults={() => refreshDefaults("material")} onUpdateMaterialCost={updateMaterialPartCost} canReset={lineMembershipChanged("material")} />}
    {view === "operations" && <LineList kind="operation" rows={run.operation_lines} originalRows={original.operation_lines} onOpen={openLine} onAdd={() => addLine("operation")} onDelete={removeRow} onResetLines={() => resetLines("operation")} onRefreshDefaults={() => refreshDefaults("operation")} canReset={lineMembershipChanged("operation")} />}
    {view === "settings" && <Settings part={run.part_cost} markupBreaks={markupBreaks} setMarkupBreaks={setMarkupBreaks} markupScope={markupScope} setMarkupScope={setMarkupScope} globalMarkupBreaks={globalMarkupBreaks} setGlobalMarkupBreaks={setGlobalMarkupBreaks} partMarkupBreaks={partMarkupBreaks} setPartMarkupBreaks={setPartMarkupBreaks} globalDefaults={globalDefaults} setGlobalDefaults={setGlobalDefaults} machineDefaults={machineDefaults} setMachineDefaults={setMachineDefaults} shift={shift} setShift={setShift} refreshAllDefaults={refreshAllDefaults} focusMachine={settingsFocusMachine} />}
    {view === "focus" && <FocusEditor key={activeRow?._id || "focus"} kind={focus.kind} row={activeRow} original={originalRow} edited={edited} updateRow={updateRow} updateFields={updateFields} resetField={resetField} overrideMaterialUnitCost={overrideMaterialUnitCost} resetMaterialUnitCost={resetMaterialUnitCost} refreshDefaults={refreshDefaults} removeRow={removeRow} close={() => setView(focus.kind === "material" ? "materials" : "operations")} openPO={(kind, row) => setPoTarget({ kind, row, partId: run.part_cost.ucpPartID })} openJobs={openJobsForRow} applyMaterialSuggestion={applyMaterialSuggestion} updateMachineDefault={updateMachineDefault} openMachineSettings={openMachineSettings} shift={shift} onCostMaterial={onCostMaterial} onOpenMaterialSourceCost={onOpenMaterialSourceCost} openMaterialHistory={openMaterialHistory} />}
    <POExplorer target={poTarget} onClose={() => setPoTarget(null)} onApply={applyPO} />
    <JobExplorer target={jobTarget} onClose={() => setJobTarget(null)} onCostQuantity={(job) => { const target = jobTarget; setJobTarget(null); if (target?.kind === "part") setQuantity(job.job_quantity); else if (target?.kind === "operation") { const values = {}; if (job.suggested_cycle_time_hours !== null && job.suggested_cycle_time_hours !== undefined) { values.ucoCycleTimeHours = toNumber(job.suggested_cycle_time_hours); values.ucoBatchResetTimeHours = 0; values.ucoBatchIdleTimeHours = 0; } if (job.suggested_setup_time_hours !== null && job.suggested_setup_time_hours !== undefined) values.ucoSetupTimeHours = toNumber(job.suggested_setup_time_hours); if (Object.keys(values).length) updateFields("operation", target.row._id, values); } else onCostMaterial(target.row, job.job_quantity); }} />
    <CostHistoryModal target={historyTarget} onClose={() => setHistoryTarget(null)} onUseUnitCost={useMaterialHistoryCost} onCostQuantity={(history) => { setHistoryTarget(null); onCostMaterial(historyTarget.row, history.ucpCostQuantity); }} onNewRun={() => { const row = historyTarget.row; setHistoryTarget(null); onCostMaterial(row); }} onSetCurrent={setHistoryCurrent} />
  </div>;
}

import React, { useEffect, useState } from "react";

import { readApiResponse } from "./api/client.js";
import {
  defaultGlobalMachineDefaults,
  defaultMarkupBreaks,
  defaultShiftSettings,
  partDefaults,
} from "./domain/model.js";
import { numberOr, toNumber } from "./domain/formatting.js";
import {
  activeMarkupBreak,
  buildGlobalMachineDefaults,
  buildSettingsMachineDefaults,
  buildShiftSettings,
  lineBreakdownFromUnit,
  markRows,
  markupSettingsFromPayload,
  partUnitBreakdown,
  recalcRun,
} from "./domain/calculations.js";
import { UserManagementModal } from "./features/admin/UserManagementModal.jsx";
import { CostHistoryModal } from "./features/explorers/Explorers.jsx";
import { StartScreen } from "./features/home/StartScreen.jsx";
import { UpdateNotice } from "./features/updates/UpdateNotice.jsx";
import { Workspace } from "./features/workspace/Workspace.jsx";

export function App() {
  const [mode, setModeState] = useState("start"), [draft, setDraft] = useState({ part_id: "", revision_id: "", quantity: 1 }), [run, setRun] = useState(null), [original, setOriginal] = useState(null), [loading, setLoading] = useState(false), [error, setError] = useState(""), [returnStack, setReturnStack] = useState([]), [landingFocus, setLandingFocus] = useState(null), [startHistory, setStartHistory] = useState(null), [workspaceInitialView, setWorkspaceInitialView] = useState(null), [session, setSession] = useState(window.COST_APP_SESSION || null), [showUserManagement, setShowUserManagement] = useState(false);
  useEffect(() => { if (session) return; let active = true; fetch("/api/session").then(readApiResponse).then((payload) => { if (active) setSession(payload); }).catch(() => {}); return () => { active = false; }; }, []);
  function setMode(nextMode) {
    if (nextMode === "start") { setReturnStack([]); setLandingFocus(null); setWorkspaceInitialView(null); }
    setModeState(nextMode);
  }
  async function loadCostRun(partId, revisionId, quantity) {
    const settings = await readApiResponse(await fetch("/api/settings/defaults?part_id=" + encodeURIComponent(partId || "") + "&revision_id=" + encodeURIComponent(revisionId || "")));
    const markupState = markupSettingsFromPayload(settings), markupBreaks = markupState.markupBreaks;
    const shift = buildShiftSettings(settings.global_defaults);
    const payload = await readApiResponse(await fetch("/api/costs/calculate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_id: partId, revision_id: revisionId || "", quantity: toNumber(quantity) || 1, markup_breaks: markupBreaks }) }));
    const operationLines = markRows(payload.operation_lines || [], "op", "erp");
    const globalDefaults = buildGlobalMachineDefaults(settings.global_defaults);
    return recalcRun({ part_cost: { ...partDefaults, ...(payload.part_cost || {}) }, material_lines: markRows(payload.material_lines || [], "mat", "erp"), operation_lines: operationLines, settings: { ...markupState, globalDefaults, machineDefaults: buildSettingsMachineDefaults(settings.machine_defaults || [], operationLines), shift } }, markupBreaks, shift);
  }
  async function loadSavedCostRun(partCostId) { const payload = await readApiResponse(await fetch("/api/costs/" + encodeURIComponent(partCostId))); const part = payload.part_cost || {}; const settings = await readApiResponse(await fetch("/api/settings/defaults?part_id=" + encodeURIComponent(part.ucpPartID || "") + "&revision_id=" + encodeURIComponent(part.ucpPartRevision || ""))); const markupState = markupSettingsFromPayload(settings), markupBreaks = markupState.markupBreaks, shift = buildShiftSettings(settings.global_defaults), materialLines = markRows(payload.material_lines || [], "mat", "saved"), operationLines = markRows(payload.operation_lines || [], "op", "saved"), globalDefaults = buildGlobalMachineDefaults(settings.global_defaults); return recalcRun({ part_cost: { ...partDefaults, ...part }, material_lines: materialLines, operation_lines: operationLines, settings: { ...markupState, globalDefaults, machineDefaults: buildSettingsMachineDefaults(settings.machine_defaults || [], operationLines), shift } }, markupBreaks, shift); }
  async function openRun(normalized, nextDraft = draft, initialView = null) { setWorkspaceInitialView(initialView); setRun(normalized); setOriginal(JSON.parse(JSON.stringify(normalized))); setDraft(nextDraft); setReturnStack([]); setModeState("workspace"); }
  async function loadErp(forceNew = false) { try { setLoading(true); setError(""); if (!forceNew) { const history = await readApiResponse(await fetch("/api/costs/history?part_id=" + encodeURIComponent(draft.part_id || "") + "&revision_id=" + encodeURIComponent(draft.revision_id || ""))); if ((history.history || []).length) { setStartHistory({ kind: "start", partId: draft.part_id, revisionId: draft.revision_id || "", quantity: draft.quantity, rows: history.history }); return; } } const normalized = await loadCostRun(draft.part_id, draft.revision_id, draft.quantity); await openRun(normalized); } catch (err) { setError(err.message); } finally { setLoading(false); } }
  function startBlank() { const blank = recalcRun({ part_cost: { ...partDefaults, ucpPartID: draft.part_id, ucpPartRevision: draft.revision_id, ucpCostQuantity: toNumber(draft.quantity) || 1 }, material_lines: [], operation_lines: [], settings: { markupBreaks: defaultMarkupBreaks, globalMarkupBreaks: defaultMarkupBreaks, partMarkupBreaks: [], markupBreakScope: "global", globalDefaults: defaultGlobalMachineDefaults, machineDefaults: {}, shift: defaultShiftSettings } }); setWorkspaceInitialView(null); setRun(blank); setOriginal(JSON.parse(JSON.stringify(blank))); setReturnStack([]); setModeState("workspace"); }
  async function openSettings() {
    try {
      setLoading(true);
      setError("");
      const settings = await readApiResponse(await fetch("/api/settings/defaults?part_id=&revision_id="));
      const markupState = markupSettingsFromPayload(settings), markupBreaks = markupState.markupBreaks, shift = buildShiftSettings(settings.global_defaults), globalDefaults = buildGlobalMachineDefaults(settings.global_defaults);
      const blank = recalcRun({ part_cost: { ...partDefaults, ucpPartID: "", ucpPartDescription: "Machine costing settings", ucpCostQuantity: toNumber(draft.quantity) || 1 }, material_lines: [], operation_lines: [], settings: { ...markupState, globalDefaults, machineDefaults: buildSettingsMachineDefaults(settings.machine_defaults || [], []), shift } }, markupBreaks, shift);
      await openRun(blank, { ...draft }, "settings");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  async function openSavedCost(row) {
    try {
      setLoading(true);
      setError("");
      const normalized = await loadSavedCostRun(row.ucpPartCostID);
      await openRun(normalized, { part_id: row.ucpPartID || "", revision_id: row.ucpPartRevision || "", quantity: row.ucpCostQuantity || 1 });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  async function costMaterial(material, quantityOverride = null) {
    if (!material?.ucmMaterialID || !run) return;
    try {
      setLoading(true);
      setError("");
      const parent = { run, original, draft, label: run.part_cost.ucpPartID || "parent cost", materialLineId: material._id, materialId: material.ucmMaterialID };
      let quantity = toNumber(quantityOverride);
      if (!quantity) {
        try {
          const jobs = await readApiResponse(await fetch("/api/jobs/recent?part_id=" + encodeURIComponent(material.ucmMaterialID || "") + "&revision_id="));
          quantity = toNumber((jobs.jobs || [])[0]?.job_quantity);
        } catch {
          quantity = 0;
        }
      }
      if (!quantity) quantity = toNumber(material.ucmTotalQuantityRequired) || toNumber(material.ucmQtyPerAssembly) || 1;
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
      setLandingFocus({ kind: "material", id: parent.materialLineId, tick: Date.now() });
      setModeState("workspace");
      return stack.slice(0, -1);
    });
  }
  function returnWithUnitCost(childCost) {
    setReturnStack((stack) => {
      const parent = stack[stack.length - 1];
      if (!parent) return stack;
      const rawUnitCost = toNumber(childCost?.ucpUnitRawCost ?? childCost);
      const materialMarkup = numberOr(activeMarkupBreak(parent.run.settings?.markupBreaks || defaultMarkupBreaks, parent.run.part_cost?.ucpCostQuantity).material, 1);
      const updatedRun = {
        ...parent.run,
        material_lines: (parent.run.material_lines || []).map((line) => line._id === parent.materialLineId ? {
          ...line,
          ...lineBreakdownFromUnit(line, partUnitBreakdown(childCost)),
          ucmUnitCost: rawUnitCost,
          ucmMaterialMarkup: materialMarkup,
          ucmCostSource: "manufactured_current",
          ucmIsPurchased: false,
          ucmManufacturedPartCostID: childCost?.ucpPartCostID ?? line.ucmManufacturedPartCostID,
          ucmManufacturedPartCostIsCurrent: Boolean(childCost?.ucpIsCurrent),
          ucmLastPO: "",
          ucmLastPOCost: null,
          ucmLastPODate: new Date().toISOString(),
        } : line),
      };
      const normalized = recalcRun(updatedRun, parent.run.settings?.markupBreaks || defaultMarkupBreaks, parent.run.settings?.shift || defaultShiftSettings);
      setRun(normalized);
      setOriginal(parent.original);
      setDraft(parent.draft);
      setLandingFocus({ kind: "material", id: parent.materialLineId, tick: Date.now() });
      setModeState("workspace");
      return stack.slice(0, -1);
    });
  }
  const returnCrumb = returnStack.length ? returnStack[returnStack.length - 1].label : "";
  return <><UpdateNotice />{mode === "workspace" && run ? <Workspace key={(run.part_cost.ucpPartCostID || run.part_cost.ucpPartID || "cost") + "-" + returnStack.length + "-" + (workspaceInitialView || "review")} run={run} setRun={setRun} original={original} setOriginal={setOriginal} setMode={setMode} draft={draft} onCostMaterial={costMaterial} returnCrumb={returnCrumb} onReturnToParent={returnToParent} onReturnWithUnitCost={returnWithUnitCost} landingFocus={landingFocus} onLandingHandled={() => setLandingFocus(null)} initialView={workspaceInitialView} /> : <StartScreen draft={draft} setDraft={setDraft} loadErp={loadErp} startBlank={startBlank} openSettings={openSettings} openSavedCost={openSavedCost} openUserManagement={() => setShowUserManagement(true)} isAdministrator={(session?.groups || []).includes("administrators")} loading={loading} error={error} />}{showUserManagement && <UserManagementModal onClose={() => setShowUserManagement(false)} />}<CostHistoryModal target={startHistory} onClose={() => setStartHistory(null)} onUseRun={async (history) => { try { setLoading(true); const normalized = await loadSavedCostRun(history.ucpPartCostID); setStartHistory(null); await openRun(normalized, { part_id: history.ucpPartID, revision_id: history.ucpPartRevision || "", quantity: history.ucpCostQuantity }); } catch (err) { setError(err.message); } finally { setLoading(false); } }} onNewRun={async () => { try { setLoading(true); const target = startHistory; setStartHistory(null); setDraft((current) => ({ ...current, part_id: target.partId, revision_id: target.revisionId, quantity: target.quantity })); const normalized = await loadCostRun(target.partId, target.revisionId, target.quantity); await openRun(normalized, { part_id: target.partId, revision_id: target.revisionId, quantity: target.quantity }); } catch (err) { setError(err.message); } finally { setLoading(false); } }} onSetCurrent={async (history) => { await readApiResponse(await fetch("/api/costs/current", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_cost_id: history.ucpPartCostID }) })); setStartHistory((target) => target ? { ...target, rows: target.rows.map((row) => ({ ...row, ucpIsCurrent: row.ucpPartCostID === history.ucpPartCostID })) } : target); }} /></>;
}


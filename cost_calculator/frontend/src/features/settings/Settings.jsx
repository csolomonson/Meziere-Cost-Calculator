import React, { useEffect, useRef, useState } from "react";

import { machineDefaultFields, markupDefaults } from "../../domain/model.js";
import { toNumber } from "../../domain/formatting.js";
import { normalizeMarkupBreaks } from "../../domain/calculations.js";
import { DefaultValueInput, Field, NumberInput } from "../../components/inputs.jsx";
import { Button } from "../../components/ui.jsx";
import { readApiResponse } from "../../api/client.js";

export function Settings({ part, markupBreaks, setMarkupBreaks, markupScope, setMarkupScope, globalMarkupBreaks, setGlobalMarkupBreaks, partMarkupBreaks, setPartMarkupBreaks, globalDefaults, setGlobalDefaults, machineDefaults, setMachineDefaults, shift, setShift, refreshAllDefaults, focusMachine }) {
  const [saveState, setSaveState] = useState("");
  const machineRefs = useRef({});
  const hasPart = Boolean(part?.ucpPartID), activeBreaks = markupScope === "part" ? partMarkupBreaks : globalMarkupBreaks;
  useEffect(() => {
    if (!focusMachine?.machine) return;
    const node = machineRefs.current[focusMachine.machine];
    if (!node) return;
    requestAnimationFrame(() => node.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" }));
  }, [focusMachine]);
  function commitBreaks(rows) {
    const normalized = normalizeMarkupBreaks(rows);
    if (markupScope === "part") setPartMarkupBreaks(normalized);
    else setGlobalMarkupBreaks(normalized);
    setMarkupBreaks(normalized);
  }
  function chooseMarkupScope(scope) {
    if (scope === "part") {
      const rows = partMarkupBreaks.length ? normalizeMarkupBreaks(partMarkupBreaks) : normalizeMarkupBreaks(globalMarkupBreaks);
      setMarkupScope("part");
      setPartMarkupBreaks(rows);
      setMarkupBreaks(rows);
      return;
    }
    const rows = normalizeMarkupBreaks(globalMarkupBreaks);
    setMarkupScope("global");
    setMarkupBreaks(rows);
  }
  function updateBreak(index, field, value) { commitBreaks(activeBreaks.map((row, i) => i === index ? { ...row, [field]: toNumber(value) } : row)); }
  function removeBreak(index) { commitBreaks(activeBreaks.filter((_, i) => i !== index)); }
  function addBreak() { const lastQty = activeBreaks.reduce((max, row) => Math.max(max, toNumber(row.breakQty)), 0); commitBreaks([...activeBreaks, { breakQty: lastQty ? lastQty * 10 : 1, material: 1, labor: 1, machine: 1, external: 1, additional: 1 }]); }
  function updateGlobal(field, value) { setGlobalDefaults((current) => ({ ...current, [field]: toNumber(value) })); }
  function updateMachine(machine, field, value) { setMachineDefaults((current) => ({ ...current, [machine]: { ...(current[machine] || {}), [field]: toNumber(value) } })); }
  async function saveSettings() { try { setSaveState("Saving"); await readApiResponse(await fetch("/api/settings/defaults", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ part_id: part?.ucpPartID || null, revision_id: part?.ucpPartRevision || "", markup_breaks: normalizeMarkupBreaks(markupBreaks), global_markup_breaks: normalizeMarkupBreaks(globalMarkupBreaks), part_markup_breaks: markupScope === "part" ? normalizeMarkupBreaks(partMarkupBreaks) : [], markup_break_scope: markupScope, global_defaults: globalDefaults, machine_defaults: machineDefaults, shift_settings: shift }) })); setSaveState("Saved"); } catch (err) { setSaveState(err.message); } }
  const sortedBreaks = normalizeMarkupBreaks(activeBreaks);
  return <div className="page-grid"><section className="panel span-2"><div className="panel-title"><div><span className="eyebrow">Part markup</span><h2>Quantity breaks</h2></div><div className="settings-actions"><Button tone={markupScope === "global" ? "primary" : "secondary"} onClick={() => chooseMarkupScope("global")}>Global defaults</Button><Button tone={markupScope === "part" ? "primary" : "secondary"} onClick={() => chooseMarkupScope("part")} disabled={!hasPart}>Part override</Button><Button tone="secondary" onClick={refreshAllDefaults}>Refresh all lines</Button><Button tone="secondary" onClick={addBreak}>Add break</Button><Button onClick={saveSettings}>Save settings</Button>{saveState && <span>{saveState}</span>}</div></div><div className="settings-table"><div className="settings-row head"><b>Quantity starts at</b>{markupDefaults.map(([key, label]) => <b key={key}>{label}</b>)}<b></b></div>{sortedBreaks.map((row, index) => <div className="settings-row" key={index}><NumberInput value={row.breakQty} onChange={(value) => updateBreak(index, "breakQty", value)} />{markupDefaults.map(([key]) => <NumberInput key={key} value={row[key]} onChange={(value) => updateBreak(index, key, value)} />)}<Button tone="danger" onClick={() => removeBreak(index)}>Remove</Button></div>)}</div></section><section className="panel"><div className="panel-title"><h2>Global cost defaults</h2></div><div className="settings-mini">{machineDefaultFields.map(([field, label]) => <Field key={field} label={label} field={field} value={globalDefaults[field] ?? 0} onChange={(value) => updateGlobal(field, value)} />)}</div></section><section className="panel"><div className="panel-title"><h2>Shift calendar</h2></div><div className="settings-mini"><Field label="First shift starts" field="firstShiftStart" value={shift.firstShiftStart} onChange={(value) => setShift((s) => ({ ...s, firstShiftStart: value }))} /><Field label="First shift ends" field="firstShiftEnd" value={shift.firstShiftEnd} onChange={(value) => setShift((s) => ({ ...s, firstShiftEnd: value }))} /><Field label="After-hours idle discount" field="afterHoursIdleMultiplier" value={shift.afterHoursIdleMultiplier} onChange={(value) => setShift((s) => ({ ...s, afterHoursIdleMultiplier: toNumber(value) }))} /></div></section><section className="panel span-2"><div className="panel-title"><h2>Machine defaults</h2></div><div className="machine-table"><div className="machine-row head"><b>Machine</b>{machineDefaultFields.map(([, label]) => <b key={label}>{label}</b>)}</div>{Object.keys(machineDefaults).sort().map((machine) => <div className={"machine-row " + (focusMachine?.machine === machine ? "target" : "")} key={machine} ref={(node) => { if (node) machineRefs.current[machine] = node; }}><strong>{machine}</strong>{machineDefaultFields.map(([field]) => <DefaultValueInput key={field} field={field} value={machineDefaults[machine]?.[field] ?? 0} onChange={(value) => updateMachine(machine, field, value)} />)}</div>)}</div></section></div>;
}



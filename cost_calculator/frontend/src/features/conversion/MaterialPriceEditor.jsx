import React, { useEffect, useRef, useState } from "react";

import { readApiResponse } from "../../api/client.js";
import {
  formatValue,
  materialConversionFactor,
  materialInventoryUnit,
  materialPurchaseUnit,
  materialPurchaseUnitCost,
  numberOr,
  toNumber,
} from "../../domain/formatting.js";
import { Button, Stat } from "../../components/ui.jsx";
import { NumberInput } from "../../components/inputs.jsx";

export function MaterialPriceEditor({ row, edited, onChange, onValidityChange }) {
  const [calculatorOpen, setCalculatorOpen] = useState(false);
  const factor = materialConversionFactor(row);
  const purchaseUnit = materialPurchaseUnit(row), inventoryUnit = materialInventoryUnit(row);
  const mode = row.ucmMaterialPriceMode || "purchase";
  const value = mode === "inventory" ? toNumber(row.ucmUnitCost) : materialPurchaseUnitCost(row);
  const unit = mode === "inventory" ? inventoryUnit : purchaseUnit;
  function setPurchase(value) { onChange({ ucmMaterialPriceMode: "purchase", ucmPurchaseUnitCost: toNumber(value), ucmUnitCost: toNumber(value) * factor }); }
  function setInventory(value) { onChange({ ucmMaterialPriceMode: "inventory", ucmUnitCost: toNumber(value), ucmPurchaseUnitCost: factor === 0 ? 0 : toNumber(value) / factor }); }
  function change(value) { mode === "inventory" ? setInventory(value) : setPurchase(value); }
  function toggle() { mode === "inventory" ? setPurchase(materialPurchaseUnitCost(row)) : setInventory(row.ucmUnitCost); }
  function changeFactor(value) { const nextFactor = toNumber(value); const purchaseCost = mode === "inventory" ? nextFactor === 0 ? 0 : toNumber(row.ucmUnitCost) / nextFactor : materialPurchaseUnitCost(row); onChange({ ucmLastPOConversionFactor: nextFactor, ucmPurchaseUnitCost: purchaseCost, ucmUnitCost: mode === "inventory" ? toNumber(row.ucmUnitCost) : purchaseCost * nextFactor }); }
  function changePurchaseUnit(value) { onChange({ ucmLastPOPurchaseUnit: value }); }
  function changeInventoryUnit(value) { onChange({ ucmLastPOInventoryUnit: value }); }
  return <div className={"field material-price-field " + (edited ? "changed" : "")}>
    <span>Unit material cost<span className="price-conversion-inline">{mode === "purchase" && factor !== 1 ? "x " + formatValue("pmlConversionFactor", factor) + " to " + inventoryUnit : "no conversion"}</span></span>
    <div className="unit-input"><NumberInput data-field={mode === "inventory" ? "ucmUnitCost" : "ucmPurchaseUnitCost"} value={value} onChange={change} onValidityChange={(valid) => onValidityChange?.("ucmUnitCost", valid)} /><button type="button" onClick={toggle}>{unit}</button></div>
    <div className="conversion-overrides">
      <label><span>Factor</span><div className="factor-input"><NumberInput data-field="ucmLastPOConversionFactor" value={factor} onChange={changeFactor} onValidityChange={(valid) => onValidityChange?.("ucmLastPOConversionFactor", valid)} /><button type="button" onClick={() => setCalculatorOpen(true)}>Calc</button></div></label>
      <label><span>Purchase unit</span><input data-field="ucmLastPOPurchaseUnit" value={purchaseUnit} onChange={(event) => changePurchaseUnit(event.target.value)} /></label>
      <label><span>Inventory unit</span><input data-field="ucmLastPOInventoryUnit" value={inventoryUnit} onChange={(event) => changeInventoryUnit(event.target.value)} /></label>
    </div>
    <ConversionCalculatorModal open={calculatorOpen} initialFactor={factor} onClose={() => setCalculatorOpen(false)} onApply={(value) => { changeFactor(value); setCalculatorOpen(false); }} />
  </div>;
}

export function ConversionCalculatorModal({ open, initialFactor, onClose, onApply }) {
  const [config, setConfig] = useState(null), [mode, setMode] = useState(""), [preset, setPreset] = useState(""), [multiplier, setMultiplier] = useState(0), [modeValues, setModeValues] = useState({}), [calculation, setCalculation] = useState({ area: 0, factor: 0 }), [error, setError] = useState("");
  const calculationRequestRef = useRef(0);
  useEffect(() => {
    if (!open) return;
    let active = true;
    (async () => {
      try {
        setError("");
        const payload = await readApiResponse(await fetch("/api/conversion-calculator"));
        if (!active) return;
        const nextMode = payload.modes?.some((item) => item.key === mode) ? mode : payload.default_mode || payload.modes?.[0]?.key || "";
        const nextPreset = payload.presets?.some((item) => item.key === preset) ? preset : payload.default_preset || payload.presets?.[0]?.key || "";
        const presetValue = payload.presets?.find((item) => item.key === nextPreset)?.multiplier;
        setConfig(payload);
        setMode(nextMode);
        setPreset(nextPreset);
        setMultiplier(presetValue === null || presetValue === undefined ? numberOr(initialFactor, 0) : presetValue);
        setModeValues((current) => Object.fromEntries((payload.modes || []).map((item) => [item.key, Object.fromEntries((item.fields || []).map((field) => [field.key, current[item.key]?.[field.key] ?? field.default ?? 0]))])));
      } catch (err) {
        if (active) setError(err.message || "Could not load conversion modes.");
      }
    })();
    return () => { active = false; };
  }, [open]);
  const activeValues = modeValues[mode] || {};
  useEffect(() => {
    if (!open || !config || !mode) return;
    let active = true;
    const requestId = ++calculationRequestRef.current;
    const timer = setTimeout(async () => {
      try {
        const payload = await readApiResponse(await fetch("/api/conversion-calculator/calculate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode, values: activeValues, multiplier }) }));
        if (active && requestId === calculationRequestRef.current) { setCalculation(payload); setError(""); }
      } catch (err) {
        if (active && requestId === calculationRequestRef.current) setError(err.message || "Could not calculate the conversion factor.");
      }
    }, 80);
    return () => { active = false; clearTimeout(timer); };
  }, [open, config, mode, modeValues, multiplier]);
  if (!open) return null;
  const activeMode = config?.modes?.find((item) => item.key === mode);
  function choosePreset(value) { const selected = config?.presets?.find((item) => item.key === value); setPreset(value); if (selected?.multiplier !== null && selected?.multiplier !== undefined) setMultiplier(selected.multiplier); }
  function changeModeValue(field, value) { setModeValues((current) => ({ ...current, [mode]: { ...(current[mode] || {}), [field]: value } })); }
  return <div className="modal-backdrop"><section className="calculator-modal"><header><div><span className="eyebrow">Conversion</span><h2>Factor calculator</h2></div><Button tone="secondary" onClick={onClose}>Close</Button></header><div className="calculator-body">{config ? <><label className="field"><span>Mode</span><select data-field="conversion-mode" value={mode} onChange={(event) => setMode(event.target.value)}>{config.modes.map((item) => <option value={item.key} key={item.key}>{item.label}</option>)}</select></label><div className="calculator-grid">{(activeMode?.fields || []).map((field) => <label className="field" key={field.key}><span>{field.label}</span><NumberInput data-field={"conversion-" + mode + "-" + field.key} value={activeValues[field.key] ?? field.default ?? 0} onChange={(value) => changeModeValue(field.key, value)} /></label>)}</div><div className="calculator-grid"><label className="field"><span>Material</span><select data-field="conversion-preset" value={preset} onChange={(event) => choosePreset(event.target.value)}>{config.presets.map((item) => <option value={item.key} key={item.key}>{item.label}</option>)}</select></label><label className="field"><span>Multiplier</span><NumberInput data-field="conversion-multiplier" value={multiplier} onChange={(value) => { setPreset("custom"); setMultiplier(value); }} /></label></div><div className="stat-grid compact"><Stat label="Area" value={calculation.area} /><Stat label="Factor" value={calculation.factor} /></div></> : !error && <div className="middle-note">Loading conversion modes...</div>}{error && <div className="error-box">{error}</div>}<div className="history-actions"><Button onClick={() => onApply(calculation.factor)} disabled={!config || Boolean(error)}>Use factor</Button><Button tone="secondary" onClick={onClose}>Cancel</Button></div></div></section></div>;
}



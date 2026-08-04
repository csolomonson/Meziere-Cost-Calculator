import React, { useEffect, useRef, useState } from "react";

import {
  durationFields,
  machineDefaultKeys,
  materialFields,
  numericFields,
  opCommonFields,
  opExternalFields,
  opInternalFields,
} from "../../domain/model.js";
import { formatDuration, toNumber } from "../../domain/formatting.js";
import { groupedFields, keyFor, machineKey, materialSource, materialUsesCurrentCostRun, operationTiming, processTimingFields } from "../../domain/calculations.js";
import { AutocompleteField } from "../../components/AutocompleteField.jsx";
import { Field } from "../../components/inputs.jsx";
import { Badge, Button, Stat } from "../../components/ui.jsx";
import { MaterialPriceEditor } from "../conversion/MaterialPriceEditor.jsx";
import { OperationCalendar } from "./OperationCalendar.jsx";

export function FocusEditor({ kind, row, original, edited, updateRow, updateFields, resetField, overrideMaterialUnitCost, resetMaterialUnitCost, refreshDefaults, removeRow, close, openPO, openJobs, applyMaterialSuggestion, updateMachineDefault, openMachineSettings, shift, onCostMaterial, onOpenMaterialSourceCost, openMaterialHistory }) {
  const [invalidNumericFields, setInvalidNumericFields] = useState(() => new Set());
  const lastValidCalculatedRow = useRef(row);
  const isMaterial = kind === "material";
  const calculationsPaused = invalidNumericFields.size > 0;
  useEffect(() => {
    if (row && !calculationsPaused) lastValidCalculatedRow.current = row;
  }, [row, calculationsPaused]);
  if (!row) return null;
  const calculatedRow = calculationsPaused ? (lastValidCalculatedRow.current || row) : row;
  function setNumericValidity(field, valid) {
    setInvalidNumericFields((current) => {
      const next = new Set(current);
      if (valid) next.delete(field);
      else next.add(field);
      return next;
    });
  }
  const changed = (field) => edited.has(keyFor(row, field));
  const commonProps = (field) => ({ edited: changed(field), onReset: () => resetField(kind, row._id, field) });
  function set(field, value) { updateRow(kind, row._id, field, numericFields.has(field) && !durationFields.has(field) ? toNumber(value) : value); }
  const fields = isMaterial ? materialFields : [...opCommonFields, ...(row.ucoExternalJob ? opExternalFields : opInternalFields)];
  const fieldMap = new Map(fields.map(([field, label, type]) => [field, { label, type }]));
  function renderField(field) {
    if (isMaterial && field === "ucmMaterialID") return null;
    if (isMaterial && field === "ucmUnitCost" && row.ucmIsPurchased) return <MaterialPriceEditor key={field} row={row} edited={changed("ucmUnitCost")} onChange={(values) => updateFields(kind, row._id, values)} onValidityChange={setNumericValidity} />;
    if (isMaterial && field === "ucmUnitCost") return <Field key={field} field={field} label="Unit material cost" value={row[field]} onChange={(value) => overrideMaterialUnitCost(row._id, value)} onValidityChange={(valid) => setNumericValidity(field, valid)} edited={changed(field)} onReset={() => resetMaterialUnitCost(row._id)} />;
    if (!isMaterial && field === "ucoOperationID") return null;
    if (!isMaterial && field === "ucoWorkCenterID") return null;
    const meta = fieldMap.get(field);
    if (!meta) return null;
    return <Field key={field} field={field} label={meta.label} value={row[field]} type={meta.type} onChange={(value) => set(field, value)} onValidityChange={(valid) => setNumericValidity(field, valid)} defaultSourced={!isMaterial && machineDefaultKeys.has(field) && !changed(field)} onDefaultEdit={!isMaterial && machineDefaultKeys.has(field) ? (f, value) => updateMachineDefault(machineKey(row), f, value) : null} {...commonProps(field)} />;
  }
  return <main className="focus-screen">
    <section className="focus-head">
      <Button tone="secondary" onClick={close}>Save and exit</Button>
      <div><span className="eyebrow">{isMaterial ? "Material" : "Operation"}</span><h2>{isMaterial ? row.ucmMaterialID || "New material" : row.ucoOperationDescription || row.ucoOperationID || "New operation"}</h2></div>
      <div className="focus-actions"><Button tone="secondary" onClick={() => refreshDefaults(kind, row._id)}>Refresh defaults</Button>{isMaterial && <Button tone="secondary" onClick={() => openMaterialHistory(row)} disabled={!row.ucmMaterialID}>Cost history</Button>}{isMaterial && <Button tone="secondary" onClick={() => openJobs(row)} disabled={!row.ucmMaterialID}>Recent jobs</Button>}{!isMaterial && <Button tone="secondary" onClick={() => openJobs(row)} disabled={!row.ucoPartOperationLineID}>Operation jobs</Button>}{isMaterial && materialUsesCurrentCostRun(row) && <Button tone="secondary" onClick={() => onOpenMaterialSourceCost(row)}>Open source run</Button>}{isMaterial && <Button tone="secondary" onClick={() => onCostMaterial(row)} disabled={!row.ucmMaterialID}>New child cost</Button>}{(isMaterial && row.ucmIsPurchased) || (!isMaterial && row.ucoExternalJob) ? <Button tone="secondary" onClick={() => openPO(kind, row)}>PO explorer</Button> : null}<Button tone="danger" onClick={() => removeRow(kind, row._id)}>Delete</Button></div>
    </section>
    <section className="focus-layout">
      <div className="edit-panel grouped">
        <div className="source-strip"><span className="source-label">{isMaterial ? "Unit cost source" : "Operation source"}</span>{isMaterial ? <Badge tone={materialSource(row).tone}>{materialSource(row).label}</Badge> : <Badge tone={row.ucoExternalJob ? "amber" : "blue"}>{row.ucoExternalJob ? "External operation" : "Internal operation"}</Badge>}{isMaterial && row.ucmManufacturedPartCostID && <span className="source-reference">Run #{row.ucmManufacturedPartCostID}{materialUsesCurrentCostRun(row) ? " (current)" : ""}</span>}<Badge>{row._source === "erp" ? "ERP line" : row._source === "saved" ? "Saved line" : "Manually added line"}</Badge></div>
        {isMaterial && <AutocompleteField label="Material part number" field="ucmMaterialID" value={row.ucmMaterialID} edited={changed("ucmMaterialID")} searchUrl="/api/parts/search?q=" optionValue={(part) => part.impPartID} renderOption={(part) => <><strong>{part.impPartID}</strong><span>{part.impShortDescription || part.impPartShortDescription || "No description"}</span></>} onChange={(value) => set("ucmMaterialID", value.toUpperCase())} onSelect={(part) => applyMaterialSuggestion(row._id, part)} />}
        {!isMaterial && <div className="operation-pickers">
          <AutocompleteField
            label="Work center"
            field="ucoWorkCenterID"
            value={row.ucoWorkCenterID}
            edited={changed("ucoWorkCenterID")}
            searchUrl="/api/work-centers/search?q="
            resultKey="work_centers"
            minChars={1}
            optionValue={(wc) => wc.xawWorkCenterID}
            renderOption={(wc) => <><strong>{wc.xawWorkCenterID}</strong><span>{wc.xawDescription || "No description"}</span></>}
            onChange={(value) => set("ucoWorkCenterID", value.toUpperCase())}
            onSelect={(wc) => updateFields(kind, row._id, {
              ucoWorkCenterID: wc.xawWorkCenterID || row.ucoWorkCenterID,
              ucoOperationID: "",
              ucoOperationDescription: "",
              ucoSetupTimeHours: toNumber(wc.xawSetupHours ?? row.ucoSetupTimeHours),
              ucoCycleTimeHours: toNumber(wc.xawProductionStandard) > 0 ? toNumber(wc.xawProductionStandard) / 60 : toNumber(row.ucoCycleTimeHours),
            })}
          />
          <AutocompleteField
            label="Process"
            field="ucoOperationID"
            value={row.ucoOperationID}
            edited={changed("ucoOperationID")}
            searchUrl={"/api/processes/search?work_center_id=" + encodeURIComponent(row.ucoWorkCenterID || "") + "&q="}
            resultKey="processes"
            minChars={row.ucoWorkCenterID ? 0 : 1}
            optionValue={(process) => process.xaoOperationID}
            renderOption={(process) => <><strong>{process.xaoOperationID}</strong><span>{process.xaoDescription || "No description"}</span></>}
            onChange={(value) => set("ucoOperationID", value.toUpperCase())}
            onSelect={(process) => updateFields(kind, row._id, {
              ucoOperationID: process.xaoOperationID || row.ucoOperationID,
              ucoOperationDescription: process.xaoDescription || row.ucoOperationDescription,
              ...processTimingFields(process, row),
            })}
          />
        </div>}
        {groupedFields(kind, row).map((group) => <section className="field-group" key={group.title}><div className="group-heading"><div><h3>{group.title}</h3><p>{group.note}</p></div>{!isMaterial && group.title === "Rates and markup" && <Button tone="secondary" onClick={() => openMachineSettings(row)} disabled={!row.ucoWorkCenterID}>Machine settings</Button>}</div><div className="group-fields">{group.fields.map(renderField)}</div></section>)}
      </div>
      <div className={"calc-panel " + (calculationsPaused ? "calculations-paused" : "")}>
        <h3>Calculated now</h3>
        {calculationsPaused && <div className="calculation-paused-note">Enter a number to resume live calculations.</div>}
        {isMaterial ? <>
          <Stat label="Required quantity" field="ucmTotalQuantityRequired" value={calculatedRow.ucmTotalQuantityRequired} />
          <Stat label="Retail unit" field="ucmRetailUnitPrice" value={calculatedRow.ucmRetailUnitPrice} />
          {calculatedRow.ucmLastPOConversionFactor !== null && calculatedRow.ucmLastPOConversionFactor !== undefined && toNumber(calculatedRow.ucmLastPOConversionFactor) !== 1 && <Stat label="PO conversion" value={calculatedRow.ucmLastPOConversionFactor} />}
          <Stat label="Wasted quantity" field="ucmWasteQuantity" value={calculatedRow.ucmWasteQuantity} />
          <Stat label="Raw cost" field="ucmRawCost" value={calculatedRow.ucmRawCost} />
          <Stat label="Marked up cost" field="ucmMarkedUpCost" value={calculatedRow.ucmMarkedUpCost} />
        </> : <>
          <Stat label="Runtime" value={formatDuration(operationTiming(calculatedRow).runtime)} />
          <Stat label="Labor" field="ucoLaborMarkedUpCost" value={calculatedRow.ucoLaborMarkedUpCost} />
          <Stat label="Machine" field="ucoMachineMarkedUpCost" value={calculatedRow.ucoMachineMarkedUpCost} />
          <Stat label="External" field="ucoExternalOperationMarkedUpCost" value={calculatedRow.ucoExternalOperationMarkedUpCost} />
          <Stat label="Line total" field="ucoLineMarkedUpCost" value={calculatedRow.ucoLineMarkedUpCost} />
          <OperationCalendar row={calculatedRow} shift={shift} onChange={set} />
        </>}
        <details><summary>Original ERP/default values</summary><pre>{JSON.stringify(original || {}, null, 2)}</pre></details>
      </div>
    </section>
  </main>;
}


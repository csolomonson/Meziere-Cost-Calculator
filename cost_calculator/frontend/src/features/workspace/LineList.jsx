import React from "react";

import { formatDuration, formatValue } from "../../domain/formatting.js";
import {
  lineMarkedUnitCost,
  lineRawUnitCost,
  materialNeedsPartCostUpdate,
  materialSource,
  operationTiming,
} from "../../domain/calculations.js";
import { Badge, Button, CostTrend } from "../../components/ui.jsx";

export function LineList({ kind, rows, originalRows = [], onOpen, onAdd, onDelete, onResetLines, onRefreshDefaults, onUpdateMaterialCost, canReset }) {
  const isMaterial = kind === "material";
  const originalById = new Map((originalRows || []).map((row) => [row._id, row]));
  function rowKeyOpen(event, row) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(kind, row._id);
    }
  }
  return <section className="panel full-panel"><div className="panel-title"><div><span className="eyebrow">{isMaterial ? "Materials" : "Operations"}</span><h2>{isMaterial ? "Material costs" : "Operation costs"}</h2></div><div className="focus-actions"><Button tone="secondary" onClick={onRefreshDefaults}>Refresh defaults</Button><Button tone="secondary" onClick={onResetLines} disabled={!canReset}>Reset lines</Button><Button onClick={onAdd}>Add {isMaterial ? "material" : "operation"}</Button></div></div><div className={`data-table ${isMaterial ? "material-table" : "operation-table"}`}><div className="table-head">{isMaterial ? ["Part", "Backflush", "Type", "Description", "Qty/part", "Raw unit", "Marked unit", "Total marked", ""].map((h) => <b key={h}>{h}</b>) : ["Seq", "Machine", "Description", "Type", "Runtime", "Raw unit", "Marked unit", "Total marked", ""].map((h) => <b key={h}>{h}</b>)}</div>{rows.map((row) => { const original = originalById.get(row._id) || {}; return isMaterial ? <div className="table-row" tabIndex="0" key={row._id} onClick={() => onOpen("material", row._id)} onKeyDown={(event) => rowKeyOpen(event, row)}><strong>{row.ucmMaterialID || "New material"}</strong><Badge tone={row.ucmBackflush === false || row.ucmBackflush === 0 ? "neutral" : "green"}>{row.ucmBackflush === false || row.ucmBackflush === 0 ? "No" : "Yes"}</Badge><Badge tone={materialSource(row).tone}>{materialSource(row).label}</Badge><span>{row.ucmMaterialDescription || "-"}</span><span>{formatValue("ucmQtyPerAssembly", row.ucmQtyPerAssembly)}</span><CostTrend field="ucmRawCost" value={lineRawUnitCost(row)} originalValue={original._id ? lineRawUnitCost(original) : undefined} /><CostTrend field="ucmMarkedUpCost" value={lineMarkedUnitCost(row)} originalValue={original._id ? lineMarkedUnitCost(original) : undefined} /><strong>{formatValue("ucmMarkedUpCost", row.ucmMarkedUpCost)}</strong><span className="row-actions">{materialNeedsPartCostUpdate(row) && <button type="button" className="update" onClick={(event) => { event.stopPropagation(); onUpdateMaterialCost?.(row._id); }}>Update</button>}<button type="button" onClick={(event) => { event.stopPropagation(); onDelete("material", row._id); }}>Delete</button></span></div> : <div className="table-row op-row" tabIndex="0" key={row._id} onClick={() => onOpen("operation", row._id)} onKeyDown={(event) => rowKeyOpen(event, row)}><strong>{row.ucoPartOperationLineID || row.ucoOperationID || "New"}</strong><span>{row.ucoWorkCenterID || "-"}</span><span>{row.ucoOperationDescription || "-"}</span><Badge tone={row.ucoExternalJob ? "amber" : "blue"}>{row.ucoExternalJob ? "External" : "Internal"}</Badge><span>{formatDuration(operationTiming(row).runtime)}</span><CostTrend field="ucoLineRawCost" value={lineRawUnitCost(row)} originalValue={original._id ? lineRawUnitCost(original) : undefined} /><CostTrend field="ucoLineMarkedUpCost" value={lineMarkedUnitCost(row)} originalValue={original._id ? lineMarkedUnitCost(original) : undefined} /><strong>{formatValue("ucoLineMarkedUpCost", row.ucoLineMarkedUpCost)}</strong><span className="row-actions"><button type="button" onClick={(event) => { event.stopPropagation(); onDelete("operation", row._id); }}>Delete</button></span></div>; })}</div></section>;
}



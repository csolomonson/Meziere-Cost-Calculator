import React, { useEffect, useRef, useState } from "react";

import { formatValue, toNumber } from "../domain/formatting.js";

export function Badge({ children, tone = "neutral" }) { return <span className={"badge " + tone}>{children}</span>; }
export function CostTrend({ field, value, originalValue }) {
  const diff = toNumber(value) - toNumber(originalValue);
  const changed = originalValue !== undefined && Math.abs(diff) >= 0.005;
  const delta = (diff > 0 ? "+" : "-") + formatValue(field, Math.abs(diff));
  const content = <>{formatValue(field, value)}{changed && <span className={"trend-pill " + (diff > 0 ? "up" : "down")} title={(diff > 0 ? "Increased by " : "Decreased by ") + formatValue(field, Math.abs(diff))}>{delta}</span>}</>;
  return <span className="cost-trend">{content}</span>;
}
export function Button({ children, tone = "primary", ...props }) { return <button {...props} className={(props.className || "") + " button " + tone}>{children}</button>; }
export function Stat({ label, value, field }) { return <div className="stat"><span>{label}</span><strong>{formatValue(field || label, value)}</strong></div>; }
export function useClickAway(ref, enabled, onAway) {
  const onAwayRef = useRef(onAway);
  onAwayRef.current = onAway;
  useEffect(() => {
    if (!enabled) return;
    function handlePointerDown(event) {
      if (ref.current && !ref.current.contains(event.target)) onAwayRef.current();
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [enabled]);
}
export function RetailStat({ part }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  useClickAway(containerRef, open, () => setOpen(false));
  const rows = part?.ucpRetailPrices?.length ? part.ucpRetailPrices : part?.ucpRetailUnitPrice !== null && part?.ucpRetailUnitPrice !== undefined ? [{ imiCustomerGroupID: "CG01", price_label: "LIST", retail_unit_price: part.ucpRetailUnitPrice }] : [];
  return <div className="retail-stat-wrap" ref={containerRef}><button type="button" className={"stat retail-stat " + (open ? "open" : "")} onClick={() => setOpen((value) => !value)}><span>Retail</span><strong>{formatValue("ucpRetailUnitPrice", part?.ucpRetailUnitPrice)}</strong></button>{open && <div className="retail-popover">{rows.length ? rows.map((row) => <div className="retail-level" key={row.imiCustomerGroupID || row.price_label}><span>{row.imiCustomerGroupID}</span><b>{row.price_label || row.imiCustomerGroupID}</b><strong>{formatValue("ucpRetailUnitPrice", row.retail_unit_price)}</strong></div>) : <p>No retail prices found.</p>}</div>}</div>;
}

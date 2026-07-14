import React, { useEffect, useRef, useState } from "react";

import { readApiResponse } from "../../api/client.js";
import { formatValue, toNumber } from "../../domain/formatting.js";
import { Badge, Button, Stat, useClickAway } from "../../components/ui.jsx";
import { NumberInput } from "../../components/inputs.jsx";

export function homeDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value).slice(0, 10) : date.toLocaleDateString();
}

export function homeCostSegments(row) {
  return [
    ["Material", toNumber(row.ucpMaterialsMarkedUpCost || row.ucpMaterialsRawCost), "material"],
    ["Machine", toNumber(row.ucpMachineTimeMarkedUpCost || row.ucpMachineTimeRawCost), "machine"],
    ["Labor", toNumber(row.ucpLaborMarkedUpCost || row.ucpLaborRawCost), "labor"],
    ["External", toNumber(row.ucpExternalOperationsMarkedUpCost || row.ucpExternalOperationsRawCost), "external"],
    ["Additional", toNumber(row.ucpAdditionalMarkedUpCost || row.ucpAdditionalRawCost), "additional"],
  ].filter(([, value]) => value > 0);
}

export function CostCompositionBar({ row }) {
  const quantity = toNumber(row.ucpCostQuantity) || 1;
  const segments = homeCostSegments(row).map(([label, value, kind]) => [label, value / quantity, kind]);
  const total = segments.reduce((sum, [, value]) => sum + value, 0) || toNumber(row.ucpUnitMarkedUpCost) || 1;
  return <div className="cost-composition">
    <div className="chart-track">{segments.length ? segments.map(([label, value, kind]) => <span key={label} className={"chart-segment " + kind} title={label + " " + formatValue("ucpUnitMarkedUpCost", value) + " per unit"} style={{ width: Math.max(3, value / total * 100) + "%" }} />) : <span className="chart-segment empty" style={{ width: "100%" }} />}</div>
    <div className="composition-values">{segments.map(([label, value, kind]) => <span key={label} className={kind}>{label.slice(0, 3)} {Math.round(value / total * 100)}%</span>)}</div>
  </div>;
}

export async function loadRecentHistory(partId, direction = "newest", cursor = null) {
  const params = new URLSearchParams({ limit: "10", direction });
  if (partId) params.set("part_id", partId);
  if (cursor) {
    const prefix = direction === "newer" ? "after" : "before";
    params.set(prefix + "_date", cursor.date);
    params.set(prefix + "_id", cursor.id);
  }
  const payload = await readApiResponse(await fetch("/api/costs/recent?" + params.toString()));
  return { rows: payload.costs || [], hasOlder: Boolean(payload.has_older), hasNewer: Boolean(payload.has_newer), olderCursor: payload.older_cursor || null, newerCursor: payload.newer_cursor || null };
}

export function historyPageLabel(page) {
  if (page.fromNewest !== undefined && page.fromNewest !== null) return page.fromNewest === 0 ? "Newest" : "Page " + (page.fromNewest + 1);
  if (page.fromOldest !== undefined && page.fromOldest !== null) return page.fromOldest === 0 ? "Oldest" : page.fromOldest + " page" + (page.fromOldest === 1 ? "" : "s") + " newer than oldest";
  return "History";
}

export function RecentCostsTable({ rows, position, hasNewer, hasOlder, loading, onNewest, onNewer, onOlder, onOldest, onOpenSaved }) {
  if (loading && !rows.length) return <div className="empty-state">Loading saved costs...</div>;
  if (!rows.length) return <div className="empty-state">No saved costs match this part number.</div>;
  return <div className="recent-table-wrap">
    <div className="recent-table">
      <div className="recent-table-head">{["Part", "Rev", "Qty", "Raw unit", "Marked unit", "Date", ""].map((head) => <b key={head}>{head}</b>)}</div>
      {rows.map((row) => <button type="button" className="recent-table-row" key={row.ucpPartCostID} onClick={() => onOpenSaved(row)}>
        <span className="part-cell"><strong>{row.ucpPartID || "Blank cost"}</strong><small>{row.ucpPartDescription || "No description"}</small></span>
        <span>{row.ucpPartRevision || "-"}</span>
        <span>{formatValue("ucpCostQuantity", row.ucpCostQuantity)}</span>
        <strong>{formatValue("ucpUnitRawCost", row.ucpUnitRawCost)}</strong>
        <strong>{formatValue("ucpUnitMarkedUpCost", row.ucpUnitMarkedUpCost)}</strong>
        <span>{homeDate(row.ucpDateCosted)}</span>
        {row.ucpIsCurrent ? <Badge tone="green">current</Badge> : <Badge>saved</Badge>}
      </button>)}
    </div>
    <div className="pager history-pager">
      <Button tone="secondary" onClick={onNewest} disabled={!hasNewer || loading}>Newest</Button>
      <Button tone="secondary" onClick={onNewer} disabled={!hasNewer || loading}>Newer</Button>
      <strong>{position}</strong>
      <Button tone="secondary" onClick={onOlder} disabled={!hasOlder || loading}>{loading ? "Loading..." : "Older"}</Button>
      <Button tone="secondary" onClick={onOldest} disabled={!hasOlder || loading}>Oldest</Button>
    </div>
  </div>;
}

export function StartScreen({ draft, setDraft, loadErp, startBlank, openSettings, openSavedCost, openUserManagement, isAdministrator, loading, error }) {
  const partRef = useRef(null), partSearchRef = useRef(null), qtyRef = useRef(null), suggestionRequestRef = useRef(0), historyRequestRef = useRef(0), [suggestions, setSuggestions] = useState([]), [recentPages, setRecentPages] = useState([]), [recentPage, setRecentPage] = useState(1), [recentLoading, setRecentLoading] = useState(true), [recentError, setRecentError] = useState("");
  useClickAway(partSearchRef, suggestions.length > 0, () => setSuggestions([]));
  useEffect(() => { partRef.current?.focus(); }, []);
  useEffect(() => { let active = true; const requestId = ++suggestionRequestRef.current, q = draft.part_id.trim(); if (q.length < 2) { setSuggestions([]); return () => { active = false; }; } const timer = setTimeout(async () => { try { const payload = await readApiResponse(await fetch("/api/parts/search?q=" + encodeURIComponent(q))); if (active && requestId === suggestionRequestRef.current) setSuggestions(document.activeElement === partRef.current ? payload.parts || [] : []); } catch { if (active && requestId === suggestionRequestRef.current) setSuggestions([]); } }, 180); return () => { active = false; clearTimeout(timer); }; }, [draft.part_id]);
  const filter = draft.part_id.trim().toUpperCase();
  useEffect(() => { let active = true; const requestId = ++historyRequestRef.current; setRecentLoading(true); setRecentError(""); setRecentPages([]); setRecentPage(1); const timer = setTimeout(async () => { try { const firstPage = await loadRecentHistory(filter, "newest"); if (active && requestId === historyRequestRef.current) setRecentPages([{ ...firstPage, fromNewest: 0 }]); } catch (err) { if (active && requestId === historyRequestRef.current) setRecentError(err.message || "Could not load recent costs."); } finally { if (active && requestId === historyRequestRef.current) setRecentLoading(false); } }, 150); return () => { active = false; clearTimeout(timer); }; }, [filter]);
  function update(field, value) { setDraft((current) => ({ ...current, [field]: field === "quantity" ? toNumber(value) : value })); }
  function choose(part) { setDraft((current) => ({ ...current, part_id: part.impPartID, revision_id: part.impPartRevisionID || "" })); setSuggestions([]); qtyRef.current?.focus(); qtyRef.current?.select(); }
  function submitStart(event) { event.preventDefault(); loadErp(); }
  const activeHistoryPage = recentPages[recentPage - 1] || { rows: [], hasOlder: false, hasNewer: false, olderCursor: null, newerCursor: null };
  const hasNewerHistory = Boolean(recentPages[recentPage - 2] || activeHistoryPage.hasNewer);
  const hasOlderHistory = Boolean(recentPages[recentPage] || activeHistoryPage.hasOlder);
  async function showHistoryEdge(direction) {
    if (recentLoading) return;
    const requestId = ++historyRequestRef.current;
    setRecentLoading(true);
    setRecentError("");
    try {
      const edgePage = await loadRecentHistory(filter, direction);
      if (requestId !== historyRequestRef.current) return;
      setRecentPages([{ ...edgePage, ...(direction === "oldest" ? { fromOldest: 0 } : { fromNewest: 0 }) }]);
      setRecentPage(1);
    } catch (err) {
      if (requestId === historyRequestRef.current) setRecentError(err.message || "Could not load history.");
    } finally {
      if (requestId === historyRequestRef.current) setRecentLoading(false);
    }
  }
  async function showNewerHistory() {
    if (recentLoading || !hasNewerHistory) return;
    if (recentPage > 1) { setRecentPage((page) => page - 1); return; }
    const requestId = ++historyRequestRef.current;
    setRecentLoading(true);
    setRecentError("");
    try {
      const newerPage = await loadRecentHistory(filter, "newer", activeHistoryPage.newerCursor);
      if (requestId !== historyRequestRef.current) return;
      const positionedPage = { ...newerPage, fromOldest: activeHistoryPage.fromOldest === undefined ? null : activeHistoryPage.fromOldest + 1 };
      setRecentPages((pages) => [positionedPage, ...pages]);
      setRecentPage(1);
    } catch (err) {
      if (requestId === historyRequestRef.current) setRecentError(err.message || "Could not load newer costs.");
    } finally {
      if (requestId === historyRequestRef.current) setRecentLoading(false);
    }
  }
  async function showOlderHistory() {
    if (recentLoading || !hasOlderHistory) return;
    if (recentPages[recentPage]) { setRecentPage((page) => page + 1); return; }
    const requestId = ++historyRequestRef.current;
    setRecentLoading(true);
    setRecentError("");
    try {
      const olderPage = await loadRecentHistory(filter, "older", activeHistoryPage.olderCursor);
      if (requestId !== historyRequestRef.current) return;
      const positionedPage = { ...olderPage, fromNewest: activeHistoryPage.fromNewest === undefined ? null : activeHistoryPage.fromNewest + 1 };
      setRecentPages((pages) => [...pages.slice(0, recentPage), positionedPage]);
      setRecentPage((page) => page + 1);
    } catch (err) {
      if (requestId === historyRequestRef.current) setRecentError(err.message || "Could not load older costs.");
    } finally {
      if (requestId === historyRequestRef.current) setRecentLoading(false);
    }
  }
  return <main className="start-screen home-screen">
    <section className="home-shell">
      <section className="home-panel start-panel dashboard-start">
        <div className="panel-title"><div><span className="eyebrow">Costing</span><h1>Cost calculator</h1></div><div className="home-actions">{isAdministrator && <Button tone="secondary" onClick={openUserManagement}>User management</Button>}<Button tone="secondary" onClick={openSettings}>Machine settings</Button><Button tone="secondary" onClick={startBlank}>Blank worksheet</Button></div></div>
        <form className="start-form dashboard-form" onSubmit={submitStart}>
          <div className="part-search-wrap" ref={partSearchRef}><label className="field part-search"><span>Part number</span><input ref={partRef} autoComplete="off" value={draft.part_id} onChange={(event) => update("part_id", event.target.value.toUpperCase())} onKeyDown={(event) => { if (event.key === "ArrowDown" && suggestions[0]) { event.preventDefault(); choose(suggestions[0]); } if (event.key === "Enter" && suggestions[0]) { event.preventDefault(); choose(suggestions[0]); } if (event.key === "Escape") setSuggestions([]); }} /></label>{suggestions.length > 0 && <div className="start-suggestions">{suggestions.map((part) => <button type="button" key={part.impPartID + "::" + (part.impPartRevisionID || "")} onClick={() => choose(part)}><strong>{part.impPartID}<small className="suggestion-revision">{part.impPartRevisionID ? "rev " + part.impPartRevisionID : "base"}</small></strong><span>{part.impShortDescription || part.impPartShortDescription || "No description"}</span></button>)}</div>}</div>
          <label className="field"><span>Revision</span><input autoComplete="off" value={draft.revision_id} onChange={(event) => update("revision_id", event.target.value)} /></label>
          <label className="field"><span>Quantity</span><NumberInput ref={qtyRef} autoComplete="off" value={draft.quantity} onChange={(value) => update("quantity", value)} /></label>
          <div className="home-form-actions"><Button type="submit" disabled={loading || !draft.part_id}>{loading ? "Loading" : "Use ERP + defaults"}</Button><Button type="button" tone="secondary" onClick={() => loadErp(true)} disabled={loading || !draft.part_id}>New version</Button></div>
          {error && <div className="error-box">{error}</div>}
        </form>
      </section>
      <section className="home-panel recent-dashboard">
        <div className="panel-title"><div><span className="eyebrow">Recent costing runs</span><h2>{filter ? "Filtered previous costs" : "Previous costs"}</h2></div><div className="recent-summary"><span>{historyPageLabel(activeHistoryPage)}</span><span>10 per page</span></div></div>
        {recentError && <div className="error-box">{recentError}</div>}
        <RecentCostsTable rows={activeHistoryPage.rows} position={historyPageLabel(activeHistoryPage)} hasNewer={hasNewerHistory} hasOlder={hasOlderHistory} loading={recentLoading} onNewest={() => showHistoryEdge("newest")} onNewer={showNewerHistory} onOlder={showOlderHistory} onOldest={() => showHistoryEdge("oldest")} onOpenSaved={openSavedCost} />
      </section>
    </section>
  </main>;
}



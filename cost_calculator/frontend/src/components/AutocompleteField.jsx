import React, { useEffect, useRef, useState } from "react";

import { readApiResponse } from "../api/client.js";
import { useClickAway } from "./ui.jsx";

export function AutocompleteField({ label, value, field, edited, searchUrl, renderOption, optionValue, onChange, onSelect, resultKey = null, minChars = 2 }) {
  const [query, setQuery] = useState(""), [options, setOptions] = useState([]);
  const containerRef = useRef(null), requestRef = useRef(0);
  useClickAway(containerRef, options.length > 0, () => { setQuery(""); setOptions([]); });
  useEffect(() => { let active = true; const requestId = ++requestRef.current, q = query.trim(); if (q.length < minChars) { setOptions([]); return () => { active = false; }; } const timer = setTimeout(async () => { try { const payload = await readApiResponse(await fetch(searchUrl + encodeURIComponent(q))); const nextOptions = resultKey ? payload[resultKey] || [] : payload.parts || payload.operations || payload.processes || payload.work_centers || []; if (active && requestId === requestRef.current) setOptions(containerRef.current?.contains(document.activeElement) ? nextOptions : []); } catch { if (active && requestId === requestRef.current) setOptions([]); } }, 180); return () => { active = false; clearTimeout(timer); }; }, [query, searchUrl, resultKey, minChars]);
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
  return <label ref={containerRef} className={"field autocomplete " + (edited ? "changed" : "")}><span>{label}{edited && <em className="changed-flag">changed</em>}</span><input data-field={field} value={value ?? ""} onFocus={() => setQuery(value || " ")} onChange={(event) => { setQuery(event.target.value); onChange(event.target.value); }} onKeyDown={handleKey} onKeyUp={(event) => { if (event.key === "ArrowDown" && options[0]) handleKey(event); }} />{options.length > 0 && <div className="suggestion-menu">{options.map((option, index) => <button type="button" key={optionValue(option) + index} onMouseDown={(event) => event.preventDefault()} onClick={() => choose(option)}>{renderOption(option)}</button>)}</div>}</label>;
}



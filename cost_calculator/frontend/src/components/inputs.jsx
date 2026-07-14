import React, { useEffect, useState } from "react";

import { durationFields, numericFields } from "../domain/model.js";
import { durationParts, formatDurationInput, parseDurationInput } from "../domain/formatting.js";

function numberDraft(value) { return value === null || value === undefined ? "" : String(value); }
function isCompleteNumber(text) { const trimmed = String(text ?? "").trim(); return trimmed !== "" && trimmed !== "-" && trimmed !== "." && trimmed !== "-." && Number.isFinite(Number(trimmed)); }
export const NumberInput = React.forwardRef(function NumberInput({ value, onChange, onValidityChange, ...props }, ref) {
  const [draft, setDraft] = useState(numberDraft(value)), [focused, setFocused] = useState(false);
  useEffect(() => { if (!focused) setDraft(numberDraft(value)); }, [value, focused]);
  function change(event) {
    const next = event.target.value;
    setDraft(next);
    const valid = isCompleteNumber(next);
    onValidityChange?.(valid);
    if (valid) onChange(Number(next));
  }
  function blur() {
    setFocused(false);
    setDraft(isCompleteNumber(draft) ? numberDraft(Number(draft)) : numberDraft(value));
    onValidityChange?.(true);
  }
  const invalid = !isCompleteNumber(draft) && draft !== numberDraft(value);
  return <input {...props} ref={ref} type="text" inputMode="decimal" value={draft} className={((props.className || "") + (invalid ? " numeric-invalid" : "")).trim()} aria-invalid={invalid || undefined} onChange={change} onFocus={(event) => { setFocused(true); setTimeout(() => event.target.select?.(), 0); props.onFocus?.(event); }} onBlur={(event) => { blur(); props.onBlur?.(event); }} />;
});

export const DurationInput = React.forwardRef(function DurationInput({ value, onChange, onValidityChange, onKeyDown, ...props }, ref) {
  const [draft, setDraft] = useState(formatDurationInput(value)), [focused, setFocused] = useState(false), parts = durationParts(value);
  useEffect(() => { if (!focused) setDraft(formatDurationInput(value)); }, [value, focused]);
  function change(event) {
    const next = event.target.value;
    setDraft(next);
    const parsed = parseDurationInput(next);
    onValidityChange?.(parsed !== null);
    if (parsed !== null) onChange(parsed);
  }
  function blur(event) {
    setFocused(false);
    setDraft(formatDurationInput(parseDurationInput(draft) ?? value));
    onValidityChange?.(true);
    props.onBlur?.(event);
  }
  const invalid = parseDurationInput(draft) === null && draft !== formatDurationInput(value);
  return <div className={"duration-box " + (invalid ? "numeric-invalid" : "")}><input {...props} ref={ref} value={draft} aria-invalid={invalid || undefined} onFocus={(event) => { setFocused(true); setTimeout(() => event.target.select?.(), 0); props.onFocus?.(event); }} onBlur={blur} onChange={change} onKeyDown={onKeyDown} /><div className="duration-readout"><b>{parts.h}</b><small>h</small><b>{String(parts.m).padStart(2, "0")}</b><small>m</small><b>{String(parts.s).padStart(2, "0")}</b><small>s</small></div></div>;
});

export function DefaultValueInput({ field, value, onChange }) {
  return durationFields.has(field) ? <DurationInput data-field={field} value={value ?? 0} onChange={onChange} /> : <NumberInput data-field={field} value={value ?? 0} onChange={onChange} />;
}

export function Field({ label, value, field, onChange, onValidityChange, edited, defaultSourced, onDefaultEdit, onReset, type = "text" }) {
  const isDuration = durationFields.has(field), isNumeric = numericFields.has(field) && !isDuration, inputType = type === "checkbox" ? "checkbox" : "text";
  const [draft, setDraft] = useState(isNumeric ? numberDraft(value) : ""), [focused, setFocused] = useState(false);
  useEffect(() => { if (isNumeric && !focused) setDraft(numberDraft(value)); }, [isNumeric, value, focused]);
  function change(event) {
    if (inputType === "checkbox") return onChange(event.target.checked);
    if (isNumeric) { const next = event.target.value; const valid = isCompleteNumber(next); setDraft(next); onValidityChange?.(valid); if (valid) onChange(Number(next)); return; }
    onChange(event.target.value);
  }
  function blur() { setFocused(false); if (isNumeric) { setDraft(isCompleteNumber(draft) ? numberDraft(Number(draft)) : numberDraft(value)); onValidityChange?.(true); } }
  function keyDown(event) { if (event.key !== "Enter") return; event.preventDefault(); const inputs = Array.from(document.querySelectorAll(".focus-screen input")).filter((input) => !input.disabled && input.offsetParent !== null); const index = inputs.indexOf(event.currentTarget); const next = inputs[index + (event.shiftKey ? -1 : 1)]; if (next) { next.focus(); next.select?.(); } }
  function reset(event) { event.preventDefault(); event.stopPropagation(); onReset?.(); }
  const invalid = isNumeric && !isCompleteNumber(draft) && draft !== numberDraft(value);
  return <label className={"field " + (edited ? "changed" : "") + (defaultSourced ? " from-default" : "") + (invalid ? " numeric-draft-invalid" : "")} onContextMenu={(event) => { if (onDefaultEdit) { event.preventDefault(); onDefaultEdit(field, value); } }}>
    <span>{label}<span className="field-flags">{defaultSourced && <em>default</em>}{edited && <em className="changed-flag">changed</em>}{edited && onReset && <button className="reset-button" type="button" onMouseDown={reset} onClick={(event) => event.preventDefault()}>Reset</button>}</span></span>
    {isDuration ? <DurationInput data-field={field} value={value} onChange={onChange} onValidityChange={onValidityChange} onKeyDown={keyDown} /> : <input data-field={field} type={inputType} inputMode={isNumeric ? "decimal" : undefined} aria-invalid={invalid || undefined} checked={inputType === "checkbox" ? Boolean(value) : undefined} value={inputType === "checkbox" ? undefined : isNumeric ? draft : value ?? ""} onChange={change} onFocus={(event) => { setFocused(true); event.target.select?.(); }} onBlur={blur} onKeyDown={keyDown} />}
  </label>;
}



import React from "react";

import { formatDuration, hoursToClock, parseTimeHours, toNumber } from "../../domain/formatting.js";
import { calendarSegments, operationTiming, pct } from "../../domain/calculations.js";
import { Badge } from "../../components/ui.jsx";

export function OperationCalendar({ row, shift, onChange }) {
  const start = parseTimeHours(row.ucoStartTime, parseTimeHours(shift.firstShiftStart, 6));
  const timing = operationTiming(row);
  const runtime = timing.runtime;
  const finish = start + runtime;
  const days = Math.max(1, Math.ceil(finish / 24));
  const shownDays = days > 2 ? [0, days - 1] : [0, 1];
  const shiftStart = parseTimeHours(shift.firstShiftStart, 6), shiftEnd = parseTimeHours(shift.firstShiftEnd, 14.5);
  const segments = calendarSegments(row, start, shownDays);
  function setStartFromPointer(event, target = event.currentTarget) {
    const rect = target.getBoundingClientRect();
    const hour = Math.max(0, Math.min(24, ((event.clientX - rect.left) / rect.width) * 24));
    onChange("ucoStartTime", hoursToClock(hour));
  }
  function startDrag(event) {
    if (event.button !== 0) return;
    const target = event.currentTarget;
    event.preventDefault();
    setStartFromPointer(event, target);
    function move(moveEvent) { setStartFromPointer(moveEvent, target); }
    function up() {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    }
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  }
  return <section className="calendar-card"><div className="calendar-head"><div><span className="eyebrow">Schedule preview</span><strong>{formatDuration(runtime)} runtime</strong></div><Badge tone={row.ucoUseAfterHoursIdle ? "amber" : "neutral"}>{row.ucoUseAfterHoursIdle ? formatDuration(row.ucoAfterHoursIdleTimeHours) + " after-hours idle" : "not costed"}</Badge></div>{days > 2 && <div className="middle-note">{days - 2} full day{days - 2 === 1 ? "" : "s"} hidden in the middle</div>}{shownDays.map((day) => <div className="day-row" key={day}><div className="day-label">{day === 0 ? "Start day" : "Finish day"}<span>{day === 0 ? "Drag to set start " + hoursToClock(start) : "Finish " + hoursToClock(finish)}</span></div><div className={"timeline " + (day === 0 ? "draggable" : "")} onMouseDown={day === 0 ? startDrag : undefined}>{Array.from({ length: 25 }).map((_, i) => <i key={i} style={{ left: (i / 24) * 100 + "%" }} />)}<div className="shift-band" style={{ left: (shiftStart / 24) * 100 + "%", width: (((shiftEnd - shiftStart + 24) % 24 || 24) / 24) * 100 + "%" }} />{segments.map((segment, index) => { const pos = pct(segment.left, segment.duration, day); const showLabel = pos.width > 15; return pos.width > 0 && <div key={segment.kind + segment.left + index} className={"bar " + segment.kind} title={segment.label + " - " + formatDuration(segment.duration)} style={{ left: pos.left + "%", width: pos.width + "%" }}>{showLabel ? segment.label : ""}</div>; })}{row.ucoUseAfterHoursIdle && toNumber(row.ucoAfterHoursIdleTimeHours) > 0 && (() => { const pos = pct(finish, toNumber(row.ucoAfterHoursIdleTimeHours), day); return pos.width > 0 && <div className="bar after" style={{ left: pos.left + "%", width: pos.width + "%" }}>{pos.width > 18 ? "After-hours idle" : ""}</div>; })()} {day === 0 && <div className="start-marker" style={{ left: (start / 24) * 100 + "%" }}><b>{hoursToClock(start)}</b></div>}</div></div>)}</section>;
}



"use client";

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { CalendarEvent, University } from "@/lib/api";

type Props = {
  event: CalendarEvent;
  university?: University;
  language: "ms" | "en";
  typeLabel: string;
};

type Position = { left: number; top: number; above: boolean };

function eventDates(event: CalendarEvent, language: Props["language"]) {
  const locale = language === "ms" ? "ms-MY" : "en-MY";
  const start = new Date(`${event.start_date}T00:00:00`);
  const end = new Date(`${event.end_date ?? event.start_date}T00:00:00`);
  const format = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric" });
  const range = event.end_date && event.end_date !== event.start_date
    ? `${format.format(start)} — ${format.format(end)}`
    : format.format(start);
  const days = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1;
  return { range, duration: language === "ms" ? `${days} hari` : `${days} ${days === 1 ? "day" : "days"}` };
}

export function EventPopover({ event, university, language, typeLabel }: Props) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<Position | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const focusPopoverRef = useRef(false);
  const suppressFocusRef = useRef(false);
  const id = useId();
  const dates = eventDates(event, language);
  const labels = language === "ms"
    ? { source: "Lihat sumber rasmi", session: "Sesi", audience: "Sasaran", page: "Halaman sumber", close: "Tutup butiran acara" }
    : { source: "View official source", session: "Session", audience: "Audience", page: "Source page", close: "Close event details" };

  function clearTimer() {
    if (timerRef.current) clearTimeout(timerRef.current);
  }

  function show(delay = 0) {
    clearTimer();
    timerRef.current = setTimeout(() => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const width = Math.min(336, window.innerWidth - 24);
      const above = window.innerHeight - rect.bottom < 290 && rect.top > 290;
      setPosition({
        left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)),
        top: above ? rect.top - 10 : rect.bottom + 10,
        above,
      });
      setOpen(true);
    }, delay);
  }

  function hide(delay = 0) {
    clearTimer();
    timerRef.current = setTimeout(() => setOpen(false), delay);
  }

  useEffect(() => {
    if (!open) return;
    if (focusPopoverRef.current) {
      focusPopoverRef.current = false;
      requestAnimationFrame(() => popoverRef.current?.querySelector<HTMLAnchorElement>("a")?.focus());
    }
    function dismiss(event: PointerEvent) {
      const node = event.target as Node;
      if (!triggerRef.current?.contains(node) && !popoverRef.current?.contains(node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        suppressFocusRef.current = true;
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    const close = () => setOpen(false);
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", close, true);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [open]);

  useEffect(() => () => clearTimer(), []);

  const color = university?.color ?? "#657068";
  return <>
    <button
      ref={triggerRef}
      type="button"
      className="calendar-event"
      style={{ "--uni": color } as React.CSSProperties}
      aria-expanded={open}
      aria-haspopup="dialog"
      aria-controls={id}
      aria-label={`${university?.short_name ?? event.university_code}: ${event.title}, ${dates.range}`}
      onMouseEnter={() => show(180)}
      onMouseLeave={() => hide(180)}
      onFocus={() => {
        if (suppressFocusRef.current) suppressFocusRef.current = false;
        else show();
      }}
      onClick={() => {
        if (open) popoverRef.current?.querySelector<HTMLAnchorElement>("a")?.focus();
        else { focusPopoverRef.current = true; show(); }
      }}
    >
      <span>{university?.short_name}</span>{event.title}
    </button>
    {open && position && createPortal(
      <div
        ref={popoverRef}
        id={id}
        role="dialog"
        aria-label={event.title}
        className={`event-popover ${position.above ? "above" : "below"}`}
        style={{ left: position.left, top: position.top, "--uni": color } as React.CSSProperties}
        onMouseEnter={clearTimer}
        onMouseLeave={() => hide(180)}
      >
        <div className="event-popover-topline">
          <span className="event-popover-uni">{university?.short_name ?? event.university_code}</span>
          <span>{typeLabel}</span>
          <button type="button" onClick={() => hide()} aria-label={labels.close}>×</button>
        </div>
        <h3>{event.title}</h3>
        <p className="event-popover-date">{dates.range} <span>· {dates.duration}</span></p>
        <dl>
          {event.semester && <><dt>{labels.session}</dt><dd>{event.semester}</dd></>}
          {event.audience && <><dt>{labels.audience}</dt><dd>{event.audience}</dd></>}
          {event.source_page && <><dt>{labels.page}</dt><dd>{event.source_page}</dd></>}
        </dl>
        <a href={event.source_url} target="_blank" rel="noreferrer">{labels.source} ↗</a>
      </div>,
      document.body,
    )}
  </>;
}

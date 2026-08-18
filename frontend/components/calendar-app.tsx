"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { API_URL, CalendarEvent, EventPage, fetchJson, University } from "@/lib/api";
import { Brand } from "./brand";

type Language = "ms" | "en";
type ViewMode = "month" | "list";

const copy = {
  ms: {
    eyebrow: "Kalendar akademik Malaysia",
    titleA: "Lima universiti.", titleB: "Satu pandangan.",
    intro: "Bandingkan jadual kampus kawan-kawan dan rancang masa bersama dengan lebih mudah.",
    search: "Cari acara…", filters: "Tapis", session: "Sesi", type: "Jenis acara",
    allTypes: "Semua jenis", selected: "Universiti dipilih", month: "Bulan", list: "Senarai",
    download: "Muat turun .ICS", today: "Hari ini", events: "acara", source: "Sumber",
    empty: "Tiada acara untuk pilihan ini.", loading: "Memuatkan kalendar…",
    error: "Kalendar tidak dapat dimuatkan. Pastikan API UniDate sedang berjalan.",
    universities: "Universiti", viewUniversity: "Lihat kalendar", footer: "Data disemak manusia sebelum diterbitkan.",
  },
  en: {
    eyebrow: "Malaysian academic calendars",
    titleA: "Five universities.", titleB: "One clear view.",
    intro: "Compare your friends’ campus schedules and make time together easier to plan.",
    search: "Search events…", filters: "Filters", session: "Session", type: "Event type",
    allTypes: "All types", selected: "Selected universities", month: "Month", list: "List",
    download: "Download .ICS", today: "Today", events: "events", source: "Source",
    empty: "No events match this view.", loading: "Loading calendars…",
    error: "Calendars could not be loaded. Make sure the UniDate API is running.",
    universities: "Universities", viewUniversity: "View calendar", footer: "Data is reviewed by a human before publication.",
  },
};

const typeLabels: Record<Language, Record<string, string>> = {
  ms: { registration: "Pendaftaran", orientation: "Orientasi", lecture: "Kuliah", assessment: "Penilaian", mid_semester_break: "Cuti pertengahan semester", revision: "Ulang kaji", examination: "Peperiksaan", semester_break: "Cuti semester", public_holiday: "Cuti umum", convocation: "Konvokesyen", other: "Lain-lain" },
  en: { registration: "Registration", orientation: "Orientation", lecture: "Lecture", assessment: "Assessment", mid_semester_break: "Mid-semester break", revision: "Revision", examination: "Examination", semester_break: "Semester break", public_holiday: "Public holiday", convocation: "Convocation", other: "Other" },
};

const weekdays = { ms: ["Isn", "Sel", "Rab", "Kha", "Jum", "Sab", "Ahd"], en: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] };

function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function monthCells(month: Date) {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const mondayOffset = (first.getDay() + 6) % 7;
  const start = new Date(first);
  start.setDate(first.getDate() - mondayOffset);
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    return date;
  });
}

function dateRange(event: CalendarEvent, language: Language) {
  const locale = language === "ms" ? "ms-MY" : "en-MY";
  const start = new Date(`${event.start_date}T00:00:00`);
  const end = event.end_date ? new Date(`${event.end_date}T00:00:00`) : null;
  const format = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric" });
  return end && event.end_date !== event.start_date ? `${format.format(start)} — ${format.format(end)}` : format.format(start);
}

export function CalendarApp() {
  const [language, setLanguage] = useState<Language>("ms");
  const [universities, setUniversities] = useState<University[]>([]);
  const [selected, setSelected] = useState<string[]>(["uitm", "unimap", "um", "ukm"]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [query, setQuery] = useState("");
  const [session, setSession] = useState("2026/2027");
  const [eventType, setEventType] = useState("");
  const [month, setMonth] = useState(new Date(2026, 9, 1));
  const [view, setView] = useState<ViewMode>("month");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const t = copy[language];

  useEffect(() => {
    const controller = new AbortController();
    fetchJson<University[]>("/api/v1/universities", controller.signal)
      .then(setUniversities)
      .catch(() => setStatus("error"));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ academic_session: session, page_size: "500" });
    if (selected.length) params.set("universities", selected.join(","));
    if (query.trim()) params.set("q", query.trim());
    if (eventType) params.set("event_type", eventType);
    fetchJson<EventPage>(`/api/v1/events?${params}`, controller.signal)
      .then((data) => { setEvents(data.items); setStatus("ready"); })
      .catch((error: Error) => { if (error.name !== "AbortError") setStatus("error"); });
    return () => controller.abort();
  }, [selected, query, session, eventType]);

  const universityMap = useMemo(() => Object.fromEntries(universities.map((item) => [item.code, item])), [universities]);
  const days = useMemo(() => monthCells(month), [month]);
  const visibleEvents = useMemo(() => events.filter((event) => {
    const first = isoDate(days[0]);
    const last = isoDate(days[days.length - 1]);
    return (event.end_date ?? event.start_date) >= first && event.start_date <= last;
  }), [events, days]);
  const selectedNames = selected.map((code) => universityMap[code]?.short_name).filter(Boolean).join(" + ");
  const locale = language === "ms" ? "ms-MY" : "en-MY";
  const monthTitle = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(month);
  const icsParams = new URLSearchParams({ academic_session: session });
  if (selected.length) icsParams.set("universities", selected.join(","));
  if (eventType) icsParams.set("event_type", eventType);
  if (query.trim()) icsParams.set("q", query.trim());

  function toggleUniversity(code: string) {
    setSelected((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]);
  }

  function shiftMonth(amount: number) {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + amount, 1));
  }

  return (
    <main>
      <header className="site-header">
        <Brand />
        <nav aria-label="Language">
          <button className={language === "ms" ? "active" : ""} onClick={() => setLanguage("ms")}>BM</button>
          <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button>
        </nav>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow"><span />{t.eyebrow}</p>
          <h1>{t.titleA}<br /><em>{t.titleB}</em></h1>
        </div>
        <p className="hero-copy">{t.intro}</p>
      </section>

      <section className="workspace" aria-label={t.filters}>
        <div className="filters-panel">
          <div className="filter-heading"><span>{t.filters}</span><b>{events.length} {t.events}</b></div>
          <label className="search-field"><span aria-hidden="true">⌕</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t.search} /></label>
          <label><span className="label">{t.session}</span><select value={session} onChange={(e) => setSession(e.target.value)}><option>2026/2027</option><option>2027/2028</option></select></label>
          <label><span className="label">{t.type}</span><select value={eventType} onChange={(e) => setEventType(e.target.value)}><option value="">{t.allTypes}</option>{Object.entries(typeLabels[language]).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <fieldset><legend>{t.selected}</legend><div className="university-options">{universities.map((university) => <label key={university.code} className={selected.includes(university.code) ? "selected" : ""} style={{ "--uni": university.color } as React.CSSProperties}><input type="checkbox" checked={selected.includes(university.code)} onChange={() => toggleUniversity(university.code)} /><span className="uni-dot" /> <b>{university.short_name}</b><small>{university.event_count}</small></label>)}</div></fieldset>
          <a className="download-button" href={`${API_URL}/api/v1/calendar.ics?${icsParams}`}><span>↓</span>{t.download}</a>
        </div>

        <div className="calendar-panel">
          <div className="calendar-toolbar">
            <div><p>{selectedNames || t.selected}</p><h2>{monthTitle}</h2></div>
            <div className="toolbar-actions">
              <div className="segmented"><button className={view === "month" ? "active" : ""} onClick={() => setView("month")}>{t.month}</button><button className={view === "list" ? "active" : ""} onClick={() => setView("list")}>{t.list}</button></div>
              <div className="month-nav"><button onClick={() => shiftMonth(-1)} aria-label="Previous month">←</button><button onClick={() => setMonth(new Date())}>{t.today}</button><button onClick={() => shiftMonth(1)} aria-label="Next month">→</button></div>
            </div>
          </div>

          {status === "error" && <div className="state-message error">{t.error}</div>}
          {status === "loading" && <div className="state-message">{t.loading}</div>}
          {status === "ready" && view === "month" && <div className="month-grid">{weekdays[language].map((day) => <div className="weekday" key={day}>{day}</div>)}{days.map((day) => {
            const iso = isoDate(day);
            const dayEvents = visibleEvents.filter((event) => event.start_date <= iso && (event.end_date ?? event.start_date) >= iso);
            const isCurrentMonth = day.getMonth() === month.getMonth();
            const isToday = iso === isoDate(new Date());
            return <div className={`day-cell ${isCurrentMonth ? "" : "muted"}`} key={iso}><time className={isToday ? "today" : ""}>{day.getDate()}</time><div className="day-events">{dayEvents.slice(0, 3).map((event) => { const university = universityMap[event.university_code]; return <a href={event.source_url} target="_blank" rel="noreferrer" className="calendar-event" style={{ "--uni": university?.color ?? "#777" } as React.CSSProperties} key={event.id}><span>{university?.short_name}</span>{event.title}</a>; })}{dayEvents.length > 3 && <small>+{dayEvents.length - 3}</small>}</div></div>;
          })}</div>}
          {status === "ready" && view === "list" && <div className="event-list">{visibleEvents.length === 0 ? <div className="state-message">{t.empty}</div> : visibleEvents.map((event) => { const university = universityMap[event.university_code]; return <article key={event.id} style={{ "--uni": university?.color ?? "#777" } as React.CSSProperties}><div className="event-date">{dateRange(event, language)}</div><div><div className="event-meta"><span>{university?.short_name}</span><span>{typeLabels[language][event.event_type] ?? event.event_type}</span></div><h3>{event.title}</h3><p>{event.semester}{event.audience ? ` · ${event.audience}` : ""}</p></div><a href={event.source_url} target="_blank" rel="noreferrer">{t.source} ↗</a></article>; })}</div>}
        </div>
      </section>

      <section className="university-directory">
        <div className="section-heading"><p className="eyebrow"><span />{t.universities}</p><h2>{universities.length.toString().padStart(2, "0")}</h2></div>
        <div className="university-cards">{universities.map((university, index) => <Link href={`/universities/${university.code}`} key={university.code} style={{ "--uni": university.color } as React.CSSProperties}><small>0{index + 1}</small><span className="card-dot" /><h3>{university.short_name}</h3><p>{university.name}</p><b>{t.viewUniversity} →</b></Link>)}</div>
      </section>

      <footer><Brand /><p>{t.footer}</p><a href="https://github.com/muazhazali/unidate" target="_blank" rel="noreferrer">Open source ↗</a></footer>
    </main>
  );
}

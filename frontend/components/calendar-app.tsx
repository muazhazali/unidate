"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { API_URL, CalendarEvent, EventPage, fetchJson, University } from "@/lib/api";
import { Brand } from "./brand";
import { EventPopover } from "./event-popover";

type Language = "ms" | "en";
type ViewMode = "month" | "list";

const copy = {
  ms: {
    eyebrow: "Kalendar universiti berpusat",
    titleA: "Universiti berbeza.", titleB: "Satu jadual.",
    intro: "Bandingkan kalendar akademik dan cari masa terbaik untuk bersama rakan atau keluarga.",
    explore: "Teroka kalendar", browseUniversities: "Lihat universiti",
    heroPoints: ["Sumber rasmi", "Mudah dibandingkan", "Dikemas kini berkala"],
    search: "Cari acara…", filters: "Tapis", session: "Sesi", type: "Jenis acara",
    allTypes: "Semua jenis", selected: "Universiti dipilih", month: "Bulan", list: "Senarai",
    download: "Muat turun .ICS", today: "Hari ini", events: "acara", source: "Sumber",
    empty: "Tiada acara untuk pilihan ini.", loading: "Memuatkan kalendar…",
    error: "Kalendar tidak dapat dimuatkan sekarang. Sila cuba lagi.",
    selectPrompt: "Pilih sekurang-kurangnya satu universiti untuk melihat acara.",
    selectAll: "Pilih semua", clear: "Kosongkan", reset: "Tetapkan semula", retry: "Cuba lagi",
    showFilters: "Tunjukkan penapis", hideFilters: "Sembunyikan penapis", updating: "Mengemas kini acara…",
    more: "lagi", dayEvents: "Acara pada", close: "Tutup", previous: "Bulan sebelumnya", next: "Bulan seterusnya",
    viewLabel: "Paparan kalendar", languageLabel: "Bahasa",
    universities: "Universiti", viewUniversity: "Lihat kalendar", footer: "Data disemak manusia sebelum diterbitkan.",
  },
  en: {
    eyebrow: "Centralized university calendars",
    titleA: "Different universities.", titleB: "One calendar.",
    intro: "Compare academic calendars and find the best time to be with friends or family.",
    explore: "Explore calendars", browseUniversities: "View universities",
    heroPoints: ["Official sources", "Easy comparison", "Regularly updated"],
    search: "Search events…", filters: "Filters", session: "Session", type: "Event type",
    allTypes: "All types", selected: "Selected universities", month: "Month", list: "List",
    download: "Download .ICS", today: "Today", events: "events", source: "Source",
    empty: "No events match this view.", loading: "Loading calendars…",
    error: "Calendars could not be loaded right now. Please try again.",
    selectPrompt: "Select at least one university to view events.",
    selectAll: "Select all", clear: "Clear", reset: "Reset", retry: "Try again",
    showFilters: "Show filters", hideFilters: "Hide filters", updating: "Updating events…",
    more: "more", dayEvents: "Events on", close: "Close", previous: "Previous month", next: "Next month",
    viewLabel: "Calendar view", languageLabel: "Language",
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
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [session, setSession] = useState("2026/2027");
  const [eventType, setEventType] = useState("");
  const [month, setMonth] = useState(new Date(2026, 9, 1));
  const [view, setView] = useState<ViewMode>("month");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [expandedDay, setExpandedDay] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const t = copy[language];

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    const controller = new AbortController();
    fetchJson<University[]>("/api/v1/universities", controller.signal)
      .then(setUniversities)
      .catch(() => setStatus("error"));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (window.matchMedia("(max-width: 640px)").matches) setView("list");
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!expandedDay) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setExpandedDay(null); };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [expandedDay]);

  useEffect(() => {
    if (selected.length === 0) {
      return;
    }
    const controller = new AbortController();
    const loadingTimer = window.setTimeout(() => setStatus("loading"), 0);
    const params = new URLSearchParams({ academic_session: session, page_size: "500" });
    params.set("universities", selected.join(","));
    if (debouncedQuery) params.set("q", debouncedQuery);
    if (eventType) params.set("event_type", eventType);
    fetchJson<EventPage>(`/api/v1/events?${params}`, controller.signal)
      .then((data) => { setEvents(data.items); setStatus("ready"); })
      .catch((error: Error) => { if (error.name !== "AbortError") setStatus("error"); });
    return () => {
      window.clearTimeout(loadingTimer);
      controller.abort();
    };
  }, [selected, debouncedQuery, session, eventType, retryKey]);

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
  if (debouncedQuery) icsParams.set("q", debouncedQuery);
  const activeFilterCount = Number(Boolean(query)) + Number(Boolean(eventType)) + selected.length;
  const expandedDate = expandedDay ? days.find((day) => isoDate(day) === expandedDay) : null;
  const expandedEvents = expandedDay ? visibleEvents.filter((event) => event.start_date <= expandedDay && (event.end_date ?? event.start_date) >= expandedDay) : [];

  function toggleUniversity(code: string) {
    setSelected((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]);
  }

  function shiftMonth(amount: number) {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + amount, 1));
  }

  function resetFilters() {
    setQuery("");
    setEventType("");
    setSelected(universities.map((university) => university.code));
  }

  return (
    <main>
      <header className="site-header">
        <Brand />
        <nav aria-label={t.languageLabel}>
          <button aria-pressed={language === "ms"} className={language === "ms" ? "active" : ""} onClick={() => setLanguage("ms")}>BM</button>
          <button aria-pressed={language === "en"} className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button>
        </nav>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow"><span />{t.eyebrow}</p>
          <h1>{t.titleA}<br /><em>{t.titleB}</em></h1>
        </div>
        <div className="hero-content">
          <p className="hero-copy">{t.intro}</p>
          <div className="hero-actions">
            <a className="hero-primary" href="#calendar">{t.explore}</a>
            <a className="hero-secondary" href="#universities">{t.browseUniversities} →</a>
          </div>
          <ul className="hero-points">{t.heroPoints.map((point) => <li key={point}>{point}</li>)}</ul>
        </div>
      </section>

      <section className="workspace" id="calendar" aria-label={t.filters}>
        <div className={`filters-panel ${filtersOpen ? "open" : ""}`}>
          <div className="filter-heading"><span>{t.filters}</span><div><b>{selected.length ? events.length : 0} {t.events}</b><button className="filter-toggle" type="button" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((open) => !open)}>{filtersOpen ? t.hideFilters : `${t.showFilters} (${activeFilterCount})`}</button></div></div>
          <div className="filter-controls">
          <label className="search-field"><span aria-hidden="true">⌕</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t.search} /></label>
          <label><span className="label">{t.session}</span><select value={session} onChange={(e) => setSession(e.target.value)}><option>2026/2027</option><option>2027/2028</option></select></label>
          <label><span className="label">{t.type}</span><select value={eventType} onChange={(e) => setEventType(e.target.value)}><option value="">{t.allTypes}</option>{Object.entries(typeLabels[language]).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <fieldset><legend><span>{t.selected}</span><span className="selection-actions"><button type="button" onClick={() => setSelected(universities.map((item) => item.code))}>{t.selectAll}</button><button type="button" onClick={() => setSelected([])}>{t.clear}</button></span></legend><div className="university-options">{universities.map((university) => <label key={university.code} className={selected.includes(university.code) ? "selected" : ""} style={{ "--uni": university.color } as React.CSSProperties}><input type="checkbox" checked={selected.includes(university.code)} onChange={() => toggleUniversity(university.code)} /><span className="uni-dot" /> <b>{university.short_name}</b><small>{university.event_count}</small></label>)}</div></fieldset>
          <button className="reset-filters" type="button" onClick={resetFilters}>{t.reset}</button>
          {selected.length > 0 ? <a className="download-button" href={`${API_URL}/api/v1/calendar.ics?${icsParams}`}><span>↓</span>{t.download}</a> : <button className="download-button" type="button" disabled><span>↓</span>{t.download}</button>}
          </div>
        </div>

        <div className="calendar-panel">
          <div className="calendar-toolbar">
            <div><p>{selectedNames || t.selected}</p><h2>{monthTitle}</h2></div>
            <div className="toolbar-actions">
              <div className="segmented" role="group" aria-label={t.viewLabel}><button aria-pressed={view === "month"} className={view === "month" ? "active" : ""} onClick={() => setView("month")}>{t.month}</button><button aria-pressed={view === "list"} className={view === "list" ? "active" : ""} onClick={() => setView("list")}>{t.list}</button></div>
              <div className="month-nav"><button onClick={() => shiftMonth(-1)} aria-label={t.previous}>←</button><button onClick={() => setMonth(new Date())}>{t.today}</button><button onClick={() => shiftMonth(1)} aria-label={t.next}>→</button></div>
            </div>
          </div>

          <div className="sr-only" aria-live="polite">{status === "loading" && selected.length ? t.updating : `${selected.length ? events.length : 0} ${t.events}`}</div>
          {selected.length === 0 && <div className="state-message empty"><p>{t.selectPrompt}</p><button type="button" onClick={() => setSelected(universities.map((item) => item.code))}>{t.selectAll}</button></div>}
          {selected.length > 0 && status === "error" && <div className="state-message error"><p>{t.error}</p><button type="button" onClick={() => setRetryKey((key) => key + 1)}>{t.retry}</button></div>}
          {selected.length > 0 && status === "loading" && <div className="state-message loading">{t.loading}</div>}
          {selected.length > 0 && status === "ready" && view === "month" && <><div className="month-grid" role="grid" aria-label={monthTitle}>{weekdays[language].map((day) => <div className="weekday" role="columnheader" key={day}>{day}</div>)}{days.map((day) => {
            const iso = isoDate(day);
            const dayEvents = visibleEvents.filter((event) => event.start_date <= iso && (event.end_date ?? event.start_date) >= iso);
            const isCurrentMonth = day.getMonth() === month.getMonth();
            const isToday = iso === isoDate(new Date());
            return <div className={`day-cell ${isCurrentMonth ? "" : "muted"}`} role="gridcell" aria-label={new Intl.DateTimeFormat(locale, { dateStyle: "full" }).format(day)} key={iso}><time dateTime={iso} className={isToday ? "today" : ""}>{day.getDate()}</time><div className="day-events">{dayEvents.slice(0, 3).map((event) => { const university = universityMap[event.university_code]; return <EventPopover event={event} university={university} language={language} typeLabel={typeLabels[language][event.event_type] ?? event.event_type} key={event.id} />; })}{dayEvents.length > 3 && <button className="more-events" type="button" onClick={() => setExpandedDay(iso)}>+{dayEvents.length - 3} {t.more}</button>}</div></div>;
          })}</div>{visibleEvents.length === 0 && <div className="calendar-empty">{t.empty}</div>}</>}
          {selected.length > 0 && status === "ready" && view === "list" && <div className="event-list">{visibleEvents.length === 0 ? <div className="state-message">{t.empty}</div> : visibleEvents.map((event) => { const university = universityMap[event.university_code]; return <article key={event.id} style={{ "--uni": university?.color ?? "#777" } as React.CSSProperties}><div className="event-date">{dateRange(event, language)}</div><div><div className="event-meta"><span>{university?.short_name}</span><span>{typeLabels[language][event.event_type] ?? event.event_type}</span></div><h3>{event.title}</h3><p>{event.semester}{event.audience ? ` · ${event.audience}` : ""}</p></div><a href={event.source_url} target="_blank" rel="noreferrer">{t.source} ↗</a></article>; })}</div>}
        </div>
      </section>

      <section className="university-directory" id="universities">
        <div className="section-heading"><p className="eyebrow"><span />{t.universities}</p><h2>{universities.length.toString().padStart(2, "0")}</h2></div>
        <div className="university-cards">{universities.map((university, index) => <Link href={`/universities/${university.code}`} key={university.code} style={{ "--uni": university.color } as React.CSSProperties}><small>0{index + 1}</small><span className="card-dot" /><h3>{university.short_name}</h3><p>{university.name}</p><b>{t.viewUniversity} →</b></Link>)}</div>
      </section>

      <footer><Brand /><p>{t.footer}</p><a href="https://github.com/muazhazali/unidate" target="_blank" rel="noreferrer">Open source ↗</a></footer>
      {expandedDay && expandedDate && <div className="day-dialog-backdrop" onPointerDown={() => setExpandedDay(null)}><section className="day-dialog" role="dialog" aria-modal="true" aria-labelledby="day-dialog-title" onPointerDown={(event) => event.stopPropagation()}><div className="day-dialog-heading"><div><small>{t.dayEvents}</small><h2 id="day-dialog-title">{new Intl.DateTimeFormat(locale, { dateStyle: "full" }).format(expandedDate)}</h2></div><button type="button" onClick={() => setExpandedDay(null)} aria-label={t.close}>×</button></div><div className="event-list">{expandedEvents.map((event) => { const university = universityMap[event.university_code]; return <article key={event.id} style={{ "--uni": university?.color ?? "#777" } as React.CSSProperties}><div className="event-date">{dateRange(event, language)}</div><div><div className="event-meta"><span>{university?.short_name}</span><span>{typeLabels[language][event.event_type] ?? event.event_type}</span></div><h3>{event.title}</h3><p>{event.semester}{event.audience ? ` · ${event.audience}` : ""}</p></div><a href={event.source_url} target="_blank" rel="noreferrer">{t.source} ↗</a></article>; })}</div></section></div>}
    </main>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API_URL, CalendarEvent, EventPage, fetchJson, University } from "@/lib/api";
import { Brand } from "./brand";

export function UniversityDetail({ code }: { code: string }) {
  const [university, setUniversity] = useState<University | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([
      fetchJson<University>(`/api/v1/universities/${code}`),
      fetchJson<EventPage>(`/api/v1/events?universities=${code}&page_size=500`),
    ]).then(([universityData, eventData]) => {
      setUniversity(universityData);
      setEvents(eventData.items);
    }).catch(() => setError(true));
  }, [code]);

  return <main>
    <header className="site-header"><Brand /><Link className="back-link" href="/">← Kalendar gabungan</Link></header>
    {error && <div className="detail-state"><h1>Universiti tidak dijumpai</h1><Link href="/">Kembali ke UniDate</Link></div>}
    {!error && !university && <div className="detail-state">Memuatkan…</div>}
    {university && <>
      <section className="detail-hero" style={{ "--uni": university.color } as React.CSSProperties}>
        <div className="detail-index">{university.short_name}</div>
        <div><p className="eyebrow"><span />Kalendar universiti</p><h1>{university.name}</h1><p>{events.length} acara yang telah disemak untuk sesi tersedia.</p></div>
        <a className="download-button" href={`${API_URL}/api/v1/calendar.ics?universities=${code}`}>↓ Muat turun .ICS</a>
      </section>
      <section className="detail-events">
        {events.length === 0 && <div className="state-message">Data kalendar belum tersedia. Sumber akan diperiksa dalam kitaran bulanan seterusnya.</div>}
        {events.map((event) => <article key={event.id} style={{ "--uni": university.color } as React.CSSProperties}>
          <time><b>{new Intl.DateTimeFormat("ms-MY", { day: "2-digit" }).format(new Date(`${event.start_date}T00:00:00`))}</b><span>{new Intl.DateTimeFormat("ms-MY", { month: "short", year: "numeric" }).format(new Date(`${event.start_date}T00:00:00`))}</span></time>
          <div><p>{event.semester} · {event.event_type.replaceAll("_", " ")}</p><h2>{event.title}</h2><small>{event.audience}</small></div>
          <a href={event.source_url} target="_blank" rel="noreferrer">Sumber ↗</a>
        </article>)}
      </section>
    </>}
  </main>;
}


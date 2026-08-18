export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type University = {
  code: string;
  name: string;
  short_name: string;
  color: string;
  website: string;
  event_count: number;
};

export type CalendarEvent = {
  id: string;
  university_code: string;
  academic_session: string;
  semester: string | null;
  audience: string | null;
  event_type: string;
  title: string;
  start_date: string;
  end_date: string | null;
  source_url: string;
  source_page: number | null;
  last_checked: string;
};

export type EventPage = {
  items: CalendarEvent[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

export async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal });
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}


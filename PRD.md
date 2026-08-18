# UniDate Product Requirements Document

## 1. Product summary

UniDate is an open-source, mobile-friendly web application and public API that overlays academic calendar events from selected Malaysian universities. It helps students compare university schedules when planning activities with friends.

## 2. Goals

- Present multiple university calendars in one consistent interface.
- Preserve every event title exactly as published by its university.
- Make each event traceable to a public university webpage or PDF.
- Offer one-time ICS calendar downloads.
- Keep published data trustworthy through automated collection and human-reviewed GitHub pull requests.

## 3. Target users

Primary users are students who want to compare their university schedule with their friends' schedules.

## 4. MVP scope

### Universities

- Universiti Teknologi MARA (UiTM)
- Universiti Malaysia Perlis (UniMAP)
- Universiti Utara Malaysia (UUM)
- Universiti Malaya (UM)
- Universiti Kebangsaan Malaysia (UKM)

### Academic sessions

- 2026/2027
- 2027/2028

### User-facing features

- Search for universities and calendar events.
- Filter by university, academic session, semester or term, event type, and date range.
- View a dedicated page for each university.
- Overlay events from multiple selected universities in a combined calendar.
- Open the original source link for every event.
- Download a university or combined calendar once as an ICS file.
- Use the site effectively on mobile and desktop.
- Access calendar data through a public API without authentication.
- Switch interface labels between Malay (default) and English.

The product does not calculate or recommend dates when all students are free.

## 5. Data requirements

UniDate must collect all dated events found in the supported universities' public academic calendars. Event titles must remain exactly as published and must not be translated. Interface labels may be localized independently.

Each published event must include:

- University
- Academic session
- Semester or term, when supplied
- Original event title
- Normalized event type
- Start date
- End date, when supplied
- Source URL
- Source page number, when the source is a PDF and the page can be identified
- Date the source was last checked

The system must retain the original source document or a verifiable reference to it and must keep prior data versions rather than silently overwriting them.

## 6. Collection and publishing workflow

1. A scheduled job checks registered, publicly accessible university webpages and PDFs once per month.
2. The pipeline detects new or changed sources and extracts structured calendar events.
3. Programmatic validation checks dates, required fields, duplicates, and suspicious changes.
4. The pipeline creates a GitHub pull request containing the proposed data changes, source references, and a readable diff.
5. A project maintainer reviews the pull request against the original source.
6. Only merged changes become publicly available.

Pages or portals requiring authentication are out of scope. The MVP has no admin dashboard and no end-user accounts.

## 7. Public API

The API must provide read-only access to:

- Supported universities
- Academic sessions
- Calendar events
- Filtered event results
- Data source metadata
- One-time ICS generation

The API must support filtering by university, academic session, semester or term, event type, and date range. It must be versioned and return consistent JSON error responses. Exact endpoint paths and pagination rules are implementation decisions to document in the API specification.

## 8. Technical direction

- Frontend: Next.js
- Backend/API: FastAPI
- Hosting: self-hosted Linux containers (LXC) on Proxmox
- Source control and review: GitHub
- Data ingestion: automated webpage/PDF scraping and extraction
- Deployment topology, database, object storage, CI/CD tooling, and extraction libraries: TBD during technical design

## 9. Non-functional requirements

- **Accessibility:** Meet WCAG 2.2 AA for core journeys, including keyboard navigation, visible focus, semantic markup, adequate contrast, and screen-reader labels.
- **Performance:** On a typical mobile connection, core pages should achieve a 75th-percentile Largest Contentful Paint of 2.5 seconds or less. Cached API reads should respond within 500 ms at the 95th percentile under expected MVP load.
- **Security:** Treat scraped content as untrusted, validate all pipeline and API inputs, sanitize rendered content, restrict publishing credentials, keep dependencies patched, and apply rate limiting to the unauthenticated API.
- **Privacy:** Collect no personal data and use no user accounts in the MVP. Any operational logs must avoid unnecessary identifying information and use documented retention limits.
- **Reliability:** A failed scrape must not remove or replace the last approved dataset. Jobs must produce actionable failure logs.
- **Traceability:** Every published event must link back to its source and an approved GitHub change.
- **Localization:** Malay is the default interface language; English is the secondary interface language. Event content remains in its original published language.

## 10. MVP success metrics

The MVP is successful when, for four consecutive monthly checks:

- All five universities have approved data for both target academic sessions when those sessions are publicly available.
- At least 95% of sampled published events match their original source dates and titles exactly.
- 100% of published events include a working or archived source reference.
- No extracted change is published without a merged human-reviewed GitHub pull request.
- At least 95% of scheduled source checks complete successfully, excluding confirmed upstream outages.
- Search, filtering, combined overlay, and ICS download pass acceptance testing on current mobile and desktop browsers.

Usage-growth targets are deferred until the project has a baseline audience.

## 11. Out of scope for MVP

- Private or authenticated student portals
- User registration, login, profiles, or saved preferences
- Admin dashboard
- Automatic publishing without human approval
- AI recommendations or automatic free-date suggestions
- Recurring ICS subscription feeds
- Native mobile applications
- Universities other than the five listed above

## 12. Release acceptance criteria

- Students can select two or more supported universities and see their events overlaid for a chosen date range.
- Search and every documented filter return correct results from the approved dataset.
- Every displayed event exposes its original title, dates, university, and source link.
- University and combined calendar views produce valid one-time ICS downloads.
- Malay and English interface labels are available without translating source event titles.
- The unauthenticated public API supports all MVP data and filtering capabilities.
- A monthly extraction run can create a reviewable GitHub pull request without publishing unapproved changes.

## 13. Open implementation decisions

- Database and raw-source storage technology
- Exact API routes, pagination, rate limits, and versioning policy
- Source registry format and university-specific extraction methods
- GitHub Actions or self-hosted scheduling and deployment workflow
- Definition and mapping rules for normalized event types
- Browser support matrix and operational log retention period

# UniDate Calendar Proposal Review Prompt

You are the senior data reviewer responsible for approving UniDate academic-calendar proposals. Your job is not to trust or lightly proofread AI output. Your job is to independently verify every proposed event against the official source and publish only evidence-supported data.

Accuracy is more important than speed or event count. Never claim that a proposal is accurate merely because it passed schema validation or has a high confidence score.

## Objective

For each requested university and academic session:

1. Download the registered official source.
2. Extract it into a review proposal.
3. Independently compare every candidate event with the source.
4. Correct OCR, table-layout, date, audience, semester, and classification errors.
5. Publish only the reviewed events into `backend/data/events.json`.
6. Preserve all events outside the reviewed universities and academic session.
7. Run the complete validation and test suite before reporting success.

## Non-negotiable rules

- Treat every proposal as untrusted input, including proposals with confidence `1.0`.
- The official university PDF or webpage is the source of truth.
- Never approve a PDF proposal using extracted text alone. Render every relevant page to images and visually inspect its table structure.
- Never infer an event absent from the official source.
- Keep event titles exactly as published, except for obvious extraction artifacts such as an OCR bullet accidentally included as text.
- Do not translate, summarize, modernize, or silently rename official event titles.
- Never silently repair an ambiguous date. Hold the event for human review if the source does not resolve the ambiguity.
- Schema validity does not prove factual accuracy.
- A model-provided `evidence` string does not prove that its interpretation is correct.
- Never expose `.env` values or API keys in terminal output, logs, proposals, or reports.
- Never publish by blindly replacing the complete event database.
- Do not publish duplicate events simply because they appear in more than one programme calendar.
- Do not mark the task complete if tests, integrity checks, or source comparisons fail.

## Repository locations

- Source registry: `backend/data/sources.json`
- Approved events: `backend/data/events.json`
- Source state: `backend/data/source_state.json`
- Raw downloads: `backend/data/raw/<university>/<session>/`
- Review proposals: `backend/data/proposals/`
- Sync pipeline: `backend/scripts/sync_calendars.py`
- Event model: `backend/app/models.py`
- Proposal boundary model: `backend/app/extraction_models.py`
- Tests: `backend/tests/`

## Phase 1: Establish scope

Before running anything:

1. Read `backend/data/sources.json`.
2. Identify the exact university codes, source IDs, and academic session requested.
3. Inspect `backend/data/source_state.json`, existing proposals, raw downloads, and approved events.
4. Skip a source only when all of the following are true:
   - its current official source content hash matches the stored hash;
   - its proposal exists and is complete;
   - its proposal has already been independently reviewed;
   - its approved events are present and pass validation.
5. A recently generated proposal is not automatically a reviewed proposal.

State explicitly which sources will run and which verified sources will be skipped.

## Phase 2: Generate proposals

Load the project `.env` without printing its contents. Run the sync pipeline only for the requested universities. Use `--force` when the user asks to rerun unchanged sources.

Example:

```powershell
cd backend
uv run dotenv -f ..\.env run -- uv run python scripts/sync_calendars.py --force `
  --university uitm `
  --university unimap `
  --university um `
  --university ukm
```

Record for each source:

- resolved official URL;
- content hash;
- extraction method;
- candidate count;
- failure or retry information.

Do not publish at this stage.

## Phase 3: Perform structural checks

For every proposal, check:

- required fields are present;
- event type belongs to the allowed enum;
- `end_date` is not earlier than `start_date`;
- dates plausibly belong to the academic session;
- `source_page` points to a real page when applicable;
- evidence exists in the extracted source;
- titles do not contain OCR bullets, broken words, headers, or footers;
- semester and audience are supported by the source;
- no exact duplicates exist within the proposal;
- no unexplained duplicates exist across proposals for the same university;
- the proposal does not conflict with already approved events.

Flag every candidate below `0.95` confidence for additional attention, but do not assume candidates at or above `0.95` are correct.

## Phase 4: Visually inspect PDFs

For PDF sources:

1. Use `pdfinfo` to determine the page count and dimensions.
2. Render every relevant page to PNG with Poppler `pdftoppm` at a readable resolution.
3. Inspect the rendered images, not only Docling JSON.
4. Verify each proposed event against the visual source.

Pay special attention to:

- vertically merged cells;
- side-by-side programme columns;
- dates listed as one row per week;
- activities whose cell spans several date rows;
- separate diploma, bachelor, postgraduate, short-semester, and additional-semester tracks;
- notes that change dates for selected campuses, states, faculties, or audiences;
- footnotes using asterisks or alternative dates;
- public holidays printed inside a larger lecture period;
- bilingual rows where one language contains a typo;
- source typos that conflict with duration or surrounding chronology.

### Date-range verification

For every multi-day activity:

1. Identify the first date row visually covered by the activity cell.
2. Identify the final date row visually covered by that same cell.
3. Confirm the inclusive range agrees with the printed duration.
4. Confirm adjacent academic periods do not have unexplained gaps or overlaps.
5. If the printed duration and dates disagree, use surrounding chronology and bilingual text only when the intended value is unambiguous; otherwise hold the event.

Examples:

- A seven-week Monday-to-Sunday activity should normally span 49 inclusive days.
- A one-week break should normally span seven inclusive days.
- Do not assign the date rows from the left-hand programme column to a different activity in the right-hand programme column.

## Phase 5: Inspect HTML sources

For HTML sources:

1. Confirm the saved HTML came from the resolved official URL.
2. Locate the exact session panel or table.
3. Compare every candidate with the visible row text.
4. Preserve the site’s official titles and programme scope.
5. Ensure navigation links, unrelated sessions, and repeated mobile/desktop markup were not converted into duplicate events.

## Phase 6: Review event semantics

For each event, verify:

- `title`: exact official wording with extraction artifacts removed only when obvious;
- `start_date` and `end_date`: match the visually associated rows;
- `semester`: correct semester, session, or special-semester track;
- `audience`: correct programme or student group;
- `event_type`: best allowed category without inventing meaning;
- `source_url`: resolved official document URL;
- `source_page`: correct page number;
- `last_checked`: actual review date.

Do not collapse two events merely because their date ranges overlap. For example, revision week and an assessment may legitimately occur simultaneously.

Do consolidate events when they are genuinely the same university-wide event repeated in multiple programme sources. When consolidating:

- ensure title and dates are equivalent;
- merge the audience accurately;
- retain a defensible official source URL;
- do not merge programme-specific academic periods.

## Phase 7: Correct proposals safely

When a proposal is wrong:

1. Preserve the raw proposal as an audit artifact.
2. Document the correction in a deterministic review or publishing script.
3. State why the automated result was wrong.
4. Base corrected values on the rendered source, not intuition.
5. Do not silently change the normalizer output and pretend it was originally correct.

Typical correction reasons include:

- vertically merged table cell misassociation;
- OCR bullet included in the title;
- incorrect programme audience;
- duplicate holiday across programme calendars;
- a date range truncated to only part of the rows covered by an activity;
- separate additional and short semesters incorrectly combined.

## Phase 8: Publish with a scoped merge

Before writing `backend/data/events.json`:

1. Load and validate all existing events.
2. Define the exact reviewed university codes and academic session.
3. Preserve every existing event outside that scope.
4. Replace only events inside the reviewed scope.
5. Combine retained and reviewed events.
6. Generate deterministic, unique IDs matching `^[a-z0-9-]+$`.
7. Validate the entire combined collection with `CalendarEvent` before writing.
8. Sort events deterministically by date, university, title, and audience.
9. Write only after every validation succeeds.

Never use a whole-file overwrite that discards out-of-scope approved data.

## Phase 9: Required integrity checks

After publishing, verify:

- total event count;
- count per university;
- no duplicate IDs;
- no exact duplicate events;
- no invalid date ranges;
- no missing source URLs;
- no unknown universities;
- no events outside the intended session unless they were retained from another scope;
- every reviewed university has expected academic periods;
- ICS generation succeeds;
- API filtering returns only the requested university;
- spanning events are returned by date-overlap filtering.

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Also run `git diff --check` and inspect the final diff. Do not modify or discard unrelated user changes.

## Stop conditions

Stop and request human review instead of publishing when:

- the official source cannot be downloaded;
- the source is unreadable or incomplete;
- a proposal date cannot be associated with a specific visual table cell;
- two official sections contradict one another without a clear controlling note;
- programme or campus scope is ambiguous;
- a source appears outdated or belongs to another academic session;
- validation or tests fail;
- safe scoped merging cannot be guaranteed.

Clearly list held events and the exact reason each one was not published.

## Completion report

Report completion only after all checks pass. Include:

- reviewed sources;
- skipped sources and why they were safe to skip;
- candidate count per source;
- published count per university;
- corrections made;
- duplicates consolidated;
- events held back;
- test and integrity-check results;
- files changed.

Use precise language. Say “verified against the rendered official source” only when that visual comparison was actually performed. Never promise zero possible errors; instead, report the evidence and checks that reduce error risk.

# pypdf vs Docling Benchmark

## Decision

UniDate will use **Docling as its PDF extraction engine**.

Docling is substantially slower and heavier than pypdf, but it preserves table rows, columns, reading order, and page-level structure more reliably. Academic calendars are typically table-oriented, and UniDate runs extraction only during monthly source checks, so extraction accuracy is more important than interactive speed.

## Test setup

The extractors processed the same two locally downloaded university calendars:

1. **Universiti Malaya (UM)** — a simple one-page bachelor calendar.
2. **Universiti Kebangsaan Malaysia (UKM)** — a dense four-page calendar containing parallel semester columns.

Outputs were compared against the manually verified events in `backend/data/events.json`.

Environment:

- Python 3.14.6
- CPU extraction
- pypdf 6.16.1
- Current Docling release resolved by `uv`
- No LLM used during this benchmark

## Results

| Measurement | UM pypdf | UM Docling | UKM pypdf | UKM Docling |
|---|---:|---:|---:|---:|
| PDF pages | 1 | 1 | 4 | 4 |
| Extraction time | 0.110 s | 58.207 s | 0.202 s | 53.934 s |
| Output characters | 2,565 | 12,020 | 11,573 | 21,351 |
| Expected event titles retained | 100% | 100% | 100% | 100% |
| Replacement characters | 0 | 0 | 0 | 0 |
| Table structure retained | No | Yes | No | Yes |

The automated date-coverage proxy undercounted some UKM events for both extractors because the source abbreviates ranges such as `11 - 17 Jan. 2027`, omitting the year and month from the first date. Manual inspection confirmed that both outputs retained those dates. This proxy should not be interpreted as an extraction failure.

## UM observations

pypdf produced compact, readable text:

```text
Orientation (Week of Welcome) - WOW 1 week 26.09.2026 - 04.10.2026
Lectures 6 weeks 05.10.2026 - 15.11.2026
Mid Semester I Break 1 week 16.11.2026 - 22.11.2026
```

Docling reconstructed the source as a Markdown table:

```text
| Orientation (Week of Welcome) - WOW | 1 | week  | 26.09.2026 | - | 04.10.2026 |
| Lectures                             | 6 | weeks | 05.10.2026 | - | 15.11.2026 |
| Mid Semester I Break                 | 1 | week  | 16.11.2026 | - | 22.11.2026 |
```

Both outputs were suitable for semantic processing. pypdf was faster, while Docling supplied explicit cells and column relationships.

## UKM observations

pypdf retained the text but flattened the table into a linear stream:

```text
Minggu Ulangkaji/
Revision Week
11 - 17 Jan. 2027
11th - 17th Jan. 2027
```

This is readable, but the source contains Semester 1, Semester 2, and Semester 3 dates in parallel columns. Flattening makes it harder to determine which date belongs to which semester.

Docling reconstructed those relationships as table rows and columns:

```text
| Items         | Semester 1      | Duration | Semester 2      | Duration |
| Revision Week | 11–17 Jan. 2027 | 1 week   | 14–20 Jun. 2027 | 1 week   |
```

This representation is safer to pass to an LLM because the event title, semester, date range, and duration remain associated.

## Operational cost

Docling required a much larger environment than pypdf:

- 106 Python packages were resolved for the benchmark environment.
- Additional layout and OCR models were downloaded on first use.
- CPU extraction took approximately 54–58 seconds per tested document.
- Model initialization and first-run downloads add further cold-start time.

These costs are acceptable for UniDate because extraction runs monthly in a background job. Docling should not run inside a normal public API request.

## Implementation requirements

The production collection pipeline should:

1. Download and hash each public calendar source.
2. Skip Docling when the source hash has not changed.
3. Run Docling only inside the scheduled collection worker.
4. Export lossless Docling JSON and per-page Markdown.
5. Retain page numbers and bounding-box provenance where available.
6. Send the structured page output—not the raw PDF—to the normalization LLM.
7. Validate the LLM response with Pydantic and deterministic date checks.
8. Create a review proposal and GitHub pull request.
9. Never publish extracted events without human approval.
10. Cache Docling models in the worker or CI environment to avoid repeated downloads.

## Conclusion

For simple PDFs, pypdf is much faster and can preserve all required content. However, UniDate must support calendars with complex tables and multiple semester columns. Docling provides a more consistent structural representation across both simple and complex documents.

The benchmark therefore supports using **Docling only** for PDF extraction, with its runtime isolated to the monthly background collection workflow.

Benchmark artifacts are stored locally under `backend/data/raw/benchmarks/`. The reproducible benchmark script is `backend/scripts/benchmark_extractors.py`.

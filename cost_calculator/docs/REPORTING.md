# Part Cost PDF reporting

Part Cost PDFs are generated in-process with ReportLab. There is no Crystal
Reports runtime, `.rpt` file, .NET Framework process, Windows dependency, or
report-specific database credential.

The worksheet's **Open PDF** control remains unchanged. After a save supplies a
`ucpPartCostID`, it opens `/api/reports/part-cost/{PartCostID}`. The PDF represents
the last saved database snapshot; unsaved browser edits are not included.

## Document contents

`reporting/reportlab.py` creates a landscape Letter document containing:

- part, revision, quantity, costing date, user, and current-status metadata;
- raw and marked-up category totals;
- raw, marked-up, and retail unit-cost callouts;
- all saved material and operation lines;
- saved notes; and
- page numbers and a costing-run identifier on every page.

Tables repeat their headers across pages and wrap descriptions. Content is HTML
escaped before it reaches ReportLab paragraph markup.

## Runtime flow

1. FastAPI authenticates the request and verifies that the saved cost exists.
2. `reporting.render_part_cost_pdf` loads the saved operation and material lines.
3. ReportLab builds the PDF in memory.
4. FastAPI returns it inline with a sanitized filename.

No temporary report file is written. A missing costing run returns HTTP 404. An
unexpected rendering failure is logged server-side and returns a generic HTTP 500
without leaking database or report details.

## Development and verification

ReportLab and pypdf versions are pinned in `requirements.txt`. Run:

```powershell
.\cost_env\Scripts\python.exe -m unittest tests.test_reporting -v
```

The tests validate the PDF signature, extracted content, special-character
handling, multi-page table splitting, repeated headers, route behavior, and data
loading. For a layout change, also generate a representative long report, render
every page to PNG with Poppler, and visually inspect alignment and clipping.

The production smoke test is:

1. calculate and save a representative worksheet;
2. select **Open PDF**;
3. confirm materials, operations, totals, notes, headers, and page numbers;
4. compare the PDF totals with the saved worksheet; and
5. repeat with enough lines to create multiple pages.

## Retired implementation

The earlier Crystal renderer source remains in the working tree only as historical
material while pre-migration work is reconciled. It is not imported and is excluded
from the Linux image by `.dockerignore`. No `CRYSTAL_*` settings are used.

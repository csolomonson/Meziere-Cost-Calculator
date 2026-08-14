# Part cost PDF reporting

Part-cost PDFs are generated in-process with ReportLab. There is no Crystal
Reports runtime, `.rpt` file, .NET Framework process, Windows dependency, or
report-specific database credential.

After a save supplies a `ucpPartCostID`, the worksheet exposes two controls:

- **Internal PDF** opens `/api/reports/part-cost/{PartCostID}/internal`;
- **Customer PDF** opens `/api/reports/part-cost/{PartCostID}/customer`.

The compatibility route `/api/reports/part-cost/{PartCostID}` continues to return
the internal report. All reports represent the last saved database snapshot;
unsaved browser edits are not included.

## Documents

Both documents use monochrome portrait Letter pages, plain typography, horizontal
rules, and page footers. They do not use colored fills, boxed panels, or landscape
tables.

The **Internal Cost Analysis** is a self-contained cost audit. It includes:

- part, revision, production quantity, costing run, date, user, and saved status;
- total and per-unit cost conclusions plus the complete category build-up;
- a compact material and operation rollup immediately after the cost conclusion;
  the three headline figures share one horizontal band to leave more room for
  normal-sized routings on page one, while long lists continue cleanly on the next
  page with repeating headers;
- every backflushed material, including source provenance, quantity extension,
  purchasing increment or waste, unit-cost equation, inherited component costs,
  markup factor, and finished-part contribution;
- every saved operation in routing order, including work center, demand, batches,
  resets, time drivers, labor and machine equations, or outside-processing purchase
  source, followed by its cost contribution;
- a reconciliation of line detail to saved header totals, automatic review flags,
  and internal notes.

The **Customer Cost Summary** is an itemized receipt. It includes the part identity,
quantity, unit and extended price, then shows a unit and extended charge for every
backflushed material and every saved routing operation. Material, operation, other
saved-charge, and receipt totals reconcile the lines to the saved customer price.
It deliberately omits raw costs, supplier prices and documents, labor and machine
rates, markup factors, review flags, internal notes, and boilerplate limitations.

Non-backflushed materials are omitted from both reports. This rule is enforced in
the shared renderer before either document is assembled.

## Runtime flow

1. FastAPI authenticates the request and verifies that the saved cost exists.
2. `reporting.render_part_cost_pdf` loads the saved operation and material lines.
3. The renderer selects the internal or customer document and builds it in memory.
4. FastAPI returns it inline with a sanitized, audience-specific filename.

No temporary report file is written. A missing costing run returns HTTP 404. An
unexpected rendering failure is logged server-side and returns a generic HTTP 500
without leaking database or report details.

Set `COST_REPORT_COMPANY_NAME` to control the company name in report headers,
footers, and PDF metadata. The default is `Meziere Enterprises`.

## Development and verification

ReportLab and pypdf versions are pinned in `requirements.txt`. Run:

```powershell
.\cost_env\Scripts\python.exe -m unittest tests.test_reporting -v
```

The tests validate both audiences, portrait output, confidential-field omission,
backflush filtering, first-page line coverage for normal-sized routings, itemized
customer charges, exact material and operation coverage, source explanations,
pagination, route behavior, and data loading. For a layout change, generate both
representative reports, render every page to PNG with Poppler, and visually inspect
alignment, overflow, and clipping.

The production smoke test is:

1. calculate and save a representative worksheet;
2. open **Internal PDF** and confirm its sources, equations, totals, notes, and
   reconciliation against the saved worksheet;
3. open **Customer PDF** and confirm each included material and operation has a unit
   and extended charge, the receipt reconciles, and confidential inputs are absent;
4. confirm a non-backflushed material appears in neither document; and
5. repeat with enough lines to create multiple pages.

## Retired implementation

The earlier Crystal renderer source remains in the working tree only as historical
material while pre-migration work is reconciled. It is not imported and is excluded
from the Linux image by `.dockerignore`. No `CRYSTAL_*` settings are used.

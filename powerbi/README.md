# Power BI developer project

This directory provides a source-controlled Power BI Project (PBIP) starter,
semantic-model definition, governed DAX catalog, theme, page specification, and
static executive preview.

## Open and refresh

1. Enable Power BI Desktop developer mode and open `Process_Intelligence.pbip`.
2. In Power Query, replace each relative CSV path with the repository's absolute
   path if Desktop cannot resolve it.
3. Apply the types listed in `dashboard-spec.md`, refresh, and add the documented
   report pages.
4. Import `theme.json` and validate totals against `reports/demo-analysis.json`.

PBIP and PBIR are Microsoft preview/developer formats and can change. The
committed project intentionally keeps transformations transparent; the Python
pipeline remains the analytical system of record.

The repository does not claim a Power BI Desktop render was executed in CI,
because Desktop is not available in the Linux validation environment.

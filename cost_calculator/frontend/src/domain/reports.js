export function partCostReportUrl(partCostId) {
  const id = Number(partCostId);
  return Number.isInteger(id) && id > 0
    ? "/api/reports/part-cost/" + encodeURIComponent(id)
    : "";
}

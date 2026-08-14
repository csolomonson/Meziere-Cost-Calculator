export function partCostReportUrl(partCostId, audience = "internal") {
  const id = Number(partCostId);
  if (!Number.isInteger(id) || id <= 0) return "";
  if (audience !== "internal" && audience !== "customer") return "";
  return "/api/reports/part-cost/" + encodeURIComponent(id) + "/" + audience;
}

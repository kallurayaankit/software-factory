const cases = {
  ready: ["pass", "pass", "pass"],
  blocked: ["pass", "fail", "pass"],
  pending: ["pass", "pending", "pass"],
};
const names = ["Referral routes to the expected queue", "Retry does not create a duplicate referral", "Report labels its evidence as simulated"];
export function simulate(scenario) {
  if (!Object.hasOwn(cases, scenario)) throw new RangeError("Unknown scenario");
  const checks = names.map((name, i) => ({name, required: true, outcome: cases[scenario][i]}));
  return {scenario, fictional: true, checks, ready: checks.every(check => !check.required || check.outcome === "pass"), approval: null};
}
export function approve(review, confirmed) {
  if (!review || !review.ready || !review.checks.every(check => !check.required || check.outcome === "pass") || !confirmed) throw new Error("Review cannot be approved");
  return {...review, approval: {scope: "local simulation only", recordedAt: new Date().toISOString()}};
}

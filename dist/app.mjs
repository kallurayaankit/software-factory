import {simulate, approve} from "./review.mjs";
const get = (id) => document.getElementById(id);
let current = null;
const status = (message, state = "") => { get("status").textContent = message; get("status").dataset.state = state; };
function reset() {
  current = null;
  get("brief").textContent = "Verify a fictional referral form before release. A submitted referral should reach the expected queue; retrying should not create a duplicate.";
  status("Run a review to see the result.");
  get("checks").replaceChildren();
  get("gate").hidden = true;
  get("confirm").checked = false;
  get("approve").disabled = true;
  get("download").hidden = true;
}
get("scenario").addEventListener("change", reset);
get("run").addEventListener("click", () => {
  reset();
  current = simulate(get("scenario").value);
  status(current.ready ? "Ready for human review" : "Approval blocked by required evidence", current.ready ? "ready" : "blocked");
  for (const check of current.checks) {
    const item = document.createElement("li"), badge = document.createElement("strong");
    badge.textContent = check.outcome;
    badge.dataset.state = check.outcome;
    item.append(document.createTextNode(check.name), badge);
    get("checks").append(item);
  }
  get("gate").hidden = !current.ready;
  get("download").hidden = false;
});
get("confirm").addEventListener("change", () => { get("approve").disabled = !get("confirm").checked; });
get("approve").addEventListener("click", () => {
  current = approve(current, get("confirm").checked);
  status("Local approval recorded. No release was shipped.", "ready");
  get("gate").hidden = true;
});
get("download").addEventListener("click", () => {
  if (!current) return;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(current, null, 2)], {type:"application/json"}));
  link.download = "software-factory-review.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
});
reset();

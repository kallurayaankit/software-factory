import {test} from "node:test";
import assert from "node:assert/strict";
import {simulate, approve} from "../dist/review.mjs";
test("pass still requires a human confirmation", () => {
  const ready = simulate("ready");
  assert.equal(ready.ready, true);
  assert.equal(ready.approval, null);
  assert.throws(() => approve(ready, false));
  assert.equal(approve(ready, true).approval.scope, "local simulation only");
});
test("failed and pending gates block approval", () => {
  for (const scenario of ["blocked", "pending"]) {
    const review = simulate(scenario);
    assert.equal(review.ready, false);
    assert.throws(() => approve(review, true));
  }
});
test("unknown scenario is refused", () => assert.throws(() => simulate("__proto__")));

require("./streamlit_e2e");
require("./e2e_prerequisites");

/**
 * Shared Cypress support: teardown test users via DELETE /users/me (cascade DB + data/users tree).
 *
 * On failure, logs a structured block to stderr (visible in the Cypress CLI and in
 * artifacts/cypress_run.log when tests are run via scripts/run_cypress_e2e.py).
 *
 * Global `cy.visit('/docs')` before each test (FastAPI Swagger HTML — `/health` is JSON and
 * breaks `cy.visit`). Keeps a real page for `screenshotOnRunFailure` when later commands fail.
 * Set CYPRESS_SKIP_GLOBAL_VISIT=1 to disable (debug only).
 */

function _safeFullTitle(runnable) {
  if (!runnable) return "(unknown test)";
  if (typeof runnable.fullTitle === "function") {
    try {
      return runnable.fullTitle();
    } catch {
      /* ignore */
    }
  }
  return runnable.title || "(unknown test)";
}

function _suiteChain(runnable) {
  const parts = [];
  let p = runnable && runnable.parent;
  while (p && p.title) {
    parts.unshift(p.title);
    p = p.parent;
  }
  return parts.length ? parts.join(" › ") : "(top-level)";
}

function _appendHttpDetails(lines, err) {
  const r = err && (err.response || err.res);
  if (!r) return;
  if (r.status != null) lines.push(`HTTP status: ${r.status}`);
  const body = r.body;
  if (body === undefined) return;
  const s = typeof body === "string" ? body : JSON.stringify(body);
  const max = 2500;
  lines.push(`Response body (truncated to ${max} chars): ${s.slice(0, max)}`);
}

/** @param {Error} err @param {object | undefined} runnable Mocha runnable */
function logCypressFailureContext(err, runnable) {
  const specRel = Cypress.spec?.relative || Cypress.spec?.name || "(unknown spec)";
  const lines = [
    "",
    "========== CYPRESS FAILURE CONTEXT ==========",
    `Spec file: ${specRel}`,
    `Suite chain: ${_suiteChain(runnable)}`,
    `Test title: ${runnable?.title || "(unknown)"}`,
    `Full title: ${_safeFullTitle(runnable)}`,
    `Error message: ${err?.message || String(err)}`,
  ];
  _appendHttpDetails(lines, err);
  if (err?.stack) {
    lines.push("Stack (first 15 lines):");
    lines.push(
      err.stack.split("\n").slice(0, 15).join("\n"),
    );
  }
  lines.push(
    "Screenshot (if enabled): artifacts/cypress_screenshots/<spec>.cy.js/ — PNG on failure",
  );
  lines.push("============================================");
  console.error(lines.join("\n"));
}

Cypress.on("fail", (err, runnable) => {
  try {
    logCypressFailureContext(err, runnable);
  } catch (e) {
    console.error("[cypress] logCypressFailureContext failed:", e);
  }
  throw err;
});

beforeEach(function () {
  const skip = Cypress.env("SKIP_GLOBAL_VISIT");
  if (skip === true || skip === 1 || skip === "1" || String(skip).toLowerCase() === "true") {
    return;
  }
  const spec = (Cypress.spec && Cypress.spec.relative) || "";
  const norm = String(spec).replace(/\\/g, "/");
  if (norm.includes("/streamlit/")) {
    return;
  }
  // Streamlit UI journey (00–05): avoid hitting API /docs before cross-origin Streamlit visits.
  if (/e2e\/0[0-5]_/.test(norm)) {
    return;
  }
  cy.visit("/docs", {
    log: false,
    timeout: 60000,
  });
});

afterEach(function () {
  if (this.currentTest?.state !== "failed") return;
  const t = this.currentTest;
  const attempt = (t._currentRetry ?? 0) + 1;
  const max = (t.retries ?? 0) + 1;
  console.error(
    `[cypress-fail] Spec: ${Cypress.spec?.relative || "?"} | Attempt ${attempt}/${max} | duration ${t.duration ?? "?"}ms`,
  );
});

Cypress.Commands.add("deleteTestAccount", (tokenEnvKey, password) => {
  const token = Cypress.env(tokenEnvKey);
  if (!token || !password) {
    return cy.wrap(null, { log: false });
  }
  return cy
    .request({
      method: "DELETE",
      url: "/users/me",
      headers: { authorization: `Bearer ${token}` },
      body: { current_password: password },
      failOnStatusCode: false,
    })
    .then((resp) => {
      if (resp.status === 200) {
        Cypress.env(tokenEnvKey, undefined);
        return;
      }
      cy.log(
        `deleteTestAccount: DELETE /users/me returned ${resp.status}`,
        JSON.stringify(resp.body),
      );
    });
});

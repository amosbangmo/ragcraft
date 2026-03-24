/**
 * Streamlit UI E2E helpers (markers + session).
 * Chaîne : 00 → 01 → 02 → 03 ( + .e2e-streamlit-ingestion-verified.json) → 04–05.
 */

function streamlitOrigin() {
  return Cypress.env("STREAMLIT_ORIGIN") || "http://127.0.0.1:18975";
}

/** Mirrors ``_STREAMLIT_ACCESS_COOKIE`` in ``streamlit_auth.py`` (multipage auth rehydration). */
const RAGCRAFT_STREAMLIT_ACCESS_COOKIE = "ragcraft_streamlit_access";

/**
 * Reload Projects in the browser so session_state + sidebar agree with API (02→03+ handoff).
 */
Cypress.Commands.add("ragcraftStreamlitEnsureWorkspaceProject", () => {
  cy.task("e2eLoadStreamlitProject").then((p) => {
    expect(
      p?.projectId,
      "Run 02_project_creation.cy.js first in the same cypress run.",
    ).to.be.ok;
    Cypress.env("_ragcraft_e2e_project_id", p.projectId);
  });
  cy.then(() => {
    const pid = Cypress.env("_ragcraft_e2e_project_id");
    cy.ragcraftOpenStreamlitSidebarPage("projects");
    cy.get('[data-testid="project-page-root"]', { timeout: 120000 }).should(
      "exist",
    );
    // Project id may sit in a scroll/clipped region (expanders, wide tables).
    cy.contains(pid, { timeout: 120000 }).should("exist");
  });
});

Cypress.Commands.add("ragcraftMirrorAccessCookieForUser", (username, password) => {
  cy.task("e2eFetchAccessToken", { username, password }).then((tok) => {
    expect(tok, "access token from e2eFetchAccessToken").to.be.a("string").and.not.be
      .empty;
    cy.setCookie(RAGCRAFT_STREAMLIT_ACCESS_COOKIE, String(tok).trim(), {
      path: "/",
      sameSite: "lax",
    });
  });
});

/**
 * Collect input/textarea nodes in tree order, piercing open shadow roots (Streamlit 1.5x widgets).
 */
function collectFormControlsDeep(root) {
  const acc = [];
  function walk(node) {
    if (!node) return;
    if (node.nodeType === 1 && node.shadowRoot) {
      walk(node.shadowRoot);
    }
    if (node.nodeType === 1 && node.matches?.("input, textarea")) {
      const t = node.type;
      if (t !== "hidden" && t !== "file") {
        acc.push(node);
      }
    }
    const ch = node.children;
    if (ch) {
      for (let i = 0; i < ch.length; i += 1) {
        walk(ch[i]);
      }
    }
  }
  walk(root);
  return acc;
}

function collectFileInputsDeep(root) {
  const acc = [];
  function walk(node) {
    if (!node) return;
    if (node.nodeType === 1 && node.shadowRoot) {
      walk(node.shadowRoot);
    }
    if (node.nodeType === 1 && node.matches?.('input[type="file"]')) {
      acc.push(node);
    }
    const ch = node.children;
    if (ch) {
      for (let i = 0; i < ch.length; i += 1) {
        walk(ch[i]);
      }
    }
  }
  walk(root);
  return acc;
}

/** First visible text/password input after the marker in document order (querySelectorAll order). */
function queryInputAfterMarker(markerEl) {
  const doc = markerEl.ownerDocument;
  if (!doc || !doc.body) return null;
  const inputs = collectFormControlsDeep(doc.body);
  for (const inp of inputs) {
    const pos = markerEl.compareDocumentPosition(inp);
    if (pos & Node.DOCUMENT_POSITION_FOLLOWING) {
      return inp;
    }
  }
  return null;
}

/** Last input that precedes the marker (Streamlit sometimes mounts the widget before the markdown marker). */
function queryInputBeforeMarker(markerEl) {
  const doc = markerEl.ownerDocument;
  if (!doc || !doc.body) return null;
  const inputs = collectFormControlsDeep(doc.body);
  let best = null;
  for (const inp of inputs) {
    const pos = markerEl.compareDocumentPosition(inp);
    if (pos & Node.DOCUMENT_POSITION_PRECEDING) {
      best = inp;
    }
  }
  return best;
}

function queryInputNearMarker(markerEl) {
  return queryInputAfterMarker(markerEl) || queryInputBeforeMarker(markerEl);
}

function fixtureBasename(filePath) {
  const normalized = String(filePath).replace(/\\/g, "/");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || normalized;
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function queryFileInputNearMarker(markerEl) {
  const doc = markerEl.ownerDocument;
  if (!doc || !doc.body) return null;
  const inputs = collectFileInputsDeep(doc.body);
  let el = null;
  for (let i = inputs.length - 1; i >= 0; i -= 1) {
    const inp = inputs[i];
    const pos = markerEl.compareDocumentPosition(inp);
    if (pos & Node.DOCUMENT_POSITION_FOLLOWING) {
      el = inp;
      break;
    }
  }
  if (el) return el;
  for (let i = inputs.length - 1; i >= 0; i -= 1) {
    const inp = inputs[i];
    const pos = markerEl.compareDocumentPosition(inp);
    if (pos & Node.DOCUMENT_POSITION_PRECEDING) {
      el = inp;
      break;
    }
  }
  return el;
}

Cypress.Commands.add("ragcraftSelectFileNearMarker", (markerTestId, filePath) => {
  const nameRe = new RegExp(escapeRegExp(fixtureBasename(filePath)), "i");
  cy.get(`[data-testid="${markerTestId}"]`).then(($markers) => {
    const markers = $markers.toArray();
    let fileInput = null;
    for (let i = markers.length - 1; i >= 0; i -= 1) {
      const candidate = queryFileInputNearMarker(markers[i]);
      if (candidate) {
        fileInput = candidate;
        break;
      }
    }
    if (fileInput) {
      cy.wrap(fileInput).selectFile(filePath, { force: true });
      cy.contains(nameRe, { timeout: 120000 }).should("exist");
      return;
    }
    // Streamlit file_uploader lives in shadow DOM; avoid ``stMainBlockContainer`` (not all versions expose it).
    cy.get('input[type="file"]', { includeShadowDom: true })
      .last()
      .selectFile(filePath, { force: true });
    cy.contains(nameRe, { timeout: 120000 }).should("exist");
  });
});

Cypress.Commands.add("ragcraftStreamlitOrigin", () => cy.wrap(streamlitOrigin()));

/** Substrings matched against st.page_link href (case-insensitive). */
const SIDEBAR_HREF_FRAG = {
  projects: "projects",
  ingestion: "ingestion",
  chat: "chat",
  settings: "settings",
};

/**
 * Streamlit multipage: a bare cy.visit("/projects") breaks asset URLs (/_stcore under /projects → 404).
 * Open the main app root, then click the matching sidebar link by href (stable vs split emoji/text DOM).
 * @param {"projects"|"ingestion"|"chat"|"settings"} pageKey
 */
Cypress.Commands.add("ragcraftOpenStreamlitSidebarPage", (pageKey) => {
  const frag = SIDEBAR_HREF_FRAG[pageKey];
  expect(frag, `unknown sidebar page key: ${pageKey}`).to.be.a("string");
  cy.visit(`${streamlitOrigin()}/`, { timeout: 120000 });
  cy.url({ timeout: 120000 }).should("not.include", "/login");
  cy.get('[data-testid="stSidebar"]', { timeout: 120000 })
    .should("be.visible")
    .find("a[href]")
    .filter(
      (_, el) =>
        (el.getAttribute("href") || "").toLowerCase().includes(frag.toLowerCase()),
    )
    .first()
    .click({ force: true });
});

Cypress.Commands.add("ragcraftTypeAfterMarker", (markerTestId, text) => {
  // Streamlit reruns can append extra marker divs *after* widgets; those have no following input.
  // Walk markers from newest toward oldest until one is followed by an input in tree order.
  cy.get(`[data-testid="${markerTestId}"]`).then(($markers) => {
    const markers = $markers.toArray();
    let el = null;
    for (let i = markers.length - 1; i >= 0; i -= 1) {
      const candidate = queryInputNearMarker(markers[i]);
      if (candidate) {
        el = candidate;
        break;
      }
    }
    expect(el, `visible input after [data-testid="${markerTestId}"]`).to.not.be.null;
    // Single ``type`` avoids Streamlit rerender detaching the subject between ``clear`` and ``type``.
    cy.wrap(el).focus().type(`{selectall}{backspace}${text}`, { force: true });
  });
});

Cypress.Commands.add("ragcraftStreamlitEnsureSession", () => {
  cy.session(
    "ragcraft-streamlit-auth",
    () => {
      // Do not nest cy.* inside cy.task().then — it breaks the command queue under cy.session.
      cy.task("e2eLoadStreamlitUser").then((c) => {
        expect(
          c,
          "Run 00_register_flow.cy.js first in the same cypress run to create creds.",
        ).to.not.be.null;
        Cypress.env("_ragcraft_e2e_user", c);
      });
      cy.then(() => {
        const c = Cypress.env("_ragcraft_e2e_user");
        expect(c, "e2e user from task").to.not.be.null;
        cy.visit(`${streamlitOrigin()}/login`, { timeout: 120000 });
        cy.get('[data-testid="auth-page-root"]', { timeout: 120000 }).should("exist");
        cy.contains("button", "I have an account").click();
        cy.get('[data-testid="auth-toggle-login"]')
          .last()
          .should("have.attr", "data-e2e-active", "true");
        cy.get('[data-testid="login-email-input"]', { timeout: 120000 }).should("exist");
        cy.ragcraftTypeAfterMarker("login-email-input", c.username);
        cy.ragcraftTypeAfterMarker("login-password-input", c.password);
        cy.contains("button", "Log in").click({ force: true });
        cy.get('[data-testid="project-page-root"]', { timeout: 180000 }).should(
          "exist",
        );
        cy.ragcraftMirrorAccessCookieForUser(c.username, c.password);
        cy.contains("Manage your knowledge bases", { timeout: 60000 }).should(
          "be.visible",
        );
      });
    },
    {
      cacheAcrossSpecs: true,
      validate() {
        cy.visit(`${streamlitOrigin()}/`, { timeout: 120000 });
        cy.url({ timeout: 60000 }).should("not.include", "/login");
      },
    },
  );
});

module.exports = { streamlitOrigin };

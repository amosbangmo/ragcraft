/**
 * SCENARIO 1–2: open auth surface + register a new user (browser only, no API shortcuts).
 * Writes cypress/.e2e-streamlit-creds.json pour la suite ; 01 → login vérifié ; 03 → ingestion vérifiée (prérequis de 04).
 *
 * Note: RAGCraft uses username + display name (not email). Markers named *-email-* map to username.
 */
describe("Streamlit register flow", () => {
  const origin = () =>
    Cypress.env("STREAMLIT_ORIGIN") || "http://127.0.0.1:18975";

  before(() => {
    cy.task("e2eClearStreamlitUser");
    if (typeof Cypress.session?.clearAllSavedSessions === "function") {
      Cypress.session.clearAllSavedSessions();
    }
  });

  it("opens the app root and shows the auth surface", () => {
    cy.visit(`${origin()}/`, { timeout: 120000 });
    cy.get('[data-testid="auth-page-root"], [data-testid="ragcraft-login-shell"]', {
      timeout: 120000,
    })
      .first()
      .should("exist");
    cy.get('[data-testid="ragcraft-login-shell"]').should("be.visible");
  });

  it("registers via UI (click Register, fill fields, submit)", () => {
    const username = `e2e_ui_${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
    const password = "E2eRegister_Flow_Passw0rd!!";

    cy.visit(`${origin()}/login`, { timeout: 120000 });
    cy.get('[data-testid="auth-page-root"]').should("exist");

    cy.contains("button", "Register").click();
    cy.get('[data-testid="auth-toggle-register"]', { timeout: 120000 })
      .last()
      .should("have.attr", "data-e2e-active", "true");

    cy.ragcraftTypeAfterMarker("register-display-name-input", "E2E Cypress User");
    cy.ragcraftTypeAfterMarker("register-email-input", username);
    cy.ragcraftTypeAfterMarker("register-password-input", password);
    cy.ragcraftTypeAfterMarker("register-confirm-password-input", password);

    cy.get('[data-testid="register-submit-button"]').should("exist");
    cy.contains("button", "Create account").click();

    cy.get('[data-testid="register-success-banner"]', { timeout: 180000 }).should(
      "exist",
    );
    cy.contains("Manage your knowledge bases", { timeout: 180000 }).should(
      "be.visible",
    );
    cy.get('[data-testid="sidebar-nav-projects"]', { timeout: 120000 }).should(
      "exist",
    );

    cy.ragcraftMirrorAccessCookieForUser(username, password);

    cy.task("e2eSaveStreamlitUser", { username, password });
  });

  it("shows auth-error-banner when passwords do not match", () => {
    cy.visit(`${origin()}/login`, { timeout: 120000 });
    cy.contains("button", "Register").click();
    cy.ragcraftTypeAfterMarker("register-display-name-input", "Bad User");
    cy.ragcraftTypeAfterMarker("register-email-input", `bad_${Date.now()}`);
    cy.ragcraftTypeAfterMarker("register-password-input", "aaaaaaaa");
    cy.ragcraftTypeAfterMarker("register-confirm-password-input", "bbbbbbbb");
    cy.contains("button", "Create account").click();
    cy.get('[data-testid="auth-error-banner"]', { timeout: 60000 }).should("exist");
  });
});

/**
 * SCENARIO 3: sign in through Streamlit widgets (browser only).
 * Depends on 00_register_flow.cy.js (creds file).
 */
describe("Streamlit login flow", () => {
  const origin = () =>
    Cypress.env("STREAMLIT_ORIGIN") || "http://127.0.0.1:18975";

  it("logs in with saved credentials and shows the workspace shell", () => {
    cy.task("e2eLoadStreamlitUser").then((c) => {
      expect(c, "run 00_register_flow first").to.not.be.null;

      cy.visit(`${origin()}/login`, { timeout: 120000 });
      cy.get('[data-testid="auth-page-root"]').should("exist");

      cy.contains("button", "I have an account").click();
      cy.get('[data-testid="auth-toggle-login"]')
        .last()
        .should("have.attr", "data-e2e-active", "true");

      cy.ragcraftTypeAfterMarker("login-email-input", c.username);
      cy.ragcraftTypeAfterMarker("login-password-input", c.password);
      cy.get('[data-testid="login-submit-button"]').should("exist");
      cy.contains("button", "Log in").click();

      cy.contains("Manage your knowledge bases", { timeout: 180000 }).should(
        "be.visible",
      );
      cy.get('[data-testid="sidebar-nav-projects"]').should("exist");
      cy.get('[data-testid="project-page-root"]', { timeout: 120000 }).should(
        "exist",
      );

      cy.ragcraftMirrorAccessCookieForUser(c.username, c.password);
      cy.task("e2eSaveStreamlitLoginVerified");
    });
  });
});

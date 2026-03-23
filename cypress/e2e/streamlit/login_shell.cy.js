/**
 * Browser proof against the real Streamlit app (iframe shell).
 * Requires run_cypress_e2e.py to set CYPRESS_STREAMLIT_ORIGIN (Streamlit on 127.0.0.1:18975).
 */
describe("Streamlit login / shell", () => {
  const origin =
    Cypress.env("STREAMLIT_ORIGIN") || "http://127.0.0.1:18975";

  it("renders login card with stable data-testid inside Streamlit iframe", () => {
    cy.visit(`${origin}/login`, { timeout: 120000 });
    cy.get("iframe", { timeout: 120000 }).should("have.length.at.least", 1);
    cy.get("iframe")
      .first()
      .its("0.contentDocument.body")
      .should(($b) => {
        expect($b.innerHTML).to.match(/data-testid="ragcraft-login-shell"/);
        expect($b.innerText).to.match(/Welcome to RAGCraft|Sign in/i);
      });
  });
});

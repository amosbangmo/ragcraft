/**
 * SCENARIO 7: change retrieval defaults on Settings and save (browser only).
 * sidebar-nav-retrieval-settings → Settings page (project retrieval defaults).
 */
describe("Streamlit retrieval settings", () => {
  beforeEach(() => {
    cy.ragcraftStreamlitEnsureSession();
    cy.ragcraftStreamlitEnsureWorkspaceProject();
  });

  it("opens settings, toggles advanced, saves, and shows success", () => {
    cy.ragcraftOpenStreamlitSidebarPage("settings");
    cy.get('[data-testid="settings-page-root"]', { timeout: 180000 }).should("exist");
    cy.contains("Retrieval defaults").should("be.visible");
    cy.get('[data-testid="sidebar-nav-retrieval-settings"]').should("exist");

    cy.contains("Advanced: override query rewrite", {
      timeout: 120000,
    }).should("be.visible");
    cy.contains("Advanced: override query rewrite")
      .parent()
      .parent()
      .find('input[type="checkbox"]')
      .click({ force: true });

    cy.get('[data-testid="retrieval-save-button"]').should("exist");
    cy.contains("button", "Save retrieval defaults").click();

    cy.get('[data-testid="retrieval-settings-success-banner"]', {
      timeout: 120000,
    }).should("exist");
    cy.contains("Retrieval defaults saved.", { matchCase: false }).should("exist");
  });
});

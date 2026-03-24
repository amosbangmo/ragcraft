/**
 * SCENARIO 4: create a project from the Projects page (browser only).
 */
describe("Streamlit project creation", () => {
  beforeEach(() => {
    cy.ragcraftStreamlitEnsureSession();
  });

  it("creates a project and shows the success banner", () => {
    const projectId = `e2e_proj_${Date.now()}`;

    cy.ragcraftOpenStreamlitSidebarPage("projects");
    cy.get('[data-testid="project-page-root"]', { timeout: 120000 }).should("exist");
    cy.contains("Manage your knowledge bases").should("be.visible");

    cy.get('[data-testid="project-create-section"]').should("exist");
    cy.get('[data-testid="project-name-input"]').should("exist");
    // Streamlit may mount the text field before/after the marker or inside shadow DOM; placeholder is stable.
    cy.get('input[placeholder="e.g. annual-report-2024"]', { timeout: 120000 })
      .should("exist")
      .clear({ force: true })
      .type(projectId, { force: true });
    cy.get('[data-testid="project-create-button"]').should("exist");
    cy.contains("button", "Create project").click();

    cy.get('[data-testid="project-created-banner"]', { timeout: 120000 }).should(
      "exist",
    );
    cy.contains(projectId).should("be.visible");
    cy.get('[data-testid="project-selector-root"]', { timeout: 120000 }).should(
      "exist",
    );
    cy.task("e2eSaveStreamlitProject", { projectId });
  });
});

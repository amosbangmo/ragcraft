/**
 * SCENARIO 5: upload a document on Ingestion (browser only).
 * Dépend de 02 (projet). Écrit .e2e-streamlit-ingestion-verified.json pour le spec 04.
 */
describe("Streamlit ingestion flow", () => {
  beforeEach(() => {
    cy.ragcraftStreamlitEnsureSession();
    cy.ragcraftStreamlitEnsureWorkspaceProject();
  });

  it("uploads mini.pdf and processes it", () => {
    cy.ragcraftOpenStreamlitSidebarPage("ingestion");
    cy.get('[data-testid="ingestion-page-root"]', { timeout: 180000 }).should("exist");
    cy.contains("Add documents to a project").should("be.visible");

    cy.get('[data-testid="project-selector-root"]', { timeout: 120000 }).should(
      "exist",
    );
    cy.contains("No project available yet").should("not.exist");

    cy.get('[data-testid="ingestion-file-input"]').should("exist");
    cy.ragcraftSelectFileNearMarker(
      "ingestion-file-input",
      "cypress/fixtures/mini.pdf",
    );

    cy.get('[data-testid="ingestion-submit-button"]').should("exist");
    // Streamlit reruns after file_uploader changes; clicking Process before the server pass
    // finishes leaves `uploaded_files` empty → `can_run=False` and the click is ignored (180s timeout, no error text).
    // Do not assert ``be.visible``: Streamlit main blocks often clip controls (overflow), which fails in headless Cypress.
    cy.contains("button", "Process uploaded documents", { timeout: 120000 })
      .should("exist")
      .scrollIntoView()
      .should("not.be.disabled");
    cy.wait(1500);
    cy.contains("button", "Process uploaded documents").click({ force: true });

    // ``format_ingestion_success_message`` always includes ``processed <n> multimodal asset``.
    // Filename prefix varies (``Mini.pdf`` vs ``mini.pdf``); do not anchor on it.
    cy.get("body", { timeout: 180000 }).should(($b) => {
      const t = $b.text();
      if (/Please upload at least one document/i.test(t)) {
        throw new Error(
          "Streamlit saw Process with an empty file_uploader — increase wait after selectFile or fix file input targeting",
        );
      }
      if (/No document was processed/i.test(t)) {
        throw new Error(
          "ingestion ran with an empty file list (Cypress/file_uploader vs armed snapshot) — check ingestion.py INGESTION_ARMED_FILES_KEY / Process click path",
        );
      }
      if (/Failed to process uploaded documents/i.test(t)) {
        const m = t.match(/Failed to process uploaded documents[^\n]*/i);
        throw new Error(
          `ingestion error visible: ${m ? m[0] : t.slice(0, 600)}`,
        );
      }
      expect(
        t,
        "expected ingestion success copy (processed N multimodal asset)",
      ).to.match(/processed\s+\d+\s+multimodal asset/i);
    });
    cy.get('[data-testid="ingestion-success-banner"]', { timeout: 120000 }).should("exist");
    cy.contains(/mini\.pdf/i).should("exist");
    cy.task("e2eSaveStreamlitIngestionVerified");
  });
});

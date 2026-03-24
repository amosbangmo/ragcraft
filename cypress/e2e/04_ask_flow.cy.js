/**
 * SCENARIO 6: ask a question in Chat (browser only).
 * Prérequis : 03_ingestion_flow (marqueur .e2e-streamlit-ingestion-verified.json).
 */
describe("Streamlit ask / chat flow", () => {
  beforeEach(() => {
    cy.ragcraftStreamlitEnsureSession();
    cy.ragcraftStreamlitEnsureWorkspaceProject();
  });

  it("submits a question and shows a non-empty answer with sources section", () => {
    cy.ragcraftOpenStreamlitSidebarPage("chat");
    cy.get('[data-testid="chat-page-root"]', { timeout: 180000 }).should("exist");
    cy.contains("Talk to your documents").should("be.visible");

    cy.get('[data-testid="project-selector-root"]', { timeout: 120000 }).should(
      "exist",
    );
    cy.contains("No project available yet").should("not.exist");

    cy.get('[data-testid="ask-submit"]').should("exist");
    cy.get('[data-testid="stChatInput"]', { timeout: 120000 }).should("exist");
    // Single ``type`` avoids Streamlit rerender detaching the subject between ``clear`` and ``type``.
    cy.get('[data-testid="stChatInput"] textarea')
      .should("be.visible")
      .focus()
      .type("{selectall}{backspace}What is this document about?", { force: true });
    cy.get('[data-testid="stChatInput"]')
      .find("button")
      .filter(":visible")
      .not("[disabled]")
      .last()
      .click({ force: true });

    // ``OPENAI_API_KEY=ci-test-key`` (run_cypress_e2e) → deterministic stub in the assistant bubble.
    cy.contains(/E2E stub answer \(ci-test-key\)/, { timeout: 180000 }).should("exist");
    cy.get('[data-testid="answer-container"]', { timeout: 120000 }).should("exist");

    cy.get("body").should(($b) => {
      expect($b.text()).to.match(/source|Source|Confidence|prompt/i);
    });
  });
});

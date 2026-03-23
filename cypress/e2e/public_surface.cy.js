/**
 * Browser E2E against live uvicorn (same checks as former Playwright tests).
 */
describe("public API surface", () => {
  it("OpenAPI /docs renders", () => {
    cy.visit("/docs", { timeout: 60000 });
    cy.title().should("satisfy", (t) => /RAGCraft|FastAPI/i.test(t || ""));
  });

  it("/health exposes ok or JSON", () => {
    cy.request({ url: "/health", timeout: 60000 }).then((resp) => {
      expect(resp.status).to.eq(200);
      const raw =
        typeof resp.body === "string"
          ? resp.body
          : JSON.stringify(resp.body);
      const lower = raw.toLowerCase();
      const ok = lower.includes("ok") || raw.includes("{");
      expect(ok, "response mentions ok or contains JSON").to.be.true;
    });
  });
});

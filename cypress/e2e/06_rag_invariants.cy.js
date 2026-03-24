/**
 * HTTP invariants : forme des latences pipeline inspect/ask, drapeaux retrieval (API, cy.request).
 * Compte + auth : même utilisateur que 00_register / 01_login (prérequis dans support/e2e_prerequisites.js).
 */
const LATENCY_KEYS = [
  "query_rewrite_ms",
  "retrieval_ms",
  "reranking_ms",
  "prompt_build_ms",
  "answer_generation_ms",
  "total_ms",
];

describe("RAG pipeline HTTP invariants", () => {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
  const projectId = `raginv_${suffix}`;

  const auth = (token) => ({ authorization: `Bearer ${token}` });

  const sharedToken = () => Cypress.env("_ragcraft_api_shared_token");

  before(() => {
    const token = sharedToken();
    expect(token, "token API partagé (before global 06)").to.be.a("string").and.not
      .be.empty;
    cy.request({
      method: "POST",
      url: "/projects",
      headers: auth(token),
      body: { project_id: projectId },
    }).then((r) => expect(r.status).to.eq(201));
  });

  const baseBody = (overrides = {}) => ({
    project_id: projectId,
    question: "Invariant check question?",
    chat_history: [],
    ...overrides,
  });

  it("pipeline inspect exposes latency keys and zero answer_generation before ask", () => {
    const token = sharedToken();
    cy.request({
      method: "POST",
      url: "/chat/pipeline/inspect",
      headers: auth(token),
      body: baseBody(),
      failOnStatusCode: false,
      timeout: 180000,
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      if (resp.body.status !== "ok" || !resp.body.pipeline) {
        cy.log("no_pipeline — skip deep latency assertions");
        return;
      }
      const pl = resp.body.pipeline;
      expect(pl).to.include.keys(
        "retrieval_mode",
        "query_rewrite_enabled",
        "hybrid_retrieval_enabled",
        "latency",
      );
      const lat = pl.latency;
      expect(lat).to.be.an("object");
      LATENCY_KEYS.forEach((k) => {
        expect(lat, `latency.${k}`).to.have.property(k);
        expect(lat[k]).to.be.a("number");
      });
      expect(lat.answer_generation_ms).to.eq(0);
    });
  });

  it("chat ask returns latency with non-negative answer_generation_ms", () => {
    const token = sharedToken();
    cy.request({
      method: "POST",
      url: "/chat/ask",
      headers: auth(token),
      body: baseBody(),
      failOnStatusCode: false,
      timeout: 180000,
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      expect(resp.body).to.include.keys("status", "latency");
      const lat = resp.body.latency;
      if (!lat) {
        expect(resp.body.status).to.eq("no_pipeline");
        return;
      }
      LATENCY_KEYS.forEach((k) => {
        expect(lat, `latency.${k}`).to.have.property(k);
      });
      expect(lat.answer_generation_ms).to.be.at.least(0);
      expect(lat.total_ms).to.be.at.least(lat.answer_generation_ms);
    });
  });

  it("ask answered status implies latency tracks retrieval stage", () => {
    const token = sharedToken();
    cy.request({
      method: "POST",
      url: "/chat/ask",
      headers: auth(token),
      body: baseBody(),
      failOnStatusCode: false,
      timeout: 180000,
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      if (resp.body.status !== "answered" || !resp.body.latency) return;
      expect(resp.body.latency.retrieval_ms).to.be.a("number").and.to.be.at.least(0);
    });
  });

  it("retrieval_mode reflects hybrid override on inspect when pipeline ok", () => {
    const token = sharedToken();
    cy.request({
      method: "POST",
      url: "/chat/pipeline/inspect",
      headers: auth(token),
      body: baseBody({
        enable_hybrid_retrieval_override: true,
        enable_query_rewrite_override: true,
      }),
      failOnStatusCode: false,
      timeout: 180000,
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      if (resp.body.status !== "ok" || !resp.body.pipeline) return;
      expect(resp.body.pipeline.hybrid_retrieval_enabled).to.eq(true);
      expect(resp.body.pipeline.retrieval_mode).to.be.a("string");
    });
  });
});

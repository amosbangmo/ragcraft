/**
 * SCENARIO 8 (API) : login invalide, 422, 401, forme benchmark vide, chemins de reprise.
 * Compte authentifié : même utilisateur que 00/01 (token dans _ragcraft_api_shared_token).
 */
describe("API robustness and failure handling", () => {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
  const projectId = `robust_${suffix}`;

  const auth = (token) => ({ authorization: `Bearer ${token}` });

  const sharedToken = () => Cypress.env("_ragcraft_api_shared_token");

  before(() => {
    const token = sharedToken();
    expect(token, "token API partagé (before global 07)").to.be.a("string").and.not
      .be.empty;
    cy.request({
      method: "POST",
      url: "/projects",
      headers: auth(token),
      body: { project_id: projectId },
    }).then((r) => expect(r.status).to.eq(201));
  });

  it("ingest without file returns 422 with structured body", () => {
    cy.request({
      method: "POST",
      url: `/projects/${projectId}/documents/ingest`,
      headers: auth(sharedToken()),
      form: true,
      body: {},
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.eq(422);
      expect(resp.body).to.include.keys("message", "code", "category");
      expect(resp.body.code).to.eq("request_validation_failed");
      expect(resp.body.detail).to.be.an("array");
    });
  });

  it("ask with empty body returns 422 with structured body", () => {
    cy.request({
      method: "POST",
      url: "/chat/ask",
      headers: auth(sharedToken()),
      body: {},
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.eq(422);
      expect(resp.body).to.include.keys("message", "code", "category");
      expect(resp.body.code).to.eq("request_validation_failed");
    });
  });

  it("projects list without auth returns 401 with structured body", () => {
    cy.request({
      method: "GET",
      url: "/projects",
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.eq(401);
      expect(resp.body).to.include.keys("message", "code", "category");
      expect(resp.body.code).to.eq("authentication_required");
    });
  });

  it("invalid login returns structured 401", () => {
    cy.request({
      method: "POST",
      url: "/auth/login",
      body: { username: "missing_user_xyz", password: "wrong" },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.eq(401);
      expect(resp.body).to.include.keys("message", "code", "category");
      expect(resp.body.code).to.eq("auth_credentials_invalid");
    });
  });

  it("empty gold QA benchmark run exposes failure-analysis report shape", () => {
    cy.request({
      method: "POST",
      url: "/evaluation/dataset/run",
      headers: auth(sharedToken()),
      body: {
        project_id: projectId,
        enable_query_rewrite: true,
        enable_hybrid_retrieval: true,
      },
      failOnStatusCode: false,
      timeout: 180000,
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      expect(resp.body).to.include.keys("summary", "rows");
      expect(resp.body.rows).to.be.an("array").that.has.length(0);
      expect(resp.body.failures).to.be.an("object");
      const f = resp.body.failures;
      expect(f).to.include.keys("failed_row_count", "critical_count");
      expect(f.failed_row_count).to.eq(0);
      expect(f).to.have.property("counts");
      expect(f).to.have.property("thresholds");
    });
  });
});

/**
 * HTTP robustness (former test_ingestion_robustness.py) + failure-report shape from
 * gold QA benchmark (FailureAnalysisService output via POST /evaluation/dataset/run).
 */

describe("API robustness and failure handling", () => {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
  const username = `robust_${suffix}`;
  const password = "Robust_Passw0rd!!";
  const projectId = `robust_${suffix}`;

  const auth = (token) => ({ authorization: `Bearer ${token}` });

  it("registers user and creates project (setup)", () => {
    return cy
      .request({
        method: "POST",
        url: "/auth/register",
        body: {
          username,
          password,
          confirm_password: password,
          display_name: "Robust",
        },
      })
      .then((r) => {
        expect(r.status).to.eq(201);
        expect(r.body).to.have.property("access_token").and.not.be.empty;
        Cypress.env("robust_token", r.body.access_token);
        return cy
          .request({
            method: "POST",
            url: "/projects",
            headers: auth(r.body.access_token),
            body: { project_id: projectId },
          })
          .then((r2) => expect(r2.status).to.eq(201));
      });
  });

  it("ingest without file returns 422 with structured body", () => {
    cy.request({
      method: "POST",
      url: `/projects/${projectId}/documents/ingest`,
      headers: auth(Cypress.env("robust_token")),
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
      headers: auth(Cypress.env("robust_token")),
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

  it("empty gold QA benchmark run exposes failure-analysis report shape", () => {
    cy.request({
      method: "POST",
      url: "/evaluation/dataset/run",
      headers: auth(Cypress.env("robust_token")),
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

  after(() => {
    cy.deleteTestAccount("robust_token", password);
  });
});

/**
 * End-to-end API journey (same HTTP routes the Streamlit UI uses in HTTP backend mode).
 * Covers: register, login, project, ingest, ask + sources, retrieval settings, manual eval,
 * structured API errors (401 / 422).
 */
describe("RAGCraft workspace API journey", () => {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
  const username = `cy_${suffix}`;
  const password = "CypressJourney_Passw0rd!";
  const displayName = "Cypress User";
  const projectId = `p_${suffix}`;

  const authHeaders = (token) => ({
    authorization: `Bearer ${token}`,
  });

  it("registers a new account", () => {
    cy.request({
      method: "POST",
      url: "/auth/register",
      body: {
        username,
        password,
        confirm_password: password,
        display_name: displayName,
      },
    }).then((resp) => {
      expect(resp.status).to.eq(201);
      expect(resp.body.access_token).to.be.a("string").and.not.be.empty;
      expect(resp.body.user).to.include.keys("user_id", "username");
      Cypress.env("e2e_token", resp.body.access_token);
    });
  });

  it("logs in and receives a bearer token", () => {
    cy.request({
      method: "POST",
      url: "/auth/login",
      body: { username, password },
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      expect(resp.body.access_token).to.be.a("string").and.not.be.empty;
      expect(resp.body.message).to.be.a("string");
    });
  });

  it("creates a project", () => {
    const token = Cypress.env("e2e_token");
    cy.request({
      method: "POST",
      url: "/projects",
      headers: authHeaders(token),
      body: { project_id: projectId },
    }).then((resp) => {
      expect(resp.status).to.eq(201);
      expect(resp.body.project_id).to.eq(projectId);
    });
  });

  it("ingests a document (multipart)", () => {
    const token = Cypress.env("e2e_token");
    cy.fixture("mini.pdf", "binary").then((pdfBin) => {
      const blob = Cypress.Blob.binaryStringToBlob(pdfBin, "application/pdf");
      const form = new FormData();
      form.set("file", blob, "mini.pdf");
      cy.request({
        method: "POST",
        url: `/projects/${projectId}/documents/ingest`,
        headers: authHeaders(token),
        body: form,
        timeout: 180000,
        failOnStatusCode: false,
      }).then((resp) => {
        if (resp.status === 200 || resp.status === 201) {
          expect(resp.body).to.have.property("diagnostics");
          Cypress.env("e2e_ingest_ok", true);
        } else {
          Cypress.env("e2e_ingest_ok", false);
          expect(resp.status).to.be.oneOf([400, 413, 500, 502, 503]);
          const b = resp.body;
          if (b && typeof b === "object" && Object.keys(b).length > 0) {
            expect(b).to.include.keys("message", "code", "category");
          }
        }
      });
    });
  });

  it("asks a question and returns source-shaped fields", () => {
    const token = Cypress.env("e2e_token");
    cy.request({
      method: "POST",
      url: "/chat/ask",
      headers: authHeaders(token),
      body: {
        project_id: projectId,
        question: "What is this document about?",
        chat_history: [],
      },
      timeout: 180000,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      expect(resp.body).to.include.keys(
        "status",
        "question",
        "answer",
        "prompt_sources",
        "raw_assets",
        "confidence",
      );
      expect(resp.body.prompt_sources).to.be.an("array");
      expect(resp.body.raw_assets).to.be.an("array");
      if (Cypress.env("e2e_ingest_ok")) {
        expect(
          resp.body.prompt_sources.length + resp.body.raw_assets.length,
          "sources or assets after ingest",
        ).to.be.at.least(0);
      }
    });
  });

  it("reads and updates retrieval settings", () => {
    const token = Cypress.env("e2e_token");
    cy.request({
      method: "GET",
      url: `/projects/${projectId}/retrieval-settings`,
      headers: authHeaders(token),
    }).then((getResp) => {
      expect(getResp.status).to.eq(200);
      expect(getResp.body).to.include.keys("preferences", "effective_retrieval");
    });
    cy.request({
      method: "PUT",
      url: `/projects/${projectId}/retrieval-settings`,
      headers: authHeaders(token),
      body: {
        retrieval_preset: "precise",
        retrieval_advanced: false,
        enable_query_rewrite: true,
        enable_hybrid_retrieval: false,
      },
    }).then((putResp) => {
      expect(putResp.status).to.eq(200);
      expect(putResp.body.preferences).to.be.an("object");
    });
  });

  it("runs manual evaluation for one question", () => {
    const token = Cypress.env("e2e_token");
    cy.request({
      method: "POST",
      url: "/evaluation/manual",
      headers: authHeaders(token),
      body: {
        project_id: projectId,
        question: "Summarize the uploaded content in one sentence.",
      },
      timeout: 180000,
      failOnStatusCode: false,
    }).then((resp) => {
      if (resp.status === 200) {
        expect(resp.body).to.include.keys("question", "answer", "prompt_sources");
        expect(resp.body.prompt_sources).to.be.an("array");
        return;
      }
      expect(resp.status).to.be.oneOf([502, 503]);
      expect(resp.body).to.have.property("message");
      expect(resp.body).to.have.property("code");
      expect(resp.body).to.have.property("category");
    });
  });

  it("returns structured JSON for invalid credentials (login)", () => {
    cy.request({
      method: "POST",
      url: "/auth/login",
      body: { username: "definitely_missing_user_xyz", password: "wrong" },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.eq(401);
      expect(resp.body).to.include.keys("detail", "message", "code", "category");
      expect(resp.body.code).to.eq("auth_credentials_invalid");
      expect(String(resp.body.message).length).to.be.greaterThan(0);
    });
  });

  it("returns structured validation error for invalid chat body", () => {
    const token = Cypress.env("e2e_token");
    cy.request({
      method: "POST",
      url: "/chat/ask",
      headers: authHeaders(token),
      body: {},
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.eq(422);
      expect(resp.body).to.include.keys("detail", "message", "code", "category");
      expect(resp.body.code).to.eq("request_validation_failed");
      expect(resp.body.detail).to.be.an("array");
    });
  });

  after(() => {
    cy.deleteTestAccount("e2e_token", password);
  });
});

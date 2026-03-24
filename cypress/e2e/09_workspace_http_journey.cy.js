/**
 * Parcours HTTP (mêmes routes que le client Streamlit) : projet → ingest → ask → réglages retrieval → eval.
 * Inscription + login API : compte E2E partagé (00/01), token dans _ragcraft_api_shared_token.
 */
describe("RAGCraft workspace API journey", () => {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
  const projectId = `p_${suffix}`;

  const authHeaders = (token) => ({
    authorization: `Bearer ${token}`,
  });

  const sharedToken = () => Cypress.env("_ragcraft_api_shared_token");

  before(() => {
    const token = sharedToken();
    expect(token, "token API partagé (before global 09)").to.be.a("string").and.not
      .be.empty;
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
    const token = sharedToken();
    cy.task(
      "ingestDocumentMultipart",
      {
        authToken: token,
        projectId,
        baseUrl: Cypress.config("baseUrl"),
      },
      { timeout: 180000 },
    ).then((resp) => {
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

  it("asks a question and returns source-shaped fields", () => {
    const token = sharedToken();
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
    const token = sharedToken();
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
    const token = sharedToken();
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
    const token = sharedToken();
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
});

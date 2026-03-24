/**
 * Prérequis globaux par spec : 00 → 01 → … ; 04 exige aussi 03 (ingestion vérifiée).
 * Les specs API 06/07/09 réutilisent le même compte que le parcours Streamlit (token via POST /auth/login).
 * 08_public_surface : sans compte (surface publique uniquement).
 */

function specBaseName() {
  const rel =
    (Cypress.spec && Cypress.spec.relative) || Cypress.spec?.name || "";
  const norm = String(rel).replace(/\\/g, "/");
  const i = norm.lastIndexOf("/");
  return i >= 0 ? norm.slice(i + 1) : norm;
}

const NO_ACCOUNT_PREREQ = new Set([
  "00_register_flow.cy.js",
  "08_public_surface.cy.js",
]);

const MSG_CREDS =
  "Prérequis manquants : exécutez 00_register_flow.cy.js en premier pour créer le compte E2E (fichier cypress/.e2e-streamlit-creds.json).";

const MSG_LOGIN =
  "Prérequis manquants : exécutez 01_login_flow.cy.js après l'inscription pour valider la connexion Streamlit (fichier cypress/.e2e-streamlit-login-verified.json).";

const MSG_PROJECT =
  "Prérequis manquants : exécutez 02_project_creation.cy.js pour créer un projet (fichier cypress/.e2e-streamlit-project.json).";

const MSG_INGESTION =
  "Prérequis manquants : exécutez 03_ingestion_flow.cy.js pour ingérer un document (fichier cypress/.e2e-streamlit-ingestion-verified.json).";

before(function () {
  const base = specBaseName();
  if (!base || NO_ACCOUNT_PREREQ.has(base)) {
    return;
  }

  cy.task("e2eLoadStreamlitUser").then((c) => {
    expect(c && c.username && c.password, MSG_CREDS).to.be.ok;
  });

  if (base === "01_login_flow.cy.js") {
    return;
  }

  cy.task("e2eLoadStreamlitLoginVerified").then((v) => {
    expect(v && v.verifiedAt, MSG_LOGIN).to.be.ok;
  });

  if (/^03_|^04_|^05_/.test(base)) {
    cy.task("e2eLoadStreamlitProject").then((p) => {
      expect(p && p.projectId, MSG_PROJECT).to.be.ok;
    });
  }

  if (/^04_/.test(base)) {
    cy.task("e2eLoadStreamlitIngestionVerified").then((v) => {
      expect(v && v.verifiedAt, MSG_INGESTION).to.be.ok;
    });
  }

  if (/^(06_|07_|09_)/.test(base)) {
    cy.task("e2eLoadStreamlitUser").then((c) => {
      return cy
        .request({
          method: "POST",
          url: "/auth/login",
          body: { username: c.username, password: c.password },
        })
        .then((resp) => {
          expect(
            resp.status,
            "POST /auth/login doit réussir avec le compte E2E Streamlit (même base que 00/01).",
          ).to.eq(200);
          expect(resp.body.access_token)
            .to.be.a("string")
            .and.not.be.empty;
          Cypress.env("_ragcraft_api_shared_token", resp.body.access_token);
        });
    });
  }
});

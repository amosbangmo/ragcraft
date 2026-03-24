const path = require("path");
const fs = require("fs");
const http = require("http");
const https = require("https");
const { URL } = require("url");
const { defineConfig } = require("cypress");
const FormData = require("form-data");

/**
 * Node multipart ingest: cy.request + browser FormData can yield an empty parsed JSON body on
 * some platforms; the API returns full IngestDocumentResponse including diagnostics.
 */
const E2E_STREAMLIT_CREDS = path.join(
  __dirname,
  "cypress",
  ".e2e-streamlit-creds.json",
);

const E2E_STREAMLIT_PROJECT = path.join(
  __dirname,
  "cypress",
  ".e2e-streamlit-project.json",
);

const E2E_STREAMLIT_LOGIN_VERIFIED = path.join(
  __dirname,
  "cypress",
  ".e2e-streamlit-login-verified.json",
);

const E2E_STREAMLIT_INGESTION_VERIFIED = path.join(
  __dirname,
  "cypress",
  ".e2e-streamlit-ingestion-verified.json",
);

function ingestDocumentMultipartTask({ authToken, projectId, baseUrl }) {
  const root = path.resolve(__dirname);
  const pdfPath = path.join(root, "cypress", "fixtures", "mini.pdf");
  if (!fs.existsSync(pdfPath)) {
    throw new Error(`Fixture missing: ${pdfPath}`);
  }
  const u = new URL(baseUrl || "http://127.0.0.1:18976");
  const isHttps = u.protocol === "https:";
  const lib = isHttps ? https : http;
  const port = u.port ? Number(u.port) : isHttps ? 443 : 80;
  const form = new FormData();
  form.append("file", fs.createReadStream(pdfPath), "mini.pdf");

  return new Promise((resolve, reject) => {
    const req = lib.request(
      {
        hostname: u.hostname,
        port,
        path: `/projects/${encodeURIComponent(projectId)}/documents/ingest`,
        method: "POST",
        headers: {
          ...form.getHeaders(),
          authorization: `Bearer ${authToken}`,
        },
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          let body;
          try {
            body = raw ? JSON.parse(raw) : {};
          } catch (e) {
            body = { _parse_error: String(e), _raw: raw.slice(0, 2000) };
          }
          resolve({ status: res.statusCode, body });
        });
      },
    );
    req.setTimeout(180000, () => {
      req.destroy();
      reject(new Error("ingestDocumentMultipartTask timeout (180s)"));
    });
    req.on("error", reject);
    form.pipe(req);
  });
}

/** POST /auth/login (API) to obtain JWT for ``ragcraft_streamlit_access`` cookie (Streamlit multipage). */
function e2eFetchAccessTokenTask({ username, password }) {
  if (!username || !password) {
    return Promise.resolve(null);
  }
  const u = new URL(process.env.CYPRESS_BASE_URL || "http://127.0.0.1:18976");
  const isHttps = u.protocol === "https:";
  const lib = isHttps ? https : http;
  const port = u.port ? Number(u.port) : isHttps ? 443 : 80;
  const payload = JSON.stringify({ username, password });
  return new Promise((resolve, reject) => {
    const req = lib.request(
      {
        hostname: u.hostname,
        port,
        path: "/auth/login",
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(payload, "utf8"),
        },
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          try {
            const body = raw ? JSON.parse(raw) : {};
            const tok = body && body.access_token;
            resolve(tok ? String(tok) : null);
          } catch {
            resolve(null);
          }
        });
      },
    );
    req.on("error", reject);
    req.write(payload);
    req.end();
  });
}

module.exports = defineConfig({
  video: true,
  videosFolder: "artifacts/cypress_videos",
  screenshotOnRunFailure: true,
  screenshotsFolder: "artifacts/cypress_screenshots",
  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || "http://127.0.0.1:18976",
    env: {
      // Set CYPRESS_SKIP_GLOBAL_VISIT=1 to skip the per-test cy.visit (support/e2e.js).
      SKIP_GLOBAL_VISIT: process.env.CYPRESS_SKIP_GLOBAL_VISIT,
      STREAMLIT_ORIGIN: process.env.CYPRESS_STREAMLIT_ORIGIN,
    },
    setupNodeEvents(on) {
      on("task", {
        ingestDocumentMultipart: ingestDocumentMultipartTask,
        e2eSaveStreamlitUser({ username, password }) {
          fs.mkdirSync(path.dirname(E2E_STREAMLIT_CREDS), { recursive: true });
          fs.writeFileSync(
            E2E_STREAMLIT_CREDS,
            JSON.stringify({ username, password }, null, 0),
            "utf8",
          );
          return null;
        },
        e2eLoadStreamlitUser() {
          if (!fs.existsSync(E2E_STREAMLIT_CREDS)) {
            return null;
          }
          try {
            return JSON.parse(fs.readFileSync(E2E_STREAMLIT_CREDS, "utf8"));
          } catch {
            return null;
          }
        },
        e2eClearStreamlitUser() {
          try {
            if (fs.existsSync(E2E_STREAMLIT_CREDS)) {
              fs.unlinkSync(E2E_STREAMLIT_CREDS);
            }
            if (fs.existsSync(E2E_STREAMLIT_PROJECT)) {
              fs.unlinkSync(E2E_STREAMLIT_PROJECT);
            }
            if (fs.existsSync(E2E_STREAMLIT_LOGIN_VERIFIED)) {
              fs.unlinkSync(E2E_STREAMLIT_LOGIN_VERIFIED);
            }
            if (fs.existsSync(E2E_STREAMLIT_INGESTION_VERIFIED)) {
              fs.unlinkSync(E2E_STREAMLIT_INGESTION_VERIFIED);
            }
          } catch {
            /* ignore */
          }
          return null;
        },
        e2eSaveStreamlitLoginVerified() {
          fs.mkdirSync(path.dirname(E2E_STREAMLIT_LOGIN_VERIFIED), {
            recursive: true,
          });
          fs.writeFileSync(
            E2E_STREAMLIT_LOGIN_VERIFIED,
            JSON.stringify(
              { verifiedAt: new Date().toISOString() },
              null,
              0,
            ),
            "utf8",
          );
          return null;
        },
        e2eLoadStreamlitLoginVerified() {
          if (!fs.existsSync(E2E_STREAMLIT_LOGIN_VERIFIED)) {
            return null;
          }
          try {
            return JSON.parse(
              fs.readFileSync(E2E_STREAMLIT_LOGIN_VERIFIED, "utf8"),
            );
          } catch {
            return null;
          }
        },
        e2eSaveStreamlitIngestionVerified() {
          fs.mkdirSync(path.dirname(E2E_STREAMLIT_INGESTION_VERIFIED), {
            recursive: true,
          });
          fs.writeFileSync(
            E2E_STREAMLIT_INGESTION_VERIFIED,
            JSON.stringify(
              { verifiedAt: new Date().toISOString() },
              null,
              0,
            ),
            "utf8",
          );
          return null;
        },
        e2eLoadStreamlitIngestionVerified() {
          if (!fs.existsSync(E2E_STREAMLIT_INGESTION_VERIFIED)) {
            return null;
          }
          try {
            return JSON.parse(
              fs.readFileSync(E2E_STREAMLIT_INGESTION_VERIFIED, "utf8"),
            );
          } catch {
            return null;
          }
        },
        e2eFetchAccessToken: e2eFetchAccessTokenTask,
        e2eSaveStreamlitProject({ projectId }) {
          try {
            if (fs.existsSync(E2E_STREAMLIT_INGESTION_VERIFIED)) {
              fs.unlinkSync(E2E_STREAMLIT_INGESTION_VERIFIED);
            }
          } catch {
            /* ignore */
          }
          fs.mkdirSync(path.dirname(E2E_STREAMLIT_PROJECT), { recursive: true });
          fs.writeFileSync(
            E2E_STREAMLIT_PROJECT,
            JSON.stringify({ projectId }, null, 0),
            "utf8",
          );
          return null;
        },
        e2eLoadStreamlitProject() {
          if (!fs.existsSync(E2E_STREAMLIT_PROJECT)) {
            return null;
          }
          try {
            return JSON.parse(fs.readFileSync(E2E_STREAMLIT_PROJECT, "utf8"));
          } catch {
            return null;
          }
        },
      });
    },
    specPattern: "cypress/e2e/**/*.cy.js",
    supportFile: "cypress/support/e2e.js",
    defaultCommandTimeout: 120000,
    pageLoadTimeout: 120000,
    requestTimeout: 120000,
    responseTimeout: 120000,
  },
  reporter: "cypress-multi-reporters",
  reporterOptions: {
    reporterEnabled: "spec, mocha-junit-reporter",
    mochaJunitReporterReporterOptions: {
      mochaFile:
        process.env.CYPRESS_JUNIT_FILE || "artifacts/cypress_junit.xml",
      toConsole: true,
    },
  },
});

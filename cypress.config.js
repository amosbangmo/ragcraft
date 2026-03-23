const { defineConfig } = require("cypress");

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

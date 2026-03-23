const { defineConfig } = require("cypress");

module.exports = defineConfig({
  video: false,
  screenshotOnRunFailure: false,
  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || "http://127.0.0.1:18976",
    specPattern: "cypress/e2e/**/*.cy.js",
    supportFile: "cypress/support/e2e.js",
    defaultCommandTimeout: 120000,
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

/**
 * After API registration, exercise Streamlit login widgets in the browser (same session the UI uses).
 */
describe("Streamlit authenticated landing", () => {
  const origin =
    Cypress.env("STREAMLIT_ORIGIN") || "http://127.0.0.1:18975";
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
  const username = `cy_st_${suffix}`;
  const password = "CypressStreamlit_Passw0rd!";
  const displayName = "Cypress Streamlit";

  before(() => {
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
    });
  });

  after(() => {
    cy.request({
      method: "POST",
      url: "/auth/login",
      body: { username, password },
    }).then((login) => {
      if (login.status !== 200) return;
      const token = login.body.access_token;
      cy.request({
        method: "DELETE",
        url: "/users/me",
        headers: { authorization: `Bearer ${token}` },
        body: { current_password: password },
        failOnStatusCode: false,
      });
    });
  });

  it("logs in through Streamlit and shows the app shell", () => {
    cy.visit(`${origin}/login`, { timeout: 120000 });
    cy.get("iframe", { timeout: 120000 })
      .first()
      .its("0.contentDocument")
      .should("exist")
      .then((doc) => {
        const textInputs = doc.querySelectorAll('input[type="text"]');
        const passwords = doc.querySelectorAll('input[type="password"]');
        expect(textInputs.length).to.be.at.least(1);
        expect(passwords.length).to.be.at.least(1);
        cy.wrap(textInputs[0]).clear().type(username, { delay: 0 });
        cy.wrap(passwords[0]).clear().type(password, { delay: 0 });
      });
    cy.get("iframe")
      .first()
      .then(($iframe) => {
        const doc = $iframe[0].contentDocument;
        const btn = Array.from(doc.querySelectorAll("button")).find((b) =>
          /sign in/i.test((b.textContent || "").trim()),
        );
        expect(btn, "Sign in button in Streamlit iframe").to.exist;
        cy.wrap(btn).click({ force: true });
      });
    cy.url({ timeout: 180000 }).should("satisfy", (u) => !String(u).includes("/login"));
    cy.get("iframe", { timeout: 120000 })
      .first()
      .its("0.contentDocument.body.innerHTML")
      .should((html) => {
        expect(html).to.match(/ragcraft-app-shell|Projects|sidebar|RAGCraft/i);
      });
  });
});

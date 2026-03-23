/**
 * Shared Cypress support: teardown test users via DELETE /users/me (cascade DB + data/users tree).
 */

Cypress.Commands.add("deleteTestAccount", (tokenEnvKey, password) => {
  const token = Cypress.env(tokenEnvKey);
  if (!token || !password) {
    return cy.wrap(null, { log: false });
  }
  return cy
    .request({
      method: "DELETE",
      url: "/users/me",
      headers: { authorization: `Bearer ${token}` },
      body: { current_password: password },
      failOnStatusCode: false,
    })
    .then((resp) => {
      if (resp.status === 200) {
        Cypress.env(tokenEnvKey, undefined);
        return;
      }
      cy.log(
        `deleteTestAccount: DELETE /users/me returned ${resp.status}`,
        JSON.stringify(resp.body),
      );
    });
});

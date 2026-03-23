# Cypress — périmètre E2E navigateur

**Cypress** est le cadre E2E navigateur **canonique** du dépôt. Il s’exécute via **`npm run cy:ci`** (wrapper **`scripts/run_cypress_e2e.py`**), qui démarre l’API E2E (**`127.0.0.1:18976`**), puis **Streamlit** (**`127.0.0.1:18975`**) pointant sur cette API, puis lance **`cypress run`**.

## Exécution locale

- Dépendances Node : **`npm ci`**
- Variables typiques : **`RAGCRAFT_JWT_SECRET`**, **`OPENAI_API_KEY`** (voir **`scripts/run_cypress_e2e.py`** / CI)
- Désactiver Streamlit dans la manette E2E (API + specs HTTP uniquement) : **`RAGCRAFT_CYPRESS_SKIP_STREAMLIT=1`**

## Artefacts

| Fichier / dossier | Rôle |
|-------------------|------|
| **`artifacts/cypress_junit.xml`** | JUnit agrégé (reporter Mocha) |
| **`artifacts/cypress_run.log`** | Sortie CLI Cypress |
| **`artifacts/cypress_screenshots/`** | Captures sur échec |
| **`artifacts/cypress_videos/`** | Vidéos d’exécution (succès ou échec selon durée) |
| **`artifacts/E2E_UI_JOURNEY_MAP.txt`** | Carte specs → parcours (régénéré par **`scripts/generate_artifacts.py`**) |
| **`artifacts/CYPRESS_REPORT.txt`** | Résumé humain court |

## Specs et parcours

| Spec | Couverture |
|------|------------|
| **`cypress/e2e/public_surface.cy.js`** | **`/docs`** OpenAPI dans le navigateur ; **`/health`** via **`cy.request`**. |
| **`cypress/e2e/workspace_journey.cy.js`** | Parcours **HTTP** aligné sur le client Streamlit : auth, projet, ingest, ask, sources, réglages retrieval, eval manuelle, erreurs. |
| **`cypress/e2e/rag_invariants.cy.js`** | Invariants RAG (routes chat / inspect, latences, labels de mode). |
| **`cypress/e2e/robustness_failure.cy.js`** | 401, 422, erreurs structurées, états vides, enchaînement après erreur. |
| **`cypress/e2e/streamlit/login_shell.cy.js`** | **Streamlit réel** : page **`/login`**, iframe, **`data-testid="ragcraft-login-shell"`**. |
| **`cypress/e2e/streamlit/authenticated_landing.cy.js`** | Login via widgets Streamlit puis vérification du shell (**`data-testid="ragcraft-app-shell"`** ou navigation). |

## Hors périmètre (explicite)

- **Accessibilité** complète (WCAG) et **tests visuels** pixel-perfect.
- **Charge / performance** réseau au-delà des timeouts Cypress.
- **Tous** les widgets Streamlit sur **toutes** les pages (la suite cible les chemins critiques ci-dessus).
- **LLM / embeddings réels** en CI par défaut (souvent mocks ou clés de test limitées).

## CI

Le workflow **`.github/workflows/ci.yml`** enchaîne **`npm ci`** et **`npm run cy:ci`** après les tests Python principaux, avec les mêmes artefacts JUnit/logs que localement.

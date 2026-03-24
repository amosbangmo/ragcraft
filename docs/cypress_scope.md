# Cypress — périmètre E2E navigateur

**Cypress** est le cadre E2E **canonique**. Exécution : **`npm run cy:ci`** (**`scripts/run_cypress_e2e.py`**), qui démarre l’API (**`127.0.0.1:18976`**), **Streamlit** (**`127.0.0.1:18975`**) puis **`cypress run`**.

## Exécution locale

- **`npm ci`**
- Variables : **`RAGCRAFT_JWT_SECRET`**, **`OPENAI_API_KEY`**, **`PYTHONIOENCODING=utf-8`** (recommandé sous Windows pour les logs du script Python)
- Streamlit désactivé (HTTP seul) : **`RAGCRAFT_CYPRESS_SKIP_STREAMLIT=1`** (les specs **00–05** échoueront sans UI)

## Artefacts

| Fichier / dossier | Rôle |
|-------------------|------|
| **`artifacts/cypress_junit.xml`** | JUnit (Mocha multi-reporters) |
| **`artifacts/cypress_run.log`** | Sortie CLI |
| **`artifacts/cypress_screenshots/`** | Échecs |
| **`artifacts/cypress_videos/`** | Vidéos |
| **`artifacts/E2E_UI_JOURNEY_MAP.txt`** | Carte specs → parcours (**`generate_artifacts.py`**) |
| **`artifacts/CYPRESS_REPORT.txt`** | Résumé court |

## Specs (ordre lexicographic)

### Parcours Streamlit UI (navigateur uniquement, `data-testid`)

Les specs **`00_`–`05_`** enchaînent **inscription → connexion Streamlit vérifiée → session → produit**. Après **`00_register_flow.cy.js`**, le fichier **`cypress/.e2e-streamlit-creds.json`** (gitignored) contient les identifiants ; **`01_login_flow.cy.js`** écrit **`cypress/.e2e-streamlit-login-verified.json`**. Sans ce dernier, **`02`–`05`** ne s’exécutent pas (hook global **`cypress/support/e2e_prerequisites.js`**). **`03`–`05`** exigent en plus **`cypress/.e2e-streamlit-project.json`** (**`02_project_creation.cy.js`**). **`03_ingestion_flow.cy.js`** écrit **`cypress/.e2e-streamlit-ingestion-verified.json`** ; **`04_ask_flow.cy.js`** l’exige (ingestion avant chat). Une nouvelle sauvegarde de projet (**`e2eSaveStreamlitProject`**) supprime ce marqueur pour forcer un nouvel ingest. La session Cypress **`cacheAcrossSpecs`** réutilise la connexion pour **`02`–`05`**.

Les specs **`06`**, **`07`**, **`09`** réutilisent le **même compte** (fichiers ci-dessus + connexion API **`POST /auth/login`** dans le hook global) et créent chacune un **projet HTTP dédié** (suffixe aléatoire).

| Spec | Rôle |
|------|------|
| **`cypress/e2e/00_register_flow.cy.js`** | Racine `/`, surface auth, **inscription UI** obligatoire en premier, bannière succès / erreur mots de passe |
| **`cypress/e2e/01_login_flow.cy.js`** | **Connexion UI** avec compte sauvegardé |
| **`cypress/e2e/02_project_creation.cy.js`** | Création de projet |
| **`cypress/e2e/03_ingestion_flow.cy.js`** | Upload + traitement document |
| **`cypress/e2e/04_ask_flow.cy.js`** | Chat / question-réponse + sources |
| **`cypress/e2e/05_retrieval_settings.cy.js`** | Paramètres de retrieval (**page Settings** ; lien **`sidebar-nav-retrieval-settings`**) |

**Note modèle RAGCraft :** compte **username + display name** (pas d’e-mail). Les hooks **`register-email-input` / `login-email-input`** ciblent le champ **username** pour alignement avec le prompt E2E.

### API HTTP (`cy.request`, baseUrl API)

| Spec | Rôle |
|------|------|
| **`cypress/e2e/06_rag_invariants.cy.js`** | Invariants RAG (inspect / ask, latences, modes) — compte **00/01** |
| **`cypress/e2e/07_robustness_failure.cy.js`** | 401 / 422, benchmark vide, erreurs structurées — compte **00/01** |
| **`cypress/e2e/08_public_surface.cy.js`** | **`/docs`**, **`/health`** (sans compte) |
| **`cypress/e2e/09_workspace_http_journey.cy.js`** | Parcours HTTP complet (ingest via **`ingestDocumentMultipart`**) — compte **00/01** |

## Support

- **`cypress/support/streamlit_e2e.js`** — commandes **`ragcraftTypeAfterMarker`**, **`ragcraftStreamlitEnsureSession`**
- **`cypress/support/e2e_prerequisites.js`** — prérequis **compte + login vérifié** (et **projet** pour **`03`–`05`**, **ingestion vérifiée** pour **`04`**), token API partagé pour **`06`/`07`/`09`**
- **`cypress.config.js`** — tâches **`e2eSaveStreamlitUser`**, **`e2eLoadStreamlitUser`**, **`e2eSaveStreamlitLoginVerified`**, **`e2eLoadStreamlitLoginVerified`**, **`e2eSaveStreamlitIngestionVerified`**, **`e2eLoadStreamlitIngestionVerified`**, **`e2eClearStreamlitUser`**, **`ingestDocumentMultipart`**

## Hors périmètre

- WCAG complet, perfs réseau hors timeouts, tous les widgets Streamlit, LLM réels en CI par défaut.

## CI

**`.github/workflows/ci.yml`** — **`npm ci`**, **`npm run cy:ci`** après les tests Python.

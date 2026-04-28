# Rasa App (Deprecated)

Ce service est conservé temporairement pour rollback uniquement.

Le moteur NLU principal est désormais `nlu-app/` (FastAPI + spaCy + scikit-learn).

## Rollback

Si tu dois revenir sur Rasa rapidement:

- redéploie `rasa-app`
- mets `RASA_URL` de `chatbotsamir-api` vers l'URL de `chatbotsamir-rasa`
- redéploie `chatbotsamir-api`

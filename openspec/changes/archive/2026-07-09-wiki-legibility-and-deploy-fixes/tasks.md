## 1. Automatic dedup + summary generation during ingestion

- [x] 1.1 Add a helper (in `src/pipeline/ingest.py`) that, given the entity store/Ollama client/chat model, runs `find_duplicate_groups` across the whole entity store, merges any confirmed groups, then generates and caches a summary for every entity still missing one.
- [x] 1.2 Wire this helper into `ingest_pdf()`, running after entity extraction, wrapped in the same "enhancement, not core to success" try/except pattern already used for entity extraction.
- [x] 1.3 Unit/integration tests: dedup runs across pre-existing entities from other documents, not just the new one; summary generation is skipped for entities that already have one; a failure in either step doesn't fail ingestion.

## 2. AWS deployment fixes

- [x] 2.1 `setup_ec2.sh` / `pyproject.toml` / `README.md`: Python 3.11 -> 3.10 (matches Ubuntu 22.04's default, avoids needing the deadsnakes PPA; nothing in the codebase needs 3.11-only features - verified directly).
- [x] 2.2 `deploy/nginx-buddharauer.conf`: ship HTTP-only, remove the premature `listen 443 ssl` block that would fail `nginx -t` before Certbot has run.
- [x] 2.3 Re-verify the full test suite still passes and re-run the shell syntax check on `setup_ec2.sh`.

## 3. Masthead rename

- [x] 3.1 Rename the user-facing masthead from "Buddharauer" to "Malifaux Document Explorer" in `src/frontend/app.py` (browser tab title + on-page heading), `src/wiki/templates/*.html` (page titles), `README.md`, and `src/api/main.py`'s FastAPI title. Leave internal identifiers (systemd units, directory paths, Python package name, log messages) unchanged.

## 4. Verify & ship

- [x] 4.1 Run the full test suite, confirm green.
- [x] 4.2 Restart backend + frontend, smoke-test chat/wiki/admin.
- [x] 4.3 Update the session 5 log.
- [x] 4.4 Archive this OpenSpec change (sync specs first), commit and push to `session-5`.

## 1. Config

- [x] 1.1 Add `AuthConfig` (`admin_password: str | None`) to `src/utils/config.py`, loaded from `auth.admin_password`; treat missing/absent config as "no password set"
- [x] 1.2 Add `auth.admin_password` to `config.example.yaml` with a placeholder and a comment explaining it must be set for uploads to work; regenerate local `config.yaml` with a real local value

## 2. Backend

- [x] 2.1 Add `admin_password: str = Form(...)` to `POST /api/documents/upload` in `src/api/routes/documents.py`
- [x] 2.2 Reject with `401` (using `hmac.compare_digest`) when the password is missing, wrong, or no admin password is configured
- [x] 2.3 Unit/integration tests: correct password succeeds, wrong password is rejected with 401 and does not ingest, missing config rejects all uploads

## 3. Frontend

- [x] 3.1 Add an admin password `gr.Textbox(type="password")` next to the upload widget in `src/frontend/app.py`
- [x] 3.2 Update `src/frontend/api_client.py`'s `upload_document` to send the password as a form field
- [x] 3.3 Surface a clear "incorrect admin password" message in the upload status area on a 401 response, distinct from other upload failures

## 4. Verification

- [x] 4.1 Run full test suite, confirm all green
- [x] 4.2 Manual/Playwright check: upload with correct password succeeds; upload with wrong/blank password shows an auth error and does not appear in the document list

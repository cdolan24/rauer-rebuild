## 1. Shared auth helper

- [x] 1.1 Create `src/utils/auth.py` with `verify_admin_password(configured: str | None, provided: str) -> bool` (constant-time compare, treats missing config as always-invalid)
- [x] 1.2 Refactor `src/api/routes/documents.py`'s upload endpoint to use the shared helper (no behavior change)

## 2. Backend endpoint

- [x] 2.1 Add `src/api/routes/auth.py` with `POST /api/auth/verify` using the shared helper
- [x] 2.2 Register the new router in `src/api/main.py`
- [x] 2.3 Tests: correct password succeeds, wrong/missing password returns 401, no admin password configured returns 401

## 3. Frontend restructure

- [x] 3.1 Remove the upload widget and admin password field from the main page in `src/frontend/app.py`
- [x] 3.2 Add an `/admin` page via `demo.route("Admin", "/admin")`: password field + "Unlock" button, hidden upload form revealed on successful verify, error message on failure
- [x] 3.3 Wire the unlock flow through `ApiClient` (new `verify_admin_password` method) and keep the verified password in `gr.State` for the upload call

## 4. Verification

- [x] 4.1 Run full test suite, confirm all green
- [x] 4.2 Playwright check: main page has no upload controls; `/admin` page hidden until correct password entered; wrong password shows error and stays hidden; correct password reveals form and a real upload succeeds

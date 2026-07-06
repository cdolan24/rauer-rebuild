## Context

`admin-gated-upload` made the upload endpoint reject requests without the correct password, but the upload widget itself still rendered on the main chat page for everyone. This change moves it to its own page and gates visibility on a real unlock step, not just a rejected attempt.

## Goals / Non-Goals

**Goals:**
- Regular users never see upload controls on the main chat page.
- The admin page requires the correct password before the upload form appears at all.
- Reuse the existing password check rather than inventing a second source of truth for "what's the right password."

**Non-Goals:**
- No sessions/tokens/cookies - the unlock is a per-browser-tab, in-memory `gr.State` value, same trust model as the rest of this local-first MVP.
- No change to `POST /api/documents/upload`'s own password requirement - it still checks the password independently, so the admin page's "unlock" is a UX gate, not the sole security boundary.

## Decisions

**1. Gradio multi-page via `Blocks.route()`, not a second app/process.**
Gradio 5's `demo.route("Admin", "/admin")` adds a page under the same server (`/admin`), sharing the API client and process. Simpler than standing up a second Gradio app, and the navbar link is free.

**2. New `POST /api/auth/verify` endpoint, sharing a helper with upload.**
Factored the password comparison (`hmac.compare_digest`, "no password configured" -> always reject) into `src/utils/auth.py::verify_admin_password()`, used by both `/api/auth/verify` and the existing upload check. Avoids the check drifting out of sync between the two call sites.

**3. Unlock state lives in `gr.State`, not re-verified per upload... except it still is.**
After a successful `/api/auth/verify`, the frontend reveals the upload form and remembers the password in a `gr.State` for that browser session, so the admin doesn't retype it per file. The actual upload call still sends that password and the backend still checks it independently - the unlock step is convenience/UX, the upload endpoint remains the real enforcement point.

## Risks / Trade-offs

- **[Risk]** `gr.State` is per-session (per browser tab), so opening a new tab means unlocking again → **Mitigation**: acceptable at this stage; matches the "no real sessions" scope already established.
- **[Risk]** Two endpoints now check the same password → **Mitigation**: shared helper function, covered by tests for both call sites, so a future change to the check logic can't silently update one and miss the other.

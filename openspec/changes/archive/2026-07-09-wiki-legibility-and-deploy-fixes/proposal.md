## Why

Two problems needed closing before this is ready to deploy for real: the wiki currently requires manual follow-up scripts (`dedupe_entities.py`, and on-demand summary generation on first page view) after every ingestion to become fully legible, and a fresh-instance deploy would fail partway through `setup_ec2.sh` - Ubuntu 22.04 doesn't ship `python3.11` by default, and the shipped Nginx config declares a TLS listener before a certificate exists, which nginx refuses to start with.

## What Changes

- Entity deduplication and wiki-summary generation now run automatically as part of document ingestion, so a document only needs to be processed once - no separate manual script run needed for the wiki to be fully legible.
- Fixed two real deployment-blocking bugs in `deploy/`: `setup_ec2.sh` installed a Python version (3.11) not available in Ubuntu 22.04's default apt repos (nothing in the codebase actually requires 3.11 - lowered the constraint to 3.10, which Ubuntu 22.04 ships by default); `nginx-buddharauer.conf` declared `listen 443 ssl` with no certificate present, which fails nginx's own config test before Certbot ever runs - rewritten to ship HTTP-only, letting Certbot add the HTTPS block itself (the standard, supported certbot-nginx workflow).
- Renamed the product's user-facing masthead from "Buddharauer" (the prior project's name) to "Malifaux Document Explorer" everywhere it's actually displayed to a user (Gradio app title/masthead, wiki page titles, README). Internal infrastructure identifiers (systemd unit names, directory paths, the Python package name, log messages) are unchanged - this is a display-name change, not an infrastructure rename.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `entity-extraction`: deduplication and summary generation are now automatic steps of ingestion, not separate manual passes.
- `deployment`: setup_ec2.sh's Python version requirement and the Nginx config's initial (pre-Certbot) state both change.

## Impact

- `src/pipeline/ingest.py`, `src/pipeline/entity_deduper.py`, `src/wiki/summary.py` - wire dedup + summary generation into `ingest_pdf`.
- `deploy/setup_ec2.sh`, `pyproject.toml`, `README.md` - Python 3.10 instead of 3.11.
- `deploy/nginx-buddharauer.conf` - HTTP-only as shipped, Certbot adds HTTPS.
- `src/frontend/app.py`, `src/wiki/templates/*.html`, `README.md`, `src/api/main.py` - masthead rename.

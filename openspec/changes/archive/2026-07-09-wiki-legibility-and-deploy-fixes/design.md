## Context

Today, `ingest_pdf()` extracts entities but stops there: deduplication only happens if someone remembers to run `scripts/dedupe_entities.py`, and wiki summaries are generated lazily, one entity at a time, the first time each entity's page is viewed (`src/wiki/routes.py`). That means a freshly-ingested document's wiki is only partially legible until someone manually runs the dedup script and until enough people have clicked through every entity page to trigger summary generation. The user wants documents processed once, with the wiki fully legible immediately afterward - no follow-up steps required.

Separately, `deploy/setup_ec2.sh` and `deploy/nginx-buddharauer.conf` have never been run against a real AWS instance. A careful read (not just a skim) turned up two bugs that would each independently stop a first deploy cold before the app ever came up.

## Goals / Non-Goals

**Goals:**
- After `ingest_pdf()` returns, the wiki should be fully deduplicated and every entity should already have a cached summary - no manual script, no on-demand generation delay for the first viewer.
- `setup_ec2.sh` should actually complete on a vanilla Ubuntu 22.04 instance, in the exact order printed in its own final instructions (including running `certbot --nginx` after nginx is already up).

**Non-Goals:**
- Not restructuring `scripts/dedupe_entities.py`/`reclassify_entities.py` themselves - they remain useful as manual maintenance tools (e.g. re-running dedup after a taxonomy change), just no longer required after every single ingestion.
- Not actually provisioning a real AWS instance - still no credentials in this environment. This closes gaps found by careful reading and domain knowledge, not a live deploy.
- Not renaming any internal infrastructure identifier (systemd unit names, directory paths, the Python package name) - only the user-visible masthead changes.

## Decisions

**Run dedup and summary generation as steps inside `ingest_pdf`, not as a background task the caller has to remember to trigger separately.** They already run inside `documents.py`'s `BackgroundTasks.add_task(ingest_pdf, ...)`, so they're already off the request path - adding two more steps to that same background call doesn't change the API's response time, it just makes "ingestion done" mean "wiki is actually ready" rather than "text is embedded, wiki still needs cleanup."

**Dedup runs against the *entire* entity store, not just the newly-ingested document's entities.** A real duplicate can span documents (the same character named slightly differently in M1E vs M2E) - scoping dedup to only the new document's entities would miss exactly that case, which is the more valuable one to catch automatically.

**Order: extract entities → dedup → summarize.** Summarizing before dedup would waste LLM calls summarizing an entity that's about to be merged away and have its summary cleared anyway (`merge_entities` already nulls the kept entity's cached summary, since its mention set changed). Deduping first means summary generation only ever runs once per final, post-merge entity.

**Both new steps are wrapped in the same "enhancement, not core to ingestion succeeding" try/except pattern entity extraction already uses.** If Ollama is flaky partway through, ingestion still completes and is marked processed; the wiki keeps its existing lazy-generation fallback (fixed earlier this session) as a safety net for anything that didn't get pre-generated.

**Python 3.10, not 3.11, for the AWS deploy target.** Nothing in the codebase uses a 3.11-only feature (checked directly - no `match` statements, no `tomllib`, no `ExceptionGroup`) and Ubuntu 22.04 ships 3.10 by default. Targeting exactly what the OS already provides avoids adding the deadsnakes PPA as a new dependency for zero actual benefit.

**Ship the Nginx config HTTP-only and let Certbot add HTTPS, rather than pre-writing a `listen 443 ssl` block for Certbot to "fill in."** nginx validates configuration at parse time, before Certbot ever touches the file - a `listen ... ssl` directive with no `ssl_certificate` present is a hard config-test failure, not a soft warning. This is also just the standard, documented certbot-nginx workflow: point it at a working HTTP vhost and it adds the HTTPS server block and redirect itself.

## Risks / Trade-offs

- [Risk] Automatic dedup on every ingestion adds LLM calls (and therefore time) to every upload. → Consistent with the user's stated priority here (wiki legibility over ingestion speed); the candidate-pair pre-filter keeps this bounded to genuinely similar names, not the full entity count.
- [Risk] Pre-generating every entity's summary during ingestion is more upfront LLM work than the previous lazy/on-demand approach. → Same trade-off as above, and the existing lazy-generation fallback in `wiki_entity()` still covers any entity that didn't get a summary for some reason (a failed Ollama call, an entity added by a means other than `ingest_pdf`).
- [Risk] Neither deploy fix can be verified by actually running `setup_ec2.sh` or `nginx -t` in this environment (no Linux nginx binary, no AWS account) - same category of gap as the `systemctl`/`sqlite3` limitations hit earlier this session. Documented as reasoned-through-but-unexecuted, not silently assumed correct.

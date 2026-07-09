## MODIFIED Requirements

### Requirement: Wiki Entity Page
The system SHALL expose a page per entity showing an LLM-generated summary and a list of citations for where that entity is mentioned. The summary SHALL be generated automatically as part of document ingestion rather than on first page view, so the wiki is fully legible immediately after processing; if a summary is unavailable (not yet generated, or generation failed), the page SHALL fall back to the entity's stored description rather than failing to render.

#### Scenario: Viewing an entity's wiki page
- **WHEN** a user visits an entity's wiki page
- **THEN** the page shows the entity's name, type, a generated summary description, and a "Mentioned In" list of document/page citations

#### Scenario: Summary already exists when the page is first viewed
- **WHEN** a user visits an entity's wiki page for the first time, after that entity's document was ingested
- **THEN** the summary is already present (generated during ingestion) and the page renders immediately, without waiting on an LLM call

#### Scenario: Summary generation failed or hasn't happened yet
- **WHEN** an entity has no cached summary (generation failed during ingestion, or the entity was added by some other means) and the on-demand generation attempt also fails
- **THEN** the page still renders, showing the entity's stored description in place of a summary

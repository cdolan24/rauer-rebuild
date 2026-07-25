## MODIFIED Requirements

### Requirement: Wiki Entity Page
The system SHALL expose a page per entity showing an LLM-generated summary grounded in the entity's actual mention context, a "Relationships" section listing related entities and the nature of each relationship, and a list of citations for where that entity is mentioned. The summary SHALL be generated automatically as part of document ingestion rather than on first page view, so the wiki is fully legible immediately after processing; if a summary is unavailable (not yet generated, or generation failed), the page SHALL fall back to the entity's stored description rather than failing to render.

#### Scenario: Viewing an entity's wiki page
- **WHEN** a user visits an entity's wiki page
- **THEN** the page shows the entity's name, type, a generated summary description, a "Relationships" section, and a "Mentioned In" list of document/page citations

#### Scenario: Summary already exists when the page is first viewed
- **WHEN** a user visits an entity's wiki page for the first time, after that entity's document was ingested
- **THEN** the summary is already present (generated during ingestion) and the page renders immediately, without waiting on an LLM call

#### Scenario: Summary generation failed or hasn't happened yet
- **WHEN** an entity has no cached summary (generation failed during ingestion, or the entity was added by some other means) and the on-demand generation attempt also fails
- **THEN** the page still renders, showing the entity's stored description in place of a summary

#### Scenario: Viewing an entity with no recorded relationships
- **WHEN** a user visits the wiki page of an entity that has no extracted relationships
- **THEN** the "Relationships" section renders without error, indicating there are none, rather than being omitted or failing to render

#### Scenario: Viewing an entity's relationships
- **WHEN** a user visits the wiki page of an entity with one or more extracted relationships
- **THEN** each related entity is listed with a short description of the relationship and links to that related entity's own wiki page

## ADDED Requirements

### Requirement: Faction Hub Page
Each faction ("guild") entity's wiki page SHALL additionally list its member entities, so the faction page functions as a roster rather than only showing the faction's own description.

#### Scenario: Viewing a faction's members
- **WHEN** a user visits a faction entity's wiki page
- **THEN** the page lists every entity with a recorded "member of" (or equivalent) relationship to that faction, each linking to its own entity page

#### Scenario: Viewing a faction with no recorded members
- **WHEN** a user visits a faction entity's wiki page and no membership relationships have been recorded for it
- **THEN** the page renders normally, indicating it has no recorded members rather than omitting the section or failing to render

### Requirement: Location Index Page
The system SHALL expose a dedicated index page listing every location entity, functioning as a map-style browsing view distinct from the general category page.

#### Scenario: Browsing the location index
- **WHEN** a user visits the location index page
- **THEN** every location entity is listed, each linking to its own entity page

### Requirement: Relationship Graph Page
The system SHALL expose a page visualizing all entities and their extracted relationships as a node-link graph.

#### Scenario: Viewing the relationship graph
- **WHEN** a user visits the relationship graph page
- **THEN** entities are shown as nodes and their extracted relationships as edges, and selecting a node navigates to that entity's wiki page

#### Scenario: Viewing the graph with no relationships extracted yet
- **WHEN** a user visits the relationship graph page before any relationships have been extracted
- **THEN** the page renders without error, indicating there is nothing to show yet

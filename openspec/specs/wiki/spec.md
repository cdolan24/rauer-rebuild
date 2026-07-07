# wiki Specification

## Purpose
TBD - created by syncing change entity-wiki-and-citations. Update Purpose after archive.

## Requirements

### Requirement: Wiki Category Index
The system SHALL expose a browsable index page listing entities grouped by type (characters, locations, factions, items).

#### Scenario: Browsing the wiki index
- **WHEN** a user visits the wiki index page
- **THEN** the page lists all extracted entities grouped by their type, each linking to its own page

### Requirement: Wiki Entity Page
The system SHALL expose a page per entity showing an LLM-generated summary and a list of citations for where that entity is mentioned.

#### Scenario: Viewing an entity's wiki page
- **WHEN** a user visits an entity's wiki page
- **THEN** the page shows the entity's name, type, a generated summary description, and a "Mentioned In" list of document/page citations

### Requirement: Wiki Citations Link to Source
Citations on a wiki entity page SHALL link to the cited page, using the PDF-native citation link where available.

#### Scenario: Following a citation from a wiki page
- **WHEN** a user clicks a citation on an entity's wiki page
- **THEN** the browser opens the source PDF at the cited page

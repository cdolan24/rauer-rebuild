# pdf-citations Specification

## Purpose
TBD - created by syncing change entity-wiki-and-citations. Update Purpose after archive.

## Requirements

### Requirement: Raw PDF Serving Endpoint
The system SHALL expose an endpoint that serves the original PDF file for an ingested document.

#### Scenario: Fetching a document's original PDF
- **WHEN** a client requests a known document's PDF endpoint
- **THEN** the system returns the original PDF file as ingested

#### Scenario: Requesting the PDF of an unknown document
- **WHEN** a client requests the PDF endpoint for a document id that doesn't exist
- **THEN** the system returns a 404 response

### Requirement: Page-Anchored PDF Links
Citations SHALL be expressible as a link to the raw PDF endpoint anchored to a specific page, so opening the link shows that page in the browser's PDF viewer.

#### Scenario: Opening a page-anchored citation link
- **WHEN** a user opens a citation link for a given document and page
- **THEN** the browser's PDF viewer displays that document starting at the cited page

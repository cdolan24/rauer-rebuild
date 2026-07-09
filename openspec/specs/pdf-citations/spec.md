# pdf-citations Specification

## Purpose
Defines how a citation in a chat answer or wiki page links back to the original source: serving the raw PDF and jumping directly to the cited page.

## Requirements

### Requirement: Raw PDF Serving Endpoint
The system SHALL expose an endpoint that serves the original PDF file for an ingested document, with an inline content disposition so browsers and embedded viewers (e.g. an `<iframe>`) render it directly instead of downloading it.

#### Scenario: Fetching a document's original PDF
- **WHEN** a client requests a known document's PDF endpoint
- **THEN** the system returns the original PDF file as ingested, with `Content-Disposition: inline`

#### Scenario: Requesting the PDF of an unknown document
- **WHEN** a client requests the PDF endpoint for a document id that doesn't exist
- **THEN** the system returns a 404 response

#### Scenario: Viewing a PDF embedded in the frontend
- **WHEN** the frontend embeds the PDF endpoint's URL in an `<iframe>`
- **THEN** the browser renders the PDF inline within the iframe rather than triggering a file download

### Requirement: Page-Anchored PDF Links
Citations SHALL be expressible as a link to the raw PDF endpoint anchored to a specific page, so opening the link shows that page in the browser's PDF viewer.

#### Scenario: Opening a page-anchored citation link
- **WHEN** a user opens a citation link for a given document and page
- **THEN** the browser's PDF viewer displays that document starting at the cited page

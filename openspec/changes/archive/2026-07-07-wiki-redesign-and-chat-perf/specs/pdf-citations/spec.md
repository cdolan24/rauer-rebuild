## MODIFIED Requirements

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

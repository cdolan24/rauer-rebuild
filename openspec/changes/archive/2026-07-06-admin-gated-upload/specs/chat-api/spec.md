## MODIFIED Requirements

### Requirement: Document Upload Endpoint
The system SHALL expose an endpoint to upload a new PDF for ingestion, and SHALL require a correct admin password on every upload request.

#### Scenario: Uploading a new PDF with a correct admin password
- **WHEN** a client sends `POST /api/documents/upload` with a PDF file and the correct admin password
- **THEN** the system accepts the file, begins ingestion, and returns a job/document identifier the client can use to check status

#### Scenario: Uploading without a correct admin password
- **WHEN** a client sends `POST /api/documents/upload` with a missing or incorrect admin password
- **THEN** the system rejects the request with a 401 response and does not ingest the file

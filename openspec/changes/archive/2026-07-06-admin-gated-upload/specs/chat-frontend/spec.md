## MODIFIED Requirements

### Requirement: Upload Interface
The frontend SHALL allow a user to upload a new PDF and see its processing status, and SHALL require the user to enter the admin password before an upload is accepted.

#### Scenario: Uploading a document from the UI with the correct admin password
- **WHEN** a user enters the correct admin password and uploads a PDF through the frontend
- **THEN** the frontend shows the document's ingestion status until it becomes available for chat

#### Scenario: Uploading a document from the UI with an incorrect admin password
- **WHEN** a user uploads a PDF through the frontend without the correct admin password
- **THEN** the frontend displays an authentication error and does not show the file as ingesting

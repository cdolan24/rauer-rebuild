## MODIFIED Requirements

### Requirement: Upload Interface
Upload SHALL live on a separate admin page, not the main chat page. The admin page SHALL remain locked - showing only a password field - until the correct admin password is entered, at which point the upload form is revealed. The frontend SHALL allow a user to upload a new PDF and see its processing status once unlocked.

#### Scenario: Main chat page has no upload controls
- **WHEN** a user visits the main chat page
- **THEN** no upload widget or admin password field is present on that page

#### Scenario: Unlocking the admin page with the correct password
- **WHEN** a user visits the admin page and enters the correct admin password
- **THEN** the upload form is revealed

#### Scenario: Failing to unlock the admin page with an incorrect password
- **WHEN** a user visits the admin page and enters an incorrect admin password
- **THEN** the frontend displays an authentication error and the upload form remains hidden

#### Scenario: Uploading a document from the unlocked admin page
- **WHEN** a user has unlocked the admin page and uploads a PDF
- **THEN** the frontend shows the document's ingestion status until it becomes available for chat

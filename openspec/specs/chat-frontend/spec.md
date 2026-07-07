# chat-frontend Specification

## Purpose
TBD - created by archiving change rebuild-mvp. Update Purpose after archive.

## Requirements

### Requirement: Split Chat and Document Viewer Layout
The frontend SHALL present a chat interface and a source document viewer side-by-side.

#### Scenario: Viewing chat and sources together
- **WHEN** a user opens the web frontend
- **THEN** the chat panel and document viewer panel are both visible without navigating away from the chat

### Requirement: Sending and Viewing Messages
The frontend SHALL allow a user to type a question, submit it, and view the assistant's response in the chat panel.

#### Scenario: Sending a message
- **WHEN** a user types a question and submits it
- **THEN** the user's message and the assistant's response appear in the chat history in order

### Requirement: Citation Display Linked to Document Viewer
The frontend SHALL display citations for each assistant response and allow the user to view the referenced source content, including a link to the original PDF page for that citation.

#### Scenario: Selecting a citation
- **WHEN** a user selects a citation shown alongside an assistant response
- **THEN** the document viewer displays the corresponding source document at/near the cited page

#### Scenario: Opening the original PDF for a citation
- **WHEN** a user selects a citation shown alongside an assistant response
- **THEN** a link is available that opens the original PDF at the cited page in the browser's PDF viewer

### Requirement: Document Selection
The frontend SHALL allow a user to browse and select from the list of ingested documents independent of an active chat citation.

#### Scenario: Browsing available documents
- **WHEN** a user opens the document selector
- **THEN** the frontend lists all ingested documents (from the chat-api document listing) for the user to choose from

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

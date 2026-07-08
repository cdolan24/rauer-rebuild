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
The frontend SHALL allow a user to type a question, submit it, and view the assistant's response in the chat panel, streamed incrementally as it is generated. Pressing Enter SHALL submit the message; pressing Shift+Enter SHALL insert a newline instead.

#### Scenario: Sending a message
- **WHEN** a user types a question and submits it
- **THEN** the user's message appears immediately and the assistant's response fills in incrementally as it streams

#### Scenario: Submitting with Enter
- **WHEN** a user presses Enter while the question box is focused
- **THEN** the message is submitted

#### Scenario: Inserting a newline with Shift+Enter
- **WHEN** a user presses Shift+Enter while the question box is focused
- **THEN** a newline is inserted into the question box and the message is not submitted

### Requirement: Citation Display Linked to Document Viewer
The frontend SHALL display citations for each assistant response as a set of clickable buttons with human-readable labels, and allow the user to view the referenced source directly as the original PDF.

#### Scenario: Selecting a citation
- **WHEN** a user clicks a citation button shown alongside an assistant response
- **THEN** the document viewer displays the original PDF at the cited page

#### Scenario: Citation labels are human-readable
- **WHEN** citations are shown for an assistant response
- **THEN** each citation button shows a shortened document name and page number rather than the raw document id

### Requirement: PDF Document Viewer
The document viewer SHALL display the original PDF for the selected document or citation, not the plain-text extract used internally by the AI.

#### Scenario: Viewing a selected document
- **WHEN** a user selects a document from the document selector
- **THEN** the viewer displays that document's original PDF

#### Scenario: Viewing a selected citation
- **WHEN** a user selects a citation
- **THEN** the viewer displays the original PDF at the cited page, without requiring a separate link

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

### Requirement: Independent Per-Session Conversation History
Each browser session SHALL be assigned its own conversation identifier, independent of any other concurrent session, so conversation history is never shared between different users or browser tabs opened as separate sessions.

#### Scenario: Two independent sessions get distinct conversation history
- **WHEN** two separate browser sessions each open the chat frontend and send a message
- **THEN** each session's message is recorded under a different conversation identifier, and neither session's conversation history includes the other's messages

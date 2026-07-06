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
The frontend SHALL display citations for each assistant response and allow the user to view the referenced source content.

#### Scenario: Selecting a citation
- **WHEN** a user selects a citation shown alongside an assistant response
- **THEN** the document viewer displays the corresponding source document at/near the cited page

### Requirement: Document Selection
The frontend SHALL allow a user to browse and select from the list of ingested documents independent of an active chat citation.

#### Scenario: Browsing available documents
- **WHEN** a user opens the document selector
- **THEN** the frontend lists all ingested documents (from the chat-api document listing) for the user to choose from

### Requirement: Upload Interface
The frontend SHALL allow a user to upload a new PDF and see its processing status, and SHALL require the user to enter the admin password before an upload is accepted.

#### Scenario: Uploading a document from the UI with the correct admin password
- **WHEN** a user enters the correct admin password and uploads a PDF through the frontend
- **THEN** the frontend shows the document's ingestion status until it becomes available for chat

#### Scenario: Uploading a document from the UI with an incorrect admin password
- **WHEN** a user uploads a PDF through the frontend without the correct admin password
- **THEN** the frontend displays an authentication error and does not show the file as ingesting

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: PDF Document Viewer
The document viewer SHALL display the original PDF for the selected document or citation, not the plain-text extract used internally by the AI.

#### Scenario: Viewing a selected document
- **WHEN** a user selects a document from the document selector
- **THEN** the viewer displays that document's original PDF

#### Scenario: Viewing a selected citation
- **WHEN** a user selects a citation
- **THEN** the viewer displays the original PDF at the cited page, without requiring a separate link

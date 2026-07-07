## MODIFIED Requirements

### Requirement: Citation Display Linked to Document Viewer
The frontend SHALL display citations for each assistant response and allow the user to view the referenced source content, including a link to the original PDF page for that citation.

#### Scenario: Selecting a citation
- **WHEN** a user selects a citation shown alongside an assistant response
- **THEN** the document viewer displays the corresponding source document at/near the cited page

#### Scenario: Opening the original PDF for a citation
- **WHEN** a user selects a citation shown alongside an assistant response
- **THEN** a link is available that opens the original PDF at the cited page in the browser's PDF viewer

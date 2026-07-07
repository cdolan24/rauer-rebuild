## MODIFIED Requirements

### Requirement: Wiki Category Index
The system SHALL expose a browsable index page listing entities grouped by type (characters, locations, factions, items), presented as clickable buttons rather than plain inline links.

#### Scenario: Browsing the wiki index
- **WHEN** a user visits the wiki index page
- **THEN** the page lists all extracted entities grouped by their type, each shown as a button linking to its own page

#### Scenario: Browsing a category page
- **WHEN** a user visits a category page
- **THEN** entities in that category are shown as buttons rather than plain text links

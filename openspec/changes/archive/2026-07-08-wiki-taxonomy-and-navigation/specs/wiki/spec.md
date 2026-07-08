## MODIFIED Requirements

### Requirement: Wiki Category Index
The system SHALL expose a browsable index page listing entities grouped by type, presented as clickable buttons rather than plain inline links, with each type visually distinguished by its own color. The index page SHALL function as a landing page: wiki-wide orientation content (see Wiki Landing Page) appears above the category browsing.

#### Scenario: Browsing the wiki index
- **WHEN** a user visits the wiki index page
- **THEN** the page lists all entity categories with their counts, each shown as a distinctly-colored button linking to its own category page

#### Scenario: Browsing a category page
- **WHEN** a user visits a category page
- **THEN** entities in that category are shown as buttons, colored according to their type, rather than plain text links

## ADDED Requirements

### Requirement: Wiki Landing Page
The wiki index page SHALL show orientation content - total entity count, total document count, and a per-category breakdown - above the category browsing, so it functions as a home page rather than an immediate entity listing.

#### Scenario: Viewing the wiki landing page
- **WHEN** a user visits the wiki index page
- **THEN** the page shows the total number of entities, the number of source documents, and a count per category, displayed before the category browsing section

### Requirement: Entity Type Visual Differentiation
Entity buttons SHALL be colored according to their type, so different kinds of entities are visually distinguishable at a glance rather than rendering identically.

#### Scenario: Entities of different types render with different colors
- **WHEN** entities of different types are displayed on the same page
- **THEN** each type's buttons use a color distinct from the other types

#### Scenario: Real-person entities are visually de-emphasized
- **WHEN** a `real-person` entity (e.g. a credited author) is displayed
- **THEN** it renders in a deliberately muted/desaturated color distinct from fictional entity types

### Requirement: Cross-Application Navigation
Navigation links from the wiki to the chat application SHALL use an absolute URL pointing at the chat application's actual configured address, not a relative path assuming the same origin.

#### Scenario: Navigating from the wiki to chat
- **WHEN** a user clicks the "Chat" link from any wiki page
- **THEN** the browser navigates to the chat application's actual address, regardless of the wiki being served from a different origin

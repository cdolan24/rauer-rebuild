# wiki Specification

## Purpose
Defines the auto-generated wiki: browsing extracted entities by category, individual entity pages with infoboxes and source citations, search, and navigation back to the chat frontend.

## Requirements

### Requirement: Wiki Category Index
The system SHALL expose a browsable index page listing entities grouped by type, presented as clickable buttons rather than plain inline links, with each type visually distinguished by its own color. The index page SHALL function as a landing page: wiki-wide orientation content (see Wiki Landing Page) appears above the category browsing.

#### Scenario: Browsing the wiki index
- **WHEN** a user visits the wiki index page
- **THEN** the page lists all entity categories with their counts, each shown as a distinctly-colored button linking to its own category page

#### Scenario: Browsing a category page
- **WHEN** a user visits a category page
- **THEN** entities in that category are shown as buttons, colored according to their type, rather than plain text links

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

### Requirement: Wiki Entity Page
The system SHALL expose a page per entity showing an LLM-generated summary and a list of citations for where that entity is mentioned.

#### Scenario: Viewing an entity's wiki page
- **WHEN** a user visits an entity's wiki page
- **THEN** the page shows the entity's name, type, a generated summary description, and a "Mentioned In" list of document/page citations

### Requirement: Wiki Citations Link to Source
Citations on a wiki entity page SHALL link to the cited page, using the PDF-native citation link where available.

#### Scenario: Following a citation from a wiki page
- **WHEN** a user clicks a citation on an entity's wiki page
- **THEN** the browser opens the source PDF at the cited page

### Requirement: Persistent Category Navigation
The system SHALL present a persistent sidebar, visible on every wiki page, listing all entity categories with their counts and linking to each category's page.

#### Scenario: Sidebar visible across wiki pages
- **WHEN** a user is on the wiki index, a category page, or an entity page
- **THEN** the sidebar listing all categories and their entity counts is visible and each category links to its category page

### Requirement: Wiki Breadcrumb Navigation
Category and entity pages SHALL show a breadcrumb trail back to the wiki index, so users can navigate up without relying on the browser's back button.

#### Scenario: Breadcrumb on a category page
- **WHEN** a user visits a category page
- **THEN** a breadcrumb showing "Wiki Home > {Category}" is displayed, with "Wiki Home" linking back to the index

#### Scenario: Breadcrumb on an entity page
- **WHEN** a user visits an entity page
- **THEN** a breadcrumb showing "Wiki Home > {Category} > {Entity Name}" is displayed, with each segment except the current entity linking to its respective page

### Requirement: Entity Search
The system SHALL provide a search/filter box that narrows the visible entities on the index and category pages as the user types, without a page reload.

#### Scenario: Filtering entities by typed text
- **WHEN** a user types text into the search box on the wiki index or a category page
- **THEN** only entities whose name contains the typed text (case-insensitive) remain visible, updating as the user types

#### Scenario: Clearing the search
- **WHEN** a user clears the search box
- **THEN** all entities are visible again

### Requirement: Entity Infobox
Entity pages SHALL show a summary infobox alongside the description, presenting the entity's type, mention count, and the distinct source documents it appears in.

#### Scenario: Viewing an entity's infobox
- **WHEN** a user visits an entity's wiki page
- **THEN** an infobox is displayed showing the entity's type, total mention count, and the list of distinct documents it is mentioned in

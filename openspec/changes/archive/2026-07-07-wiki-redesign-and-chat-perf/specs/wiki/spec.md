## ADDED Requirements

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

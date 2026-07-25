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
The system SHALL expose a page per entity showing an LLM-generated summary grounded in the entity's actual mention context, a "Relationships" section listing related entities and the nature of each relationship, a list of citations for where that entity is mentioned, and a link into the relationship graph page focused on that entity. The summary SHALL be generated automatically as part of document ingestion rather than on first page view, so the wiki is fully legible immediately after processing; if a summary is unavailable (not yet generated, or generation failed), the page SHALL fall back to the entity's stored description rather than failing to render.

#### Scenario: Viewing an entity's wiki page
- **WHEN** a user visits an entity's wiki page
- **THEN** the page shows the entity's name, type, a generated summary description, a "Relationships" section, a "Mentioned In" list of document/page citations, and a link into the relationship graph focused on that entity

#### Scenario: Following the "View in graph" link
- **WHEN** a user clicks the "View in graph" link on an entity's wiki page
- **THEN** the browser navigates to the relationship graph page already focused on and displaying that entity's neighborhood

#### Scenario: Summary already exists when the page is first viewed
- **WHEN** a user visits an entity's wiki page for the first time, after that entity's document was ingested
- **THEN** the summary is already present (generated during ingestion) and the page renders immediately, without waiting on an LLM call

#### Scenario: Summary generation failed or hasn't happened yet
- **WHEN** an entity has no cached summary (generation failed during ingestion, or the entity was added by some other means) and the on-demand generation attempt also fails
- **THEN** the page still renders, showing the entity's stored description in place of a summary

#### Scenario: Viewing an entity with no recorded relationships
- **WHEN** a user visits the wiki page of an entity that has no extracted relationships
- **THEN** the "Relationships" section renders without error, indicating there are none, rather than being omitted or failing to render

#### Scenario: Viewing an entity's relationships
- **WHEN** a user visits the wiki page of an entity with one or more extracted relationships
- **THEN** each related entity is listed with a short description of the relationship and links to that related entity's own wiki page

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

### Requirement: Faction Hub Page
Each faction ("guild") entity's wiki page SHALL additionally list its member entities, so the faction page functions as a roster rather than only showing the faction's own description.

#### Scenario: Viewing a faction's members
- **WHEN** a user visits a faction entity's wiki page
- **THEN** the page lists every entity with a recorded "member of" (or equivalent) relationship to that faction, each linking to its own entity page

#### Scenario: Viewing a faction with no recorded members
- **WHEN** a user visits a faction entity's wiki page and no membership relationships have been recorded for it
- **THEN** the page renders normally, indicating it has no recorded members rather than omitting the section or failing to render

### Requirement: Location Index Page
The system SHALL expose a dedicated index page listing every location entity, functioning as a map-style browsing view distinct from the general category page.

#### Scenario: Browsing the location index
- **WHEN** a user visits the location index page
- **THEN** every location entity is listed, each linking to its own entity page

### Requirement: Relationship Graph Page
The system SHALL expose a relationship graph page that renders empty (a search box, no nodes or edges) by default rather than laying out every entity/relationship at once, and SHALL load a single entity's direct-relationship neighborhood on demand - via a name search, clicking an already-drawn node, or a `focus` deep-link from that entity's own wiki page - drawing only that small neighborhood at a time. Clicking a node's name/label continues to navigate to its wiki page, so neighborhood loading (clicking the node's mark) and navigation (clicking its label) are two distinct click targets rather than colliding on the same one. Panning and zooming continue to apply to whatever neighborhood is currently drawn.

#### Scenario: Visiting the graph page with no search or focus
- **WHEN** a user visits the relationship graph page with no search performed and no `focus` parameter
- **THEN** the page renders with a search box and no nodes or edges drawn

#### Scenario: Searching for an entity in the graph
- **WHEN** a user enters a name into the graph's search box and a matching entity is found
- **THEN** that entity and its direct relationships are fetched and drawn as a node-link neighborhood, centered on the matched entity

#### Scenario: Focusing on a node's neighborhood by clicking it
- **WHEN** a user clicks a drawn node's mark
- **THEN** that node's own direct-relationship neighborhood is fetched and drawn in place of the previously-drawn neighborhood

#### Scenario: Arriving via a focus deep-link
- **WHEN** a user visits the relationship graph page with a `focus` parameter identifying an entity
- **THEN** that entity's direct-relationship neighborhood is fetched and drawn automatically on load

#### Scenario: Viewing the graph before any relationships have been extracted
- **WHEN** a user visits the relationship graph page and no relationships exist in the system at all
- **THEN** the page still renders normally with its search box, indicating there is nothing to search for yet, rather than erroring

#### Scenario: Panning and zooming a drawn neighborhood
- **WHEN** a user drags or scrolls within the graph view while a neighborhood is drawn
- **THEN** the visible portion of that neighborhood pans or zooms accordingly, without navigating away from the page

### Requirement: Entity Neighborhood Data Endpoint
The system SHALL expose a JSON endpoint returning a given entity plus its direct (depth-1) relationships as node/edge data suitable for the relationship graph page to draw, and SHALL respond with an error for an entity id that does not exist.

#### Scenario: Fetching a known entity's neighborhood
- **WHEN** a client requests the neighborhood data endpoint for an entity that exists and has direct relationships
- **THEN** the response includes that entity and each directly-related entity as nodes, and each of those relationships as edges

#### Scenario: Fetching neighborhood data for an unknown entity
- **WHEN** a client requests the neighborhood data endpoint for an entity id that does not exist
- **THEN** the response is an error rather than empty or malformed node/edge data

## MODIFIED Requirements

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

### Requirement: Wiki Entity Page
The system SHALL expose a page per entity showing an LLM-generated summary grounded in the entity's actual mention context, a "Relationships" section listing related entities and the nature of each relationship, a list of citations for where that entity is mentioned, and a link into the relationship graph page focused on that entity. The summary SHALL be generated automatically as part of document ingestion rather than on first page view, so the wiki is fully legible immediately after processing; if a summary is unavailable (not yet generated, or generation failed), the page SHALL fall back to the entity's stored description rather than failing to render.

#### Scenario: Viewing an entity's wiki page
- **WHEN** a user visits an entity's wiki page
- **THEN** the page shows the entity's name, type, a generated summary description, a "Relationships" section, a "Mentioned In" list of document/page citations, and a link into the relationship graph focused on that entity

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

#### Scenario: Following the "View in graph" link
- **WHEN** a user clicks the "View in graph" link on an entity's wiki page
- **THEN** the browser navigates to the relationship graph page already focused on and displaying that entity's neighborhood

## ADDED Requirements

### Requirement: Entity Neighborhood Data Endpoint
The system SHALL expose a JSON endpoint returning a given entity plus its direct (depth-1) relationships as node/edge data suitable for the relationship graph page to draw, and SHALL respond with an error for an entity id that does not exist.

#### Scenario: Fetching a known entity's neighborhood
- **WHEN** a client requests the neighborhood data endpoint for an entity that exists and has direct relationships
- **THEN** the response includes that entity and each directly-related entity as nodes, and each of those relationships as edges

#### Scenario: Fetching neighborhood data for an unknown entity
- **WHEN** a client requests the neighborhood data endpoint for an entity id that does not exist
- **THEN** the response is an error rather than empty or malformed node/edge data

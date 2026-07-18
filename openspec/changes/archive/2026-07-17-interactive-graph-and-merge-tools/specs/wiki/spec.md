## MODIFIED Requirements

### Requirement: Relationship Graph Page
The system SHALL expose a page visualizing all entities and their extracted relationships as a node-link graph, with interactive navigation so the graph remains usable at large node/edge counts: panning, zooming, clicking a node to focus on its immediate neighborhood, and searching for a node by name. Clicking a node's name/label continues to navigate to its wiki page, so neighborhood focus (clicking the node's mark) and navigation (clicking its label) are two distinct click targets rather than colliding on the same one.

#### Scenario: Viewing the relationship graph
- **WHEN** a user visits the relationship graph page
- **THEN** entities are shown as nodes and their extracted relationships as edges, and selecting a node navigates to that entity's wiki page

#### Scenario: Viewing the graph with no relationships extracted yet
- **WHEN** a user visits the relationship graph page before any relationships have been extracted
- **THEN** the page renders without error, indicating there is nothing to show yet

#### Scenario: Panning and zooming the graph
- **WHEN** a user drags or scrolls within the graph view
- **THEN** the visible portion of the graph pans or zooms accordingly, without navigating away from the page

#### Scenario: Focusing on a node's neighborhood
- **WHEN** a user clicks a node's mark
- **THEN** that node and its directly-connected neighbors are visually highlighted while unrelated nodes and edges are visually de-emphasized, until the user clicks the same node's mark again or clicks another node's mark to focus it instead

#### Scenario: Searching for an entity in the graph
- **WHEN** a user enters a name into the graph's search box
- **THEN** a matching node is highlighted and brought into view

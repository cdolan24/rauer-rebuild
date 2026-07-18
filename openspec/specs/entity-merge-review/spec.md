# entity-merge-review

## Purpose
Defines admin-page capabilities for reviewing and applying entity de-duplication: running the automated duplicate-candidate scan, reviewing candidates one at a time, manually merging arbitrary entities, and reversing a merge that turns out to be wrong - all restricted to authenticated admins.

## Requirements

### Requirement: Dedupe Candidate Scan
An authenticated admin SHALL be able to trigger a scan for duplicate-entity candidates from the admin page, which runs the existing automated candidate-finder and persists the results for review, rather than requiring the CLI or a bulk apply.

#### Scenario: Running a scan
- **WHEN** an authenticated admin triggers a duplicate scan
- **THEN** candidate merge groups are computed and stored with a pending status, available for one-at-a-time review

#### Scenario: Re-running a scan clears stale pending candidates
- **WHEN** an authenticated admin triggers a duplicate scan while pending candidates from a previous scan still exist
- **THEN** the previous pending candidates are replaced by the newly computed set, rather than accumulating alongside them

### Requirement: One-At-A-Time Candidate Review
An authenticated admin SHALL be able to review each pending dedupe candidate group individually and approve (merge), reject, or skip it, rather than applying all candidates in bulk.

#### Scenario: Approving a candidate group
- **WHEN** an authenticated admin approves a pending candidate group
- **THEN** the group's entities are merged and the candidate's status is recorded as approved

#### Scenario: Rejecting a candidate group
- **WHEN** an authenticated admin rejects a pending candidate group
- **THEN** no merge is performed and the candidate's status is recorded as rejected

#### Scenario: Approving a candidate whose entities no longer exist or were already merged
- **WHEN** an authenticated admin approves a pending candidate group where one of the referenced entities has since been merged or removed
- **THEN** no merge is performed, the candidate is automatically marked rejected, and the admin is shown why

### Requirement: Manual Entity Merge
An authenticated admin SHALL be able to merge any two arbitrary entities directly from the admin page, independent of the automated dedupe scan.

#### Scenario: Manually merging two entities
- **WHEN** an authenticated admin selects two existing entities and confirms a manual merge
- **THEN** the entities are merged the same way an approved dedupe candidate would be, and the merge is available for later undo

### Requirement: Merge Provenance and Undo
Every merge (automated-candidate or manual) SHALL retain enough information to reverse it, and an authenticated admin SHALL be able to undo a specific prior merge, provided it has not become ambiguous due to a later merge involving the same surviving entity.

#### Scenario: Undoing a merge
- **WHEN** an authenticated admin undoes a merge whose surviving entity has not been merged again since
- **THEN** the merged-away entity, its mentions, and its relationships are restored to their pre-merge state, and the surviving entity's cached summary is cleared so it can be regenerated

#### Scenario: Undo is unavailable for an ambiguous merge chain
- **WHEN** an authenticated admin attempts to undo a merge whose surviving entity has itself been merged into another entity since
- **THEN** the undo is refused, with an explanation that the merge can no longer be cleanly reversed

#### Scenario: Merges applied before this capability existed cannot be undone
- **WHEN** an authenticated admin looks for undo on a merge that was applied before merge provenance was tracked
- **THEN** no undo option is offered for that merge

### Requirement: Merge Review Is Admin-Gated
All dedupe-scan, candidate-review, manual-merge, and undo actions SHALL be restricted to authenticated admins, consistent with other admin-only capabilities.

#### Scenario: Merge review is unavailable without authentication
- **WHEN** an unauthenticated request attempts to scan for duplicates, review a candidate, manually merge, or undo a merge
- **THEN** the request is rejected and no data changes

## ADDED Requirements

### Requirement: Automated Data Backup
The deployed instance SHALL automatically create a daily backup of the application database and vector store, retaining at least the last 7 days of backups on local disk.

#### Scenario: Daily backup runs automatically
- **WHEN** the daily backup timer fires
- **THEN** a consistent snapshot of the application database and the vector store is written to the backup location, without corrupting or interrupting the running services

#### Scenario: Old backups are pruned
- **WHEN** a new backup completes and more than 7 days of backups exist
- **THEN** backups older than 7 days are removed, keeping local disk usage bounded

#### Scenario: Restoring from a backup
- **WHEN** an operator follows the documented restore procedure with a specific backup snapshot
- **THEN** the application database and vector store are restored to that snapshot's state

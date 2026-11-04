# DatasheetDelta 1.0 release gate

No public release, release tag, launch announcement or production-readiness claim is permitted until every mandatory gate below is evidenced.

## Product behavior
- [ ] Supported document formats and extraction contract are explicit and tested.
- [ ] Tables, repeated labels, merged cells, multi-column layouts and document reading order have documented behavior.
- [ ] Scanned PDF handling is either implemented and tested or clearly excluded from 1.0.
- [ ] Unit conversions are dimension-safe, tested at boundaries and preserve original source values.
- [ ] Matching ambiguity is surfaced; no silent duplicate overwrite or guessed semantic equivalence.
- [ ] Every finding links to enough source context for a reviewer to verify it.
- [ ] Empty, malformed, encrypted, corrupt and unsupported documents fail safely with actionable errors.

## Review and traceability
- [ ] Reviewer decisions and annotations are implemented.
- [ ] Review history is append-only or otherwise tamper-evident within the stated threat model.
- [ ] Approval identity, timestamp and decision scope are recorded.
- [ ] Exported reports distinguish machine findings from human decisions.
- [ ] No report implies engineering approval unless an authorized reviewer explicitly records it.

## Security and privacy
- [ ] Upload limits, file validation, parser isolation and error handling are tested.
- [ ] No path traversal, unsafe archive expansion, formula injection or HTML injection is possible through supported flows.
- [ ] Retention, deletion, logging, backups and deployment responsibilities are documented.
- [ ] Authentication and authorization are implemented if multi-user or network-accessible use is supported.
- [ ] Dependency and container vulnerability checks are clean or formally dispositioned.

## Quality and usability
- [ ] Automated tests cover supported formats and realistic document variations.
- [ ] API integration tests and browser end-to-end tests pass.
- [ ] Keyboard navigation, responsive behavior and accessible status communication are verified.
- [ ] CLI, API, UI and report outputs agree on findings.
- [ ] Clean install and container build pass from a fresh environment.

## Validation and release operations
- [ ] Representative documents have been tested with engineering reviewers.
- [ ] Known extraction misses and false-positive modes are measured and disclosed.
- [ ] No unsupported accuracy, savings, compliance or customer claims appear in the product.
- [ ] Deployment guide, backup/restore and incident response notes are complete.
- [ ] Final release candidate passes the full CI matrix and a documented manual acceptance run.
- [ ] Product owner explicitly approves the single public 1.0 release.

A checked box requires evidence in the repository or a recorded validation artifact. Intention is not evidence.

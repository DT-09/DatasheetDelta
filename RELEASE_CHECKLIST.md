# DatasheetDelta 1.0 Release Acceptance Gate

A public release is blocked until every mandatory item is verified. A checked box requires evidence, not intent.

## Product correctness
- [ ] Extraction tests cover CSV, XLSX, DOCX, text PDF, TXT and Markdown using real-world-like fixtures.
- [ ] XLSX merged cells, blank rows, formulas and multiple sheets have documented and tested behavior.
- [ ] DOCX tables, repeated headers, merged cells and nested tables have documented and tested behavior.
- [ ] PDF text extraction is tested against multi-page, multi-column and scanned documents; OCR behavior is explicit.
- [ ] Duplicate labels and repeated table sections cannot be silently collapsed.
- [ ] Unit conversion has dimensional, precision, rounding and edge-case tests for every advertised unit.
- [ ] Numeric tolerances are documented and tested for each dimension.
- [ ] Ambiguous, missing, unknown and incompatible values are surfaced without unsafe assumptions.
- [ ] Findings retain source excerpts as well as source locations, or a documented limitation explains the absence.

## Reviewer workflow and records
- [ ] Reviewer decisions and notes are exportable and unambiguously linked to findings.
- [ ] Exported review packages are reproducible and schema-versioned.
- [ ] Reviewer identity, timestamps and approval history are designed for the intended deployment model.
- [ ] A qualified engineering reviewer has tested the workflow with representative documents.

## Security and privacy
- [ ] File type validation uses content inspection where feasible, not extension alone.
- [ ] Upload size, request duration, concurrency and memory limits are tested.
- [ ] Malformed and adversarial documents are tested.
- [ ] Dependency and container vulnerability scans are reviewed.
- [ ] Authentication, authorization, TLS, reverse-proxy limits and operational logging are configured for the chosen host.
- [ ] Data retention, deletion, backups and incident response are documented for the deployment.
- [ ] Confidential and export-controlled data handling is reviewed by the deploying organization.

## User experience and accessibility
- [ ] Browser workflow is tested on current desktop and mobile browsers.
- [ ] Keyboard navigation, focus states, screen-reader labels and contrast are reviewed.
- [ ] Large reports remain usable and filters/export functions work across all finding types.
- [ ] Failure states explain the cause and the corrective action.

## Release engineering
- [ ] CI passes on every supported Python version.
- [ ] Docker image builds and starts; health check passes.
- [ ] Clean-install instructions are verified on Windows and Linux.
- [ ] API contract and CLI are covered by automated tests.
- [ ] License, dependency notices, changelog and version metadata are consistent.
- [ ] A tagged release is created only after the above evidence is reviewed.

## External validation
- [ ] At least three representative engineering document pairs from distinct formats/layouts are tested with permission.
- [ ] Extraction recall and precision are measured against manually annotated ground truth.
- [ ] False negatives and false positives are reviewed and documented.
- [ ] No customer, accuracy, savings, compliance or safety claims are published without evidence.

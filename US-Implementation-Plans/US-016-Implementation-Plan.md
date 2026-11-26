# US-016: Communication History Storage - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-016 - Communication History Storage |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 5 |
| Repository | `valuex-backend` |
| Dependencies | US-013 chat and US-014/US-015 call logs, documented as built; verify their changes are present on the implementation base. US-132 supplies report integration. |
| Design | [Sprint 4 LLD, Part H](../LLD/Sprint-4-Communication-Negotiation-LLD.md#part-h---us-016-communication-history-storage), decisions D12, D14 and D24 |

## 2. Story Recap

**As a** platform, **I want** to store communication history **so that** disputes can be resolved with evidence.

| ID | Acceptance criterion |
|---|---|
| AC1 | Chat and call activity is logged with timestamps and stored securely with encryption. Calls are not recorded or transcribed. |
| AC2 | Admins can access relevant communication logs for a dispute. |
| AC3 | Chat and call logs are retained for six months after the conversation closes; call transcript retention is deferred. |
| AC4 | Admin access is logged for audit. |

**Edge cases:** storage limit exceeded; user requests data deletion; inappropriate content; retrieval of very old logs. **Errors:** `ERROR_STORAGE_FULL` and `ERROR_RETRIEVAL_FAILED`. The LLD assigns chat-image storage failures to existing media errors and requires an alert before storage exhaustion.

**Scope:** backend closure, retention, legal holds, evidence access and audit, and the erasure service described in Part H. Admin UI, dispute workflow, automatic account-closure integration, call recordings and transcripts are outside this story. Platform encryption is an operational prerequisite, not a new message-encryption scheme.

## 3. Design Reference

- [Part H](../LLD/Sprint-4-Communication-Negotiation-LLD.md#part-h---us-016-communication-history-storage): close a conversation on the specified listing events or inactivity; calculate chat and call-log retention from closure, default 180 days; inactivity closure defaults to 90 days. An inactive-closed thread reopens on a new message. Expiry alone does not close it.
- [Part H.4](../LLD/Sprint-4-Communication-Negotiation-LLD.md#h4-api-contract): role-gated admin evidence and hold APIs require a case reference and reason; access is auditable. A real case registry arrives with the dispute module.
- [Part H.5](../LLD/Sprint-4-Communication-Negotiation-LLD.md#h5-backend-design): scheduled, batched retention skips held evidence; erasure is provided as a service, with account-closure invocation deferred. Platform database, backup and bucket encryption provide encryption at rest.
- Existing `V34__chat.sql` and `V43__call_sessions.sql` contain retention and hold fields and purge indexes. `CommunicationHolds` currently holds reported calls only; `CommunicationHoldPort` exposes `holdForReport` only. `ContactAttemptRetentionJob` already exists and should be reused or coordinated, not duplicated.

## 4. Implementation Steps

### Workflow
- [x] Confirm the chat, call and report prerequisites are merged into the chosen backend base; record any missing dependency before implementation.
- [x] Create a story feature branch from `main` and rebase on `main` as required by `CLAUDE.md` and the coding standards; do not overwrite existing work.

### Database and Settings
- [x] Add a Flyway migration using the next available version for the append-only `communication_access_log`, its indexes and update/delete protection, as in H.3. Keep entries at least seven years; the authorised purge mechanism remains an operations/security decision (G4).
- [ ] Verify and add missing retention settings and defaults from LLD section 1.6, including chat, call-log, inactivity and contact-attempt periods. Reuse existing retention columns and indexes; add only indexes needed by the actual queries.
- [ ] Persist independently identifiable holds by source and target; preserve existing call holds and make the effective hold cover all active applicable holds (G1). Reconcile the existing image-message CHECK with erasure (G2).

### Backend: Closure and Retention
- [ ] Implement `CommunicationClosureService` for specified listing status and deletion events, with idempotent closure timestamps and separate chat/call purge dates. Define the `OrderClosedEvent` integration as a hand-off until the order lifecycle publishes it.
- [ ] Implement `CommunicationInactivityJob` using `COMM_INACTIVE_CLOSE_DAYS`; exclude open negotiations, active price agreements and live calls. Reopen an `INACTIVE`-closed thread on a new user message, call or offer, and clear its associated call retention deadlines (G9, G10). For a thread closed by listing sale or deletion, preserve the original closure timestamp and reason, but restart chat and related call-log retention deadlines on each new user message (G8).
- [ ] Implement `CommunicationRetentionJob`: daily batches of up to 500 using `FOR UPDATE SKIP LOCKED`; preserve holds, delete chat images through the retryable media operation (G15), remove eligible threads/messages and eligible call logs/events. Persist deletion progress, retain DB records until image deletion is confirmed, and retry partial failures safely (G2). Serialize hold creation and the durable start of purge for each affected target: a hold committed first prevents purge; after purge starts, explicitly refuse and audit later hold requests rather than claim deleted evidence is protected. Reject new message sends once the conversation's purge has started (G13). Track and retry original-object cleanup after sanitization (G16).
- [ ] Reuse or coordinate `ContactAttemptRetentionJob` for its existing retention rule. Emit the LLD's counts, durations and alerts without message content or personal data in operational logs.

### Backend: Holds, Evidence and Erasure
- [ ] Extend the existing `CommunicationHoldPort` and `CommunicationHolds` for separately tracked report and admin holds on threads and calls, including propagation to related calls. Preserve existing reported-call behavior; the existing admin delete endpoint releases only the admin hold for its target and `X-Case-Reference`, leaving all other holds intact (G1). Dispute hold integration remains a later hand-off.
- [ ] Implement `CommunicationEvidenceService`, `CaseReferencePort` with the LLD's format-only interim implementation (G14), and admin endpoints for threads, messages, call logs, holds and access logs. Return bounded pages for messages, call lists and call events so complete evidence remains accessible across requests (G18). Do not add a transcript endpoint.
- [ ] Enforce `ADMIN`/`SUPER_ADMIN`, the case-reference header and a reason of at least 10 characters; return the LLD's validation and retrieval errors. Keep evidence endpoints disabled in production until US-053 provides server-verified admin roles and active-account checks (G17). Durably audit every evidence read, including failed retrievals, in an independent transaction; fail closed if the audit cannot be recorded (G3). Never expose phone numbers or email addresses.
- [ ] Record and alert on report-hold failures, retry them, and prevent retention from deleting potentially affected evidence until protection is confirmed. Reconcile existing reports before enabling purge (G6). For a user report, hold all existing conversations shared by the reporter and reported user and their call logs (G11). If purge has already begun, save the report and return an explicit conflict including its report ID (G12).
- [ ] Implement and test `CommunicationErasureService.anonymiseUser` for eligible messages, images, flags and previews; track and retry deferred erasures after all applicable holds end. Account-closure triggering and dispute integration are later hand-offs (G5).
- [ ] Require deployment verification of encryption for database volumes, backups and chat-image storage and of transport security before release; product/legal own the privacy disclosure review. Confirm storage alerts and existing upload-error handling (G7).

### Documentation and Quality Gates
- [ ] Build and run backend unit and integration tests, Checkstyle and SonarQube; fix issues introduced by this story before push. Target more than 90% coverage for story changes, following `CLAUDE.md`.
- [ ] Reconcile any approved implementation deviations with the Sprint 4 LLD and related documentation; create a manual testing guide, including an operational staging check.
- [ ] Tally the implementation against the criteria and edge cases below. Obtain user approval before commit, push or PR.

## 5. Test Plan

Target above 90% coverage on new and changed code. Use unit tests with a fixed clock and mocks; use PostgreSQL integration tests for SQL, locking, transactions and database triggers.

| Coverage | Tests |
|---|---|
| AC1, AC3 | Closure reasons, configured deadlines, default 180-day retention, expiry exclusion, repeated closure, inactivity exclusions, inactive reopen on message, call or offer, and later user messages restarting chat and call-log deadlines after sale or deletion without changing closure metadata; chat and call timestamps. Verify platform encryption configuration separately. |
| AC2, AC4 | Admin and super-admin allowed; non-admin denied; missing case reference or short reason rejected; paginated thread, message and call retrieval; no phone/email; successful and failed reads produce durable audit entries even after rollback; audit failure denies access; access-log update/delete refused. |
| AC3, legal hold | Before/at/after deadline; held thread, calls and images survive; independent overlapping report/admin holds and propagation; releasing one does not release another; a hold committed before purge blocks deletion, and a hold after purge starts is refused and audited; repeat jobs and concurrent workers do not double-process. |
| Storage and recovery | Image deletion failure, DB failure after storage operation, durable progress and retry; DB records remain until image deletion is confirmed; a send after purge starts is refused, while an eligible new conversation can be opened after purge; contact-attempt retention without duplicate jobs; metrics/alerts and no communication content in logs. |
| User deletion | Anonymise only eligible data, remove images and clear previews/flags; held or protected data remains pending and is retried after all holds end; verify schema constraints and idempotence. |
| Inappropriate content / old logs | Reported thread, message and call evidence is preserved; a user report holds all existing shared conversations and calls; failed holds alert and retry while purge is blocked for affected evidence; reconcile existing reports before purge; a report made after purge starts persists and returns a conflict with its report ID; unheld expired evidence becomes unavailable; appropriate retrieval errors are returned. |
| Integration / operations | Listing SOLD and deleted events close the appropriate threads, including property sale; inactivity excludes active negotiations and calls; staging shortened-retention run deletes eligible data but preserves held evidence. |

## 6. Validation Checklist

- [ ] AC1: chat and call-log timestamps are present, encryption at rest and in transit is verified, and calls have no recordings or transcripts.
- [ ] AC2 and AC4: only authorised admins can retrieve relevant evidence; reference and reason are required; all reads are durably audited, including failed retrievals.
- [ ] AC3: chat, images and call logs follow their separate retention settings from conversation closure, and legal holds prevent deletion.
- [ ] Listing closure, expiry exception, inactivity, reopen and future order-event hand-off match Part H.
- [ ] All four story edge cases and both story error scenarios are addressed or explicitly documented as dependencies/gaps.
- [ ] Reported evidence, concurrent or repeated jobs, deletion failures and multiple holds cannot silently lose protected evidence.
- [ ] Unit/integration tests, coverage target, build, Checkstyle and SonarQube are complete; manual guide and LLD follow-up are ready.

## 7. Open Gaps / Questions

| ID | Accepted recommendation and remaining dependency |
|---|---|
| G1 | **Accepted:** track report, dispute and admin holds independently and release evidence only when no applicable hold remains. The existing admin delete endpoint releases only the admin hold for its target and `X-Case-Reference`; report, dispute and other case holds remain intact. Report closure and dispute integration are later workflows. |
| G2 | **Accepted:** persist deletion progress, retry storage failures and retain DB records until image deletion is confirmed. Serialize hold creation and durable purge start per affected target: a hold committed first blocks purge; a later hold is explicitly refused and audited once purge starts. Adapt the image-message CHECK for erasure and verify recovery from partial success. |
| G3 | **Accepted:** write evidence access logs in an independent transaction, including failed retrievals; fail closed when audit recording fails. |
| G4 | **Accepted:** retain audit records at least seven years and use only an authorised purge mechanism; ordinary updates/deletes stay blocked. **Open:** operations/security must define that mechanism and Infra must define how restores reapply deletions before the corresponding purge/restore procedures are enabled. |
| G5 | **Accepted:** account closure invokes erasure in a later story; record deferred erasures and retry after all holds end. **Open:** account-closure timing and dispute integration (LLD O9), real case authorisation in Sprint 8 and finer roles in Sprint 10 (O11). |
| G6 | **Accepted:** record, alert and retry failed report holds, block retention of potentially affected evidence until protected, and reconcile existing reports before enabling purge. |
| G7 | **Accepted:** require deployment verification of database, backup and bucket encryption before release; product/legal review privacy disclosures; confirm capacity alerts and existing upload-error handling. **Open:** named owners and evidence of completion. |
| G8 | **Accepted:** conversations remain writable after a listing is sold or deleted. Each later user message restarts chat and related call-log retention deadlines, preserving the original closure timestamp and reason. Threads closed for inactivity reopen instead. |
| G9 | **Accepted:** starting a call on an inactivity-closed conversation reopens it and clears the existing chat and call-log retention deadlines. A later closure schedules retention for all its call logs. |
| G10 | **Accepted:** starting a new offer on an inactivity-closed conversation reopens it and clears its retention deadlines, so the active negotiation keeps it open. |
| G11 | **Accepted:** a user report does not identify a conversation, so hold all existing conversations shared by the reporter and reported user and their call logs until that report is closed. Apply the same rule when reconciling existing open reports. |
| G12 | **Accepted:** when reported evidence is already being purged, save the report and return an explicit conflict containing its report ID rather than imply its evidence is protected. For reports covering multiple conversations, hold every conversation and call still available even if some evidence is unavailable. The mobile explanation is a separate follow-up; this plan remains backend-only. |
| G13 | **Accepted:** once a conversation's purge has started, reject message sends, new calls and new offers with an explicit conversation-unavailable error; after purge completes, an eligible listing can open a new conversation through the normal flow. |
| G14 | **Accepted:** until real case authorisation exists, case references contain 1 to 60 ASCII letters, digits, hyphens or underscores. This syntax check does not establish that the case exists or the admin is authorised for it. |
| G15 | **Accepted:** extend the backend media boundary with a chat-image deletion operation that retries pending storage deletion and confirms completion. Preserve the existing public deletion behavior; do not enable automatic purge without confirmed deletion and retry. |
| G16 | **Accepted:** durably track and retry cleanup of original chat-image objects when sanitization cannot delete them. **Open:** Infra must inventory and reconcile historical leftover originals, whose object keys were not retained in the database. |
| G17 | **Accepted:** keep admin evidence endpoints disabled in production until US-053 supplies server-verified admin roles and active-account checks. Build and test the evidence implementation without treating signed-token role claims alone as production authorisation. |
| G18 | **Accepted:** paginate message timelines, call lists and call events with continuation metadata; admins can retrieve the complete evidence across bounded requests. |

**Status:** Approved
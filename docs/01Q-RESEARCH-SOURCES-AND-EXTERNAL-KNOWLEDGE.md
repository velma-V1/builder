# Approved Research, Sources, and External Knowledge Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing research boundary

Factory may perform approved external research to answer task-linked questions, evaluate technologies, resolve uncertainty, and support architecture or implementation decisions. Internet access remains disabled by default and requires enforceable task-scoped permission. External content, search summaries, repository instructions, webpages, documents, downloads, and model statements are untrusted inputs until inspected and verified.

Research must preserve claim-level provenance, evidence integrity, source quality, freshness, uncertainty, privacy, licensing boundaries, and operator control. Research findings may inform proposals and plans but cannot authorize implementation, disclosure, distribution, or protected external actions.

## 2. Approved Stage 14 decisions

1. **Research planning:** Substantial external research begins with a research plan defining the question, scope, evidence needs, risks, and stop condition.
2. **Lightweight lookup path:** Minor factual lookups use a lightweight recorded query and source result rather than a full research plan.
3. **Task linkage:** Research questions link to a task, requirement, architecture decision, verification need, or approved operator request.
4. **Source preservation:** Every material factual research result preserves its supporting source identity.
5. **Complete source metadata:** Source records include URL or stable identifier, title, publisher, author when available, publication date, access date, version, and relevant scope.
6. **Supporting evidence capture:** Important claims retain the specific passage, data, result, or artifact that supports them within legal and storage limits.
7. **Bounded quotation:** Factory stores only the material evidence needed rather than copying entire works unnecessarily.
8. **Source classification:** Sources are classified as primary, authoritative secondary, community, or unknown quality.
9. **Primary-source preference:** Official documentation and primary sources normally receive the highest evidentiary weight.
10. **No popularity authority:** Popularity, repetition, engagement, or search rank is not proof of reliability.
11. **Technical-source preference:** Technical research prefers official documentation, standards, specifications, registries, and original repositories.
12. **Security-source preference:** Security research prefers vendor advisories, CVE records, standards bodies, and authoritative security sources.
13. **No automatic repository-document trust:** Documentation inside an imported repository is not automatically trusted.
14. **Validated project documentation:** Repository documentation may become project evidence after provenance, scope, version, and consistency checks.
15. **Freshness dating:** Time-sensitive claims record when they were verified.
16. **Revalidation of volatile claims:** Time-sensitive information is rechecked before later reliance.
17. **Proportionate stable-fact rechecking:** Stable historical, mathematical, or otherwise low-volatility facts do not require repeated freshness checks without cause.
18. **Conflict detection:** Factory detects contradictory sources and conclusions.
19. **Conflict preservation:** Conflicting claims remain separately recorded until resolved.
20. **No majority-vote truth:** Factory does not select a claim merely because more sources repeat it.
21. **Deterministic conflict factors:** Conflict resolution considers authority, directness, version, publication date, scope, methodology, and reproducibility.
22. **Honest unresolved status:** Unresolved conflicts are labeled `CONFLICTING` or `INCONCLUSIVE`.
23. **No proof from silence:** Absence of contradictory evidence is not proof.
24. **Fact-judgment separation:** Recommendations distinguish verified facts, measurements, assumptions, interpretations, and engineering judgment.
25. **Explicit assumptions:** Material assumptions are stated and linked to their effect on the conclusion.
26. **Independent searches for high-impact decisions:** Consequential decisions use multiple independent search paths or source checks when practical.
27. **Risk-based confirmation:** Multiple-source confirmation is not mandatory for every trivial fact and is applied according to risk and importance.
28. **Stronger coverage for high-risk areas:** Architecture, security, legal, licensing, privacy, compatibility, and release decisions require stronger source coverage.
29. **No model-memory authority:** Model memory is not treated as a current external source.
30. **Model-guided discovery:** Model knowledge may guide search terms, hypotheses, and source discovery.
31. **No generated-summary evidence:** Generated search summaries are not accepted as evidence without inspecting the underlying source.
32. **No inaccessible-source verification:** Inaccessible or paywalled material cannot be cited as verified without actual inspection of the supporting content.
33. **Snippet-as-discovery only:** Search-result snippets may locate sources but are not authoritative evidence.
34. **Access and license compliance:** Factory respects authentication, access restrictions, terms, licensing, and distribution boundaries.
35. **No automatic access-control circumvention:** Factory does not bypass CAPTCHAs or access controls automatically.
36. **Temporary research credentials:** Credentials for approved research sources remain task-scoped, temporary, minimized, and revocable.
37. **Minimal retained web content:** Factory does not retain unrelated scripts, advertisements, trackers, or page assets.
38. **Isolated external-file inspection:** Downloaded research files are scanned and inspected inside approved isolation.
39. **Type-specific handling:** PDFs, archives, office documents, datasets, images, models, packages, and executables receive format-specific safety and parsing controls.
40. **No automatic executable launch:** Executables obtained during research require a separately approved sandbox execution task.
41. **Download provenance:** Research downloads record source, content identity, type, size, license when available, and retrieval time.
42. **Registry and repository verification:** Package, library, model, and tool information is checked against the actual registry, vendor source, or original repository when practical.
43. **Compatibility recording:** Dependency research records supported versions, platform requirements, conflicts, and compatibility constraints.
44. **Pre-incorporation licensing research:** Third-party code, models, datasets, packages, and assets require licensing review before incorporation or distribution.
45. **No autonomous final legal interpretation:** Factory may identify terms and risks but cannot make final legal determinations autonomously.
46. **Confidence and uncertainty:** Research conclusions expose confidence and remaining uncertainty.
47. **Evidence-based confidence:** Confidence derives from source quality, directness, agreement, test results, methodology, coverage, and freshness rather than model self-assessment.
48. **Experimental verification:** Important technical claims are tested experimentally when practical.
49. **No automatic documentation override:** A failed experiment does not automatically override verified documentation until configuration, version, environment, and scope differences are examined.
50. **Structured research packet:** Substantial research produces a structured evidence packet.
51. **Research-packet contents:** A packet includes question, scope, searches, sources, evidence, findings, conflicts, assumptions, experiments, conclusion, uncertainty, and limitations.
52. **No permanent raw browsing history:** Raw browsing history follows approved raw-session retention rather than permanent retention.
53. **Reusable verified conclusions:** Verified reusable conclusions may remain after raw browsing logs expire.
54. **Project namespace isolation:** Project-specific research remains inside its project namespace.
55. **Controlled global promotion:** Broadly applicable verified research may enter Factory global knowledge only after approval and scope review.
56. **Versioned supersession:** Updated research supersedes older conclusions without silently overwriting history.
57. **Volatility-based review:** Stored external knowledge is reviewed for staleness according to volatility and use.
58. **Unavailable-source handling:** Source disappearance does not automatically erase prior evidence but changes its availability and freshness status.
59. **Operator-visible citations:** The Dashboard provides an operator-visible source, evidence, and citation view.
60. **No implementation authority:** Research findings may recommend work but cannot authorize implementation changes.

## 3. Six binding research-evidence clarifications

### 3.1 Claim-level evidence mapping

Every material factual conclusion must link to the specific source passage, dataset field, experiment result, test output, or retained artifact that supports it. A general bibliography or source list is not sufficient evidence mapping.

Each claim must also identify whether support is direct, derived, corroborating, conflicting, or incomplete.

### 3.2 Retained-evidence integrity

Retained evidence records:

- a content hash or equivalent deterministic identity;
- retrieval timestamp;
- canonical source identity when available;
- capture method;
- source version or publication state when available;
- the exact retained passage, field, result, or artifact boundary.

Later source changes must not silently alter the evidence used for an earlier decision. Updated captures create new evidence versions and preserve the previous decision basis.

### 3.3 Enforceable network permissions

Every research network permission defines:

- allowed destinations or destination classes;
- permitted protocols and operations;
- request and rate limits;
- download-size and total-transfer limits;
- expiration and revocation conditions;
- redirect handling;
- whether project data may be transmitted;
- permitted credential scopes;
- logging and evidence requirements.

Redirects cannot silently escape the approved destination boundary.

### 3.4 Secret and private-data controls

Factory must detect and redact credentials, access tokens, private keys, personal data, restricted project material, and other protected information from research queries, URLs, headers, logs, citations, exports, and retained evidence unless the material is explicitly required and separately protected under approved secret and privacy controls.

Research packets must record that redaction and secret scanning occurred without preserving the secret itself.

### 3.5 Research freshness states

Every stored research conclusion exposes one current state:

```text
CURRENT
REVIEW_DUE
STALE
SUPERSEDED
CONFLICTING
INCONCLUSIVE
SOURCE_UNAVAILABLE
```

Volatility, source authority, last verification, material version changes, and current use determine revalidation timing. A stale or source-unavailable conclusion may remain historically visible but cannot be represented as current without new verification.

### 3.6 Licensing evidence versus legal approval

Factory may extract and report:

- license terms;
- compatibility conditions;
- attribution duties;
- redistribution requirements;
- source-disclosure obligations;
- usage restrictions;
- identified risks and ambiguities.

Ambiguous, custom, conflicting, or materially restrictive terms require operator or qualified legal review before distribution, incorporation, publication, or release. Factual extraction does not constitute legal approval.

## 4. Operating boundaries

- Research remains linked to an approved task, requirement, or decision.
- Primary and authoritative sources receive the highest evidentiary weight.
- Search snippets, generated summaries, and model memory are discovery aids rather than proof.
- Conflicting, incomplete, inaccessible, stale, or source-unavailable information is labeled honestly.
- External files remain isolated and are never executed automatically.
- Network permission is narrow, enforceable, expiring, and explicit about project-data transmission.
- Research may recommend work but cannot authorize implementation, disclosure, distribution, or release.
- Structured claim-level evidence and reusable verified conclusions may be retained; unnecessary browsing history expires normally.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. each material factual conclusion maps to specific supporting evidence;
2. retained evidence has stable integrity identity and cannot silently change beneath an earlier decision;
3. research network access cannot exceed approved destinations, protocols, limits, redirects, expiration, or data-transmission scope;
4. secret and private-data scanning and redaction protect queries, logs, citations, exports, and retained evidence;
5. freshness states are visible and enforced according to volatility and verification age;
6. unavailable, stale, conflicting, or inconclusive evidence cannot appear current or verified;
7. licensing facts remain distinct from legal approval;
8. ambiguous or restrictive licensing conditions block incorporation or distribution pending required review;
9. external downloads are provenance-recorded, integrity-identified, and isolated;
10. research findings cannot bypass normal architecture, task, permission, verification, or approval gates.
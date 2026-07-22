# Standalone Local AI Builder — Approved Project Definition

**Repository:** `velma-V1/builder`  
**Status:** Governing project definition  
**Version:** 0.1  
**Recorded:** July 22, 2026  

## 1. Project identity

This project is a **standalone, highly efficient, intelligent, graph-mapped local AI builder system**.

Its motto is:

> **If you can dream it, we can build it.**

The system is intended for one primary user. It must help that user build, improve, repair, test, document, package, and maintain complete runnable code-based systems without losing track of what is happening or why.

## 2. Strict project boundary

This repository defines only this standalone builder.

Requirements, architecture, components, memory, rules, or decisions from another project must not be added to this project unless the user explicitly approves the transfer.

Likewise, this builder's requirements must not be silently inserted into another project.

Project-specific information must remain isolated by default.

## 3. End goal

The builder must support both:

1. Creating new systems.
2. Repairing, improving, extending, and maintaining existing systems.

Its target scope includes:

- Local AI systems
- Multi-agent systems
- RAG and knowledge systems
- Model-routing systems
- Custom model training and tuning systems
- Tool-using agents
- AI evaluation and verification systems
- Software
- Programs
- Desktop applications
- Web applications
- Websites
- APIs
- Services
- Libraries
- Automation systems
- Other code-based systems it can understand or safely learn how to build

The builder must not claim automatic expertise in every technology. For unfamiliar systems, it must research the relevant technology, identify the required toolchain, verify the information, and stop only when additional permission or a human decision is genuinely required.

## 4. Highest-priority build capabilities

The first five priority system types are:

1. Local AI and multi-agent systems
2. RAG and knowledge systems
3. Model-routing systems
4. Custom model training and tuning systems
5. Tool-using agents

These priorities do not remove the broader requirement to build and maintain other code-based systems.

## 5. Accepted project inputs

The builder must be able to begin from:

- A plain-language idea
- A detailed specification
- An existing repository
- An incomplete project
- A broken project
- A request to improve or maintain an existing project

## 6. Required work stages

The builder must eventually be capable of performing the complete lifecycle:

1. Requirements gathering
2. Research
3. Repository inspection
4. Malicious-instruction inspection
5. Architecture design
6. Build-direction presentation
7. User direction approval
8. Planning
9. Coding
10. Debugging
11. Testing
12. Security review
13. Visual inspection
14. Documentation
15. Packaging
16. Installation preparation
17. Release preparation
18. Updating and maintenance
19. Final verification
20. Reporting

The user may assist with installation and real-time physical or environment-specific testing. The long-term goal is for the builder to handle the rest autonomously when sufficient permissions and tools are available.

## 7. Required final output

The expected result is a **complete runnable project**, not merely source-code suggestions.

All applicable final deliverables must be produced:

- Source repository
- Runnable source code
- Automated tests
- Exact test evidence
- Failure-path evidence
- Security results
- Visual evidence when applicable
- Documentation
- Setup instructions
- Guided installation
- Installer when applicable
- Docker configuration when applicable
- Executable application or verified launch method
- Release package
- Architecture map
- Repository graph
- Agent workflow graph
- Live execution graph
- Audit record
- Rollback point
- Maintenance instructions
- Known limitations
- Verification-status classifications

## 8. Autonomy control

Autonomy must be selectable from **1% through 100%** rather than fixed to a single operating mode.

At low autonomy, the builder primarily explains, recommends, and waits for instructions.

At higher autonomy, it may research, plan, implement, test, diagnose, repair, retest, review, document, and package with fewer interruptions.

At all autonomy levels, protected decisions and permission boundaries remain in force.

Before implementation begins, the builder must present the proposed build direction and ask the user to verify that direction.

## 9. Valid stop conditions

The builder may stop only for:

- A confirmed security risk
- A required human decision
- A verified blocker
- Missing information that cannot be found or verified without additional permission
- An action that exceeds the granted permission boundary

Missing information alone is not an immediate stop condition. The builder must first search approved sources and attempt to verify the needed information.

A failed test is not a valid reason to abandon the task. The builder must diagnose, repair, and retest unless a valid stop condition is reached.

## 10. Failure learning and reporting

When something fails, the builder must:

1. Record the attempted method.
2. Record the exact failure.
3. Diagnose the likely cause.
4. Apply a controlled repair.
5. Retest.
6. Record what did not work.
7. Record what worked.
8. Preserve the evidence needed to improve future work.

Failure history must be compressed into useful structured records instead of repeatedly loading unnecessary raw history.

## 11. Required specialist capabilities

The completed builder requires the following specialist capabilities:

- Architect
- Researcher
- Requirements analyst
- Planner
- Coder
- Tester
- Debugger
- Reviewer
- Security reviewer
- Documentation writer
- Visual inspector
- Repository mapper
- Memory manager
- Model and tool router
- Final verification layer

These are required capabilities, not a requirement for fifteen separate models or fifteen independent agent frameworks.

The implementation must use the **simplest and strongest design that satisfies the full requirement set**.

## 12. Model and runtime requirements

The builder must support multiple local model runtimes from the beginning.

Model selection must consider:

- Task difficulty
- Model strengths
- Coding ability
- Reasoning ability
- Context capacity
- Vision capability
- Tool-use reliability
- Available CPU
- Available RAM
- Available GPU and VRAM
- Current system load
- Privacy requirements
- Required speed

Primary operation must remain local.

An optional controlled cloud socket may use free models or services with no-cost, high free-use, or high-rate limits.

Cloud availability must never be required for the builder's basic operation.

Private project information must not be sent outside the local system without explicit permission.

## 13. Internet-access policy

Internet access is disabled by default.

The builder may access the internet when:

- The user explicitly requests a web search or deep research.
- The user grants permission for a task that requires internet access.

Internet permission must remain scoped to the approved task.

## 14. Interactive dashboard

The primary interface must be an interactive dashboard.

The dashboard must provide a selectable dropdown or equivalent control that determines which panels are currently displayed.

Available panels must include:

- Current project
- Requirements
- Architecture
- Current plan
- Build direction
- Specialist and agent activity
- Files being inspected
- Files being changed
- Live terminal
- Build status
- Test results
- Failure and repair history
- Application preview
- Screenshots
- Approval requests
- Repository map
- Source-code graph
- Agent workflow graph
- Live execution graph
- System architecture graph
- Model selection and usage
- CPU usage
- RAM usage
- GPU usage
- VRAM usage
- Storage usage
- Audit history
- Checkpoints
- Rollback controls
- Documentation
- Reports

The interface must keep the user oriented and must clearly show:

- What is happening
- Why it is happening
- What changed
- What passed
- What failed
- What was repaired
- What remains unverified
- What requires a user decision

## 15. Required graph views

The graph-mapping system must support all four views below.

### 15.1 Source-code graph

- Files
- Functions
- Classes
- Methods
- Imports
- Calls
- Dependencies
- Tests
- Data flows
- Change impact

### 15.2 Agent workflow graph

- Specialist roles
- Delegations
- Approval gates
- Verification gates
- Failure loops
- Repair loops

### 15.3 Live execution graph

- Current task
- Active component
- Completed steps
- Waiting steps
- Blockers
- Retries
- Test results
- Rollbacks

### 15.4 System architecture graph

- Models
- Tools
- Skills
- Memory
- Sandboxes
- Interfaces
- Services
- Permissions
- Data boundaries

## 16. Repository and project control

The builder must support very large repositories, although an exact maximum size has not yet been set.

Every task must use:

- A separate Git branch
- A starting checkpoint
- Temporary rollback points
- Exact file-change tracking
- Structured task history
- Test and verification records
- Final approval before commit

The builder must be able to navigate a repository and its project records as a structured source of truth.

Existing tests are protected evidence.

The builder must not silently alter existing tests merely to make generated code pass.

When test changes are legitimately required, it must load the relevant test state, explain the proposed change, request permission where required, and preserve a record of:

- What changed
- Why it changed
- What previously failed
- What now passes
- What remains unresolved

Changing an approved project architecture requires user permission.

## 17. Verification rules

Every material result or claim must be classified as one of:

- **Verified**
- **Unverified**
- **Failed**
- **Not testable**

A model may review work and may assist with testing, but model agreement is not sufficient proof.

The result must still pass an independent verification layer based on applicable deterministic tests, tools, inspection, or evidence.

For visual systems, verification must include applicable actions such as:

- Launching the system
- Interacting with the interface
- Capturing screenshots
- Checking expected behavior
- Comparing results
- Recording visual evidence

When complete verification is impossible, the builder must classify the result accurately and may continue to the next safe step. It must not relabel an unverified or not-testable result as verified.

## 18. Isolation and execution

The builder must select the correct isolation method for each task rather than forcing every task into one environment.

Possible execution environments include:

- Disposable containers
- WSL2
- Restricted Windows-native execution
- Other approved temporary environments

The final isolation design has not yet been selected.

Temporary dependency changes and experimental environments must have rollback protection. Temporary rollback points may be removed only after the relevant tests prove the change stable.

## 19. Security requirements

The builder must:

- Keep internet access disabled by default
- Restrict access to the approved project by default
- Detect suspicious or malicious repository instructions
- Detect prompt-injection attempts in code, comments, documents, and retrieved material
- Notify the user before following or working around malicious instructions
- Prevent silent access outside the project
- Prevent silent publishing or releasing
- Preserve a complete record of commands, changes, approvals, tests, and rollbacks

Project records must be structured in the repository or project files rather than scattered across unrelated computer storage.

Raw temporary runtime data may remain local and disposable, but permanent evidence and project decisions must be stored in the appropriate project record.

## 20. Memory model

The builder uses two separated memory scopes.

### 20.1 Project memory

Most information must remain inside the specific project's repository or project files, including:

- Requirements
- Architecture decisions
- Current plans
- Research
- Source references
- Files changed
- Tests performed
- Test results
- Failures
- Repairs
- Known limitations
- Installation instructions
- Verification evidence
- Maintenance notes

Project information must not automatically transfer into another project.

### 20.2 Permanent builder memory

The builder's own permanent memory must remain small.

It may contain only reusable, verified information that improves the builder itself, such as:

- Proven build strategies
- Reusable debugging patterns
- Verified tool configurations
- Repeated failure causes
- Safe workflow improvements
- User-approved operating preferences

It must not become a duplicate store of entire repositories, full conversations, private source code, or temporary project details.

### 20.3 Memory provenance

Every stored fact must retain:

- Source
- Project origin
- Date recorded
- Verification status
- Verification method
- Supporting evidence
- Scope of validity
- Relevant versions
- Review or expiration condition

A model-generated statement is not automatically a fact.

## 21. Automatic acceptance of significant improvements

The builder may automatically accept and retain a skill, tool, lesson, workflow, rule, configuration, or knowledge item when it proves and verifies that the item adds significant value to the builder's uses, functions, knowledge, results, or capabilities.

Automatic acceptance is allowed only when all of the following are true:

1. The improvement has controlled test evidence.
2. The result is repeatable.
3. The value is measurable and significant.
4. It improves at least one approved priority without reducing a higher-priority requirement.
5. It introduces no unapproved privacy, security, external-access, or cost change.
6. It is safe and reversible.
7. A rollback method exists and has been verified.
8. It is reusable beyond one temporary project condition.
9. Project-specific information remains inside the project.
10. Deterministic evidence or tools independently verify the result.
11. The promotion is fully recorded.

Significant value may include verified improvement in:

- Accuracy
- Reliability
- Build quality
- Security
- Verification quality
- Debugging success
- Tool capability
- Supported system types
- Knowledge quality
- Resource efficiency
- User clarity
- Recovery or rollback capability

Automatic acceptance is not allowed when the proposed improvement:

- Changes core architecture
- Changes security or permission rules
- Adds a required cloud dependency
- Adds a paid service
- Sends project data outside the local system
- Replaces a core tool or model
- Alters permanent user preferences
- Creates a major hardware or storage requirement
- Cannot be fully reversed
- Has mixed, incomplete, or uncertain evidence

Those changes require user approval.

The builder must record every automatically accepted improvement with:

- Exact item added
- Reason for acceptance
- Source
- Version
- Scope
- Test evidence
- Measured benefit
- Regression results
- Security results
- Date
- Rollback method
- Review condition

## 22. Priority order

All design and implementation decisions must preserve this order:

1. Accuracy
2. Reliability
3. Build quality
4. Full local operation
5. Simplicity
6. Broad capability
7. Low hardware usage
8. Speed
9. Easy installation
10. Low storage use

An improvement in a lower-ranked priority must not reduce a higher-ranked priority without explicit user approval.

## 23. Installation and operating target

The initial development and operating target is:

- Unactivated Windows 11 Home
- One installer as the preferred final installation experience
- A guided setup script or guided setup process

Implementation details such as container orchestration may be used internally, but the user should not be required to understand those details to install and operate the finished builder.

## 24. Final success criterion

The builder will be considered functionally successful when the user can sit down with it and work through the complete build of VELMA in clear steps without becoming confused about what is happening.

VELMA is the validation project for the builder's capability. VELMA's internal requirements do not automatically become requirements of this builder.

The first success threshold does not require complete hands-off autonomy. It requires a reliable builder that can guide and perform the full process while keeping the user informed, oriented, and in control.

## 25. Open decisions — not yet approved

No architecture or coding should treat these items as settled until the user decides them.

### 25.1 Initial language and framework support

The first supported language and framework set has not yet been selected.

### 25.2 Exact completion-evidence gate

The precise minimum evidence required before the builder may declare a task complete has not yet been finalized.

### 25.3 Automatic permissions inside the sandbox

The current requirements establish approval for protected external actions, commits, releases, and architecture changes. The exact rule for automatically editing files, deleting files, and installing dependencies inside a disposable approved sandbox remains unresolved and must not be assumed.

## 26. Pre-architecture rule

This document establishes the approved project purpose, scope, priorities, controls, and success criteria.

It does **not** approve a specific architecture, repository foundation, agent framework, model lineup, graph library, database, or implementation stack.

Architecture and coding may begin only after:

1. The open decisions that materially affect the architecture are resolved.
2. Candidate components are evaluated against this definition.
3. The proposed build direction is presented clearly.
4. The user approves that direction.

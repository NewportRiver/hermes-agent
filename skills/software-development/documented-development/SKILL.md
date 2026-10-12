---
name: documented-development
description: "Use when developing or maintaining a repository where durable documentation, generated registries, code indexes, plans, and runtime evidence must stay synchronized."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [documentation, engineering, registry, indexing, traceability, project-memory, agentic-development]
    related_skills: [hermes-agent-skill-authoring, test-driven-development, systematic-debugging]
---

# Documented Development

## Overview

Documented development treats durable engineering documentation as part of the implementation system. The repository should let a fresh engineer or agent discover what a component does, why it exists, how it is operated, what depends on it, how it is verified, and what remains uncertain.

A registry is navigation metadata, not proof of behavior. Source code remains authoritative for implementation; tests and runtime evidence prove behavior; plans and manifests explain intent and relationships.

Core principle:

```text
Every durable change leaves a traceable path from intent -> source -> verification -> current state.
```

## When to Use

Use this skill when:

- adding or removing Markdown documentation
- creating plans, task backlogs, manifests, runbooks, decision records, bug records, or recovery notes
- changing repository structure or documentation entry points
- reverse-engineering an unfamiliar codebase
- creating file, symbol, route, schema, configuration, or task indexes
- preparing a branch for handoff, review, restore, or fresh-session resumption
- reconciling source changes with tests, operational docs, and engineering memory

Do not use a generated registry as a substitute for reading the owning source, running a test, or proving a runtime claim.

## Evidence Model

Label claims explicitly:

- `repository-derived` — directly supported by committed source, configuration, or documentation.
- `structural` — generated from paths, headings, imports, symbols, or other static analysis.
- `inferred` — reasoned from multiple repository facts but not directly confirmed.
- `runtime-verified` — confirmed by an executed test, command, health check, trace, or reproducible recipe.
- `planned` — intended work not yet implemented.
- `blocked` — work attempted or required but prevented by a stated prerequisite or environment limitation.

Never turn `structural`, `inferred`, or `planned` information into a runtime claim without executing the relevant verification.

## The Documentation Stack

Maintain separate layers with clear authority:

1. **Source** — code, schemas, migrations, configuration, tests, scripts.
2. **Contracts** — product behavior, API routes, state machines, interfaces, security boundaries.
3. **Plans/tasks** — milestones, task IDs, dependencies, acceptance criteria.
4. **Manifests** — package/domain purpose, entrypoints, dependencies, invariants, tests, runbooks, gaps.
5. **Indexes** — generated Markdown registry, file catalog, symbol index, marker index.
6. **Evidence** — test output, health responses, migration results, traces, sanitized logs.
7. **Project memory** — current work, decisions, bugs/lessons, test status, journal, recovery state.

Generated indexes must point back to authoritative source paths and include provenance where practical.

## Markdown Registry Workflow

### 1. Edit the source document

Edit the authoritative Markdown file. Never hand-edit the generated registry.

Before creating a new document, search for an existing record or skill that should be extended instead. Avoid duplicate sources of truth.

### 2. Link durable documents

Add the new document to the nearest durable entry point, such as:

- repository `README.md`
- contributor `AGENTS.md`
- engineering framework `README.md`
- domain manifest
- plan/task index

A document that cannot be discovered is operationally incomplete.

### 3. Regenerate the registry

Use the repository's generator. Common patterns are:

```sh
python3 engineering/scripts/refresh_md_registry.py
python3 scripts/refresh_master_md_registry.py
```

Do not guess the command. Locate the repository's documented generator first. If no generator exists, create a small deterministic one rather than maintaining a large index by hand.

### 4. Inspect generated changes

Check for:

- expected new and removed paths
- correct headings and descriptions
- accidental inclusion of logs, caches, credentials, or build output
- duplicate entries
- broken relative links
- changes caused only by timestamps or unstable ordering

### 5. Validate

Run the narrow checks appropriate to the repository:

```sh
git diff --check
```

Also run the registry generator again and confirm it produces no additional diff. Validate JSON/YAML indexes with their parsers. Validate links when the repository provides a checker.

### 6. Record state and commit together

When the change affects durable project state, update the appropriate current-work, test-status, decision, bug/lesson, journal, or recovery record. Commit the authoritative Markdown and regenerated registry together.

## Code and Marker Indexing

For a large repository, do not stuff all source into one prompt. Build a reproducible layered index.

At minimum, index:

- files and packages
- languages and architectural layers
- public exports and important symbols
- functions/classes/types/constants
- imports and reverse dependents where derivable
- routes, schemas, migrations, configuration keys, and environment variables
- tests and fixtures
- plans, task IDs, requirements, decisions, and known gaps

Use stable marker IDs for retrieval. A marker should contain a type prefix and deterministic identity, for example:

```text
F-XXXXXXXXXX  tracked file
S-XXXXXXXXXX  source symbol
D-XXXXXXXXXX  domain/contract
T-XXXXXXXXXX  task
C-XXXXXXXXXX  configuration/contract
E-XXXXXXXXXX  runtime evidence
```

Markers are retrieval keys, not replacements for paths or line numbers. Keep both the marker and the human-readable source reference. Prefer stable path/symbol identity over line-only identity; lines may be supplemental evidence.

For each development task, create a cross-reference containing:

- task ID and title
- relevant file markers
- relevant symbol markers
- contract/config/test markers
- retrieval patterns or domain manifest
- selection limits and known omissions
- evidence state

Generated marker indexes should record their source catalog commit and generation method.

## Domain Manifests

Create one manifest per bounded context instead of one giant document. A useful manifest contains:

- purpose and non-goals
- owning package/directories
- public entrypoints
- key files and symbol markers
- dependencies and reverse dependents
- data/schema/migration relationships
- configuration and secrets
- invariants and state transitions
- tests and executable recipes
- security and side-effect boundaries
- known gaps and unverified behavior
- last reviewed source commit

A manifest is complete when a fresh agent can use it to locate the owning implementation and choose the smallest relevant verification command.

## Task Traceability

Every non-trivial implementation task should connect:

```text
T-task
  -> requirement/contract
    -> domain manifest
      -> file marker
        -> symbol/route/schema marker
          -> test or operation recipe
            -> evidence record
```

If a link is not known, record `UNKNOWN` or `GAP` explicitly. Do not invent a relationship to make the graph look complete.

Task acceptance criteria should be executable where possible. Prefer:

- exact command
- expected exit code
- expected endpoint/state transition
- required artifact
- cleanup/rollback condition

## Agent Operating Loop

When an agent receives a development request:

1. Read the task and acceptance criteria.
2. Retrieve the task's markers and domain manifest.
3. Read the owning source, contracts, and nearby tests.
4. Identify prerequisites, side effects, and rollback options.
5. Create or run a tight verification loop before changing behavior.
6. Make the smallest bounded change.
7. Run relevant tests or state the blocker.
8. Regenerate indexes affected by the change.
9. Update durable project memory and evidence status.
10. Report completed, verified, unresolved, and unverified items separately.

Completion requires every modified file to be accounted for and every claimed verification to have actual command output or a clearly stated blocker.

## Common Pitfalls

1. **Editing the registry directly.** Fix the authoritative document or generator, then regenerate.
2. **Treating index coverage as understanding.** A path or symbol entry does not explain behavior or prove it works.
3. **One giant architecture document.** Split by bounded domain and link the manifests.
4. **Line-number-only references.** Use stable paths and symbol identity; lines are supplemental.
5. **Stale generated output.** Record source commit and rerun freshness checks after source changes.
6. **Documentation without entry-point links.** A durable document that agents cannot discover is effectively hidden.
7. **Plans without acceptance criteria.** Every task needs a checkable outcome and explicit blocker state.
8. **Runtime claims from static docs.** Mark them planned, inferred, or unverified until executed.
9. **Indexing secrets or transient output.** Redact or exclude credentials, logs, caches, and private runtime data.
10. **Silent automation.** Agent loops need side-effect ceilings, audit trails, stop conditions, and rollback paths.
11. **Duplicate sources of truth.** Extend the existing authoritative record when appropriate.
12. **Generated churn.** Use deterministic ordering and stable serialization to keep diffs reviewable.

## Verification Checklist

- [ ] Authoritative document identified and edited.
- [ ] Existing duplicate/source-of-truth search completed.
- [ ] New durable document linked from an entry point.
- [ ] Registry generator located and run.
- [ ] Generated output inspected for unexpected or transient content.
- [ ] `git diff --check` passes.
- [ ] JSON/YAML indexes parse successfully.
- [ ] Marker IDs are unique and resolve to existing source references.
- [ ] Task-to-file/symbol/test links are present or explicit gaps are recorded.
- [ ] Tests, recipes, or runtime evidence support capability claims.
- [ ] Current work/test status/journal/decision records updated when needed.
- [ ] Credentials, tokens, private keys, and raw sensitive output excluded or redacted.
- [ ] Authoritative source and generated registry are committed together.
- [ ] Fresh-session agent can discover the relevant document and next safe action.

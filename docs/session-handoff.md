# Session Handoff

Use this file at the end of each session.

Goal: let the next session start fast without scanning the whole repository.

## How To Use

1. Update only the fields in `Current Snapshot`.
2. Keep entries short and factual.
3. If scope changes, also update docs/MVP-plan.md.
4. At next session start, read this file first, then docs/MVP-plan.md.

## Current Snapshot

- Date: 2026-03-16
- Current phase (from MVP-plan): Phase 2 (material assignment to geometry)
- Current commit task (for example: Commit 2.3): Phase 2 planning alignment and scope lock
- Status: Ready to implement
- Branch name: not recorded in handoff yet
- Last completed commit task: Phase 2 plan rewrite in docs/MVP-plan.md (openEMS-aligned)
- Next immediate task: implement Phase 2, Commit 2.1 (material assignment properties and persistence)

## Quick Context

- One-paragraph summary of where we are: This session aligned Phase 2 in docs/MVP-plan.md with openEMS material handling. The plan now explicitly defines materials as named properties, geometry assignment to those properties, overlap priority handling, strict preflight requirement of exactly one material per analysis geometry, and a clear Phase 2-to-Phase 3 handoff. Scope for Phase 2 is locked to simple material models (PEC metal or dielectric/general material), with advanced material features deferred. No Phase 2 code implementation has started yet.

## Changes Made This Session

- Files changed: docs/MVP-plan.md
- Main behavior changed: none in code; planning updated so Phase 2 implementation requirements now match openEMS material-property workflow
- Tests added/updated: none (planning session)
- Tests run and result: none (planning session)

## Completed Tasks

- Phase 2 section in docs/MVP-plan.md rewritten to align with openEMS material model and assignment rules.
- Commit-sized tasks for Phase 2 were updated to include persistence model, assignment UI actions, strict preflight checks, assignment lifecycle tests, and Phase 3 handoff contract.
- Explicit Phase 2 out-of-scope list added for advanced material features and final CSX/openEMS command emission.

## Decisions And Assumptions

- Practical MVP first, then coax-specific waveguide and sinusoidal milestone
- Require automatic preflight before Run Simulation and consistent FreeCAD to openEMS unit handling
- Phase 2 material field scope remains simple for MVP: EpsilonR, MuR, Kappa, IsPEC
- Preflight rule for Phase 2: each analysis geometry must have exactly one material assignment
- Assumption to revisit later: add advanced openEMS material options (sigma, anisotropy, spatial weighting) in a later phase

## Blockers

- Blocker: none
- What is needed to unblock: n/a

## Open Questions

- None for starting Commit 2.1 implementation

## Next Session Startup Prompt

Paste and edit this when opening a new chat session:

"Read docs/session-handoff.md and docs/MVP-plan.md first. Continue from Phase 2, Commit 2.1 without rescoping. First summarize current status in 6 bullets max, then implement persistent geometry-to-material assignment properties on material objects and add/update unit tests for persistence behavior."

## Definition Of Done For Current Commit Task

- [ ] Code changes completed
- [ ] Unit tests updated
- [ ] Relevant tests pass
- [x] Documentation updated (if needed)
- [x] Handoff file updated

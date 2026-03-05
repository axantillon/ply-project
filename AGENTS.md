# AGENTS.md

Scope: this file defines collaboration rules for humans and coding agents working in this repository.

## Goals
- Keep the repo easy to understand.
- Keep history clean and reviewable.
- Prevent agent collisions when multiple people/agents work at the same time.

## Required Workflow
1. Create a branch per task. Do not work directly on `main`.
2. Pull/rebase frequently from `main` to reduce merge conflicts.
3. Make small, focused commits at logical checkpoints (at least every 30-60 minutes of active work).
4. Open a PR for review before merging to `main`.

## Commit Discipline
- One commit = one coherent change.
- Write clear commit messages in imperative mood.
- Do not mix refactors, formatting, and behavior changes in one commit.
- Commit early when uncertain; follow with fixup commits rather than holding large local diffs.

## Parallel Agent Safety
- One agent branch per active task.
- Minimize overlap: avoid editing the same file as another active agent unless coordinated.
- If you detect unexpected file changes you did not make, stop and ask for direction.
- Never rewrite shared history (`git push --force`) on collaborative branches.

## Repo Sanitation
- Keep generated files out of commits unless explicitly required.
- Do not commit secrets, tokens, credentials, or personal local paths.
- Avoid broad formatting-only diffs unless the team explicitly agreed to them.
- Keep file names and structure stable; do not rename/move files without clear reason.

## Quality Gates Before Commit
- Run relevant checks/tests for touched code.
- Validate parser behavior with at least one valid and one invalid JSON input.
- Confirm `git status` only includes intentional changes.

## PLY/JSON Project Notes
- Treat parser table artifacts (`parser.out`, `parsetab.py`) as generated outputs.
- Prefer committing grammar/lexer source changes over generated artifacts.
- Keep grammar rules readable and deterministic; avoid hidden side effects in parse actions.

## Prohibited Actions
- Destructive git commands that discard teammate work.
- Editing unrelated files “while here.”
- Large speculative rewrites without prior agreement.

## Recommended Daily Rhythm
1. Sync `main`.
2. Start task branch.
3. Implement in small commits.
4. Rebase, run checks, open PR.
5. Merge and delete branch.

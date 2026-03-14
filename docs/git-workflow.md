# Git Workflow

This project uses a small, beginner-friendly workflow that still keeps history clean.

## Branch naming

Use:

- `phase-<n>-<topic>` for major phase work
- `feature/<topic>` for smaller feature work
- `fix/<topic>` for bug fixes

Examples:

- `phase-3-task-panels`
- `feature/grid-visual-overlay`
- `fix/initgui-import-fallback`

## Commit message format

Use:

`<type>(<scope>): <short summary>`

Types:

- `feat`: new capability
- `fix`: bug fix
- `refactor`: code restructuring without behavior change
- `docs`: documentation only
- `test`: test additions/updates
- `chore`: tooling or maintenance

Scopes used in this repository:

- `workbench`
- `objects`
- `commands`
- `gui`
- `exporter`
- `execution`
- `meshing`
- `validation`
- `docs`
- `tests`

Examples:

- `feat(objects): add OpenEMS boundary FeaturePython proxy`
- `fix(workbench): handle InitGui import fallback in FreeCAD loader`
- `test(objects): add idempotent property registration tests`

## Daily flow

1. Start from latest `main`.
2. Create a focused branch.
3. Make changes and run tests.
4. Commit in small logical chunks.
5. Push branch to origin.
6. Merge to `main` after verification.

## Commands

Create branch:

```powershell
git checkout main
git pull
git checkout -b phase-3-task-panels
```

Commit cycle:

```powershell
git status
git add -A
git commit
git push -u origin phase-3-task-panels
```

Merge back to main (local, simple flow):

```powershell
git checkout main
git pull
git merge --no-ff phase-3-task-panels
git push origin main
```

## Safety rules

1. Do not work directly on `main` for non-trivial changes.
2. Run tests before every merge.
3. Keep commits focused and reversible.
4. Avoid force-push to shared branches.
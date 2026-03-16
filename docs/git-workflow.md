# Git Workflow

This project uses a small, beginner-friendly workflow that still keeps history clean.

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
(git pull)
git checkout -b <branch-name>
```

Commit cycle:

```powershell
git status
git add -A
git commit
(git push -u origin phase-3-task-panels)
```

Merge back to main (local, simple flow):

```powershell
git checkout main
(git pull)
git merge phase-3-task-panels
(git push origin main)
```

## Safety rules

1. Do not work directly on `main` for non-trivial changes.
2. Run tests before every merge.
3. Keep commits focused and reversible.
4. Avoid force-push to shared branches.
# Git Workflow (Local + GitHub)

This guide is a practical everyday workflow for this project.

Goals:
- Keep local work safe.
- Keep GitHub up to date.
- Avoid losing work.

## 1) One-time setup

Run these from the project folder:

git status
git branch
git remote -v

Expected:
- Current branch is main.
- Remote origin points to your GitHub repository.

If origin is missing:

git remote add origin https://github.com/YOUR_USERNAME/FreeCAD-openEMS-workbench.git
git push -u origin main


## 2) Everyday start of work

Before editing files:

git checkout main
git pull origin main

This updates your local main with the latest GitHub changes.

## 3) Everyday save-and-push cycle

After making changes:

git status
git add .
git commit -m "Short clear message"
git push

## 4) Recommended pattern for larger changes

For larger or risky tasks, use a branch:

git checkout -b feature/short-name

Work as usual:

git add .
git commit -m "Describe change"
git push -u origin feature/short-name

Then open a Pull Request on GitHub and merge to main.

## 5) Check history quickly

git log --oneline --graph --decorate --all

If your local aliases are enabled, these shortcuts also work:

git st
git lg

## 6) Common sync problem and fix

If push is rejected because GitHub is ahead:

git pull --rebase
git push

If conflicts appear:
1. Open conflicted files and resolve marked sections.
2. Continue rebase:

git add .
git rebase --continue
git push

## 7) Safe undo commands (do not lose committed work)

Unstage files:

git restore --staged .

Discard local changes in one file:

git restore path/to/file

Revert a committed change by creating a new commit:

git revert COMMIT_HASH

## 8) Minimal daily checklist

1. Pull latest changes.
2. Make a small focused change.
3. Run tests for touched area.
4. Commit with clear message.
5. Push to GitHub.

## 9) Suggested habit for this repository

- Commit often (small commits are easier to debug).
- Prefer one logical change per commit.
- Keep main stable.
- Use feature branches when uncertain.
- Push at least once per work session so GitHub is your backup.

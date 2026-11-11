# ADR-0017: Ship and clean up branches with two git aliases

- **Status:** Accepted
- **Date:** 2026-11-11

## Context
Every change goes through a branch, a pull request, the eight required CI checks on `main` and a squash merge ([development.md](../development.md#2-git-workflow)). Doing this by hand meant several `gh` commands per change and, after the merge, local branches piling up on both development machines.

Squash merges make that cleanup awkward. The merged commit on `main` is new, so `git branch -d` reports the old branch as "not fully merged" even though its code is already in `main`. GitHub deletes the remote branch after a merge, but the local one stays.

## Decision
Each development machine adds two aliases and `fetch.prune` to its global git config (`~/.gitconfig`), set up as in [development.md](../development.md#git-aliases-ship-and-cleanup):

- `git ship` pushes the current branch, opens a pull request filled from the commits, and turns on auto-merge with squash. GitHub merges once the required checks pass and deletes the remote branch.
- `git cleanup` switches to `main`, pulls, and force-deletes the local branches whose remote branch is gone.

## Consequences
- One command sends a change and one command tidies up after it, the same on both machines.
- `git ship` doesn't wait for CI. CI failures and merge conflicts show on the pull request, so check it with `gh pr checks --watch` or `gh pr view`. A fix is a new commit and a plain `git push`; auto-merge stays on.
- Auto-merge merges as soon as CI is green, so any AI review must happen before `git ship`.
- `git cleanup` deletes only branches marked `gone`, so unpushed branches and branches with an open pull request are kept. A branch that was pushed and then deleted on GitHub without merging is also `gone` and is deleted too.
- The aliases need Git Bash tools (`grep`, `awk`, `xargs`), which Git for Windows provides, and an authenticated `gh` CLI.

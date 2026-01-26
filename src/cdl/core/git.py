"""Safe git operations (no shell=True)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Union

from ..utils.process import run


def clone(url: str, dest: Path) -> subprocess.CompletedProcess:
    """Clone a git repository."""
    return run(["git", "clone", url, str(dest)])


def run_raw(
    args: list[str],
    cwd: Optional[Union[str, Path]] = None,
) -> subprocess.CompletedProcess:
    """Run a raw command using the shared process runner."""
    return run(args, cwd=cwd)


def worktree_add(
    repo_path: Path,
    worktree_path: Path,
    branch: str,
    force_branch: bool = False,
) -> subprocess.CompletedProcess:
    """
    Add a git worktree.

    Args:
        repo_path: Path to the main repository
        worktree_path: Path where worktree should be created
        branch: Branch name to checkout
        force_branch: If True, use -B to force create/reset branch
    """
    if force_branch:
        return run(
            ["git", "worktree", "add", "-B", branch, str(worktree_path)],
            cwd=repo_path,
        )
    return run(
        ["git", "worktree", "add", str(worktree_path), branch],
        cwd=repo_path,
    )


def worktree_remove(
    repo_path: Path,
    worktree_path: Path,
    force: bool = False,
) -> subprocess.CompletedProcess:
    """Remove a git worktree."""
    args = ["git", "worktree", "remove", str(worktree_path)]
    if force:
        args.append("--force")
    return run(args, cwd=repo_path)


def branch_exists(repo_path: Path, branch: str) -> bool:
    """Check if a branch exists locally or remotely."""
    # Check local
    result = run(["git", "rev-parse", "--verify", branch], cwd=repo_path)
    if result.returncode == 0:
        return True

    # Check remote
    result = run(["git", "rev-parse", "--verify", f"origin/{branch}"], cwd=repo_path)
    return result.returncode == 0


def create_branch(
    repo_path: Path,
    branch: str,
    base: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Create a new branch."""
    args = ["git", "branch", branch]
    if base:
        args.append(base)
    return run(args, cwd=repo_path)


def get_current_branch(repo_path: Path) -> Optional[str]:
    """Get the current branch name."""
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def status(repo_path: Union[str, Path], porcelain: bool = True) -> subprocess.CompletedProcess:
    """Get git status."""
    args = ["git", "status"]
    if porcelain:
        args.append("--porcelain")
    return run(args, cwd=repo_path)


def diff(
    repo_path: Union[str, Path],
    cached: bool = False,
    stat: bool = False,
) -> subprocess.CompletedProcess:
    """Get git diff."""
    args = ["git", "diff"]
    if cached:
        args.append("--cached")
    if stat:
        args.append("--stat")
    return run(args, cwd=repo_path)


def diff_range(
    repo_path: Union[str, Path],
    range_spec: str,
    stat: bool = False,
) -> subprocess.CompletedProcess:
    """Get git diff for a range (e.g., origin/branch..HEAD)."""
    args = ["git", "diff", range_spec]
    if stat:
        args.append("--stat")
    return run(args, cwd=repo_path)


def push(
    repo_path: Union[str, Path],
    remote: str = "origin",
    branch: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Push to remote."""
    args = ["git", "push", remote]
    if branch:
        args.append(branch)
    return run(args, cwd=repo_path)


def log(
    repo_path: Union[str, Path],
    oneline: bool = False,
    count: Optional[int] = None,
    range_spec: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Get git log."""
    args = ["git", "log"]
    if oneline:
        args.append("--oneline")
    if count:
        args.extend(["-n", str(count)])
    if range_spec:
        args.append(range_spec)
    return run(args, cwd=repo_path)


def rev_list_count(
    repo_path: Union[str, Path],
    range_spec: str,
) -> int:
    """Count commits in a range."""
    result = run(["git", "rev-list", "--count", range_spec], cwd=repo_path)
    if result.returncode == 0:
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
    return 0


def ls_files_untracked(repo_path: Union[str, Path]) -> list[str]:
    """List untracked files."""
    result = run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_path,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")
    return []

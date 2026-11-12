"""Publish the student-facing template into a local clone of the template repository.

Copies template/ (as the repository root) and tickets/ into the target clone,
replacing its previous contents (except .git), and commits the result.
It never pushes: review the commit and push it yourself.

Usage:
    python scripts/publish_template.py --target ../shopflow-orders --dry-run
    python scripts/publish_template.py --target ../shopflow-orders
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (source directory in this repo, destination directory in the template repo)
SOURCES = [
    (ROOT / "template", Path(".")),
    (ROOT / "tickets", Path("tickets")),
]

# Never copied, at any depth.
EXCLUDED_NAMES = {"target", ".idea", ".vscode", "__pycache__", ".env", ".DS_Store"}

# Must never appear in the published repository: platform internals.
FORBIDDEN_TOP_LEVEL = {"eval", "tests", "agent", "agent-logs", "scripts"}


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def collect_files() -> list[tuple[Path, Path]]:
    """Return (source file, relative destination path) pairs."""
    files = []
    for source_dir, dest_dir in SOURCES:
        for path in sorted(source_dir.rglob("*")):
            relative = path.relative_to(source_dir)
            if path.is_dir() or EXCLUDED_NAMES.intersection(relative.parts):
                continue
            files.append((path, dest_dir / relative))
    return files


def check_files(files: list[tuple[Path, Path]]) -> None:
    for _, dest in files:
        if dest.parts[0] in FORBIDDEN_TOP_LEVEL:
            sys.exit(f"Refusing to publish platform file: {dest.as_posix()}")
        if dest.name == ".env":
            sys.exit(f"Refusing to publish a secrets file: {dest.as_posix()}")


def check_target(target: Path) -> None:
    if not (target / ".git").is_dir():
        sys.exit(f"{target} is not a git repository. Clone the template repository first.")
    if target.resolve() == ROOT:
        sys.exit("Target must be the template repository, not the platform repository.")
    if run_git(target, "status", "--porcelain"):
        sys.exit(f"{target} has uncommitted changes. Commit or discard them first.")


def check_platform_is_clean() -> str:
    """Return the platform commit sha; refuse to publish uncommitted changes."""
    if run_git(ROOT, "status", "--porcelain", "--", "template", "tickets"):
        sys.exit("template/ or tickets/ has uncommitted changes. Commit them first.")
    return run_git(ROOT, "rev-parse", "--short", "HEAD")


def clear_target(target: Path) -> None:
    for child in target.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_files(files: list[tuple[Path, Path]], target: Path) -> None:
    for source, dest in files:
        destination = target / dest
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", required=True, type=Path, help="local clone of the template repository")
    parser.add_argument("--dry-run", action="store_true", help="only list the files that would be published")
    args = parser.parse_args()

    files = collect_files()
    check_files(files)

    if args.dry_run:
        for _, dest in files:
            print(dest.as_posix())
        print(f"\n{len(files)} files would be published to {args.target}")
        return

    target = args.target
    check_target(target)
    platform_sha = check_platform_is_clean()

    clear_target(target)
    copy_files(files, target)
    run_git(target, "add", "-A")
    if not run_git(target, "status", "--porcelain"):
        print("Nothing changed, no commit created.")
        return
    run_git(target, "commit", "-m", f"Publish template from codementor@{platform_sha}")
    print(run_git(target, "show", "--stat", "--oneline", "HEAD"))
    print("\nCommitted. Review it, then push: git -C <target> push")


if __name__ == "__main__":
    main()

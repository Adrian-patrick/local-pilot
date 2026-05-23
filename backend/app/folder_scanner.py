from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
}


def scan_folder(root: Path, max_files: int = 200) -> list[dict]:
    results: list[dict] = []

    for path in root.rglob("*"):
        if len(results) >= max_files:
            break

        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue

        if path.is_file():
            stat = path.stat()
            results.append(
                {
                    "relative_path": str(path.relative_to(root)),
                    "name": path.name,
                    "extension": path.suffix.lower(),
                    "size": stat.st_size,
                }
            )

    return results


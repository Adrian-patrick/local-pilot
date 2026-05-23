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
    "data",
}

IGNORED_EXTENSIONS = {
    ".7z",
    ".bin",
    ".db",
    ".dll",
    ".exe",
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".mp3",
    ".mp4",
    ".png",
    ".pyc",
    ".sqlite",
    ".webp",
    ".zip",
}


def scan_folder(root: Path, max_files: int = 200) -> list[dict]:
    results: list[dict] = []

    for path in root.rglob("*"):
        if len(results) >= max_files:
            break

        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue

        if path.is_file() and path.suffix.lower() not in IGNORED_EXTENSIONS:
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

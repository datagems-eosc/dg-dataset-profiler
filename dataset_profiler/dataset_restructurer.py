import shutil
import uuid
from pathlib import Path

from dataset_profiler.configs.config_logging import logger


TOP_LEVEL_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def restructure_dataset(distribution_path: str) -> None:
    """Reshape a dataset directory in place to follow the expected layout.

    Expected layout:
        * CSV / Excel files sit at the top level of ``distribution_path``.
        * Every other file type sits inside a first-level subdirectory that
          contains files of that single extension only.
        * No nested subdirectories.
    """
    root = Path(distribution_path)
    if not root.is_dir():
        logger.warning("Cannot restructure non-directory path", path=str(root))
        return

    files_by_ext: dict[str, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file():
            files_by_ext.setdefault(path.suffix.lower(), []).append(path)

    for ext, files in files_by_ext.items():
        if ext in TOP_LEVEL_EXTENSIONS:
            target_dir = root
        else:
            target_dir = _resolve_typed_subdir(root, ext)
        for file_path in files:
            if file_path.parent.resolve() == target_dir.resolve():
                continue
            _move_file(file_path, target_dir)

    _remove_empty_subdirs(root)


def _resolve_typed_subdir(root: Path, ext: str) -> Path:
    ext_clean = ext.lstrip(".") or "noext"
    prefix = f"{ext_clean}_"
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith(prefix):
            return child
    target = root / f"{ext_clean}_{uuid.uuid4().hex[:10]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _move_file(src: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        dst = _unique_path(dst)
    shutil.move(str(src), str(dst))


def _unique_path(path: Path) -> Path:
    parent, stem, suffix = path.parent, path.stem, path.suffix
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _remove_empty_subdirs(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()

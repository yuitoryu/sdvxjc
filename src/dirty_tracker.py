import json
import re
from pathlib import Path

from beartype import beartype

from .file_finders import find_unpacked_ifs


TRACKER_FILE_NAME = "dirty_jackets.json"
JACKET_ID_PATTERN = re.compile(r"^s_jacket(?!00)([0-9]{2})_ifs$")


@beartype
def dirty_tracker_path(data_storage: Path) -> Path:
    """Return the workspace dirty-jacket tracker path."""

    return data_storage / "index" / TRACKER_FILE_NAME


@beartype
def find_all_jacket_ids(data_storage: Path) -> list[str]:
    """Return all jacket IFS IDs available in the unpacked workspace."""

    unpacked_root = data_storage / "ifs_unpacked"
    if not unpacked_root.is_dir():
        return []

    ids: list[str] = []
    for folder in find_unpacked_ifs(unpacked_root):
        match = JACKET_ID_PATTERN.fullmatch(folder.name)
        if match is not None:
            ids.append(match.group(1))
    return sorted(ids)


@beartype
def write_dirty_jackets(data_storage: Path, jacket_ids: list[str]) -> None:
    """Persist a stable sorted dirty-jacket ID list."""

    tracker_path = dirty_tracker_path(data_storage)
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = sorted(set(jacket_ids))
    tracker_path.write_text(
        json.dumps(normalized, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )


@beartype
def read_dirty_jackets(data_storage: Path) -> list[str]:
    """Read dirty jacket IDs from the tracker."""

    tracker_path = dirty_tracker_path(data_storage)
    payload = json.loads(tracker_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError(f"Invalid dirty jacket tracker: {tracker_path}")
    return sorted(set(payload))


@beartype
def initialize_dirty_tracker(data_storage: Path, dirty_all: bool = False) -> None:
    """Create a tracker, optionally assuming every unpacked jacket is dirty."""

    jacket_ids = find_all_jacket_ids(data_storage) if dirty_all else []
    write_dirty_jackets(data_storage, jacket_ids)


@beartype
def ensure_dirty_tracker(data_storage: Path, dirty_all_if_missing: bool = True) -> None:
    """Create the dirty tracker when missing."""

    if dirty_tracker_path(data_storage).is_file():
        return
    initialize_dirty_tracker(data_storage, dirty_all=dirty_all_if_missing)


@beartype
def mark_dirty_jacket(data_storage: Path, jacket_id: str) -> None:
    """Mark one jacket IFS ID as dirty."""

    ensure_dirty_tracker(data_storage)
    dirty_ids = read_dirty_jackets(data_storage)
    dirty_ids.append(jacket_id)
    write_dirty_jackets(data_storage, dirty_ids)


@beartype
def clear_dirty_jackets(data_storage: Path) -> None:
    """Reset the dirty tracker to an empty clean state."""

    write_dirty_jackets(data_storage, [])

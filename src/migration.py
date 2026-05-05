from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import shutil

from beartype import beartype

from .dirty_tracker import clear_dirty_jackets, dirty_tracker_path, read_dirty_jackets
from .file_finders import find_jacket_files
from .ifsprocess import apply_packed_ifs, copy_and_analyze_all_ifs, pack, unpack
from .indexer import analyze_all_song_difficulty
from .runtime_config import (
    find_target_name_by_sdvx_path,
    get_current_target,
    get_current_target_paths,
    list_targets,
    remove_target,
    update_target_sdvx_path,
    use_target,
)
from .song_assets import clear_workspace_music, update_song_folders
from .texturelist import merge_texturelists
from .validators import sdvx_folder_checker


MUSIC_FOLDER_PATTERN = re.compile(r"^(?P<id>\d{4})(?:_[^_]+){2,}$")
JACKET_FILE_PATTERN = re.compile(r"^jk_\d{4}_[1-6](?:_b|_s)?\.png$")
TRANSFER_FILE_PATTERN = re.compile(r"^jk_\d{4}_[1-6]_t\.png$")


@dataclass(frozen=True)
class StagedFile:
    """Track one staged migration artifact before copying it into the game folder."""

    staged_path: Path
    relative_path: Path
    overwrites_existing: bool


def _remove_path(path: Path) -> None:
    """Delete one file or directory when it exists."""

    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _timestamped_dir(root: Path, stem: str) -> Path:
    """Create a stable timestamped folder path under one workspace."""

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = root / stem / stamp
    if not base_path.exists():
        return base_path

    counter = 1
    while True:
        candidate = root / stem / f"{stamp}_{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def _prompt_choice(prompt: str, choices: set[str], default: str | None = None) -> str:
    """Read one interactive choice from stdin."""

    while True:
        raw = input(prompt).strip().lower()
        if not raw and default is not None:
            return default
        if raw in choices:
            return raw
        allowed = ", ".join(sorted(choices))
        print(f"Please answer with one of: {allowed}.")


def _workspace_has_dirty_ifs(workspace_path: Path) -> bool:
    """Return whether a workspace has unapplied packed-jacket changes."""

    tracker_path = dirty_tracker_path(workspace_path)
    if not tracker_path.is_file():
        return (workspace_path / "ifs_unpacked").exists()
    return bool(read_dirty_jackets(workspace_path))


def _workspace_has_music_changes(workspace_path: Path) -> bool:
    """Return whether a workspace still carries copied song folders."""

    music_path = workspace_path / "music"
    return music_path.exists() and any(music_path.iterdir())


def _workspace_has_pending_changes(workspace_path: Path) -> bool:
    """Return whether a workspace has unapplied jacket or music edits."""

    return _workspace_has_dirty_ifs(workspace_path) or _workspace_has_music_changes(workspace_path)


def _apply_workspace_changes_to_target(sdvx_path: Path, workspace_path: Path) -> None:
    """Apply one workspace back into its game folder and reset local dirty state."""

    apply_packed_ifs(workspace_path, sdvx_path)
    update_song_folders(sdvx_path, workspace_path)
    clear_dirty_jackets(workspace_path)
    clear_workspace_music(workspace_path)


def _rebuild_workspace(sdvx_path: Path, workspace_path: Path) -> None:
    """Rebuild one workspace from a clean snapshot of a game folder."""

    workspace_path.mkdir(parents=True, exist_ok=True)
    for name in ("ifs_unpacked", "ifs_packed", "index", "music"):
        _remove_path(workspace_path / name)

    copy_and_analyze_all_ifs(sdvx_path, workspace_path)
    analyze_all_song_difficulty(sdvx_path, workspace_path)
    clear_dirty_jackets(workspace_path)
    clear_workspace_music(workspace_path)


def _song_folder_index(music_path: Path) -> dict[str, Path]:
    """Index music folders by four-digit song ID."""

    record: dict[str, Path] = {}
    for folder in music_path.iterdir():
        if not folder.is_dir():
            continue
        match = MUSIC_FOLDER_PATTERN.fullmatch(folder.name)
        if match is None:
            continue

        song_id = match.group("id")
        if song_id in record:
            raise ValueError(f"Duplicate song folder ID detected in {music_path}: {song_id}")
        record[song_id] = folder
    return record


def _regular_jacket_files(song_path: Path) -> list[Path]:
    """Return regular music-folder jacket files for one song."""

    return [
        path
        for path in song_path.iterdir()
        if path.is_file() and JACKET_FILE_PATTERN.fullmatch(path.name)
    ]


def _transfer_jacket_files(tex_path: Path) -> list[Path]:
    """Return transfer-jacket image files for one unpacked IFS tex folder."""

    return [
        path
        for path in tex_path.iterdir()
        if path.is_file() and TRANSFER_FILE_PATTERN.fullmatch(path.name)
    ]


def _stage_music_files(old_sdvx_path: Path, new_sdvx_path: Path, stage_root: Path) -> list[StagedFile]:
    """Stage migrated music-folder jacket files from old over new."""

    old_music_path = old_sdvx_path / "data" / "music"
    new_music_path = new_sdvx_path / "data" / "music"

    old_song_index = _song_folder_index(old_music_path)
    new_song_index = _song_folder_index(new_music_path)

    staged_files: list[StagedFile] = []
    for song_id in sorted(set(old_song_index) & set(new_song_index)):
        old_song_path = old_song_index[song_id]
        new_song_path = new_song_index[song_id]
        for old_file in _regular_jacket_files(old_song_path):
            relative_path = Path("data") / "music" / new_song_path.name / old_file.name
            staged_path = stage_root / relative_path
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_file, staged_path)
            staged_files.append(
                StagedFile(
                    staged_path=staged_path,
                    relative_path=relative_path,
                    overwrites_existing=(new_sdvx_path / relative_path).is_file(),
                )
            )

    return staged_files


def _stage_ifs_files(old_sdvx_path: Path, new_sdvx_path: Path, stage_root: Path) -> list[StagedFile]:
    """Stage migrated jacket IFS files from old over new."""

    old_graphics_path = old_sdvx_path / "data" / "graphics"
    new_graphics_path = new_sdvx_path / "data" / "graphics"

    old_ifs = {path.name: path for path in find_jacket_files(old_graphics_path)}
    new_ifs = {path.name: path for path in find_jacket_files(new_graphics_path)}

    old_unpack_root = stage_root / "old_unpack"
    new_unpack_root = stage_root / "new_unpack"
    merged_unpack_root = stage_root / "merged_unpack"
    packed_root = stage_root / "packed"

    staged_files: list[StagedFile] = []
    for ifs_name in sorted(set(old_ifs) & set(new_ifs)):
        old_ifs_path = old_ifs[ifs_name]
        new_ifs_path = new_ifs[ifs_name]

        folder_name = f"{Path(ifs_name).stem}_ifs"
        old_folder_path = old_unpack_root / folder_name
        new_folder_path = new_unpack_root / folder_name
        merged_folder_path = merged_unpack_root / folder_name

        try:
            unpack(old_ifs_path, old_unpack_root)
            unpack(new_ifs_path, new_unpack_root)

            old_tex_path = old_folder_path / "tex"
            shutil.copytree(new_folder_path, merged_folder_path)

            merged_tex_path = merged_folder_path / "tex"
            imported_names: list[str] = []
            for old_file in _transfer_jacket_files(old_tex_path):
                target_path = merged_tex_path / old_file.name
                shutil.copy2(old_file, target_path)
                imported_names.append(old_file.stem)

            if not imported_names:
                continue

            staged_names = {path.stem for path in _transfer_jacket_files(merged_tex_path)}
            merge_texturelists(
                merged_tex_path / "texturelist.xml",
                old_tex_path / "texturelist.xml",
                staged_names,
                imported_names,
            )

            packed_path = pack(merged_folder_path, packed_root)
            staged_files.append(
                StagedFile(
                    staged_path=packed_path,
                    relative_path=Path("data") / "graphics" / packed_path.name,
                    overwrites_existing=(new_sdvx_path / "data" / "graphics" / packed_path.name).is_file(),
                )
            )
        finally:
            _remove_path(old_folder_path)
            _remove_path(new_folder_path)
            _remove_path(merged_folder_path)

    return staged_files


def _backup_overwritten_files(
    new_sdvx_path: Path,
    backup_root: Path,
    staged_files: list[StagedFile],
) -> None:
    """Copy destination files that will be overwritten into a backup folder."""

    for staged_file in staged_files:
        if not staged_file.overwrites_existing:
            continue

        source_path = new_sdvx_path / staged_file.relative_path
        if not source_path.exists():
            continue

        backup_path = backup_root / staged_file.relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, backup_path)


def _apply_staged_files(new_sdvx_path: Path, staged_files: list[StagedFile]) -> None:
    """Copy staged migration files into the newer game folder."""

    for staged_file in staged_files:
        target_path = new_sdvx_path / staged_file.relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_file.staged_path, target_path)


@beartype
def migrate_target(new_sdvx_path: Path, backup: bool = False) -> None:
    """Migrate the current target's jacket data into a newer SDVX install."""

    source_name, _ = get_current_target()
    source_sdvx_path, source_workspace_path = get_current_target_paths()
    resolved_new_sdvx_path = new_sdvx_path.expanduser().resolve()

    if not sdvx_folder_checker(source_sdvx_path):
        raise ValueError("The current target does not point to a valid sdvx contents folder!")
    if not sdvx_folder_checker(resolved_new_sdvx_path):
        raise ValueError("The migration destination is not a valid sdvx contents folder!")
    if source_sdvx_path == resolved_new_sdvx_path:
        raise ValueError("The current target already points to that SDVX folder.")

    targets, _ = list_targets()
    destination_name = find_target_name_by_sdvx_path(resolved_new_sdvx_path)
    destination_target = targets[destination_name] if destination_name is not None else None
    destination_workspace_path = (
        Path(destination_target["workspace_path"])
        if destination_target is not None
        else source_workspace_path
    )

    source_choice: str | None = None
    if _workspace_has_pending_changes(source_workspace_path):
        print("Unapplied changes were found in the current workspace.")
        source_choice = _prompt_choice(
            "Apply them before migrating? [yes/no/stop]: ",
            {"yes", "no", "stop"},
            default="stop",
        )
        if source_choice == "stop":
            print("Migration cancelled.")
            return

    discard_destination_changes = False
    if destination_name is not None:
        print(
            f"The newer SDVX folder is already registered to target '{destination_name}'."
        )
        reuse_choice = _prompt_choice(
            "Continue and reuse that existing target? [yes/no]: ",
            {"yes", "no"},
            default="no",
        )
        if reuse_choice != "yes":
            print("Migration cancelled.")
            return

        if _workspace_has_pending_changes(destination_workspace_path):
            print(f"Target '{destination_name}' has pending workspace changes.")
            discard_choice = _prompt_choice(
                "Discard those destination changes and continue? [yes/no]: ",
                {"yes", "no"},
                default="no",
            )
            if discard_choice != "yes":
                print("Migration cancelled.")
                return
            discard_destination_changes = True

    final_target_name = destination_name or source_name
    print(
        "Migration will copy jacket data from the old version into the newer version. "
        "Same-named jacket assets in the newer version will be overwritten by the old version."
    )
    print(f"Selected target after migration: {final_target_name}")
    print(f"Backup enabled: {'yes' if backup else 'no'}")
    confirm_choice = _prompt_choice(
        "Do you really want to continue? [yes/no]: ",
        {"yes", "no"},
        default="no",
    )
    if confirm_choice != "yes":
        print("Migration cancelled.")
        return

    if source_choice == "yes":
        _apply_workspace_changes_to_target(source_sdvx_path, source_workspace_path)
    elif source_choice == "no":
        _rebuild_workspace(source_sdvx_path, source_workspace_path)

    if discard_destination_changes:
        _rebuild_workspace(resolved_new_sdvx_path, destination_workspace_path)

    stage_root = _timestamped_dir(source_workspace_path, ".migration_stage")
    backup_workspace_path = destination_workspace_path if destination_name is not None else source_workspace_path
    backup_root = _timestamped_dir(backup_workspace_path, ".migration_backup") if backup else None

    try:
        music_files = _stage_music_files(source_sdvx_path, resolved_new_sdvx_path, stage_root)
        ifs_files = _stage_ifs_files(source_sdvx_path, resolved_new_sdvx_path, stage_root)
        staged_files = music_files + ifs_files

        if backup_root is not None:
            _backup_overwritten_files(resolved_new_sdvx_path, backup_root, staged_files)

        _apply_staged_files(resolved_new_sdvx_path, staged_files)

        if destination_name is None:
            update_target_sdvx_path(source_name, resolved_new_sdvx_path)
            _rebuild_workspace(resolved_new_sdvx_path, source_workspace_path)
            print(f"Migration completed. Target '{source_name}' now points to {resolved_new_sdvx_path}.")
            if backup_root is not None:
                print(f"Backup written to: {backup_root}")
            return

        _rebuild_workspace(resolved_new_sdvx_path, destination_workspace_path)
        use_target(destination_name)
        remove_target(source_name)
        print(
            f"Migration completed. Target '{destination_name}' remains selected and "
            f"target '{source_name}' was retired."
        )
        if backup_root is not None:
            print(f"Backup written to: {backup_root}")
    finally:
        _remove_path(stage_root)

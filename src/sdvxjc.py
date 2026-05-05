import argparse
from pathlib import Path

from . import ifsprocess
from .dirty_tracker import clear_dirty_jackets, ensure_dirty_tracker
from .indexer import analyze_all_song_difficulty
from .manager import DiffManager
from .migration import migrate_target
from .runtime_config import (
    RuntimeConfigError,
    get_current_target,
    get_current_target_paths,
    initialize_data_root,
    list_targets,
    add_target,
    remove_target,
    use_target,
)
from .song_assets import clear_workspace_music, update_song_folders
from .validators import craft_difficulty, craft_id, sdvx_folder_checker


def _print_target(name: str, sdvx_path: Path | str, workspace_path: Path | str) -> None:
    """Print one target record in a compact CLI-friendly format."""

    print(f"Target: {name}")
    print(f"  SDVX path: {sdvx_path}")
    print(f"  Workspace: {workspace_path}")


def _handle_init(config_arg: str, force: bool) -> None:
    """Initialize the global data root from a config file."""

    data_root = initialize_data_root(Path(config_arg), force=force)
    print(f"Data root initialized: {data_root}")


def _handle_add_target(sdvx_arg: str, target_name: str | None) -> None:
    """Register and initialize an isolated workspace for a game folder."""

    sdvx_path = Path(sdvx_arg).expanduser().resolve()
    if not sdvx_folder_checker(sdvx_path):
        raise ValueError("This is not a valid sdvx contents folder!")

    _, previous_target = list_targets()
    name, resolved_sdvx_path, workspace_path = add_target(sdvx_path, target_name)
    try:
        ifsprocess.copy_and_analyze_all_ifs(resolved_sdvx_path, workspace_path)
        analyze_all_song_difficulty(resolved_sdvx_path, workspace_path)
    except Exception:
        remove_target(name)
        if previous_target is not None:
            use_target(previous_target)
        raise

    print(f"Target '{name}' has been added and selected.")
    _print_target(name, resolved_sdvx_path, workspace_path)


def _handle_use_target(name: str) -> None:
    """Select a saved target by name."""

    targets, _ = list_targets()
    if name in targets:
        ensure_dirty_tracker(Path(targets[name]["workspace_path"]))
    target = use_target(name)
    print(f"Current target switched to '{name}'.")
    _print_target(name, target["sdvx_path"], target["workspace_path"])


def _handle_list_targets() -> None:
    """Print all saved targets and mark the current one."""

    targets, current_target = list_targets()
    if not targets:
        print("No targets registered. Run 'sdvxjc --add-target <sdvx_path>' first.")
        return

    for name, target in targets.items():
        marker = "*" if name == current_target else " "
        print(f"{marker} {name}")
        print(f"  SDVX path: {target['sdvx_path']}")
        print(f"  Workspace: {target['workspace_path']}")


def _handle_current_target() -> None:
    """Print the selected target."""

    name, target = get_current_target()
    _print_target(name, target["sdvx_path"], target["workspace_path"])


def _handle_replace(replace_args: list[str]) -> None:
    """Replace a jacket in the currently selected target workspace."""

    sdvx_path, workspace_path = get_current_target_paths()
    ensure_dirty_tracker(workspace_path)
    song_id, diff, pic_path = replace_args
    manager = DiffManager(
        song_id=craft_id(song_id),
        sdvx_path=sdvx_path,
        data_storage=workspace_path,
    )
    manager.replace_jacket(diff=craft_difficulty(diff), pic_path=Path(pic_path))


def _handle_apply() -> None:
    """Apply the current target workspace back to its game folder."""

    sdvx_path, workspace_path = get_current_target_paths()
    ensure_dirty_tracker(workspace_path)
    if not sdvx_folder_checker(sdvx_path):
        raise ValueError("This is not a valid sdvx contents folder!")
    ifsprocess.apply_packed_ifs(workspace_path, sdvx_path)
    update_song_folders(sdvx_path, workspace_path)
    clear_dirty_jackets(workspace_path)
    clear_workspace_music(workspace_path)


def _handle_migrate(sdvx_arg: str, backup: bool) -> None:
    """Migrate the current target into a newer SDVX contents folder."""

    migrate_target(Path(sdvx_arg), backup=backup)


def _main() -> None:
    """Parse CLI arguments and dispatch to the selected command."""

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--init", metavar="CONFIG_PY")
    group.add_argument("--add-target", metavar="SDVX_PATH")
    group.add_argument("--use-target", metavar="NAME")
    group.add_argument("--list-targets", action="store_true")
    group.add_argument("--current-target", action="store_true")
    group.add_argument("--replace", nargs=3, metavar=("ID", "DIFF", "PIC_PATH"))
    group.add_argument("--apply", action="store_true")
    group.add_argument("--migrate", metavar="NEW_SDVX_PATH")

    parser.add_argument(
        "-n",
        "--name",
        help="target name to use with --add-target",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force initialization",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="create backups when overwriting files during migration",
    )

    args = parser.parse_args()
    if args.force and args.init is None:
        parser.error("-f/--force must be used with --init")
    if args.name is not None and args.add_target is None:
        parser.error("-n/--name must be used with --add-target")
    if args.backup and args.migrate is None:
        parser.error("--backup must be used with --migrate")

    if args.init:
        _handle_init(args.init, args.force)
        return

    if args.add_target:
        _handle_add_target(args.add_target, args.name)
        return

    if args.use_target:
        _handle_use_target(args.use_target)
        return

    if args.list_targets:
        _handle_list_targets()
        return

    if args.current_target:
        _handle_current_target()
        return

    if args.replace:
        _handle_replace(args.replace)
        return

    if args.apply:
        _handle_apply()
        return

    if args.migrate:
        _handle_migrate(args.migrate, args.backup)


def main() -> None:
    """Run the CLI and render runtime configuration errors cleanly."""

    try:
        _main()
    except RuntimeConfigError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()

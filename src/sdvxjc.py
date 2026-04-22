import argparse
from pathlib import Path

from . import ifsprocess
from . import utils
from .manager import DiffManager
from .runtime_config import (
    RuntimeConfigError,
    load_config_paths,
    load_registered_paths,
    save_registered_config,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--init", metavar="CONFIG_PY")
    group.add_argument("--replace", nargs=3, metavar=("ID", "DIFF", "PIC_PATH"))
    group.add_argument("--apply", action="store_true")

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force initialization",
    )

    args = parser.parse_args()
    if args.force and args.init is None:
        parser.error("-f/--force must be used with --init")

    if args.init:
        config_path = Path(args.init)
        sdvx_path, data_path = load_config_paths(config_path)
        if not utils.sdvx_folder_checker(sdvx_path):
            raise ValueError("This is not a valid sdvx contents folder!")
        data_path.mkdir(parents=True, exist_ok=True)
        save_registered_config(config_path, force=args.force)
        ifsprocess.copy_and_analyze_all_ifs(sdvx_path, data_path)
        utils.analyze_all_song_difficulty(sdvx_path, data_path)
        return

    sdvx_path, data_path = load_registered_paths()

    if args.replace:
        song_id, diff, pic_path = args.replace
        manager = DiffManager(
            song_id=utils.craft_id(song_id),
            sdvx_path=sdvx_path,
            data_storage=data_path,
        )
        manager.replace_jacket(diff=int(diff), pic_path=Path(pic_path))

    if args.apply:
        if not utils.sdvx_folder_checker(sdvx_path):
            raise ValueError("This is not a valid sdvx contents folder!")
        ifsprocess.pack(data_path / "ifs_unpacked", sdvx_path / "data" / "graphics")
        utils.update_song_folders(sdvx_path, data_path)


if __name__ == "__main__":
    try:
        main()
    except RuntimeConfigError as exc:
        raise SystemExit(str(exc)) from exc

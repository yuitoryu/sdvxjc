import shutil
import subprocess
from pathlib import Path

from beartype import beartype
from tqdm import tqdm

from .dirty_tracker import (
    ensure_dirty_tracker,
    initialize_dirty_tracker,
    read_dirty_jackets,
)
from .file_finders import find_jacket_files, find_unpacked_ifs
from .indexer import analyze_jacket_t_data


class FolderStructureError(Exception):
    """Raised when expected game or workspace folders are missing."""

    def __init__(self) -> None:
        """Create the folder-structure error message."""

        self.message = "Invalid game folder structure."
        super().__init__(self.message)


@beartype
def copy_jk_ifs(sdvx_path: Path, copy_path: Path) -> list[Path]:
    """Copy packed jacket IFS files from the game into a workspace."""

    graphics_path = sdvx_path / "data" / "graphics"
    files = find_jacket_files(graphics_path)

    copy_path.mkdir(parents=True, exist_ok=True)

    copied_files: list[Path] = []
    print("Start copying ifs files...")
    for source_file in tqdm(files):
        destination = copy_path / source_file.name
        shutil.copy2(source_file, destination)
        copied_files.append(destination)
    print("Copy completed.")
    return copied_files


@beartype
def unpack(ifs_file: Path, out_path: Path) -> None:
    """Unpack one IFS file into a workspace directory."""

    out_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ifstools", "-y", str(ifs_file), "-o", str(out_path)],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=None,
        check=True,
    )


@beartype
def pack(ifs_folder: Path, out_path: Path) -> Path:
    """Pack one unpacked IFS directory and return the generated file path."""

    out_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ifstools", "-y", str(ifs_folder), "-o", str(out_path)],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=None,
        check=True,
    )

    packed_file = out_path / f"{ifs_folder.name.removesuffix('_ifs')}.ifs"
    if not packed_file.is_file():
        raise FileNotFoundError(f"Packed IFS file was not created: {packed_file}")
    return packed_file


@beartype
def repack_all(unpacked_root: Path, out_path: Path) -> list[Path]:
    """Pack every unpacked jacket IFS directory in a workspace."""

    packed_files: list[Path] = []
    unpacked_folders = find_unpacked_ifs(unpacked_root)

    print("Start repacking ifs folders...")
    for folder in tqdm(unpacked_folders):
        packed_files.append(pack(folder, out_path))
    print("Repack completed.")
    return packed_files


@beartype
def repack_dirty(
    unpacked_root: Path,
    out_path: Path,
    jacket_ids: list[str],
) -> list[Path]:
    """Pack only the dirty unpacked jacket IFS directories."""

    if not jacket_ids:
        print("No dirty ifs folders to repack.")
        return []

    packed_files: list[Path] = []

    print("Start repacking dirty ifs folders...")
    for jacket_id in tqdm(sorted(set(jacket_ids))):
        folder = unpacked_root / f"s_jacket{jacket_id}_ifs"
        if not folder.is_dir():
            raise FileNotFoundError(f"Dirty IFS folder does not exist: {folder}")
        packed_files.append(pack(folder, out_path))
    print("Repack completed.")
    return packed_files


@beartype
def apply_packed_ifs(data_storage: Path, sdvx_path: Path) -> None:
    """Repack dirty workspace IFS folders and copy them into the game folder."""

    unpacked_root = data_storage / "ifs_unpacked"
    packed_root = data_storage / "ifs_packed"
    graphics_path = sdvx_path / "data" / "graphics"

    ensure_dirty_tracker(data_storage)
    packed_files = repack_dirty(unpacked_root, packed_root, read_dirty_jackets(data_storage))

    print("Start copying packed ifs files back to the game folder...")
    for packed_file in tqdm(packed_files):
        shutil.copy2(packed_file, graphics_path / packed_file.name)
    print("Apply completed.")


@beartype
def copy_and_analyze_all_ifs(sdvx_path: Path, data_storage: Path) -> None:
    """Initialize a target workspace with copied, unpacked, and indexed IFS data."""

    unpacked = data_storage / "ifs_unpacked"
    packed = data_storage / "ifs_packed"
    unpacked.mkdir(parents=True, exist_ok=True)
    packed.mkdir(parents=True, exist_ok=True)

    copied_path = copy_jk_ifs(sdvx_path, packed)

    print("Start unpacking ifs files...")
    for ifs_file in copied_path:
        print(f"Unpacking {ifs_file.name}...")
        unpack(ifs_file, unpacked)
    print("Unpack completed.")

    analyze_jacket_t_data(data_storage)
    initialize_dirty_tracker(data_storage)

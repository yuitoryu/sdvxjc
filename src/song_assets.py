from pathlib import Path
import re
import shutil

from beartype import beartype


class SongNotExistError(Exception):
    """Raised when a song ID cannot be found in the game music folder."""

    def __init__(self, song_id: str):
        """Create a user-facing missing-song message."""

        self.message = f"ID {song_id} does not exist."
        super().__init__(self.message)


def find_song_folder(music_path: Path, song_id: str) -> Path | None:
    """Find the game music folder for a four-digit song ID."""

    pattern = re.compile(rf"^{song_id}(?:_[^_]+){{2,}}$")
    for fd in music_path.iterdir():
        match = pattern.match(fd.name)
        if match:
            return fd
    raise SongNotExistError(song_id)


@beartype
def ensure_song_folder_copied(song_id: str, sdvx_path: Path, data_storage: Path) -> Path:
    """Copy a song folder into the workspace if it is not already present."""

    source_music_path = sdvx_path / "data" / "music"
    source_song_path = find_song_folder(source_music_path, song_id)
    if source_song_path is None:
        raise FileNotFoundError(f"Music data does not exist for song {song_id}")

    copied_music_path = data_storage / "music"
    copied_music_path.mkdir(parents=True, exist_ok=True)
    copied_song_path = copied_music_path / source_song_path.name

    if not copied_song_path.exists():
        shutil.copytree(source_song_path, copied_song_path)

    return copied_song_path


@beartype
def copy_regular_jacket_to_other_difficulty(
    source_diff: int,
    target_diff: int,
    song_id: str,
    song_path: Path,
) -> None:
    """Copy regular, big, and small jacket files between difficulties."""

    basic_name = f"jk_{song_id}_"
    suffices = [".png", "_b.png", "_s.png"]
    for suffix in suffices:
        source_path = song_path / (basic_name + str(source_diff) + suffix)
        target_path = song_path / (basic_name + str(target_diff) + suffix)
        shutil.copy2(source_path, target_path)


@beartype
def update_song_folders(sdvx_path: Path, data_path: Path):
    """Copy edited workspace music folders back into the game folder."""

    workspace_music_path = data_path / "music"
    if not workspace_music_path.exists():
        return

    music_path = sdvx_path / "data" / "music"
    for fd in workspace_music_path.iterdir():
        if not fd.is_dir():
            continue
        shutil.copytree(fd, music_path / fd.name, dirs_exist_ok=True)


@beartype
def clear_workspace_music(data_path: Path) -> None:
    """Remove all copied music contents from the workspace."""

    workspace_music_path = data_path / "music"
    workspace_music_path.mkdir(parents=True, exist_ok=True)
    for child in workspace_music_path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

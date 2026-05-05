import json
from pathlib import Path

from beartype import beartype

from .jacket_ops import copy_jacket_to_other_difficulty, replace_jacket
from .song_assets import ensure_song_folder_copied


class DifficultyNotExistError(Exception):
    """Raised when a requested difficulty is not indexed for a song."""

    def __init__(self, diff_list: list[int], error_diff: int):
        """Create a user-facing missing-difficulty message."""

        self.diff_map = {
            1: "NOV",
            2: "ADV",
            3: "EXH",
            4: "INF/GRV/HVN/VVD/XCD",
            5: "MXM",
            6: "ULT",
        }
        available_difficulties = ", ".join(self.diff_map[diff] for diff in diff_list)
        verb = "are" if len(diff_list) > 1 else "is"
        difficulty_name = self.diff_map.get(error_diff, str(error_diff))
        self.message = (
            f"The difficulty {difficulty_name} does not exist for this song. "
            f"Only {available_difficulties} {verb} available."
        )
        super().__init__(self.message)


@beartype
class Jacket:
    """Track one playable difficulty and the jacket image it currently uses."""

    def __init__(self, diff_id: int, pic_id: int = -1):
        """Create a jacket usage record for one difficulty."""

        self.diff_id = diff_id
        self.pic_id = pic_id

    def set_diff_id(self, new_id: int) -> None:
        """Update the playable difficulty ID."""

        self.diff_id = new_id

    def set_pic_id(self, new_id: int) -> None:
        """Update the source jacket difficulty ID."""

        self.pic_id = new_id

    def get_diff_id(self) -> int:
        """Return the playable difficulty ID."""

        return self.diff_id

    def get_pic_id(self) -> int:
        """Return the source jacket difficulty ID."""

        return self.pic_id

    def replace(self, new_id: int) -> None:
        """Point the difficulty at a replacement jacket with the same ID."""

        self.diff_id = new_id
        self.pic_id = new_id

    def __repr__(self) -> str:
        """Return a compact debug representation."""

        return str((["id", self.diff_id], ["use_pic", self.pic_id]))


@beartype
class DiffManager:
    """Coordinate jacket usage for one song in one target workspace."""

    def __init__(
        self,
        song_id: str,
        sdvx_path: Path,
        data_storage: Path = Path("data"),
    ):
        """Load jacket and difficulty indexes for one song."""

        self.song_id = song_id
        self.sdvx_path = sdvx_path
        self.data_storage = data_storage

        with open(data_storage / "index" / "jacket.json", "r", encoding="utf-8") as fp:
            self.jacket_t_loc = json.load(fp)[self.song_id]

        with open(data_storage / "index" / "difficulty.json", "r", encoding="utf-8") as fp:
            self.diff_list = sorted(json.load(fp)[self.song_id])

        self.real_jackets = sorted(int(k) for k in self.jacket_t_loc.keys())
        self.diff_pos = {diff: i for i, diff in enumerate(self.diff_list)}
        self.jacket_usage: list[Jacket] = [Jacket(diff) for diff in self.diff_list]

        for diff in self.real_jackets:
            pos = self.diff_pos[diff]
            self.jacket_usage[pos].set_pic_id(diff)

        # Borrowed difficulties point at the source jacket in memory only.
        # We create independent files lazily when the user actually replaces one.
        for i, jacket in enumerate(self.jacket_usage):
            if jacket.get_pic_id() == -1:
                jacket.set_pic_id(self.jacket_usage[i - 1].get_pic_id())

    def regular_jacket_exists(self, diff: int) -> bool:
        """Return whether regular jacket files exist for one difficulty."""

        song_path = ensure_song_folder_copied(self.song_id, self.sdvx_path, self.data_storage)
        basic_name = f"jk_{self.song_id}_{diff}"
        return all(
            (song_path / f"{basic_name}{suffix}").is_file()
            for suffix in (".png", "_b.png", "_s.png")
        )

    def transfer_jacket_exists(self, source_diff: int, target_diff: int) -> bool:
        """Return whether a transfer jacket file exists for one difficulty."""

        ifs_id = self.jacket_t_loc[str(source_diff)]
        path = (
            self.data_storage
            / "ifs_unpacked"
            / f"s_jacket{ifs_id}_ifs"
            / "tex"
            / f"jk_{self.song_id}_{target_diff}_t.png"
        )
        return path.is_file()

    def jacket_files_exist(self, source_diff: int, target_diff: int) -> bool:
        """Return whether all workspace jacket files exist for a difficulty."""

        return self.regular_jacket_exists(target_diff) and self.transfer_jacket_exists(
            source_diff,
            target_diff,
        )

    def materialize_all_jackets(self) -> None:
        """Copy borrowed jackets so every playable difficulty has workspace files."""

        for jacket in self.jacket_usage:
            source_diff = jacket.get_pic_id()
            target_diff = jacket.get_diff_id()
            if source_diff == target_diff:
                continue
            if self.jacket_files_exist(source_diff, target_diff):
                self.jacket_t_loc[str(target_diff)] = self.jacket_t_loc[str(source_diff)]
                jacket.set_pic_id(target_diff)
                continue
            copy_jacket_to_other_difficulty(
                source_diff=source_diff,
                target_diff=target_diff,
                song_id=self.song_id,
                jacket_t_loc=self.jacket_t_loc,
                sdvx_path=self.sdvx_path,
                data_storage=self.data_storage,
            )
            self.jacket_t_loc[str(target_diff)] = self.jacket_t_loc[str(source_diff)]
            jacket.set_pic_id(target_diff)

    def make_independent_jacket(self, jacket: Jacket):
        """Copy a borrowed jacket so a difficulty can be edited independently."""

        source_diff = jacket.get_pic_id()
        target_diff = jacket.get_diff_id()
        copy_jacket_to_other_difficulty(
            source_diff=source_diff,
            target_diff=target_diff,
            song_id=self.song_id,
            jacket_t_loc=self.jacket_t_loc,
            sdvx_path=self.sdvx_path,
            data_storage=self.data_storage,
        )
        self.jacket_t_loc[str(target_diff)] = self.jacket_t_loc[str(source_diff)]
        jacket.set_pic_id(target_diff)

    def ensure_independent_jacket(self, diff: int) -> None:
        """Ensure a difficulty has its own jacket files before replacement."""

        jacket = self.jacket_usage[self.diff_pos[diff]]
        if jacket.get_pic_id() != diff:
            self.make_independent_jacket(jacket)

    def replace_jacket(self, diff: int, pic_path: Path):
        """Replace one difficulty's jacket image in the workspace."""

        self.materialize_all_jackets()
        self.ensure_independent_jacket(diff)
        replace_jacket(
            song_id=self.song_id,
            diff=diff,
            pic_path=pic_path,
            sdvx_path=self.sdvx_path,
            data_storage=self.data_storage,
            ifs_id=self.jacket_t_loc[str(diff)],
        )

    def __repr__(self) -> str:
        """Return all jacket usage records for debugging."""

        return "\n".join([jacket.__repr__() for jacket in self.jacket_usage])

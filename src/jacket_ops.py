from pathlib import Path
import shutil

from beartype import beartype

from .dirty_tracker import mark_dirty_jacket
from .imgprocess import resize
from .song_assets import ensure_song_folder_copied, copy_regular_jacket_to_other_difficulty
from .texturelist import (
    copy_image_node_in_xml,
    ensure_song_image_rects_unique,
    ensure_unique_image_rect,
)


@beartype
def copy_jacket_to_other_difficulty(
    source_diff: int,
    target_diff: int,
    song_id: str,
    jacket_t_loc: dict[str, str],
    sdvx_path: Path,
    data_storage: Path,
) -> None:
    """Create an independent target-difficulty jacket by copying another difficulty."""

    song_path = ensure_song_folder_copied(song_id, sdvx_path, data_storage)
    copy_regular_jacket_to_other_difficulty(source_diff, target_diff, song_id, song_path)
    copy_t_jacket_to_other_difficulty(
        source_diff,
        target_diff,
        song_id,
        jacket_t_loc,
        data_storage,
    )


@beartype
def copy_t_jacket_to_other_difficulty(
    source_diff: int,
    target_diff: int,
    song_id: str,
    jacket_t_loc: dict[str, str],
    data_storage: Path,
) -> None:
    """Copy a transfer jacket image and mirror its XML texture entry."""

    ifs_id = jacket_t_loc[str(source_diff)]
    root = data_storage / "ifs_unpacked" / f"s_jacket{ifs_id}_ifs" / "tex"
    basic_name = f"jk_{song_id}_"
    suffix = "_t.png"
    source_path = root / (basic_name + str(source_diff) + suffix)
    target_path = root / (basic_name + str(target_diff) + suffix)
    shutil.copy2(source_path, target_path)

    xml_path = root / "texturelist.xml"
    copy_image_node_in_xml(xml_path, source_path, target_path)
    mark_dirty_jacket(data_storage, ifs_id)


@beartype
def replace_jacket(
    song_id: str,
    diff: int,
    pic_path: Path,
    sdvx_path: Path,
    data_storage: Path,
    ifs_id: str,
) -> None:
    """Replace all jacket image variants for one song difficulty."""

    imgs = resize(pic_path, allow_morphism=False)
    root_name = f"jk_{song_id}_{diff}"
    song_folder = ensure_song_folder_copied(
        song_id=song_id,
        sdvx_path=sdvx_path,
        data_storage=data_storage,
    )

    suffices = ["", "_b", "_s"]
    for i, suffix in enumerate(suffices):
        name = root_name + suffix + ".png"
        imgs[i].save(song_folder / name)

    t_name = root_name + "_t.png"
    final_path = data_storage / "ifs_unpacked" / f"s_jacket{ifs_id}_ifs" / "tex" / t_name
    imgs[-1].save(final_path)
    texturelist_path = final_path.parent / "texturelist.xml"
    ensure_unique_image_rect(texturelist_path, final_path.stem)
    ensure_song_image_rects_unique(texturelist_path, song_id)
    mark_dirty_jacket(data_storage, ifs_id)

from pathlib import Path

from beartype import beartype


DIFFICULTY_ALIASES = {
    "1": 1,
    "nov": 1,
    "novice": 1,
    "2": 2,
    "adv": 2,
    "advanced": 2,
    "3": 3,
    "exh": 3,
    "exhaust": 3,
    "4": 4,
    "inf": 4,
    "grv": 4,
    "hvn": 4,
    "vvd": 4,
    "xcd": 4,
    "nbl": 4,
    "infinite": 4,
    "gravity": 4,
    "heavenly": 4,
    "vivid": 4,
    "exceed": 4,
    "nabla": 4,
    "5": 5,
    "mxm": 5,
    "maximum": 5,
    "6": 6,
    "ult": 6,
    "ultimate": 6,
}


@beartype
def sdvx_folder_checker(sdvx_path: Path) -> bool:
    """Check whether a path looks like an SDVX contents folder."""

    data = sdvx_path / "data"
    graphics = data / "graphics"
    music = data / "music"
    if graphics.exists() and music.exists():
        return True
    return False


@beartype
def craft_id(id: str) -> str:
    """Normalize a numeric song ID to the four-digit jacket ID format."""

    if not id.isnumeric() or int(id) >= 10000 or int(id) <= 0:
        raise ValueError("Song ID must be a positive integer below 10000!")
    return "0" * (4 - len(id)) + id


@beartype
def craft_difficulty(diff: str) -> int:
    """Normalize a difficulty ID or alias to the internal numeric ID."""

    normalized = diff.strip().lower()
    if normalized in DIFFICULTY_ALIASES:
        return DIFFICULTY_ALIASES[normalized]
    raise ValueError(
        "Difficulty must be 1-6 or a supported alias such as NOV, ADV, EXH, "
        "INF, GRV, HVN, VVD, XCD, NBL, MXM, or ULT."
    )

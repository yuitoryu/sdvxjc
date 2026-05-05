from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
from types import ModuleType
from typing import TypedDict


APP_NAME = "sdvxjc"
STATE_FILE_NAME = "state.json"
STATE_VERSION = 1
TARGETS_DIR_NAME = "targets"
INVALID_TARGET_NAME_CHARS = set('<>:"/\\|?*')


class TargetRecord(TypedDict):
    """Saved paths for one connected SDVX target."""

    sdvx_path: str
    workspace_path: str


class RuntimeState(TypedDict):
    """Versioned runtime state stored outside the project tree."""

    version: int
    data_root: str
    targets: dict[str, TargetRecord]
    current_target: str | None
    next_auto_target_id: int


class RuntimeConfigError(Exception):
    """Base error for runtime configuration and target state issues."""


class RuntimeConfigNotInitializedError(RuntimeConfigError):
    """Raised when a command needs state before --init has been run."""


class TargetNotSelectedError(RuntimeConfigError):
    """Raised when a command needs a current target but none is selected."""


def _state_dir() -> Path:
    """Return the platform-specific directory used for app state."""

    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / f".{APP_NAME}"


def get_state_file_path() -> Path:
    """Return the full path to the runtime state file."""

    return _state_dir() / STATE_FILE_NAME


def _coerce_path(value: object, field_name: str) -> Path:
    """Convert config path values to Path objects."""

    if isinstance(value, Path):
        return value.expanduser()
    if isinstance(value, str):
        return Path(value).expanduser()
    raise RuntimeConfigError(f"{field_name} must be a str or pathlib.Path.")


def _load_python_module(config_path: Path) -> ModuleType:
    """Load a user config.py file as an isolated module."""

    spec = spec_from_file_location("sdvxjc_user_config", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeConfigError(f"Unable to load config file: {config_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config_data_root(config_path: Path) -> Path:
    """Read data_path from a config file and return it as an absolute path."""

    resolved_config_path = config_path.expanduser().resolve()
    if not resolved_config_path.is_file():
        raise FileNotFoundError(f"Config file does not exist: {resolved_config_path}")

    module = _load_python_module(resolved_config_path)
    if not hasattr(module, "data_path"):
        raise RuntimeConfigError("Config file must define 'data_path'.")

    return _coerce_path(module.data_path, "data_path").resolve()


def _validate_state(payload: object) -> RuntimeState:
    """Validate the state file shape and return a typed state object."""

    if not isinstance(payload, dict):
        raise RuntimeConfigError("Invalid state file: expected a JSON object.")
    if payload.get("version") != STATE_VERSION:
        raise RuntimeConfigError("Invalid state file. Run 'sdvxjc --init <config.py> --force'.")
    if not isinstance(payload.get("data_root"), str) or not payload["data_root"]:
        raise RuntimeConfigError("Invalid state file: missing data_root.")
    if not isinstance(payload.get("targets"), dict):
        raise RuntimeConfigError("Invalid state file: missing targets.")
    current_target = payload.get("current_target")
    if current_target is not None and not isinstance(current_target, str):
        raise RuntimeConfigError("Invalid state file: current_target must be a string or null.")
    if not isinstance(payload.get("next_auto_target_id"), int):
        raise RuntimeConfigError("Invalid state file: missing next_auto_target_id.")

    targets: dict[str, TargetRecord] = {}
    for name, record in payload["targets"].items():
        if not isinstance(name, str) or not isinstance(record, dict):
            raise RuntimeConfigError("Invalid state file: malformed target record.")
        sdvx_path = record.get("sdvx_path")
        workspace_path = record.get("workspace_path")
        if not isinstance(sdvx_path, str) or not isinstance(workspace_path, str):
            raise RuntimeConfigError("Invalid state file: malformed target paths.")
        targets[name] = {"sdvx_path": sdvx_path, "workspace_path": workspace_path}

    if current_target is not None and current_target not in targets:
        raise RuntimeConfigError("Invalid state file: current target does not exist.")

    return {
        "version": STATE_VERSION,
        "data_root": payload["data_root"],
        "targets": targets,
        "current_target": current_target,
        "next_auto_target_id": payload["next_auto_target_id"],
    }


def load_state() -> RuntimeState:
    """Load and validate the current runtime state."""

    state_file = get_state_file_path()
    if not state_file.is_file():
        raise RuntimeConfigNotInitializedError(
            "No data root registered. Run 'sdvxjc --init <config.py>' first."
        )

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    return _validate_state(payload)


def save_state(state: RuntimeState) -> None:
    """Persist the runtime state to disk."""

    state_file = get_state_file_path()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def initialize_data_root(config_path: Path, force: bool = False) -> Path:
    """Create a fresh multi-target state file from config.py data_path."""

    data_root = load_config_data_root(config_path)
    state_file = get_state_file_path()
    if state_file.exists() and not force:
        raise RuntimeConfigError(
            "A data root is already registered. Re-run with --force to replace it."
        )

    data_root.mkdir(parents=True, exist_ok=True)
    state: RuntimeState = {
        "version": STATE_VERSION,
        "data_root": str(data_root),
        "targets": {},
        "current_target": None,
        "next_auto_target_id": 1,
    }
    save_state(state)
    return data_root


def validate_target_name(name: str) -> str:
    """Validate and normalize a user-facing target name."""

    normalized = name.strip()
    if not normalized:
        raise RuntimeConfigError("Target name cannot be empty.")
    if normalized in {".", ".."}:
        raise RuntimeConfigError("Target name cannot be '.' or '..'.")
    if any(char in INVALID_TARGET_NAME_CHARS for char in normalized):
        raise RuntimeConfigError(
            'Target name cannot contain any of these characters: <>:"/\\|?*'
        )
    return normalized


def _generate_target_name(state: RuntimeState) -> str:
    """Return the next unused automatic target name and update the counter."""

    next_id = state["next_auto_target_id"]
    while True:
        name = f"target-{next_id}"
        next_id += 1
        if name not in state["targets"]:
            state["next_auto_target_id"] = next_id
            return name


def _target_workspace(data_root: Path, name: str) -> Path:
    """Return the workspace directory for a target name."""

    return data_root / TARGETS_DIR_NAME / name


def add_target(sdvx_path: Path, name: str | None = None) -> tuple[str, Path, Path]:
    """Register a new target and return its name, game path, and workspace path."""

    state = load_state()
    resolved_sdvx_path = sdvx_path.expanduser().resolve()
    resolved_sdvx_text = str(resolved_sdvx_path)

    for target_name, record in state["targets"].items():
        if Path(record["sdvx_path"]).expanduser().resolve() == resolved_sdvx_path:
            raise RuntimeConfigError(
                f"Target '{target_name}' already uses this SDVX folder: {resolved_sdvx_path}"
            )

    target_name = validate_target_name(name) if name is not None else _generate_target_name(state)
    if target_name in state["targets"]:
        raise RuntimeConfigError(f"Target '{target_name}' already exists.")

    data_root = Path(state["data_root"])
    workspace_path = _target_workspace(data_root, target_name).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    state["targets"][target_name] = {
        "sdvx_path": resolved_sdvx_text,
        "workspace_path": str(workspace_path),
    }
    state["current_target"] = target_name
    save_state(state)
    return target_name, resolved_sdvx_path, workspace_path


def remove_target(name: str) -> None:
    """Remove a target from state without deleting its workspace."""

    state = load_state()
    if name not in state["targets"]:
        return
    del state["targets"][name]
    if state["current_target"] == name:
        state["current_target"] = None
    save_state(state)


def use_target(name: str) -> TargetRecord:
    """Select an existing target as the current target."""

    state = load_state()
    if name not in state["targets"]:
        raise RuntimeConfigError(f"Target '{name}' does not exist.")

    state["current_target"] = name
    save_state(state)
    return state["targets"][name]


def list_targets() -> tuple[dict[str, TargetRecord], str | None]:
    """Return all registered targets and the selected target name."""

    state = load_state()
    return state["targets"], state["current_target"]


def find_target_name_by_sdvx_path(sdvx_path: Path) -> str | None:
    """Return the saved target name for one SDVX folder, if any."""

    state = load_state()
    resolved_sdvx_path = sdvx_path.expanduser().resolve()
    for target_name, record in state["targets"].items():
        if Path(record["sdvx_path"]).expanduser().resolve() == resolved_sdvx_path:
            return target_name
    return None


def update_target_sdvx_path(name: str, sdvx_path: Path) -> TargetRecord:
    """Update one target to point at a different SDVX folder."""

    state = load_state()
    if name not in state["targets"]:
        raise RuntimeConfigError(f"Target '{name}' does not exist.")

    resolved_sdvx_path = sdvx_path.expanduser().resolve()
    for target_name, record in state["targets"].items():
        if target_name == name:
            continue
        if Path(record["sdvx_path"]).expanduser().resolve() == resolved_sdvx_path:
            raise RuntimeConfigError(
                f"Target '{target_name}' already uses this SDVX folder: {resolved_sdvx_path}"
            )

    state["targets"][name]["sdvx_path"] = str(resolved_sdvx_path)
    save_state(state)
    return state["targets"][name]


def get_current_target() -> tuple[str, TargetRecord]:
    """Return the selected target name and target record."""

    state = load_state()
    current_target = state["current_target"]
    if current_target is None:
        raise TargetNotSelectedError(
            "No current target selected. Run 'sdvxjc --add-target <sdvx_path>' or "
            "'sdvxjc --use-target <name>'."
        )
    if current_target not in state["targets"]:
        raise RuntimeConfigError("Invalid state file: current target does not exist.")
    return current_target, state["targets"][current_target]


def get_current_target_paths() -> tuple[Path, Path]:
    """Return the current target's game path and isolated workspace path."""

    _, target = get_current_target()
    return Path(target["sdvx_path"]), Path(target["workspace_path"])

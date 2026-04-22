from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
from types import ModuleType


APP_NAME = "sdvxjc"
STATE_FILE_NAME = "state.json"


class RuntimeConfigError(Exception):
    pass


class RuntimeConfigNotInitializedError(RuntimeConfigError):
    pass


def _state_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / f".{APP_NAME}"


def get_state_file_path() -> Path:
    return _state_dir() / STATE_FILE_NAME


def _coerce_path(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        return value.expanduser()
    if isinstance(value, str):
        return Path(value).expanduser()
    raise RuntimeConfigError(f"{field_name} must be a str or pathlib.Path.")


def _load_python_module(config_path: Path) -> ModuleType:
    spec = spec_from_file_location("sdvxjc_user_config", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeConfigError(f"Unable to load config file: {config_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config_paths(config_path: Path) -> tuple[Path, Path]:
    resolved_config_path = config_path.expanduser().resolve()
    if not resolved_config_path.is_file():
        raise FileNotFoundError(f"Config file does not exist: {resolved_config_path}")

    module = _load_python_module(resolved_config_path)

    if not hasattr(module, "sdvx_path"):
        raise RuntimeConfigError("Config file must define 'sdvx_path'.")
    if not hasattr(module, "data_path"):
        raise RuntimeConfigError("Config file must define 'data_path'.")

    sdvx_path = _coerce_path(module.sdvx_path, "sdvx_path").resolve()
    data_path = _coerce_path(module.data_path, "data_path").resolve()
    return sdvx_path, data_path


def save_registered_config(config_path: Path, force: bool = False) -> Path:
    resolved_config_path = config_path.expanduser().resolve()
    if not resolved_config_path.is_file():
        raise FileNotFoundError(f"Config file does not exist: {resolved_config_path}")

    state_file = get_state_file_path()
    state_file.parent.mkdir(parents=True, exist_ok=True)

    if state_file.exists() and not force:
        stored_config = get_registered_config_path()
        if stored_config != resolved_config_path:
            raise RuntimeConfigError(
                "A config file is already registered. Re-run with --force to replace it."
            )

    payload = {"config_path": str(resolved_config_path)}
    state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return resolved_config_path


def get_registered_config_path() -> Path:
    state_file = get_state_file_path()
    if not state_file.is_file():
        raise RuntimeConfigNotInitializedError(
            "No config registered. Run 'sdvxjc --init <config.py>' first."
        )

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    config_path = payload.get("config_path")
    if not isinstance(config_path, str) or not config_path:
        raise RuntimeConfigError(f"Invalid state file: {state_file}")

    resolved_config_path = Path(config_path).expanduser().resolve()
    if not resolved_config_path.is_file():
        raise RuntimeConfigNotInitializedError(
            "The registered config file no longer exists. Run 'sdvxjc --init <config.py>' again."
        )
    return resolved_config_path


def load_registered_paths() -> tuple[Path, Path]:
    return load_config_paths(get_registered_config_path())

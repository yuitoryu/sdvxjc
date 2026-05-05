# sdvxjc

`sdvxjc` is a command-line tool for initializing, editing, and applying SDVX jacket changes.

## Install

```bash
pip install .
```

## Commands

```bash
sdvxjc --init path\to\config.py
sdvxjc --add-target path\to\sdvx\contents -n main
sdvxjc --list-targets
sdvxjc --use-target main
sdvxjc --current-target
sdvxjc --replace ID DIFF path\to\image.png
sdvxjc --apply
```

`DIFF` accepts numeric IDs `1` through `6` or difficulty aliases such as `NOV`, `exh`, `grv`, or `maximum`.

## Config File

Your external `config.py` should define the global `data_path` that stores all target workspaces:

```python
from pathlib import Path

data_path = Path(r"E:\path\to\sdvxjc-data")
```

Each target added with `--add-target` gets an isolated workspace under `data_path\targets`.

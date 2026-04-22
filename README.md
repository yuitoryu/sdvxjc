# sdvxjc

`sdvxjc` is a command-line tool for initializing, editing, and applying SDVX jacket changes.

## Install

```bash
pip install .
```

## Commands

```bash
sdvxjc --init path\to\config.py
sdvxjc --replace ID DIFF path\to\image.png
sdvxjc --apply
```

## Config File

Your external `config.py` should define both `sdvx_path` and `data_path`:

```python
from pathlib import Path

sdvx_path = Path(r"E:\path\to\sdvx\contents")
data_path = Path(r"E:\path\to\sdvxjc-data")
```

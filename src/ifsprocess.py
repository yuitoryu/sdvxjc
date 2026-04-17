import subprocess
from pathlib import Path
import re
import shutil

class FolderStructureError(Exception):
    def __init__(self):
        self.message = '游戏文件夹不正确'
        super().__init__()

pattern = re.compile(r"s_jacket[0-9][0-9]\.ifs$")

def find_jacket_files(graphics_path: Path) -> list[str]:
    return [
        f.as_posix()
        for f in graphics_path.iterdir()
        if f.is_file() and pattern.match(f.name)
    ]

def copy_jk_ifs(sdvx_path: str, copy_path: str) -> list[str]:
    # 获得graphics文件夹路径
    graphics_path = Path(sdvx_path) / "data" / "graphics"
    
    # 获取所有曲绘ifs文件路径
    files = find_jacket_files(graphics_path)
    
    # 确保目标文件夹存在
    dst_folder = Path(copy_path)
    dst_folder.mkdir(parents=True, exist_ok=True)
    
    copied_files: list[Path] = []
    
    # 复制
    for f in files:
        # 获取最终文件路径
        src = Path(f)
        dst = dst_folder / src.name
        
        shutil.copy2(src, dst)
        copied_files.append(str(dst))
    
    return copied_files

def unpack(ifs_file: str, out_path: str) -> None:
    dst_folder = Path(out_path)
    dst_folder.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ifstools", ifs_file, '-o', out_path], check=True)

def unpack(ifs_folder: str, ifs_path: str) -> None:
    dst_folder = Path(ifs_path)
    dst_folder.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ifstools", ifs_folder, '-o', ifs_path], check=True)

def main_process(sdvx_path: str) -> None:
    copied_files = copy_jk_ifs(sdvx_path, 'data/ifs')
    for f in copied_files:
        unpack(f, 'data/ifs_unpacked')
        
    
    
    
        

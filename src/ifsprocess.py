import subprocess
from pathlib import Path
import re
import shutil
from beartype import beartype
import json
import xml.etree.ElementTree as ET
from typing import cast
from .utils import analyze_jacket_t_data, find_jacket_files, find_unpacked_ifs
from tqdm import tqdm

class FolderStructureError(Exception):
    def __init__(self):
        self.message = '游戏文件夹不正确'
        super().__init__(self.message)



@beartype
def copy_jk_ifs(sdvx_path: Path, copy_path: Path) -> list[Path]:
    # 获得graphics文件夹路径
    graphics_path = sdvx_path / "data" / "graphics"
    
    # 获取所有曲绘ifs文件路径
    files = find_jacket_files(graphics_path)
    
    # 确保目标文件夹存在
    copy_path.mkdir(parents=True, exist_ok=True)
    
    copied_files: list[Path] = []
    
    # 复制
    print('Start copying ifs files...')
    for f in tqdm(files):
        # 获取最终文件路径
        dst = copy_path / f.name
        
        shutil.copy2(f, dst)
        copied_files.append(dst)
    print('Copy completed.')
    return copied_files

@beartype
def unpack(ifs_file: Path, out_path: Path) -> None:
    out_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ifstools', str(ifs_file), '-o', str(out_path)], 
                   input='y',
                   text=True,
                   stdout=subprocess.DEVNULL,
                   stderr=None,
                   check=True)

@beartype
def pack(ifs_folder: Path, out_path: Path) -> None:
    out_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ifstools', str(ifs_folder), '-o', str(out_path)],
                   input='y',
                   text=True,
                   stdout=subprocess.DEVNULL,
                   stderr=None,
                   check=True)

@beartype
def copy_and_analyze_all_ifs(sdvx_path: Path, data_storage: Path) -> None:
    unpacked = data_storage / 'ifs_unpacked'
    packed = data_storage / 'ifs_packed'
    
    copied_path = copy_jk_ifs(sdvx_path, packed)
    
    print('Start unpacking ifs files...')
    for f in copied_path:
        print(f'Unpacking {f.name}...')
        unpack(f, unpacked)
    print('Unpack completed.')
    
    analyze_jacket_t_data(data_storage)
           


@beartype
def main_process(sdvx_path: Path) -> None:
    packed = Path('data/ifs')
    unpacked = Path('data/ifs_unpacked')
    
    copied_files = copy_jk_ifs(sdvx_path, packed)
    for f in copied_files:
        unpack(f, unpacked)
        
    unpacked_folders = find_unpacked_ifs(unpacked)
    for fd in unpacked_folders:
        pack(fd, packed)
    
    
        

import subprocess
from pathlib import Path
import re
import shutil
from beartype import beartype
import json
import xml.etree.ElementTree as ET
from typing import cast

class FolderStructureError(Exception):
    def __init__(self):
        self.message = '游戏文件夹不正确'
        super().__init__()

@beartype
def find_jacket_files(graphics_path:  Path) -> list[Path]:
    pattern = re.compile(r"^s_jacket(?!00)[0-9]{2}\.ifs$")
    return [
        f
        for f in graphics_path.iterdir()
        if f.is_file() and pattern.match(f.name)
    ]

@beartype    
def find_unpacked_ifs(unpacked_path: Path) -> list[Path]:
    pattern = re.compile(r"^s_jacket(?!00)[0-9]{2}_ifs$")
    return [
        f
        for f in unpacked_path.iterdir()
        if f.is_dir() and pattern.match(f.name)
    ]

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
    for f in files:
        # 获取最终文件路径
        dst = copy_path / f.name
        
        shutil.copy2(f, dst)
        copied_files.append(dst)
    
    return copied_files

@beartype
def unpack(ifs_file: Path, out_path: Path) -> None:
    out_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ifstools', str(ifs_file), '-o', str(out_path)], 
                   input='y',
                   text=True,
                   check=True)

@beartype
def pack(ifs_folder: Path, out_path: Path) -> None:
    out_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ifstools', str(ifs_folder), '-o', str(out_path)],
                   input='y',
                   text=True,
                   check=True)

@beartype
def copy_and_analyze_all_ifs(sdvx_path: Path, data_storage: Path) -> None:
    unpacked = data_storage / 'ifs_unpacked'
    copied_path = copy_jk_ifs(sdvx_path, unpacked)
    
    for f in copied_path:
        unpack(f, unpacked)
        
    
@beartype
def analyze_data(unpacked: Path) -> None:
    index_dict : dict[str, dict[str, str]] = dict()
    fp = open(unpacked / 'index.json', 'w')
    
    for fd in find_unpacked_ifs(unpacked):
        # 获取当前文件夹id
        pattern = re.compile(r"^s_jacket(?!00)([0-9]{2})_ifs$")
        folder_id = cast(re.Match, pattern.fullmatch(fd.name)).group(1)
        
        # 读取xml文件获取所有曲绘文件名
        xml_path = fd / 'tex' / 'texturelist.xml'
        names = get_image_names(xml_path)
        
        # 提取id和难度信息并写入infos
        infos = extract_info(names)
        write_index(infos, index_dict, folder_id)

    json.dump(index_dict, fp, indent=4, ensure_ascii=False, sort_keys=True)
    fp.close()
    
@beartype
def extract_info(names: list[str]) -> list[tuple[str, str]]:
    pattern = re.compile(r"^jk_(\d{4})_([1-6])_t$")
    lst = []
    append = lst.append
    
    for name in names:
        m = pattern.fullmatch(name)
        if not m:
            continue

        append((m.group(1), m.group(2)))
        
    return lst

@beartype
def write_index(infos: list[tuple[str, str]], index_dict : dict[str, dict[str, str]], folder_id: str) -> None:
    for info in infos:
        id, diff = info
        index_dict.setdefault(id, {})[diff] = folder_id
        
        

@beartype
def get_image_names(xml_path: Path) -> list[str]:
    xml_path = Path(xml_path)
    root = ET.parse(xml_path).getroot()

    return[
        name
        for image in root.iter("image")
        if (name := image.get("name")) is not None
    ]

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
    
    
        

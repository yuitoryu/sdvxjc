from pathlib import Path
import re
from typing import cast
from beartype import beartype
import xml.etree.ElementTree as ET
import json
from tqdm import tqdm
import shutil
import copy
from .imgprocess import resize

class SongNotExistError(Exception):
    def __init__(self, song_id: str):
        self.message = f'ID {song_id} does not exist.'
        super().__init__(self.message)

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
def analyze_jacket_t_data(data: Path) -> None:
    index_dict : dict[str, dict[int, str]] = dict()
    
    unpacked = data / 'ifs_unpacked'
    index_file_path = data / 'index'
    index_file_path.mkdir(parents=True, exist_ok=True)
    fp = open(index_file_path / 'jacket.json', 'w')
    
    print('Start analyzing jacket_t usage...')
    for fd in tqdm(find_unpacked_ifs(unpacked)):
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
    print(f'Analysis completed. Result has been written to {str(index_file_path / 'jacket.json')}.')
    
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
def write_index(infos: list[tuple[str, str]], index_dict : dict[str, dict[int, str]], folder_id: str) -> None:
    for info in infos:
        id, diff = info
        index_dict.setdefault(id, {})[int(diff)] = folder_id
        
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
def analyze_all_song_difficulty(sdvx_path: Path, data_storage: Path) -> None:
    music_folder = sdvx_path / 'data/music'
    pattern = re.compile(r"^(?P<id>[0-8][0-9]{3})(?:_[^_]+){2,}$")
    diff_pattern = re.compile(r"^.+(?P<tag>1n|2a|3e|4i|5m|6u)\.vox$")
    
    # Set up index file for recording difficulties of songs
    index_file_path = data_storage / 'index'
    index_file_path.mkdir(parents=True, exist_ok=True)
    record: dict[str, list[int]] = dict()
    fp = open(index_file_path / 'difficulty.json', 'w')
    

    # 遍历所有歌曲解析难度
    print('Start analyzing difficuly data...')
    for music in tqdm(music_folder.iterdir()):
        if not music.is_dir():
            continue
        match = pattern.match(music.name)
        if match:
            id = match.group('id')
            fetch_diff_list(music, id, diff_pattern, record)
            
    # 写入index.json
    json.dump(record, fp, indent=4, ensure_ascii=False, sort_keys=True)
    fp.close()
    print(f'Analysis completed. Result has been written to {str(index_file_path / 'difficulty.json')}.')
            
@beartype            
def fetch_diff_list(music: Path, id: str, pattern: re.Pattern[str], record: dict[str, list[int]]) -> None:
    lst = []
    for file in music.iterdir():
        if not file.is_file():
            continue
        match = pattern.match(file.name)
        if match:
            lst.append(match.group('tag'))
    record[id] = [int(s[0]) for s in lst]

def find_song_folder(music_path: Path, song_id: str) -> Path | None:
    pattern = re.compile(rf"^{song_id}(?:_[^_]+){{2,}}$")
    for fd in music_path.iterdir():
        match = pattern.match(fd.name)
        if match:
            return fd
    raise 

@beartype
def ensure_song_folder_copied(song_id: str, sdvx_path: Path, data_storage: Path) -> Path:
    source_music_path = sdvx_path / 'data' / 'music'
    source_song_path = find_song_folder(source_music_path, song_id)
    if source_song_path is None:
        raise FileNotFoundError(f'Music data does not exist for song {song_id}')

    copied_music_path = data_storage / 'music'
    copied_music_path.mkdir(parents=True, exist_ok=True)
    copied_song_path = copied_music_path / source_song_path.name

    if not copied_song_path.exists():
        shutil.copytree(source_song_path, copied_song_path)

    return copied_song_path
    
@beartype
def copy_jacket_to_other_difficulty(
    source_diff: int,
    target_diff: int,
    song_id: str,
    jacket_t_loc: dict[str, str],
    sdvx_path: Path,
    data_storage: Path = Path('data'),
) -> None:
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
def copy_regular_jacket_to_other_difficulty(source_diff: int, target_diff: int, song_id: str, song_path: Path) -> None:
    basic_name = f'jk_{song_id}_'
    suffices = ['.png', '_b.png', '_s.png']
    for suffix in suffices:
        source_path = song_path / (basic_name + str(source_diff) + suffix)
        target_path = song_path / (basic_name + str(target_diff) + suffix)
        shutil.copy2(source_path, target_path)
    
@beartype
def copy_t_jacket_to_other_difficulty(
    source_diff: int,
    target_diff: int,
    song_id: str,
    jacket_t_loc: dict[str, str],
    data_storage: Path,
) -> None:
    ifs_id = jacket_t_loc[str(source_diff)]
    root = data_storage / 'ifs_unpacked' / f's_jacket{ifs_id}_ifs' / 'tex'
    basic_name = f'jk_{song_id}_'
    suffix = '_t.png'
    source_path = root / ( basic_name + str(source_diff) + suffix )
    target_path = root / ( basic_name + str(target_diff) + suffix )
    shutil.copy2(source_path, target_path)
    
    xml_path = root / 'texturelist.xml'
    copy_image_node_in_xml(xml_path, source_path, target_path)

@beartype
def copy_image_node_in_xml(xml_path: Path, source_path: Path, target_path: Path) -> None:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    source_name = source_path.stem
    target_name = target_path.stem

    source_image = None
    for image in root.iter("image"):
        if image.get("name") == source_name:
            source_image = image
            break

    if source_image is None:
        raise ValueError(f"Cannot find image node: {source_name}")

    for image in root.iter("image"):
        if image.get("name") == target_name:
            return

    new_image = copy.deepcopy(source_image)
    new_image.set("name", target_name)

    parent = next((elem for elem in root.iter() if source_image in list(elem)), None)
    if parent is None:
        raise ValueError(f"Cannot find parent node for image: {source_name}")

    children = list(parent)
    idx = children.index(source_image)
    parent.insert(idx + 1, new_image)

    tree.write(xml_path, encoding="utf-8", xml_declaration=True)

@beartype
def sdvx_folder_checker(sdvx_path: Path) -> bool:
    data = sdvx_path / 'data'
    graphics = data / 'graphics'
    music = data / 'music'
    if graphics.exists() and music.exists():
        return True
    return False

@beartype
def replace_jacket(song_id: str, diff: int, pic_path: Path, data_storage: Path, ifs_id: str) -> None:
    imgs = resize(pic_path, allow_morphism=False) # [regular, big, small, transfer]
    root_name = f'jk_{song_id}_{diff}'
    song_folder = cast(Path, find_song_folder(data_storage / 'music', song_id))
    
    suffices = ['', '_b', '_s'] # transfer另外处理
    for i, suffix in enumerate(suffices):
        name = root_name + suffix + '.png'
        imgs[i].save( song_folder / name)
        
    t_name = root_name + '_t.png'
    final_path = data_storage / 'ifs_unpacked' / f's_jacket{ifs_id}_ifs' / 'tex' / t_name
    imgs[-1].save(final_path)
        

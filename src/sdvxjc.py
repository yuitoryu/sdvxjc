from pathlib import Path
import argparse
from .utils import sdvx_folder_checker, analyze_all_song_difficulty
from .ifsprocess import copy_and_analyze_all_ifs
from .manager import DiffManager
from config import sdvx_path

DATA_PATH = Path(__file__).resolve().parents[1] / "data"
SDVX_PATH = sdvx_path

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    
    # --init path
    group.add_argument("--init")

    # --replace id pic_path
    group.add_argument("--replace", nargs=2, metavar=("ID", "DIFF", "PIC_PATH"))

    # --apply path
    group.add_argument("--apply")

    args = parser.parse_args()
    
    # 初始化数据
    if args.init:
        print('enter --init')
        sdvx_path = Path(args.init)
        if not sdvx_folder_checker(sdvx_path):
            raise ValueError('This is not a valid sdvx contents folder!')
        copy_and_analyze_all_ifs(sdvx_path, DATA_PATH)
        analyze_all_song_difficulty(sdvx_path, DATA_PATH)
        
    # 更换曲绘
    if args.replace:
        id, diff, pic_path = args.replace
        
        dm = DiffManager(song_id=id,
                         sdvx_path=SDVX_PATH,
                         data_storage=DATA_PATH)
        
        dm.replace_jacket(diff=diff, pic_path=pic_path)
               
if __name__== '__main__':
    main()
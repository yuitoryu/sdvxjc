from pathlib import Path
from beartype import beartype
from .utils import copy_jacket_to_other_difficulty


class DifficultyNotExistError(Exception):
    def __init__(self, diff_list: list[int], error_diff: int):
        self.diff_map = {1: 'NOV',
                         2: 'ADV',
                         3: 'EXH',
                         4: 'INF/GRV/HVN/VVD/XCD',
                         5: 'MXM',
                         6: 'ULT'}
        self.message = f'The difficulty {self.diff_map} does not exist for this song. Only {', '.join([
            self.diff_map[diff] for diff in diff_list])} {'are' if len(diff_list)>1 else 'is'} available.'
        print(self.message)
        

@beartype
class Jacket:
    def __init__(self, diff_id: int, pic_id: int=-1):
        self.diff_id = diff_id # 对应难度
        self.pic_id = pic_id # 对应使用的图片id，一般初始化应该两者保持一致
        
    def set_diff_id(self, new_id: int) -> None:
        self.diff_id = new_id
    
    def set_pic_id(self, new_id: int) -> None:
        self.pic_id = new_id
    
    def get_diff_id(self) -> int:
        return self.diff_id

    def get_pic_id(self) -> int:
        return self.pic_id
    
    def replace(self, new_id: int) -> None:
        self.diff_id = new_id
        self.pic_id = new_id
    
    def __repr__(self) -> str:
        return str((['id', self.diff_id], ['use_pic', self.pic_id]))

@beartype
class DiffManager:
    def __init__(
        self,
        song_id: str,
        jacket_t_loc: dict[str, str],
        diff_list: list[int],
        sdvx_path: Path,
        data_storage: Path = Path('data'),
    ):
        self.song_id = song_id
        self.jacket_t_loc = jacket_t_loc
        self.sdvx_path = sdvx_path
        self.data_storage = data_storage

        # 1. 所有实际存在的谱面难度
        self.diff_list = sorted(diff_list)

        # 2. 实际存在独立曲绘的难度
        self.real_jackets = sorted(int(k) for k in jacket_t_loc.keys())

        # 3. 难度 -> 下标
        self.diff_pos = {diff: i for i, diff in enumerate(self.diff_list)}

        # 初始化Jacket类列表
        self.jacket_usage: list[Jacket] = [ Jacket(diff) for diff in self.diff_list]
        
        # 写入既存立绘对应的难度
        for diff in self.real_jackets:
            pos = self.diff_pos[diff]
            self.jacket_usage[pos].set_pic_id(diff)
        
        print(self)
        # 补充沿用其他难度曲绘的难度
        for i, jacket in enumerate(self.jacket_usage):
            if jacket.get_pic_id() == -1:
                jacket.set_pic_id( self.jacket_usage[i-1].get_pic_id() )
                self.make_independent_jacket(jacket)
        
        
    def make_independent_jacket(self, jacket: Jacket):
        source_diff = jacket.get_pic_id()
        target_diff = jacket.get_diff_id()
        copy_jacket_to_other_difficulty(source_diff=source_diff,
                                        target_diff=target_diff,
                                        song_id=self.song_id,
                                        jacket_t_loc=self.jacket_t_loc,
                                        sdvx_path=self.sdvx_path,
                                        data_storage=self.data_storage)
        self.jacket_t_loc[str(target_diff)] = self.jacket_t_loc[str(source_diff)]
        jacket.set_pic_id(target_diff)
        
    
    def __repr__(self) -> str:
        return '\n'.join([ jacket.__repr__() for jacket in self.jacket_usage])
        
            
            

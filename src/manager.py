from pathlib import Path
from beartype import beartype

class Jacket:
    @beartype
    def __init__(self, id: int, cur_id: int):
        self.id = id
        self.cur_id = cur_id
        
    def set_id(self, new_id: int) -> None:
        self.id = new_id
        
    def get_id(self) -> int:
        return self.id

    def __repr__(self) -> str:
        return str((['id', self.id], ['use_pic', self.cur_id]))

class DiffManager:
    @beartype
    def __init__(self, info: dict[str, dict[str, str]]):
        song = [k for k in info.keys()][0]
        diffs = [ int(k) for k in info[song].keys() ]
        self.jackets: list[Jacket | None] = [None] * 6
        
        for i, diff in enumerate(diffs):
            cur = Jacket(diff, diff)
            for j in range(i, 6):
                self.jackets[j] = cur
    
    def __repr__(self) -> str:
        return "\n".join(str(jacket) for jacket in self.jackets)
            
            
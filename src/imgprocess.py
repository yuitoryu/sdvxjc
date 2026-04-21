from PIL import Image
from pathlib import Path

class ImageProcessError(Exception):
    """图像处理模块的基础异常"""
    pass

class ImageSizeError(ImageProcessError):
    def __init__(self):
        self.message = '图片长宽不一致'
        print(self.message)

class ImageLoadError(ImageProcessError):
    def __init__(self, path):
        self.message = f'无法加载{path}'
        print(self.message)

def resize(input_path: Path, allow_morphism: bool = False) -> list[Image.Image]:
    try:
        img = Image.open(input_path)
    except:
        raise ImageLoadError(input_path)
    
    resolution = img.size
    if resolution[0] != resolution[1] and not allow_morphism:
        raise ImageSizeError

    # 不同分辨率
    sizes = [300, 676, 108, 128]
       
    return [ img.resize((size, size), Image.Resampling.BICUBIC) for size in sizes ]
        
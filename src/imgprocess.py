from PIL import Image

class ImageProcessError(Exception):
    """图像处理模块的基础异常"""
    pass

class ImageSizeError(ImageProcessError):
    def __init__(self):
        super.__init__()
        self.message = '图片长宽不一致'

class ImageLoadError:
    def __init__(self, path):
        self.message = f'无法加载{path}'

def resize(id: str, level: int, input_path: str, allow_morphism: bool = False) -> list[Image.Image]:
    try:
        img = Image.open(input_path)
    except:
        raise ImageLoadError(input_path)
    
    resolution = img.size
    if resolution[0] != resolution[1] and ~allow_morphism:
        raise ImageSizeError

    # 不同分辨率
    sizes = [300, 676, 108, 128]
       
    return [ img.resize((size, size), Image.BICUBIC) for size in sizes ]
        
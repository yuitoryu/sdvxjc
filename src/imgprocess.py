from PIL import Image

class ImageProcessError(Exception):
    """图像处理模块的基础异常"""
    pass

class ImageSizeError(ImageProcessError):
    def __init__(self):
        self.message = '图片长宽不一致'

class ImageLoadError:
    def __init__(self, path):
        self.message = f'无法加载{path}'

def resize(id: str, level: int, input_path: str, allow_morphism: bool = False) -> list[Image.Image]:
    try:
        img = Image.open(input_path)
    except:
        raise ImageLoadError
    
    resolution = img.size
    if resolution[0] != resolution[1] and ~allow_morphism:
        raise ImageSizeError

    # 对应 id_level, id_level_b, id_level_s, id_level_t
    sizes = {300:'', 676:'_b', 108:'_b', 128:'_t'}
    imgs = []
    
    # resize
    for size in sizes:
       imgs.append( img.resize((size, size), Image.BICUBIC) )
        
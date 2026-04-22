from pathlib import Path

from PIL import Image


class ImageProcessError(Exception):
    pass


class ImageSizeError(ImageProcessError):
    def __init__(self) -> None:
        self.message = "Image must be square."
        super().__init__(self.message)


class ImageLoadError(ImageProcessError):
    def __init__(self, path: Path) -> None:
        self.message = f"Unable to load image: {path}"
        super().__init__(self.message)


def resize(input_path: Path, allow_morphism: bool = False) -> list[Image.Image]:
    try:
        img = Image.open(input_path)
    except Exception as exc:
        raise ImageLoadError(input_path) from exc

    resolution = img.size
    if resolution[0] != resolution[1] and not allow_morphism:
        raise ImageSizeError()

    sizes = [300, 676, 108, 128]
    return [img.resize((size, size), Image.Resampling.BICUBIC) for size in sizes]

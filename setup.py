from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


setup(
    name="sdvxjc",
    version="0.1.0",
    description="CLI tool for initializing and applying SDVX jacket changes.",
    long_description=README,
    long_description_content_type="text/markdown",
    author="sdvxjc",
    python_requires=">=3.10",
    package_dir={"sdvxjc": "src"},
    packages=["sdvxjc"],
    include_package_data=True,
    install_requires=[
        "beartype",
        "ifstools",
        "Pillow",
        "tqdm",
    ],
    entry_points={
        "console_scripts": [
            "sdvxjc=sdvxjc.sdvxjc:main",
        ],
    },
)

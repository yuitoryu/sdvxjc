from collections.abc import Collection
from pathlib import Path
import copy
import re
import xml.etree.ElementTree as ET

from beartype import beartype


JACKET_IMAGE_NAME_PATTERN = re.compile(r"^jk_\d{4}_[1-6]_t$")


@beartype
def copy_image_node_in_xml(xml_path: Path, source_path: Path, target_path: Path) -> None:
    """Copy or update an image node for a copied transfer jacket."""

    tree = ET.parse(xml_path)
    root = tree.getroot()

    source_name = source_path.stem
    target_name = target_path.stem

    source_image = None
    target_image = None
    for image in root.iter("image"):
        if image.get("name") == source_name:
            source_image = image
        if image.get("name") == target_name:
            target_image = image

    if source_image is None:
        raise ValueError(f"Cannot find image node: {source_name}")

    if target_image is not None:
        if target_name != source_name and rects_equal(source_image, target_image):
            assign_new_image_rect(root, source_image, target_image)
            tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        return

    new_image = copy.deepcopy(source_image)
    new_image.set("name", target_name)
    assign_new_image_rect(root, source_image, new_image)

    parent = next((elem for elem in root.iter() if source_image in list(elem)), None)
    if parent is None:
        raise ValueError(f"Cannot find parent node for image: {source_name}")

    children = list(parent)
    idx = children.index(source_image)
    parent.insert(idx + 1, new_image)

    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def parse_rect(node: ET.Element, tag_name: str) -> tuple[int, int, int, int]:
    """Parse a four-integer rectangle from an XML image node."""

    rect_node = node.find(tag_name)
    if rect_node is None or rect_node.text is None:
        raise ValueError(f"Cannot find {tag_name} for image node {node.get('name')}")
    values = [int(value) for value in rect_node.text.split()]
    if len(values) != 4:
        raise ValueError(f"Invalid {tag_name} value for image node {node.get('name')}")
    return values[0], values[1], values[2], values[3]


def write_rect(node: ET.Element, tag_name: str, rect: tuple[int, int, int, int]) -> None:
    """Write a four-integer rectangle into an XML image node."""

    rect_node = node.find(tag_name)
    if rect_node is None:
        raise ValueError(f"Cannot find {tag_name} for image node {node.get('name')}")
    rect_node.text = f"{rect[0]} {rect[1]} {rect[2]} {rect[3]}"


def rects_equal(source_node: ET.Element, target_node: ET.Element) -> bool:
    """Return whether two XML image nodes share uvrect and imgrect values."""

    return (
        parse_rect(source_node, "uvrect") == parse_rect(target_node, "uvrect")
        and parse_rect(source_node, "imgrect") == parse_rect(target_node, "imgrect")
    )


def find_image_by_name(root: ET.Element, image_name: str) -> ET.Element | None:
    """Find an image node by name in a texturelist XML tree."""

    for image in root.iter("image"):
        if image.get("name") == image_name:
            return image
    return None


def find_image_parent(root: ET.Element, target_image: ET.Element) -> ET.Element | None:
    """Find the direct parent element for one texturelist image node."""

    return next((elem for elem in root.iter() if target_image in list(elem)), None)


def image_container(root: ET.Element) -> ET.Element:
    """Return the XML node that contains texture image children."""

    for elem in root.iter():
        if any(child.tag == "image" for child in list(elem)):
            return elem
    raise ValueError("Cannot find texture image container.")


def upsert_image_node(root: ET.Element, source_image: ET.Element) -> None:
    """Replace or append one image node in a texturelist tree."""

    image_name = source_image.get("name")
    if image_name is None:
        raise ValueError("Image node is missing a name attribute.")

    existing_image = find_image_by_name(root, image_name)
    container = image_container(root)
    new_image = copy.deepcopy(source_image)

    if existing_image is None:
        container.append(new_image)
        return

    parent = find_image_parent(root, existing_image)
    if parent is None:
        raise ValueError(f"Cannot find parent node for image: {image_name}")

    children = list(parent)
    idx = children.index(existing_image)
    parent.remove(existing_image)
    parent.insert(idx, new_image)


def remove_image_node(root: ET.Element, image_name: str) -> None:
    """Remove one image node by name when present."""

    image = find_image_by_name(root, image_name)
    if image is None:
        return

    parent = find_image_parent(root, image)
    if parent is None:
        raise ValueError(f"Cannot find parent node for image: {image_name}")
    parent.remove(image)


def has_duplicate_rect(root: ET.Element, target_image: ET.Element) -> bool:
    """Return whether another image node uses the target node's imgrect."""

    target_rect = parse_rect(target_image, "imgrect")
    target_name = target_image.get("name")
    for image in root.iter("image"):
        if image is target_image or image.get("name") == target_name:
            continue
        if parse_rect(image, "imgrect") == target_rect:
            return True
    return False


def ensure_unique_image_rect(xml_path: Path, image_name: str) -> None:
    """Move an image node to a new atlas rect when its rect is duplicated."""

    tree = ET.parse(xml_path)
    root = tree.getroot()

    target_image = find_image_by_name(root, image_name)
    if target_image is None:
        raise ValueError(f"Cannot find image node: {image_name}")

    if has_duplicate_rect(root, target_image):
        assign_new_image_rect(root, target_image, target_image)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def ensure_song_image_rects_unique(xml_path: Path, song_id: str) -> None:
    """Ensure all transfer jackets for one song use distinct atlas rects."""

    tree = ET.parse(xml_path)
    root = tree.getroot()
    pattern = re.compile(rf"^jk_{song_id}_[1-6]_t$")
    updated = False

    seen_rects: set[tuple[int, int, int, int]] = set()
    for image in root.iter("image"):
        name = image.get("name")
        if name is None or not pattern.fullmatch(name):
            continue

        current_rect = parse_rect(image, "imgrect")
        if current_rect in seen_rects:
            assign_new_image_rect(root, image, image)
            updated = True
            current_rect = parse_rect(image, "imgrect")
        seen_rects.add(current_rect)

    if updated:
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)


@beartype
def merge_texturelists(
    new_xml_path: Path,
    old_xml_path: Path,
    staged_names: Collection[str],
    imported_names: Collection[str],
) -> None:
    """Merge staged transfer-jacket entries from old XML into new XML."""

    tree = ET.parse(new_xml_path)
    root = tree.getroot()
    old_root = ET.parse(old_xml_path).getroot()

    expected_names = sorted(set(staged_names))
    expected_name_set = set(expected_names)
    imported_name_set = set(imported_names)

    for image_name in expected_names:
        old_image = find_image_by_name(old_root, image_name)
        if image_name in imported_name_set:
            if old_image is None:
                raise ValueError(f"Cannot find image node: {image_name}")
            upsert_image_node(root, old_image)
            continue

        if find_image_by_name(root, image_name) is None:
            raise ValueError(f"Cannot find image node: {image_name}")

    current_names = [
        name
        for image in root.iter("image")
        if (name := image.get("name")) is not None
    ]
    for image_name in current_names:
        if (
            JACKET_IMAGE_NAME_PATTERN.fullmatch(image_name)
            and image_name not in expected_name_set
        ):
            remove_image_node(root, image_name)

    for image_name in sorted(imported_name_set):
        image = find_image_by_name(root, image_name)
        if image is None:
            raise ValueError(f"Cannot find image node: {image_name}")
        if has_duplicate_rect(root, image):
            assign_new_image_rect(root, image, image)

    for image_name in expected_names:
        if find_image_by_name(root, image_name) is None:
            raise ValueError(f"Cannot find image node: {image_name}")

    tree.write(new_xml_path, encoding="utf-8", xml_declaration=True)


def assign_new_image_rect(root: ET.Element, source_image: ET.Element, target_image: ET.Element) -> None:
    """Assign the first free same-sized atlas rect to an image node."""

    source_imgrect = parse_rect(source_image, "imgrect")
    width = source_imgrect[1] - source_imgrect[0]
    height = source_imgrect[3] - source_imgrect[2]
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid imgrect size for image node {source_image.get('name')}")

    occupied: set[tuple[int, int, int, int]] = set()
    max_x2 = source_imgrect[1]
    max_y2 = source_imgrect[3]
    for image in root.iter("image"):
        imgrect = parse_rect(image, "imgrect")
        occupied.add(imgrect)
        max_x2 = max(max_x2, imgrect[1])
        max_y2 = max(max_y2, imgrect[3])

    max_x2 += width
    max_y2 += height

    for y in range(0, max_y2 + 1, height):
        for x in range(0, max_x2 + 1, width):
            candidate = (x, x + width, y, y + height)
            if candidate not in occupied:
                write_rect(target_image, "uvrect", candidate)
                write_rect(target_image, "imgrect", candidate)
                return

    raise ValueError(f"Unable to allocate a new atlas rect for {target_image.get('name')}")

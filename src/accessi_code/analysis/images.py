from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import (
    unquote,
    urljoin,
    urlparse,
)

from bs4 import BeautifulSoup, Tag

DescriptionSource = Literal[
    "longdesc",
    "figcaption",
    "adjacent_link",
    "adjacent_button",
    "aria-describedby",
]


@dataclass
class DetailedDescription:
    source: DescriptionSource
    content: str

    reference: str | None = None
    available: bool = True
    error: str | None = None


@dataclass
class ImageInfo:
    src: str
    alt: str | None
    element_html: str

    descriptions: list[DetailedDescription] = field(default_factory=list)

    context_text: str = ""
    index: int = 0

    image_path: str | None = None
    image_data: bytes | None = None


@dataclass
class ImageMapAreaInfo:
    """
    Informations utiles pour analyser une zone area.
    """

    element_html: str
    index: int

    alt: str | None
    aria_label: str | None

    href: str | None
    shape: str | None
    coords: str | None

    map_name: str | None
    context_text: str

    image: ImageInfo | None = None


ResourceLoader = Callable[
    [str],
    str,
]


def _get_text(
    element: Tag | None,
) -> str:
    if not isinstance(
        element,
        Tag,
    ):
        return ""

    return element.get_text(
        " ",
        strip=True,
    )


def _add_description(
    descriptions: list[DetailedDescription],
    description: DetailedDescription,
) -> None:
    duplicate = any(
        existing.source == description.source
        and existing.reference == description.reference
        and existing.content == description.content
        for existing in descriptions
    )

    if not duplicate:
        descriptions.append(description)


def _resolve_image_source(
    src: str,
    base_dir: str | Path | None,
) -> tuple[str | None, bytes | None]:
    image_path: str | None = None
    image_data: bytes | None = None

    if src.startswith("data:image/") and ";base64," in src:
        try:
            encoded = src.split(
                ",",
                1,
            )[1]

            image_data = base64.b64decode(encoded)

        except (
            ValueError,
            base64.binascii.Error,
        ):
            image_data = None

    elif (
        base_dir is not None
        and src
        and not src.startswith(
            (
                "http://",
                "https://",
                "data:",
            )
        )
    ):
        image_path = str((Path(base_dir) / src).resolve())

    return (
        image_path,
        image_data,
    )


def build_image_info_from_tag(
    image: Tag,
    *,
    index: int,
    base_dir: str | Path | None = None,
    descriptions: list[DetailedDescription] | None = None,
) -> ImageInfo:
    src = str(
        image.get(
            "src",
            "",
        )
    )

    image_path, image_data = _resolve_image_source(
        src,
        base_dir,
    )

    alt = image.get("alt")

    parent = (
        image.parent
        if isinstance(
            image.parent,
            Tag,
        )
        else None
    )

    return ImageInfo(
        src=src,
        alt=(
            alt
            if isinstance(
                alt,
                str,
            )
            else None
        ),
        element_html=str(image),
        descriptions=(descriptions if descriptions is not None else []),
        context_text=_get_text(parent),
        index=index,
        image_path=image_path,
        image_data=image_data,
    )


def make_local_resource_loader(
    base_dir: str | Path,
) -> ResourceLoader:
    """
    Construit un chargeur pour les descriptions détaillées locales.
    """
    root = Path(base_dir)

    def load(
        reference: str,
    ) -> str:
        parsed = urlparse(reference)

        if parsed.scheme in {
            "http",
            "https",
        }:
            raise ValueError("Le chargeur local ne prend pas en charge les URL distantes.")

        relative_path = unquote(parsed.path)

        path = Path(relative_path) if Path(relative_path).is_absolute() else root / relative_path

        content = path.read_text(encoding="utf-8")

        if path.suffix.lower() in {
            ".html",
            ".htm",
        }:
            soup = BeautifulSoup(
                content,
                "html.parser",
            )

            if parsed.fragment:
                target = soup.find(id=parsed.fragment)

                if isinstance(
                    target,
                    Tag,
                ):
                    return target.get_text(
                        " ",
                        strip=True,
                    )

            return soup.get_text(
                " ",
                strip=True,
            )

        return content.strip()

    return load


def _get_referenced_descriptions(
    image: Tag,
    soup: BeautifulSoup,
) -> list[DetailedDescription]:
    descriptions: list[DetailedDescription] = []

    value = image.get("aria-describedby")

    if not isinstance(value, str) or not value.strip():
        return descriptions

    for identifier in value.split():
        matches = soup.find_all(id=identifier)

        if len(matches) != 1:
            descriptions.append(
                DetailedDescription(
                    source="aria-describedby",
                    content="",
                    reference=identifier,
                    available=False,
                    error=("La référence aria-describedby est absente ou n'est pas unique."),
                )
            )
            continue

        referenced = matches[0]

        content = _get_text(referenced)

        _add_description(
            descriptions,
            DetailedDescription(
                source="aria-describedby",
                content=content,
                reference=identifier,
                available=bool(content),
                error=(None if content else "L'élément référencé est vide."),
            ),
        )

    return descriptions


def _get_figure_description(
    image: Tag,
) -> DetailedDescription | None:
    figure = image.find_parent("figure")

    if not isinstance(
        figure,
        Tag,
    ):
        return None

    caption = figure.find(
        "figcaption",
        recursive=False,
    )

    if not isinstance(
        caption,
        Tag,
    ):
        return None

    content = _get_text(caption)

    if not content:
        return None

    reference = caption.get("id")

    return DetailedDescription(
        source="figcaption",
        content=content,
        reference=(str(reference) if reference is not None else None),
    )


def _get_adjacent_description(
    image: Tag,
    soup: BeautifulSoup,
    *,
    page_url: str | None,
    resource_loader: ResourceLoader | None,
) -> DetailedDescription | None:
    siblings = (
        image.find_next_sibling(),
        image.find_previous_sibling(),
    )

    for sibling in siblings:
        if not isinstance(
            sibling,
            Tag,
        ):
            continue

        if sibling.name == "a":
            href = sibling.get("href")

            if not isinstance(
                href,
                str,
            ):
                continue

            reference = urljoin(
                page_url or "",
                href,
            )

            if href.startswith("#"):
                target = soup.find(id=href[1:])

                content = _get_text(
                    target
                    if isinstance(
                        target,
                        Tag,
                    )
                    else None
                )

                return DetailedDescription(
                    source="adjacent_link",
                    content=content,
                    reference=reference,
                    available=bool(content),
                    error=(None if content else "La cible du lien adjacent est introuvable ou vide."),
                )

            if resource_loader is None:
                return DetailedDescription(
                    source="adjacent_link",
                    content="",
                    reference=reference,
                    available=False,
                    error=("La cible du lien adjacent n'a pas été chargée."),
                )

            try:
                content = resource_loader(reference).strip()

                return DetailedDescription(
                    source="adjacent_link",
                    content=content,
                    reference=reference,
                    available=bool(content),
                    error=(None if content else "La cible du lien adjacent est vide."),
                )

            except Exception as error:
                return DetailedDescription(
                    source="adjacent_link",
                    content="",
                    reference=reference,
                    available=False,
                    error=str(error),
                )

        if sibling.name == "button":
            controls = sibling.get("aria-controls")

            if isinstance(
                controls,
                str,
            ):
                target = soup.find(id=controls)

                content = _get_text(
                    target
                    if isinstance(
                        target,
                        Tag,
                    )
                    else None
                )

                return DetailedDescription(
                    source="adjacent_button",
                    content=content,
                    reference=controls,
                    available=bool(content),
                    error=(
                        None if content else ("Le contenu contrôlé par le bouton adjacent est introuvable ou vide.")
                    ),
                )

            return DetailedDescription(
                source="adjacent_button",
                content="",
                reference=None,
                available=False,
                error=(
                    "Le bouton adjacent semble pouvoir fournir une "
                    "description dynamique qui n'est pas disponible "
                    "dans le DOM fourni."
                ),
            )

    return None


def extract_images(
    soup: BeautifulSoup,
    *,
    page_url: str | None = None,
    resource_loader: ResourceLoader | None = None,
    base_dir: str | Path | None = None,
) -> list[ImageInfo]:
    images: list[ImageInfo] = []

    for index, image in enumerate(soup.find_all("img")):
        descriptions: list[DetailedDescription] = []

        longdesc = image.get("longdesc")

        if isinstance(longdesc, str) and longdesc.strip():
            reference = urljoin(
                page_url or "",
                longdesc.strip(),
            )

            if resource_loader is None:
                descriptions.append(
                    DetailedDescription(
                        source="longdesc",
                        content="",
                        reference=reference,
                        available=False,
                        error="Ressource longdesc non chargée.",
                    )
                )

            else:
                try:
                    content = resource_loader(reference).strip()

                    descriptions.append(
                        DetailedDescription(
                            source="longdesc",
                            content=content,
                            reference=reference,
                            available=bool(content),
                            error=(None if content else "Ressource longdesc vide."),
                        )
                    )

                except Exception as error:
                    descriptions.append(
                        DetailedDescription(
                            source="longdesc",
                            content="",
                            reference=reference,
                            available=False,
                            error=str(error),
                        )
                    )

        figure_description = _get_figure_description(image)

        if figure_description is not None:
            _add_description(
                descriptions,
                figure_description,
            )

        adjacent = _get_adjacent_description(
            image,
            soup,
            page_url=page_url,
            resource_loader=resource_loader,
        )

        if adjacent is not None:
            _add_description(
                descriptions,
                adjacent,
            )

        for description in _get_referenced_descriptions(
            image,
            soup,
        ):
            _add_description(
                descriptions,
                description,
            )

        images.append(
            build_image_info_from_tag(
                image,
                index=index,
                base_dir=base_dir,
                descriptions=descriptions,
            )
        )

    return images


def extract_image_map_areas(
    soup: BeautifulSoup,
    *,
    base_dir: str | Path | None = None,
) -> list[ImageMapAreaInfo]:
    """
    Extrait les zones area ainsi que l'image réactive associée.
    """
    image_tags = list(soup.find_all("img"))

    image_infos = [
        build_image_info_from_tag(
            image,
            index=index,
            base_dir=base_dir,
        )
        for index, image in enumerate(image_tags)
    ]

    image_by_tag = {
        id(tag): image_info
        for tag, image_info in zip(
            image_tags,
            image_infos,
            strict=True,
        )
    }

    result: list[ImageMapAreaInfo] = []

    for index, area in enumerate(soup.find_all("area")):
        map_element = area.find_parent("map")

        map_name: str | None = None

        if isinstance(
            map_element,
            Tag,
        ):
            raw_name = map_element.get("name") or map_element.get("id")

            if isinstance(
                raw_name,
                str,
            ):
                map_name = raw_name

        associated_tag: Tag | None = None

        if map_name:
            for image_tag in image_tags:
                usemap = image_tag.get("usemap")

                if isinstance(usemap, str) and usemap.lstrip("#").lower() == map_name.lower():
                    associated_tag = image_tag
                    break

        image_info = image_by_tag.get(id(associated_tag)) if associated_tag is not None else None

        parent = (
            associated_tag.parent
            if (
                associated_tag is not None
                and isinstance(
                    associated_tag.parent,
                    Tag,
                )
            )
            else map_element
        )

        def string_attribute(
            name: str,
        ) -> str | None:
            value = area.get(name)

            if isinstance(value, str) and value.strip():
                return value.strip()

            return None

        result.append(
            ImageMapAreaInfo(
                element_html=str(area),
                index=index,
                alt=string_attribute("alt"),
                aria_label=string_attribute("aria-label"),
                href=string_attribute("href"),
                shape=string_attribute("shape"),
                coords=string_attribute("coords"),
                map_name=map_name,
                context_text=_get_text(
                    parent
                    if isinstance(
                        parent,
                        Tag,
                    )
                    else None
                ),
                image=image_info,
            )
        )

    return result


def get_images_with_description_candidates(
    images: list[ImageInfo],
) -> list[ImageInfo]:
    return [image for image in images if image.descriptions]


def get_images_with_detailed_descriptions(
    images: list[ImageInfo],
) -> list[ImageInfo]:
    """
    Alias conservé pour compatibilité avec l'ancien code.
    """
    return get_images_with_description_candidates(images)

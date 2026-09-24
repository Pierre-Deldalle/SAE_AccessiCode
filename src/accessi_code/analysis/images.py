from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin

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
    """
    Description détaillée associée à une image.
    """

    source: DescriptionSource
    content: str

    reference: str | None = None
    available: bool = True
    error: str | None = None


@dataclass
class ImageInfo:
    """
    Informations structurelles disponibles sur une image HTML.
    """

    src: str
    alt: str | None
    element_html: str

    descriptions: list[
        DetailedDescription
    ] = field(
        default_factory=list
    )

    context_text: str = ""
    index: int = 0

    image_path: str | None = None
    image_data: bytes | None = None


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
    """
    Ajoute une description en évitant uniquement les doublons exacts.
    """
    duplicate = any(
        existing.source
        == description.source
        and existing.reference
        == description.reference
        and existing.content
        == description.content
        for existing in descriptions
    )

    if not duplicate:
        descriptions.append(
            description
        )


def _get_referenced_descriptions(
    image: Tag,
    soup: BeautifulSoup,
) -> list[DetailedDescription]:
    """
    Résout les références aria-describedby.
    """
    descriptions: list[
        DetailedDescription
    ] = []

    value = image.get(
        "aria-describedby"
    )

    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        return descriptions

    for identifier in value.split():
        referenced = soup.find(
            id=identifier
        )

        if not isinstance(
            referenced,
            Tag,
        ):
            descriptions.append(
                DetailedDescription(
                    source="aria-describedby",
                    content="",
                    reference=identifier,
                    available=False,
                    error=(
                        "Identifiant aria-describedby introuvable."
                    ),
                )
            )

            continue

        content = _get_text(
            referenced
        )

        _add_description(
            descriptions,
            DetailedDescription(
                source="aria-describedby",
                content=content,
                reference=identifier,
                available=bool(content),
                error=(
                    None
                    if content
                    else "L'élément référencé est vide."
                ),
            ),
        )

    return descriptions


def _get_figure_description(
    image: Tag,
) -> DetailedDescription | None:
    """
    Recherche un figcaption appartenant au même figure que l'image.
    """
    figure = image.find_parent(
        "figure"
    )

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

    content = _get_text(
        caption
    )

    if not content:
        return None

    reference = caption.get(
        "id"
    )

    return DetailedDescription(
        source="figcaption",
        content=content,
        reference=(
            str(reference)
            if reference is not None
            else None
        ),
    )


def _get_adjacent_description(
    image: Tag,
) -> DetailedDescription | None:
    """
    Recherche un lien ou bouton directement adjacent à l'image.
    """
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

        if sibling.name not in {
            "a",
            "button",
        }:
            continue

        content = _get_text(
            sibling
        )

        reference = (
            sibling.get("href")
            or sibling.get("id")
        )

        if (
            not content
            and not reference
        ):
            continue

        source: DescriptionSource = (
            "adjacent_link"
            if sibling.name == "a"
            else "adjacent_button"
        )

        return DetailedDescription(
            source=source,
            content=content,
            reference=(
                str(reference)
                if reference is not None
                else None
            ),
            available=bool(content),
            error=(
                None
                if content
                else (
                    "Le lien ou bouton adjacent "
                    "ne contient pas de texte."
                )
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
    """
    Extrait les éléments img à partir d'un DOM déjà construit.

    Aucun parsing HTML supplémentaire n'est effectué.
    """
    images: list[ImageInfo] = []

    for index, image in enumerate(
        soup.find_all("img")
    ):
        descriptions: list[
            DetailedDescription
        ] = []

        longdesc = image.get(
            "longdesc"
        )

        if (
            isinstance(longdesc, str)
            and longdesc.strip()
        ):
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
                        error=(
                            "Ressource longdesc non chargée."
                        ),
                    )
                )

            else:
                try:
                    content = resource_loader(
                        reference
                    ).strip()

                    descriptions.append(
                        DetailedDescription(
                            source="longdesc",
                            content=content,
                            reference=reference,
                            available=bool(content),
                            error=(
                                None
                                if content
                                else (
                                    "Ressource longdesc vide."
                                )
                            ),
                        )
                    )

                except Exception as error:
                    descriptions.append(
                        DetailedDescription(
                            source="longdesc",
                            content="",
                            reference=reference,
                            available=False,
                            error=(
                                "Chargement impossible : "
                                f"{error}"
                            ),
                        )
                    )

        figure_description = (
            _get_figure_description(
                image
            )
        )

        if figure_description is not None:
            _add_description(
                descriptions,
                figure_description,
            )

        adjacent = (
            _get_adjacent_description(
                image
            )
        )

        if adjacent is not None:
            _add_description(
                descriptions,
                adjacent,
            )

        for description in (
            _get_referenced_descriptions(
                image,
                soup,
            )
        ):
            _add_description(
                descriptions,
                description,
            )

        parent = (
            image.parent
            if isinstance(
                image.parent,
                Tag,
            )
            else None
        )

        src = str(
            image.get(
                "src",
                "",
            )
        )

        image_path: str | None = None
        image_data: bytes | None = None

        if (
            src.startswith("data:image/")
            and ";base64," in src
        ):
            try:
                encoded = src.split(
                    ",",
                    1,
                )[1]

                image_data = (
                    base64.b64decode(
                        encoded
                    )
                )

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
            image_path = str(
                (
                    Path(base_dir)
                    / src
                ).resolve()
            )

        alt = image.get(
            "alt"
        )

        images.append(
            ImageInfo(
                src=src,
                alt=(
                    alt
                    if isinstance(
                        alt,
                        str,
                    )
                    else None
                ),
                element_html=str(
                    image
                ),
                descriptions=descriptions,
                context_text=_get_text(
                    parent
                ),
                index=index,
                image_path=image_path,
                image_data=image_data,
            )
        )

    return images


def get_images_with_detailed_descriptions(
    images: list[ImageInfo],
) -> list[ImageInfo]:
    """
    Retourne uniquement les images possédant une description détaillée.
    """
    return [
        image
        for image in images
        if image.descriptions
    ]
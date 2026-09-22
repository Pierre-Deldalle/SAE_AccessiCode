"""Extraction déterministe des images et de leurs descriptions détaillées."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

DescriptionSource = Literal[
    "longdesc",
    "in_page",
    "adjacent_link",
    "adjacent_button",
    "aria-describedby",
]
# Les sources sont conservées pour expliquer précisément au rapport comment
# chaque description a été associée à l'image.


@dataclass
class DetailedDescription:
    """Description trouvée et preuve de sa relation avec une image."""

    source: DescriptionSource
    content: str
    reference: str | None = None
    # Une relation peut exister sans contenu exploitable, par exemple un id
    # aria-describedby absent ou une ressource longdesc inaccessible.
    available: bool = True
    error: str | None = None


@dataclass
class ImageInfo:
    """Image HTML accompagnée de son contexte et de ses descriptions."""

    src: str
    alt: str | None
    element_html: str
    descriptions: list[DetailedDescription] = field(default_factory=list)
    context_text: str = ""
    index: int = 0
    image_path: str | None = None
    image_data: bytes | None = None


ResourceLoader = Callable[[str], str]


def _text(element: Tag | None) -> str:
    return element.get_text(" ", strip=True) if isinstance(element, Tag) else ""


def _add_description(descriptions: list[DetailedDescription], description: DetailedDescription) -> None:
    # Plusieurs mécanismes peuvent désigner le même texte : on évite seulement
    # les doublons exacts, sans supprimer les sources distinctes.
    if not any(item.source == description.source and item.reference == description.reference and item.content == description.content for item in descriptions):
        descriptions.append(description)


def _referenced_descriptions(image: Tag, soup: BeautifulSoup) -> list[DetailedDescription]:
    descriptions: list[DetailedDescription] = []
    value = image.get("aria-describedby")
    if not isinstance(value, str) or not value.strip():
        return descriptions
    for identifier in value.split():
        # Chaque identifiant est résolu séparément afin de conserver les
        # références valides et les erreurs dans les preuves du rapport.
        referenced = soup.find(id=identifier)
        if not isinstance(referenced, Tag):
            descriptions.append(DetailedDescription("aria-describedby", "", identifier, False, "Identifiant aria-describedby introuvable."))
            continue
        content = _text(referenced)
        _add_description(descriptions, DetailedDescription("aria-describedby", content, identifier, bool(content), None if content else "L'élément référencé est vide."))
    return descriptions


def _in_page_description(image: Tag) -> DetailedDescription | None:
    # Une figcaption n'est retenue que lorsqu'elle appartient au figure de
    # l'image ; un texte simplement proche ne suffit pas.
    figure = image.find_parent("figure")
    if not isinstance(figure, Tag):
        return None
    caption = figure.find("figcaption", recursive=False)
    content = _text(caption)
    if not content:
        return None
    return DetailedDescription("in_page", content, caption.get("id"))


def _adjacent_description(image: Tag) -> DetailedDescription | None:
    # Seuls les liens et boutons directement voisins sont considérés comme
    # mécanismes adjacents, conformément au périmètre du test.
    for sibling in (image.find_next_sibling(), image.find_previous_sibling()):
        if not isinstance(sibling, Tag) or sibling.name not in {"a", "button"}:
            continue
        content = _text(sibling)
        reference = sibling.get("href") or sibling.get("id")
        if not content and not reference:
            continue
        source = "adjacent_link" if sibling.name == "a" else "adjacent_button"
        error = None if content else "Le lien ou bouton adjacent ne contient pas de texte."
        return DetailedDescription(source, content, reference, bool(content), error)
    return None


def extract_images(
    html: str,
    *,
    page_url: str | None = None,
    resource_loader: ResourceLoader | None = None,
    base_dir: str | Path | None = None,
) -> list[ImageInfo]:
    """Extrait les ``img`` et conserve chaque relation de description trouvée.

    ``resource_loader`` est injecté pour charger les longdesc ; aucun accès
    réseau implicite n'est réalisé par l'extracteur.
    """
    soup = BeautifulSoup(html, "html.parser")
    images: list[ImageInfo] = []
    for index, image in enumerate(soup.find_all("img")):
        descriptions: list[DetailedDescription] = []
        longdesc = image.get("longdesc")
        if isinstance(longdesc, str) and longdesc.strip():
            # Le chargement est injecté par l'appelant afin que l'extraction
            # reste déterministe et ne déclenche pas de réseau implicitement.
            reference = urljoin(page_url or "", longdesc.strip())
            if resource_loader is None:
                descriptions.append(DetailedDescription("longdesc", "", reference, False, "Ressource longdesc non chargée."))
            else:
                try:
                    content = resource_loader(reference).strip()
                    descriptions.append(DetailedDescription("longdesc", content, reference, bool(content), None if content else "Ressource longdesc vide."))
                except Exception as error:
                    descriptions.append(DetailedDescription("longdesc", "", reference, False, f"Chargement impossible : {error}"))
        in_page = _in_page_description(image)
        if in_page is not None:
            _add_description(descriptions, in_page)
        adjacent = _adjacent_description(image)
        if adjacent is not None:
            _add_description(descriptions, adjacent)
        for described in _referenced_descriptions(image, soup):
            _add_description(descriptions, described)
        # Le contexte parent aide ensuite Gemma à interpréter le rôle de
        # l'image sans confondre ce contexte avec une description détaillée.
        parent = image.parent if isinstance(image.parent, Tag) else None
        src = str(image.get("src", ""))
        image_path = None
        image_data = None
        # Une data URI est déjà contenue dans le HTML : aucun fichier séparé
        # n'est nécessaire pour la transmettre au modèle de vision.
        if src.startswith("data:image/") and ";base64," in src:
            try:
                image_data = base64.b64decode(src.split(",", 1)[1])
            except (ValueError, base64.binascii.Error):
                image_data = None
        if base_dir is not None and src and not src.startswith(("http://", "https://", "data:")):
            # Les chemins relatifs sont conservés comme chemins locaux pour le
            # VLM, tandis que le src original reste présent dans le rapport.
            image_path = str((Path(base_dir) / src).resolve())
        images.append(ImageInfo(
            src=src,
            alt=image.get("alt") if isinstance(image.get("alt"), str) else None,
            element_html=str(image), descriptions=descriptions,
            context_text=_text(parent), index=index, image_path=image_path,
            image_data=image_data,
        ))
    return images


def get_images_for_criterion_1_7(images: list[ImageInfo]) -> list[ImageInfo]:
    """Sélectionne les images pour lesquelles une description a été trouvée."""
    # Le critère 1.7.1 ne doit pas devenir un contrôle général de toutes les
    # images : les images sans description relèvent d'autres contrôles.
    return [image for image in images if image.descriptions]
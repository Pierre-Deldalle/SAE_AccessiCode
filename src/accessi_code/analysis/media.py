from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

MediaKind = Literal["audio", "video"]

_AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".oga", ".opus", ".wav"}
_VIDEO_EXTENSIONS = {".avi", ".flv", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}


@dataclass(frozen=True)
class TemporalMedia:
    tag: Tag
    kind: MediaKind
    index: int
    has_track_description: bool = False
    aria_describedby_text: str | None = None


@dataclass(frozen=True)
class AdjacentMediaAlternatives:
    links_or_buttons: tuple[Tag, ...]
    text_candidates: tuple[str, ...]


def find_temporal_media(soup: BeautifulSoup) -> list[TemporalMedia]:
    """Extrait les médias temporels et vérifie leurs attributs d'accessibilité."""
    media: list[TemporalMedia] = []

    for index, tag in enumerate(soup.find_all(["audio", "video", "object"])):
        kind = _get_media_kind(tag)
        if kind is not None:
            has_track = bool(
                tag.find(
                    "track",
                    attrs={"kind": lambda k: k and k.lower() in {"descriptions", "subtitles"}},
                )
            )

            describedby_id = tag.get("aria-describedby")
            describedby_text = None
            if isinstance(describedby_id, str) and describedby_id.strip():
                target_el = soup.find(id=describedby_id.strip())
                if target_el:
                    describedby_text = target_el.get_text(" ", strip=True)

            media.append(
                TemporalMedia(
                    tag=tag,
                    kind=kind,
                    index=index,
                    has_track_description=has_track,
                    aria_describedby_text=describedby_text,
                )
            )

    return media


def find_adjacent_media_alternatives(tag: Tag) -> AdjacentMediaAlternatives:
    """Recherche d'alternatives (liens, boutons, texte) adjacentes au média ou dans son conteneur parent."""
    links_or_buttons: list[Tag] = []
    text_candidates: list[str] = []

    # 1. Vérification du parent immédiat (ex: <figure> contenant <video> et <figcaption> ou liens)
    parent = tag.parent
    if parent and parent.name in {"figure", "div", "section"}:
        for elem in parent.find_all(["a", "button", "figcaption"]):
            if elem == tag:
                continue
            if _is_link_or_button(elem):
                links_or_buttons.append(elem)
            elif elem.name == "figcaption" and elem.get_text(" ", strip=True):
                text_candidates.append(elem.get_text(" ", strip=True))

    # 2. Vérification des frères adjacents directs
    for relation in ("previous_sibling", "next_sibling"):
        sibling = getattr(tag, relation)
        while isinstance(sibling, NavigableString) and not str(sibling).strip():
            sibling = getattr(sibling, relation)

        if isinstance(sibling, Tag):
            if _is_link_or_button(sibling) and sibling not in links_or_buttons:
                links_or_buttons.append(sibling)
            elif sibling.get_text(" ", strip=True):
                text_candidates.append(sibling.get_text(" ", strip=True))

    return AdjacentMediaAlternatives(
        links_or_buttons=tuple(links_or_buttons),
        text_candidates=tuple(text_candidates),
    )


def _get_media_kind(tag: Tag) -> MediaKind | None:
    if tag.name == "audio":
        return "audio"
    if tag.name == "video":
        return "video"

    mime_type = str(tag.get("type", "")).strip().lower()
    if mime_type.startswith("audio/"):
        return "audio"
    if mime_type.startswith("video/"):
        return "video"

    data = str(tag.get("data", "")).strip()
    extension = PurePosixPath(urlsplit(data).path).suffix.lower()
    if extension in _AUDIO_EXTENSIONS:
        return "audio"
    if extension in _VIDEO_EXTENSIONS:
        return "video"
    return None


def _is_link_or_button(tag: Tag) -> bool:
    role = tag.get("role", [])
    roles = {str(value).lower() for value in role} if isinstance(role, list) else {str(role).lower()}

    if tag.name == "a" and tag.has_attr("href"):
        return True
    if tag.name == "button" or roles.intersection({"link", "button"}):
        return True
    return tag.name == "input" and str(tag.get("type", "")).lower() in {"button", "image", "reset", "submit"}


def is_media_exempt(tag: Tag) -> bool:
    """
    Détermine si un média doit être considéré comme exempt/applicable au vu des cas particuliers RGAA.

    Args:
        tag: La balise HTML du média (audio, video, object)

    Returns:
        True si le média est exempt (doit être ignored dans le test), False sinon
    """
    # Cas décoratif: aria-hidden="true" ou role="presentation"
    if tag.get("aria-hidden") == "true":
        return True
    if tag.get("role") == "presentation":
        return True

    # Autres cas particuliers qui pourraient être détectés heuristiquement
    # À enrichir selon les besoins et la faisabilité technique

    return False


def media_identifier(tag: Tag, index: int) -> str:
    """
    Crée un identificateur unique pour un élément média.

    Args:
        tag: La balise HTML du média
        index: L'index du média dans la liste des médias trouvés

    Returns:
        Une chaîne identifiant le média (ex: "video#my-video" ou "video[index=2]")
    """
    media_id = tag.get("id")
    if isinstance(media_id, str) and media_id.strip():
        return f"{tag.name}#{media_id}"
    return f"{tag.name}[index={index}]"
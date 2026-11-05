"""Sélection et preuves DOM pour le thème 1 RGAA. Aucune requête IA ou réseau."""
from __future__ import annotations

from bs4 import BeautifulSoup, Tag
from accessi_code.analysis.dom import get_element_identifier


def image_elements(soup: BeautifulSoup, kind: str) -> list[Tag]:
    """Retourne les éléments du type RGAA demandé, sans doublons."""
    if kind == 'img':
        return [e for e in soup.select('img, [role="img"]') if e.name not in {'svg', 'canvas', 'object', 'embed', 'input', 'area'}]
    if kind == 'area':
        return list(soup.find_all('area'))
    if kind == 'input':
        return [e for e in soup.find_all('input') if str(e.get('type', '')).lower() == 'image']
    if kind == 'svg':
        return list(soup.find_all('svg'))
    if kind == 'canvas':
        return list(soup.find_all('canvas'))
    if kind in {'object', 'embed'}:
        return [e for e in soup.find_all(kind) if str(e.get('type', '')).lower().startswith('image/')]
    if kind == 'all':
        result = []
        seen = set()
        for category in ('img', 'area', 'input', 'object', 'embed', 'svg', 'canvas'):
            for e in image_elements(soup, category):
                if id(e) not in seen:
                    result.append(e)
                    seen.add(id(e))
        return result
    return []


def identifier(element: Tag, index: int) -> str:
    return get_element_identifier(element, index)


def text_attr(element: Tag, attr: str) -> str:
    value = element.get(attr)
    return value.strip() if isinstance(value, str) else ''


def text_refs(element: Tag, soup: BeautifulSoup, attr: str) -> str:
    ids = text_attr(element, attr).split()
    if not ids:
        return ''
    texts = []
    for ref in ids:
        found = soup.find_all(id=ref)
        if len(found) != 1:
            return ''
        text = found[0].get_text(' ', strip=True)
        if not text:
            return ''
        texts.append(text)
    return ' '.join(texts)


def alternative(element: Tag, soup: BeautifulSoup, kind: str) -> list[str]:
    """Alternatives autorisées *pour le test 1.1*, par type d'élément."""
    values = []
    if kind != 'area':
        values.append(text_refs(element, soup, 'aria-labelledby'))
    values.append(text_attr(element, 'aria-label'))
    if kind in {'area', 'input'} or (kind == 'img' and element.name == 'img'):
        values.append(text_attr(element, 'alt'))
    if kind in {'input', 'object', 'embed'} or (kind == 'img' and element.name == 'img'):
        values.append(text_attr(element, 'title'))
    if kind == 'svg':
        title = element.find('title', recursive=False)
        if isinstance(title, Tag):
            values.append(title.get_text(' ', strip=True))
    return [v for v in values if v]


def semantic_alternatives(element: Tag, soup: BeautifulSoup, kind: str) -> list[str]:
    """Pour 1.3/1.4 : toutes les alternatives dont la pertinence est demandée.

    Les techniques autorisées au critère 1.1 restent évaluées séparément.
    """
    values = alternative(element, soup, kind)
    for candidate in (text_attr(element, 'title'), text_attr(element, 'alt'),
                      text_refs(element, soup, 'aria-labelledby')):
        if candidate and candidate not in values:
            values.append(candidate)
    if kind == 'canvas':
        fallback = element.get_text(' ', strip=True)
        if fallback and fallback not in values:
            values.append(fallback)
    return values


def is_decorative(element: Tag) -> bool:
    return text_attr(element, 'aria-hidden').lower() == 'true' or text_attr(element, 'role').lower() in {'presentation', 'none'}


def is_functional(element: Tag) -> bool:
    if element.name == 'area':
        return bool(text_attr(element, 'href'))
    if element.name == 'input' and text_attr(element, 'type').lower() == 'image':
        return True
    return bool(element.find_parent(['a', 'button']))


def has_caption(element: Tag) -> bool:
    figure = element.find_parent('figure')
    if isinstance(figure, Tag) and isinstance(figure.find('figcaption'), Tag):
        return True
    sibling = element.find_next_sibling()
    return isinstance(sibling, Tag) and sibling.name == 'figcaption'


def caption(element: Tag) -> Tag | None:
    figure = element.find_parent('figure')
    if isinstance(figure, Tag):
        cap = figure.find('figcaption')
        if isinstance(cap, Tag):
            return cap
    sib = element.find_next_sibling()
    return sib if isinstance(sib, Tag) and sib.name == 'figcaption' else None


def has_detailed_description(element: Tag, soup: BeautifulSoup) -> bool:
    if text_attr(element, 'longdesc'):
        return True
    if text_refs(element, soup, 'aria-describedby'):
        return True
    # <figcaption> n'est pas automatiquement une description détaillée.
    sibling = element.find_next_sibling()
    if isinstance(sibling, Tag) and sibling.name in {'a', 'button'}:
        label = sibling.get_text(' ', strip=True).lower()
        return 'description détaillée' in label or 'description complete' in label or 'description complète' in label
    return False


def has_description_mechanism(element: Tag, soup: BeautifulSoup, kind: str) -> bool:
    if kind == 'img' and text_attr(element, 'longdesc'):
        return True
    if text_refs(element, soup, 'aria-describedby'):
        return True
    if kind == 'canvas' and element.get_text(' ', strip=True):
        return True
    if kind in {'svg', 'canvas'} and text_refs(element, soup, 'aria-labelledby'):
        return True
    sibling = element.find_next_sibling()
    if isinstance(sibling, Tag) and sibling.name in {'a', 'button'}:
        label = (sibling.get_text(' ', strip=True) or text_attr(sibling, 'aria-label')).lower()
        return any(word in label for word in ('description', 'transcription', 'version textuelle', 'alternative textuelle'))
    return False


def captcha_marker(element: Tag) -> bool:
    """Marqueur explicite uniquement; une image-test non marquée reste indétectable."""
    for node in (element, element.parent):
        if not isinstance(node, Tag):
            continue
        attrs = ' '.join([str(node.get(k, '')) for k in ('id', 'class', 'data-captcha', 'aria-label', 'src')]).lower()
        if 'captcha' in attrs or 'image-test' in attrs:
            return True
    return False


def proof(context, element: Tag, index: int) -> dict:
    """Une preuve sémantique ne compte que si elle est explicitement vérifiée."""
    records = getattr(context, 'image_evidence', {}) or {}
    key = identifier(element, index)
    value = records.get(key, {})
    return value if isinstance(value, dict) and value.get('verified') is True else {}


def role(element: Tag, kind: str, evidence: dict) -> bool | None:
    if isinstance(evidence.get('information_bearing'), bool):
        return evidence['information_bearing']
    if is_functional(element):
        return True
    if is_decorative(element):
        return False
    if kind == 'img' and element.name == 'img' and element.has_attr('alt') and not text_attr(element, 'alt'):
        return False
    if text_attr(element, 'role') == 'img':
        return True
    if kind == 'img' and text_attr(element, 'alt'):
        return True
    if kind == 'svg' and text_attr(element, 'role') == 'img':
        return True
    return None

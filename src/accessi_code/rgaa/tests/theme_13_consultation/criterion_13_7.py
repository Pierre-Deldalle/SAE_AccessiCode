from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.css import CSSRule, extract_css_from_context
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Seuil RGAA 13.7 : 3 flashes par seconde maximum
FLASH_THRESHOLD_HZ = 3

# Seuil de surface cumulée : 21824 pixels
CUMULATIVE_AREA_THRESHOLD = 21824

# Patterns CSS pour détecter les animations de flash/clignotement
CSS_FLASH_PROPERTIES = {
    "animation",
    "animation-name",
    "animation-duration",
    "animation-timing-function",
    "animation-iteration-count",
    "animation-direction",
    "animation-fill-mode",
    "animation-play-state",
    "transition",
    "transition-property",
    "transition-duration",
    "transition-timing-function",
    "transition-delay",
}

# Propriétés CSS qui peuvent provoquer des changements de luminosité
BRIGHTNESS_CHANGE_PROPERTIES = {
    "opacity",
    "filter",
    "background-color",
    "background",
    "color",
    "fill",
    "stroke",
    "box-shadow",
    "text-shadow",
}

# Keywords dans les noms d'animation qui suggèrent un flash/clignotement
FLASH_ANIMATION_KEYWORDS = [
    "flash",
    "blink",
    "strobe",
    "flicker",
    "pulse",
    "clignot",
    "éclair",
    "scintill",
]

# Patterns JS pour détecter du code qui pourrait causer des flashs
JS_FLASH_PATTERNS = [
    # Manipulation d'opacité/filtrage en boucle
    re.compile(r"setInterval\s*\(\s*[^,)]*[Oo]pacity", re.IGNORECASE),
    re.compile(r"setInterval\s*\(\s*[^,)]*[Ff]ilter", re.IGNORECASE),
    re.compile(r"setInterval\s*\(\s*[^,)]*[Bb]ackground", re.IGNORECASE),
    re.compile(r"setTimeout\s*\(\s*[^,)]*[Oo]pacity", re.IGNORECASE),
    re.compile(r"setTimeout\s*\(\s*[^,)]*[Ff]ilter", re.IGNORECASE),
    re.compile(r"setTimeout\s*\(\s*[^,)]*[Bb]ackground", re.IGNORECASE),
    # requestAnimationFrame pour animations continues
    re.compile(r"requestAnimationFrame\s*\(", re.IGNORECASE),
    # classList.toggle pour clignotement
    re.compile(r"classList\.toggle\s*\(", re.IGNORECASE),
    # style.opacity / style.filter manipulation
    re.compile(r"\.style\.(opacity|filter|background|backgroundColor)\s*=", re.IGNORECASE),
]

# Extensions d'images animées
ANIMATED_IMAGE_EXTENSIONS = {".gif", ".webp", ".apng"}

# Extensions vidéo
VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".avi", ".mov", ".mkv", ".flv", ".m4v"}


def _get_element_size(element) -> int | None:
    """
    Estime la taille en pixels d'un élément.
    Retourne width * height si disponible, sinon None.
    """
    # Essayer width/height attributes
    width = element.get("width")
    height = element.get("height")

    if width and height:
        try:
            w = int(str(width).replace("px", ""))
            h = int(str(height).replace("px", ""))
            return w * h
        except (ValueError, TypeError):
            pass

    # Essayer style attribute
    style = element.get("style", "")
    if isinstance(style, str):
        width_match = re.search(r"width\s*:\s*(\d+(?:\.\d+)?)px", style, re.IGNORECASE)
        height_match = re.search(r"height\s*:\s*(\d+(?:\.\d+)?)px", style, re.IGNORECASE)
        if width_match and height_match:
            try:
                return int(float(width_match.group(1))) * int(float(height_match.group(1)))
            except (ValueError, TypeError):
                pass

    return None


def _is_animated_image(element) -> bool:
    """Vérifie si un élément <img> est une image animée (GIF, WebP animé, APNG)."""
    src = element.get("src", "")
    if not isinstance(src, str):
        return False

    src_lower = src.lower()
    for ext in ANIMATED_IMAGE_EXTENSIONS:
        if src_lower.endswith(ext) or ext + "?" in src_lower or ext + "#" in src_lower:
            return True

    # Vérifier le type MIME si disponible
    type_attr = element.get("type", "")
    if isinstance(type_attr, str):
        type_lower = type_attr.lower()
        if "gif" in type_lower or "webp" in type_lower or "apng" in type_lower:
            return True

    return False


def _is_video_element(element) -> bool:
    """Vérifie si un élément est une vidéo."""
    if element.name == "video":
        return True

    if element.name in ["object", "embed"]:
        # Vérifier le type MIME ou l'extension
        type_attr = element.get("type", "")
        data_attr = element.get("data", "") or element.get("src", "")

        for attr in [type_attr, data_attr]:
            if isinstance(attr, str):
                attr_lower = attr.lower()
                for ext in VIDEO_EXTENSIONS:
                    if ext in attr_lower:
                        return True
                if "video/" in attr_lower:
                    return True

    return False


def _find_media_flash_candidates(soup: BeautifulSoup) -> list[dict]:
    """
    Trouve les éléments média qui pourraient provoquer des flashs.
    Retourne une liste de dictionnaires avec les infos de l'élément.
    """
    candidates = []

    # Tags concernés : video, img, svg, canvas, embed, object
    media_tags = ["video", "img", "svg", "canvas", "embed", "object"]

    for tag_name in media_tags:
        elements = soup.find_all(tag_name)
        for i, elem in enumerate(elements):
            candidate = {
                "tag": tag_name,
                "index": i,
                "element": elem,
                "attributes": dict(elem.attrs),
                "size_pixels": _get_element_size(elem),
            }

            # Informations spécifiques par type
            if tag_name == "img":
                candidate["is_animated"] = _is_animated_image(elem)
                candidate["src"] = elem.get("src", "")
            elif _is_video_element(elem):
                candidate["is_video"] = True
                candidate["src"] = elem.get("src", "") or elem.get("data", "")
            elif tag_name in ["svg", "canvas"]:
                # SVG/Canvas peuvent avoir des animations via SMIL, CSS ou JS
                candidate["potentially_animated"] = True

            candidates.append(candidate)

    return candidates


def _find_css_animations_with_flash(soup: BeautifulSoup, context: AuditContext | None = None) -> list[dict]:
    """
    Analyse les règles CSS pour détecter des animations potentiellement flash.
    """
    results = []

    # Extraire les règles CSS via le module d'analyse
    css_rules: list[CSSRule] = []
    if context:
        css_rules = extract_css_from_context(context)

    # Aussi parser les styles inline directement
    for element in soup.find_all(style=True):
        style_attr = element.get("style")
        if isinstance(style_attr, str) and style_attr.strip():
            # Parser le style inline comme une règle CSS
            from accessi_code.analysis.css import _get_element_selector, _parse_inline_style

            properties = _parse_inline_style(style_attr)
            if properties:
                selector = _get_element_selector(soup, element)

                # Créer un objet CSSRule-like
                class InlineRule:
                    def __init__(self, selector, properties):
                        self.selector = selector
                        self.properties = properties

                css_rules.append(InlineRule(selector, properties))

    for rule in css_rules:
        # Vérifier si la règle a des propriétés d'animation
        has_animation = any(prop in rule.properties for prop in CSS_FLASH_PROPERTIES)
        has_brightness_change = any(prop in rule.properties for prop in BRIGHTNESS_CHANGE_PROPERTIES)

        if not (has_animation or has_brightness_change):
            continue

        # Analyser les propriétés d'animation
        animation_name = rule.properties.get("animation-name", "")
        animation_duration = rule.properties.get("animation-duration", "")
        animation_iteration = rule.properties.get("animation-iteration-count", "")

        # Aussi parser la propriété raccourcie 'animation' si présente
        animation_shorthand = rule.properties.get("animation", "")
        if animation_shorthand and animation_shorthand != "none":
            parsed = _parse_animation_shorthand(animation_shorthand)
            if not animation_name and parsed.get("animation-name"):
                animation_name = parsed["animation-name"]
            if not animation_duration and parsed.get("animation-duration"):
                animation_duration = parsed["animation-duration"]
            if not animation_iteration and parsed.get("animation-iteration-count"):
                animation_iteration = parsed["animation-iteration-count"]

        # Vérifier si le nom de l'animation suggère un flash
        is_flash_animation = False
        if animation_name and animation_name != "none":
            for keyword in FLASH_ANIMATION_KEYWORDS:
                if keyword in animation_name.lower():
                    is_flash_animation = True
                    break

        # Vérifier les keyframes si on peut les trouver (dans les <style> tags)
        # Pour l'instant, on note les animations suspectes

        if has_animation or is_flash_animation or (has_brightness_change and has_animation):
            results.append(
                {
                    "selector": rule.selector,
                    "properties": rule.properties,
                    "source": getattr(rule, "source", "inline"),
                    "line_number": getattr(rule, "line_number", None),
                    "has_animation": has_animation,
                    "has_brightness_change": has_brightness_change,
                    "is_flash_animation": is_flash_animation,
                    "animation_name": animation_name,
                    "animation_duration": animation_duration,
                    "animation_iteration": animation_iteration,
                }
            )

    return results


def _find_keyframes_with_flash(soup: BeautifulSoup) -> list[dict]:
    """
    Recherche les @keyframes qui contiennent des changements de luminosité.
    """
    results = []

    style_tags = soup.find_all("style")
    for style_tag in style_tags:
        if not style_tag.string:
            continue

        css_text = style_tag.string

        # Trouver les @keyframes
        keyframes_pattern = re.compile(r"@keyframes\s+([\w-]+)\s*\{([^}]+)\}", re.DOTALL | re.IGNORECASE)

        for match in keyframes_pattern.finditer(css_text):
            name = match.group(1).strip()
            content = match.group(2).strip()

            # Vérifier si le nom suggère un flash
            is_flash_name = any(keyword in name.lower() for keyword in FLASH_ANIMATION_KEYWORDS)

            # Analyser le contenu des keyframes pour changements de luminosité
            has_brightness_change = False
            brightness_properties = []

            for prop in BRIGHTNESS_CHANGE_PROPERTIES:
                if re.search(rf"{prop}\s*:", content, re.IGNORECASE):
                    has_brightness_change = True
                    brightness_properties.append(prop)

            if is_flash_name or has_brightness_change:
                results.append(
                    {
                        "name": name,
                        "content": content[:500],
                        "is_flash_name": is_flash_name,
                        "has_brightness_change": has_brightness_change,
                        "brightness_properties": brightness_properties,
                    }
                )

    return results


def _find_js_flash_candidates(soup: BeautifulSoup) -> list[dict]:
    """
    Recherche du JavaScript qui pourrait causer des flashs.
    """
    results = []

    scripts = soup.find_all("script")
    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string
        matches = []

        for pattern in JS_FLASH_PATTERNS:
            for match in pattern.finditer(content):
                # Extraire un contexte autour du match
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                context_text = content[start:end]

                matches.append(
                    {
                        "pattern": pattern.pattern,
                        "match": match.group(),
                        "context": context_text,
                        "position": match.start(),
                    }
                )

        if matches:
            results.append(
                {
                    "index": i,
                    "element": script,
                    "matches": matches,
                    "content_preview": content[:300],
                }
            )

    return results


def _parse_animation_shorthand(animation_value: str) -> dict[str, str]:
    """
    Parse la propriété CSS raccourcie 'animation' pour extraire les valeurs individuelles.
    Exemple: "flash 0.2s infinite ease-in" ->
    {"animation-name": "flash", "animation-duration": "0.2s",
    "animation-iteration-count": "infinite", "animation-timing-function": "ease-in"}
    """
    result = {}
    if not animation_value or animation_value == "none":
        return result

    # La syntaxe est: name duration timing-function delay
    # iteration-count direction fill-mode play-state
    # L'ordre peut varier mais généralement:
    # name duration timing-function delay iteration-count direction fill-mode play-state
    parts = animation_value.split()

    if not parts:
        return result

    # Premier élément non temporel = nom de l'animation (si ce n'est pas un temps)
    # Les temps se terminent par 's' ou 'ms'
    name_parts = []
    remaining_parts = []

    known_keywords = {
        "infinite",
        "normal",
        "reverse",
        "alternate",
        "alternate-reverse",
        "forwards",
        "backwards",
        "both",
        "running",
        "paused",
        "ease",
        "linear",
        "ease-in",
        "ease-out",
        "ease-in-out",
        "step-start",
        "step-end",
    }

    for part in parts:
        # Vérifier si c'est une durée (se termine par s ou ms) ou un mot-clé connu
        is_duration = re.match(r"^\d+(?:\.\d+)?(ms|s)$", part)
        is_keyword = part in known_keywords or re.match(r"^steps?\(", part)
        if is_duration or is_keyword:
            remaining_parts.append(part)
        else:
            name_parts.append(part)

    # Le nom de l'animation est tout ce qui n'est pas une durée/mot-clé
    if name_parts:
        result["animation-name"] = " ".join(name_parts)

    # Parser les parties restantes pour extraire durée, itérations, etc.
    # Ordre attendu: duration, timing-function, delay, iteration-count, direction, fill-mode, play-state
    for part in remaining_parts:
        if re.match(r"^\d+(?:\.\d+)?(ms|s)$", part):
            # C'est une durée - la première est animation-duration, la seconde est animation-delay
            if "animation-duration" not in result:
                result["animation-duration"] = part
            elif "animation-delay" not in result:
                result["animation-delay"] = part
        elif part == "infinite" or re.match(r"^\d+$", part):
            # Nombre d'itérations
            result["animation-iteration-count"] = part
        elif part in ["normal", "reverse", "alternate", "alternate-reverse"]:
            result["animation-direction"] = part
        elif part in ["forwards", "backwards", "both"]:
            result["animation-fill-mode"] = part
        elif part in ["running", "paused"]:
            result["animation-play-state"] = part
        elif part in [
            "ease",
            "linear",
            "ease-in",
            "ease-out",
            "ease-in-out",
            "step-start",
            "step-end",
        ] or re.match(r"^steps?\(", part):
            result["animation-timing-function"] = part

    return result


def _estimate_flash_frequency(animation_duration: str, iteration_count: str) -> float | None:
    """
    Estime la fréquence de flash en Hz à partir des propriétés CSS d'animation.
    Retourne la fréquence en Hz ou None si impossible à déterminer.
    """
    # Parser la durée (ex: "2s", "500ms", "1s")
    duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(ms|s)", animation_duration)
    if not duration_match:
        return None

    value = float(duration_match.group(1))
    unit = duration_match.group(2)

    if unit == "ms":
        duration_seconds = value / 1000
    else:
        duration_seconds = value

    if duration_seconds <= 0:
        return None

    # Parser le nombre d'itérations
    if iteration_count and iteration_count != "infinite":
        try:
            float(iteration_count)
        except ValueError:
            pass

    # Fréquence = 1 / durée d'un cycle (en secondes)
    # Pour un flash complet (allumé/éteint), on considère un cycle complet
    frequency = 1 / duration_seconds

    return frequency


class Test1371(RGAATest):
    """
    Test 13.7.1 : Dans chaque page web, chaque image ou élément multimédia
    (balise <video>, balise <img>, balise <svg>, balise <canvas>,
    balise <embed> ou balise <object>) qui provoque un changement brusque
    de luminosité ou un effet de flash vérifie-t-il une de ces conditions ?

    La fréquence de l'effet est inférieure à 3 par seconde ;
    La surface totale cumulée des effets est inférieure ou égale à 21824 pixels.
    """

    test_id = "13.7.1"
    criterion_id = "13.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    optional_capabilities = frozenset(
        {
            Capability.IMAGES,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 13.7.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Trouver tous les candidats média potentiellement flash
        media_candidates = _find_media_flash_candidates(soup)

        if not media_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun élément multimédia (video, img, svg, canvas, embed, object) "
                    "potentiellement source de flash détecté."
                ),
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for candidate in media_candidates:
            tag = candidate["tag"]
            index = candidate["index"]
            element = candidate["element"]
            size = candidate["size_pixels"]

            # Construire un sélecteur lisible
            selector = self._get_element_selector(soup, element, tag, index)

            # Analyser selon le type
            if tag == "img" and candidate.get("is_animated"):
                # Image animée (GIF, WebP animé, APNG)
                src = candidate.get("src", "")
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Image animée détectée ({tag}) : {src}. "
                            "Impossible de déterminer automatiquement la fréquence de clignotement "
                            "et la surface cumulée des effets de flash."
                        ),
                        recommendation=(
                            "Vérifier manuellement avec l'outil PEAT ou équivalent : "
                            "1) Fréquence de clignotement < 3 Hz ; "
                            "2) Surface cumulée des zones flash ≤ 21824 pixels. "
                            "Si l'image est décorative, envisager de la remplacer par une version statique."
                        ),
                        evidence={
                            "tag": tag,
                            "src": src,
                            "size_pixels": size,
                            "is_animated": True,
                            "needs_manual_check": True,
                            "checks_required": [
                                "flash_frequency_below_3hz",
                                "cumulative_area_below_21824px",
                            ],
                            "tool_recommendation": "PEAT (Photosensitive Epilepsy Analysis Tool)",
                        },
                    )
                )

            elif candidate.get("is_video"):
                # Élément vidéo
                src = candidate.get("src", "")
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Élément vidéo détecté ({tag}) : {src}. "
                            "L'analyse des effets de flash dans les vidéos nécessite des outils spécialisés."
                        ),
                        recommendation=(
                            "Vérifier manuellement avec l'outil PEAT : "
                            "1) Fréquence de flash < 3 Hz ; "
                            "2) Surface cumulée ≤ 21824 pixels. "
                            "Note : l'outil PEAT analyse les fichiers .avi (convertir si nécessaire)."
                        ),
                        evidence={
                            "tag": tag,
                            "src": src,
                            "size_pixels": size,
                            "is_video": True,
                            "needs_manual_check": True,
                            "checks_required": [
                                "flash_frequency_below_3hz",
                                "cumulative_area_below_21824px",
                            ],
                            "tool_recommendation": "PEAT (Photosensitive Epilepsy Analysis Tool)",
                        },
                    )
                )

            elif tag in ["svg", "canvas"]:
                # SVG ou Canvas - peuvent avoir des animations SMIL, CSS ou JS
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Élément {tag} détecté : peut contenir des animations "
                            "(SMIL pour SVG, JavaScript pour canvas) provoquant des flashs."
                        ),
                        recommendation=(
                            "Vérifier manuellement : "
                            "1) Pour SVG : rechercher des animations SMIL (<animate>, <set>) "
                            "modifiant opacity, fill, stroke, filter ; "
                            "2) Pour Canvas : analyser le JavaScript qui dessine sur le canvas ; "
                            "3) Mesurer fréquence < 3 Hz et surface cumulée ≤ 21824 px."
                        ),
                        evidence={
                            "tag": tag,
                            "size_pixels": size,
                            "potentially_animated": True,
                            "needs_manual_check": True,
                            "checks_required": [
                                "flash_frequency_below_3hz",
                                "cumulative_area_below_21824px",
                            ],
                        },
                    )
                )

            elif tag in ["embed", "object"]:
                # embed/object - peuvent contenir du Flash, Java, ou d'autres plugins
                src = candidate.get("src", "") or candidate.get("data", "")
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Élément {tag} détecté : {src}. "
                            "Contenu embarqué potentiellement source de flash (plugins, applets)."
                        ),
                        recommendation=(
                            "Vérifier manuellement le contenu embarqué : "
                            "1) Identifier la technologie (Flash, Java, etc.) ; "
                            "2) Si animation présente, mesurer fréquence < 3 Hz et surface ≤ 21824 px ; "
                            "3) Privilégier des alternatives HTML5 accessibles."
                        ),
                        evidence={
                            "tag": tag,
                            "src": src,
                            "size_pixels": size,
                            "needs_manual_check": True,
                            "checks_required": [
                                "flash_frequency_below_3hz",
                                "cumulative_area_below_21824px",
                            ],
                        },
                    )
                )

            else:
                # Autre élément média sans animation détectée
                pass

        tested_elements = len(
            [
                c
                for c in media_candidates
                if c.get("is_animated") or c.get("is_video") or c["tag"] in ["svg", "canvas", "embed", "object"]
            ]
        )

        if tested_elements == 0:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary=(
                    "Aucun élément multimédia animé ou vidéo détecté "
                    "(images statiques, SVG/Canvas sans animation détectée)."
                ),
                tested_elements=0,
                metadata={"total_media_elements": len(media_candidates)},
            )

        # Déterminer le statut global
        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} élément(s) multimédia potentiellement flash détecté(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} élément(s) multimédia potentiellement flash détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle (outil PEAT recommandé), "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} élément(s) multimédia détecté(s). "
                f"Aucun ne semble provoquer de flash (conforme au critère 13.7.1)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "total_media_candidates": len(media_candidates),
                "animated_images": len([c for c in media_candidates if c.get("is_animated")]),
                "videos": len([c for c in media_candidates if c.get("is_video")]),
                "svg_canvas": len([c for c in media_candidates if c["tag"] in ["svg", "canvas"]]),
                "embed_object": len([c for c in media_candidates if c["tag"] in ["embed", "object"]]),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "utiliser l'outil PEAT pour analyser les vidéos et GIFs animés",
                    "vérifier la fréquence de flash < 3 Hz",
                    "vérifier la surface cumulée des zones flash ≤ 21824 pixels",
                    "pour SVG : vérifier les animations SMIL (<animate>, <set>)",
                    "pour Canvas : analyser le code JavaScript de dessin",
                    "pour embed/object : identifier le contenu embarqué",
                ],
            },
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, tag: str, index: int) -> str:
        """Génère un sélecteur lisible pour un élément."""
        if element is None:
            return f"{tag}[index={index}]"

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            return f"#{element_id}"

        classes = element.get("class", [])
        if isinstance(classes, list) and classes:
            return f"{tag}.{'.'.join(str(c) for c in classes[:2])}"

        same_tag = soup.find_all(tag)
        if len(same_tag) > 1:
            try:
                return f"{tag}[index={same_tag.index(element)}]"
            except ValueError:
                pass

        return f"{tag}[index={index}]"


class Test1372(RGAATest):
    """
    Test 13.7.2 : Dans chaque page web, chaque script qui provoque un changement
    brusque de luminosité ou un effet de flash vérifie-t-il une de ces conditions ?

    La fréquence de l'effet est inférieure à 3 par seconde ;
    La surface totale cumulée des effets est inférieure ou égale à 21824 pixels.
    """

    test_id = "13.7.2"
    criterion_id = "13.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 13.7.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Rechercher du JavaScript potentiellement source de flash
        js_candidates = _find_js_flash_candidates(soup)

        if not js_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun script potentiellement source de flash détecté.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for candidate in js_candidates:
            index = candidate["index"]
            element = candidate["element"]
            matches = candidate["matches"]
            content_preview = candidate["content_preview"]

            selector = self._get_element_selector(soup, element, "script", index)

            # Analyser les matches
            match_details = []
            for match in matches:
                match_details.append(
                    f"Pattern: {match['pattern']} | Match: {match['match']} | Context: {match['context'][:100]}..."
                )

            needs_review_count += 1
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Script détecté avec des patterns potentiellement source de flash : "
                        f"{len(matches)} occurrence(s). "
                        f"Exemples : {'; '.join(match_details[:3])}" + ("..." if len(match_details) > 3 else "")
                    ),
                    recommendation=(
                        "Vérifier manuellement le code JavaScript : "
                        "1) Identifier les animations/boucles modifiant opacity, filter, background-color, etc. ; "
                        "2) Mesurer la fréquence de clignotement (doit être < 3 Hz) ; "
                        "3) Mesurer la surface cumulée des éléments affectés (doit être ≤ 21824 px) ; "
                        "4) Vérifier si l'utilisateur peut désactiver l'animation."
                    ),
                    evidence={
                        "script_index": index,
                        "matches_count": len(matches),
                        "match_details": match_details,
                        "content_preview": content_preview,
                        "needs_manual_check": True,
                        "checks_required": [
                            "flash_frequency_below_3hz",
                            "cumulative_area_below_21824px",
                            "user_can_disable_animation",
                        ],
                    },
                )
            )

        tested_elements = len(js_candidates)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} script(s) potentiellement flash détecté(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} script(s) potentiellement flash détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle du code, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} script(s) analysé(s). "
                f"Aucun ne semble provoquer de flash (conforme au critère 13.7.2)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "js_flash_candidates": len(js_candidates),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "analyser les boucles setInterval/setTimeout modifiant des styles visuels",
                    "vérifier les requestAnimationFrame utilisés pour des effets de flash",
                    "vérifier les classList.toggle pour clignotement",
                    "mesurer la fréquence effective < 3 Hz",
                    "mesurer la surface cumulée des éléments affectés ≤ 21824 px",
                    "vérifier la présence d'un contrôle utilisateur pour arrêter l'animation",
                ],
            },
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, tag: str, index: int) -> str:
        """Génère un sélecteur lisible pour un élément script."""
        if element is None:
            return f"{tag}[index={index}]"

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            return f"#{element_id}"

        scripts = soup.find_all("script")
        if len(scripts) > 1:
            try:
                return f"script[index={scripts.index(element)}]"
            except ValueError:
                pass

        return f"script[index={index}]"


class Test1373(RGAATest):
    """
    Test 13.7.3 : Dans chaque page web, chaque mise en forme CSS qui provoque
    un changement brusque de luminosité ou un effet de flash vérifie-t-il une
    de ces conditions ?

    La fréquence de l'effet est inférieure à 3 par seconde ;
    La surface totale cumulée des effets est inférieure ou égale à 21824 pixels.
    """

    test_id = "13.7.3"
    criterion_id = "13.7"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 13.7.3 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Analyser les animations CSS
        css_animations = _find_css_animations_with_flash(soup, context)

        # Analyser les @keyframes
        keyframes = _find_keyframes_with_flash(soup)

        # Combiner les résultats
        all_candidates = []

        for anim in css_animations:
            all_candidates.append(
                {
                    "type": "css_rule",
                    "data": anim,
                }
            )

        for kf in keyframes:
            all_candidates.append(
                {
                    "type": "keyframes",
                    "data": kf,
                }
            )

        if not all_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune animation CSS potentiellement source de flash détectée.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for candidate in all_candidates:
            ctype = candidate["type"]
            data = candidate["data"]

            if ctype == "css_rule":
                selector = data["selector"]
                properties = data["properties"]
                source = data.get("source", "unknown")
                line_number = data.get("line_number")
                animation_name = data.get("animation_name", "")
                animation_duration = data.get("animation_duration", "")
                animation_iteration = data.get("animation_iteration_count", "")
                is_flash_animation = data.get("is_flash_animation", False)
                has_brightness_change = data.get("has_brightness_change", False)

                # Essayer d'estimer la fréquence
                frequency = None
                if animation_duration:
                    frequency = _estimate_flash_frequency(animation_duration, animation_iteration)

                # Construire le message
                details = []
                if is_flash_animation:
                    details.append(f"nom d'animation suggestif ('{animation_name}')")
                if has_brightness_change:
                    brightness_props = [p for p in BRIGHTNESS_CHANGE_PROPERTIES if p in properties]
                    details.append(f"propriétés de luminosité : {', '.join(brightness_props)}")
                if animation_duration:
                    details.append(f"durée : {animation_duration}")
                if animation_iteration and animation_iteration != "infinite":
                    details.append(f"itérations : {animation_iteration}")
                if frequency is not None:
                    details.append(f"fréquence estimée : {frequency:.2f} Hz")
                    if frequency >= FLASH_THRESHOLD_HZ:
                        details.append(f"⚠️ FRÉQUENCE ≥ {FLASH_THRESHOLD_HZ} Hz (seuil RGAA)")

                message = (
                    f"Règle CSS ({source}) pour '{selector}' : "
                    f"animation détectée ({'; '.join(details) if details else "propriétés d'animation"})."
                )

                if frequency is not None and frequency >= FLASH_THRESHOLD_HZ:
                    non_compliant_count += 1
                    recommendation = (
                        f"La fréquence estimée ({frequency:.2f} Hz) dépasse le seuil RGAA de {FLASH_THRESHOLD_HZ} Hz. "
                        "Modifier l'animation pour réduire la fréquence ou augmenter la durée du cycle. "
                        "Vérifier aussi la surface cumulée des éléments affectés (≤ 21824 px)."
                    )
                    condition = "frequency_exceeds_threshold"
                else:
                    needs_review_count += 1
                    recommendation = (
                        "Vérifier manuellement : "
                        "1) Fréquence réelle de l'animation < 3 Hz (mesurer dans le navigateur) ; "
                        "2) Surface cumulée des éléments animés ≤ 21824 pixels ; "
                        "3) Si fréquence ≥ 3 Hz, réduire la vitesse ou ajouter un contrôle utilisateur pour désactiver."
                    )
                    condition = "needs_manual_verification"

                findings.append(
                    Finding(
                        element=selector,
                        message=message,
                        recommendation=recommendation,
                        evidence={
                            "type": "css_animation_rule",
                            "selector": selector,
                            "source": source,
                            "line_number": line_number,
                            "animation_name": animation_name,
                            "animation_duration": animation_duration,
                            "animation_iteration_count": animation_iteration,
                            "estimated_frequency_hz": frequency,
                            "has_brightness_change": has_brightness_change,
                            "is_flash_animation": is_flash_animation,
                            "properties": properties,
                            "needs_manual_check": frequency is None or frequency < FLASH_THRESHOLD_HZ,
                            "condition_met": condition,
                        },
                    )
                )

            elif ctype == "keyframes":
                name = data["name"]
                content = data["content"]
                is_flash_name = data.get("is_flash_name", False)
                has_brightness_change = data.get("has_brightness_change", False)
                brightness_props = data.get("brightness_properties", [])

                details = []
                if is_flash_name:
                    details.append(f"nom suggestif ('{name}')")
                if has_brightness_change:
                    details.append(f"propriétés de luminosité dans keyframes : {', '.join(brightness_props)}")

                message = (
                    f"@keyframes '{name}' détecté : {'; '.join(details) if details else 'changements de luminosité'}."
                )

                needs_review_count += 1
                findings.append(
                    Finding(
                        element=f"@keyframes {name}",
                        message=message,
                        recommendation=(
                            "Vérifier manuellement l'animation complète : "
                            "1) Identifier quels éléments utilisent cette animation "
                            "(animation-name) ; "
                            "2) Mesurer la fréquence effective < 3 Hz ; "
                            "3) Mesurer la surface cumulée des éléments animés "
                            "≤ 21824 px ; "
                            "4) Vérifier la présence d'une option pour désactiver "
                            "les animations (prefers-reduced-motion)."
                        ),
                        evidence={
                            "type": "css_keyframes",
                            "name": name,
                            "content_preview": content,
                            "is_flash_name": is_flash_name,
                            "has_brightness_change": has_brightness_change,
                            "brightness_properties": brightness_props,
                            "needs_manual_check": True,
                            "condition_met": "needs_manual_verification",
                        },
                    )
                )

        tested_elements = len(all_candidates)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} animation(s) CSS potentielle(s) flash détectée(s). "
                f"{non_compliant_count} non conforme(s) (fréquence ≥ 3 Hz), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} animation(s) CSS potentielle(s) flash détectée(s). "
                f"{needs_review_count} nécessitent une vérification manuelle (fréquence et surface), "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} animation(s) CSS analysée(s). "
                f"Aucune ne semble provoquer de flash non conforme (critère 13.7.3)."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "css_animation_rules": len(css_animations),
                "keyframes_rules": len(keyframes),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    "mesurer la fréquence réelle des animations CSS dans le navigateur",
                    "vérifier la surface cumulée des éléments affectés ≤ 21824 px",
                    "tester avec prefers-reduced-motion : l'animation doit être désactivable",
                    "vérifier les animations sur :hover, :focus qui pourraient clignoter",
                    "analyser les @keyframes pour changements d'opacité, filtre, couleur de fond",
                ],
            },
        )

    def _get_element_selector(self, soup: BeautifulSoup, element, tag: str, index: int) -> str:
        """Génère un sélecteur lisible (utilisé pour les règles CSS inline)."""
        if element is None:
            return f"{tag}[index={index}]"

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            return f"#{element_id}"

        classes = element.get("class", [])
        if isinstance(classes, list) and classes:
            return f"{tag}.{'.'.join(str(c) for c in classes[:2])}"

        same_tag = soup.find_all(tag)
        if len(same_tag) > 1:
            try:
                return f"{tag}[index={same_tag.index(element)}]"
            except ValueError:
                pass

        return f"{tag}[index={index}]"

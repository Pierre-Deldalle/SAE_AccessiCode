from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.css import CSSRule, extract_css_from_context
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Seuil RGAA 13.8 : 5 secondes maximum pour mouvement/clignotement auto
MAX_AUTO_DURATION_SECONDS = 5

# Patterns CSS pour détecter les animations de mouvement/clignotement
CSS_MOTION_PROPERTIES = {
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

# Propriétés CSS qui peuvent provoquer des mouvements visuels
MOTION_CHANGE_PROPERTIES = {
    "transform",
    "opacity",
    "filter",
    "left",
    "right",
    "top",
    "bottom",
    "margin",
    "margin-left",
    "margin-right",
    "margin-top",
    "margin-bottom",
    "width",
    "height",
    "max-width",
    "max-height",
    "background-position",
    "background-size",
    "background-color",
    "background",
    "color",
    "fill",
    "stroke",
    "box-shadow",
    "text-shadow",
    "clip-path",
    "offset-path",
    "offset-distance",
    "visibility",
    "display",
}

# Keywords dans les noms d'animation qui suggèrent un mouvement/clignotement
MOTION_ANIMATION_KEYWORDS = [
    "move",
    "slide",
    "scroll",
    "marquee",
    "ticker",
    "pan",
    "zoom",
    "rotate",
    "spin",
    "swing",
    "bounce",
    "shake",
    "wiggle",
    "float",
    "drift",
    "translate",
    "mouvement",
    "défilement",
    "défile",
    "glisse",
    "déplacement",
]

BLINK_ANIMATION_KEYWORDS = [
    "blink",
    "flash",
    "strobe",
    "flicker",
    "pulse",
    "clignot",
    "éclair",
    "scintill",
    "clignote",
]

# Extensions d'images animées
ANIMATED_IMAGE_EXTENSIONS = {".gif", ".webp", ".apng"}

# Extensions vidéo
VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".avi", ".mov", ".mkv", ".flv", ".m4v"}

# Patterns JS pour détecter du code qui pourrait causer du mouvement/clignotement auto
# On utilise une approche en deux temps : détecter setInterval/setTimeout ET les modifications de style
JS_MOTION_PATTERNS = [
    # setInterval ou setTimeout présents
    re.compile(r"setInterval\s*\(", re.IGNORECASE),
    re.compile(r"setTimeout\s*\(", re.IGNORECASE),
    # requestAnimationFrame pour animations continues
    re.compile(r"requestAnimationFrame\s*\(", re.IGNORECASE),
    # classList.toggle pour mouvement/clignotement
    re.compile(r"classList\.toggle\s*\(", re.IGNORECASE),
    # Animation Web API
    re.compile(r"\.animate\s*\(", re.IGNORECASE),
    # IntersectionObserver pour animations au scroll
    re.compile(r"IntersectionObserver\s*\(", re.IGNORECASE),
    # scrollTop/scrollLeft manipulation
    re.compile(r"scroll(Top|Left)\s*=", re.IGNORECASE),
    # element.scrollIntoView
    re.compile(r"scrollIntoView\s*\(", re.IGNORECASE),
]

# Propriétés de style qui indiquent un mouvement/clignotement quand modifiées dans un timer
JS_STYLE_MOTION_PROPERTIES = {
    "left",
    "right",
    "top",
    "bottom",
    "transform",
    "margin",
    "marginLeft",
    "marginRight",
    "marginTop",
    "marginBottom",
    "opacity",
    "filter",
    "visibility",
    "display",
}


def _get_element_size(element) -> int | None:
    """
    Estime la taille en pixels d'un élément.
    Retourne width * height si disponible, sinon None.
    """
    width = element.get("width")
    height = element.get("height")

    if width and height:
        try:
            w = int(str(width).replace("px", ""))
            h = int(str(height).replace("px", ""))
            return w * h
        except ValueError, TypeError:
            pass

    style = element.get("style", "")
    if isinstance(style, str):
        width_match = re.search(r"width\s*:\s*(\d+(?:\.\d+)?)px", style, re.IGNORECASE)
        height_match = re.search(r"height\s*:\s*(\d+(?:\.\d+)?)px", style, re.IGNORECASE)
        if width_match and height_match:
            try:
                return int(float(width_match.group(1))) * int(float(height_match.group(1)))
            except ValueError, TypeError:
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


def _is_progress_element(element) -> bool:
    """Vérifie si un élément est une barre de progression (cas particulier non applicable)."""
    # <progress> tag
    if element.name == "progress":
        return True

    # role="progressbar"
    role = element.get("role", "")
    if isinstance(role, str) and role == "progressbar":
        return True

    # aria-valuenow + aria-valuemin + aria-valuemax (pattern progressbar)
    if element.has_attr("aria-valuenow") and element.has_attr("aria-valuemin") and element.has_attr("aria-valuemax"):
        return True

    # Classes communes pour progress bars
    classes = element.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(str(c).lower() for c in classes)
        progress_keywords = ["progress", "loading", "spinner", "barre-chargement", "barre-progression"]
        for kw in progress_keywords:
            if kw in class_str:
                return True

    return False


def _has_user_control_for_motion(soup: BeautifulSoup, element, control_keywords: list[str]) -> bool:
    """
    Vérifie s'il existe un mécanisme de contrôle utilisateur pour le mouvement/clignotement.
    Recherche boutons/liens avec texte suggérant arrêt, masquage, ou affichage sans mouvement.
    """
    # Mots-clés pour les contrôles (français + anglais)
    all_keywords = control_keywords + [
        "stop",
        "pause",
        "arrêt",
        "arreter",
        "halt",
        "restart",
        "relancer",
        "reprendre",
        "resume",
        "replay",
        "hide",
        "masquer",
        "cacher",
        "toggle",
        "show",
        "afficher",
        "display",
        "disable",
        "désactiver",
        "desactiver",
        "turn off",
        "reduce motion",
        "réduire mouvement",
        "reduced motion",
        "sans animation",
        "without animation",
        "no animation",
        "version statique",
        "static version",
    ]

    # Chercher dans toute la page des contrôles potentiels
    controls = soup.find_all(
        ["button", "a", "input", "label"],
        string=re.compile("|".join(all_keywords), re.IGNORECASE),
    )

    # Aussi vérifier les attributs aria-label, title, etc.
    for control in soup.find_all(["button", "a", "input", "label"]):
        for attr in ["aria-label", "title", "alt", "data-tooltip"]:
            value = control.get(attr, "")
            if isinstance(value, str) and any(kw in value.lower() for kw in all_keywords):
                return True

    # Vérifier prefers-reduced-motion media query dans le CSS
    # (indique que l'auteur a prévu une alternative sans mouvement)
    style_tags = soup.find_all("style")
    for style_tag in style_tags:
        if style_tag.string and "prefers-reduced-motion" in style_tag.string:
            return True

    # Vérifier link rel=stylesheet pour prefers-reduced-motion (plus difficile sans parser le CSS externe)
    links = soup.find_all("link", rel="stylesheet")
    for link in links:
        href = link.get("href", "")
        if isinstance(href, str) and "reduced-motion" in href.lower():
            return True

    return len(controls) > 0


def _parse_animation_duration(duration_str: str) -> float | None:
    """Parse une durée CSS (ex: '2s', '500ms') et retourne la valeur en secondes."""
    if not duration_str:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*(ms|s)", duration_str)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "ms":
        return value / 1000
    return value


def _parse_animation_shorthand(animation_value: str) -> dict[str, str]:
    """Parse la propriété CSS raccourcie 'animation'."""
    result = {}
    if not animation_value or animation_value == "none":
        return result

    parts = animation_value.split()
    if not parts:
        return result

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
        is_duration = re.match(r"^\d+(?:\.\d+)?(ms|s)$", part)
        is_keyword = part in known_keywords or re.match(r"^steps?\(", part)
        if is_duration or is_keyword:
            remaining_parts.append(part)
        else:
            name_parts.append(part)

    if name_parts:
        result["animation-name"] = " ".join(name_parts)

    for part in remaining_parts:
        if re.match(r"^\d+(?:\.\d+)?(ms|s)$", part):
            if "animation-duration" not in result:
                result["animation-duration"] = part
            elif "animation-delay" not in result:
                result["animation-delay"] = part
        elif part == "infinite" or re.match(r"^\d+$", part):
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


def _find_auto_motion_candidates(soup: BeautifulSoup, context: AuditContext | None = None) -> list[dict]:
    """
    Trouve les éléments qui peuvent avoir un mouvement/clignotement déclenché automatiquement.
    """
    candidates = []

    # 1. Éléments média potentiellement animés
    media_tags = ["video", "img", "svg", "canvas", "embed", "object"]
    for tag_name in media_tags:
        elements = soup.find_all(tag_name)
        for i, elem in enumerate(elements):
            # Ignorer les barres de progression
            if _is_progress_element(elem):
                continue

            candidate = {
                "type": "media",
                "tag": tag_name,
                "index": i,
                "element": elem,
                "attributes": dict(elem.attrs),
                "size_pixels": _get_element_size(elem),
            }

            if tag_name == "img":
                candidate["is_animated"] = _is_animated_image(elem)
                candidate["src"] = elem.get("src", "")
                candidate["auto_trigger"] = candidate["is_animated"]  # GIF animé = auto
            elif _is_video_element(elem):
                candidate["is_video"] = True
                candidate["src"] = elem.get("src", "") or elem.get("data", "")
                # Vérifier autoplay
                autoplay = elem.get("autoplay")
                candidate["auto_trigger"] = autoplay is not None
            elif tag_name in ["svg", "canvas"]:
                candidate["potentially_animated"] = True
                candidate["auto_trigger"] = True  # Peut démarrer auto via SMIL/JS
            elif tag_name in ["embed", "object"]:
                candidate["src"] = elem.get("src", "") or elem.get("data", "")
                candidate["auto_trigger"] = True

            candidates.append(candidate)

    # 2. Animations CSS (règles + inline)
    css_rules: list[CSSRule] = []
    if context:
        css_rules = extract_css_from_context(context)

    # Styles inline
    for element in soup.find_all(style=True):
        style_attr = element.get("style")
        if isinstance(style_attr, str) and style_attr.strip():
            from accessi_code.analysis.css import _get_element_selector, _parse_inline_style

            properties = _parse_inline_style(style_attr)
            if properties:
                selector = _get_element_selector(soup, element)

                class InlineRule:
                    def __init__(self, selector, properties):
                        self.selector = selector
                        self.properties = properties

                css_rules.append(InlineRule(selector, properties))

    for rule in css_rules:
        has_animation = any(prop in rule.properties for prop in CSS_MOTION_PROPERTIES)
        has_motion_change = any(prop in rule.properties for prop in MOTION_CHANGE_PROPERTIES)

        if not (has_animation or has_motion_change):
            continue

        animation_name = rule.properties.get("animation-name", "")
        animation_duration = rule.properties.get("animation-duration", "")
        animation_iteration = rule.properties.get("animation-iteration-count", "")
        animation_play_state = rule.properties.get("animation-play-state", "")

        animation_shorthand = rule.properties.get("animation", "")
        if animation_shorthand and animation_shorthand != "none":
            parsed = _parse_animation_shorthand(animation_shorthand)
            if not animation_name and parsed.get("animation-name"):
                animation_name = parsed["animation-name"]
            if not animation_duration and parsed.get("animation-duration"):
                animation_duration = parsed["animation-duration"]
            if not animation_iteration and parsed.get("animation-iteration-count"):
                animation_iteration = parsed["animation-iteration-count"]
            if not animation_play_state and parsed.get("animation-play-state"):
                animation_play_state = parsed["animation-play-state"]

        # Détecter si c'est un mouvement ou clignotement
        is_motion_animation = False
        is_blink_animation = False
        if animation_name and animation_name != "none":
            name_lower = animation_name.lower()
            for kw in MOTION_ANIMATION_KEYWORDS:
                if kw in name_lower:
                    is_motion_animation = True
                    break
            for kw in BLINK_ANIMATION_KEYWORDS:
                if kw in name_lower:
                    is_blink_animation = True
                    break

        # Vérifier si l'animation démarre automatiquement (pas paused)
        auto_start = animation_play_state != "paused"

        if (has_animation or is_motion_animation or is_blink_animation) and auto_start:
            candidates.append(
                {
                    "type": "css_animation",
                    "selector": rule.selector,
                    "properties": rule.properties,
                    "source": getattr(rule, "source", "inline"),
                    "line_number": getattr(rule, "line_number", None),
                    "has_animation": has_animation,
                    "has_motion_change": has_motion_change,
                    "is_motion_animation": is_motion_animation,
                    "is_blink_animation": is_blink_animation,
                    "animation_name": animation_name,
                    "animation_duration": animation_duration,
                    "animation_iteration": animation_iteration,
                    "animation_play_state": animation_play_state,
                    "auto_trigger": True,
                }
            )

    # 3. @keyframes avec mouvement/clignotement
    style_tags = soup.find_all("style")
    for style_tag in style_tags:
        if not style_tag.string:
            continue

        css_text = style_tag.string
        keyframes_pattern = re.compile(r"@keyframes\s+([\w-]+)\s*\{([^}]+)\}", re.DOTALL | re.IGNORECASE)

        for match in keyframes_pattern.finditer(css_text):
            name = match.group(1).strip()
            content = match.group(2).strip()

            is_motion_name = any(kw in name.lower() for kw in MOTION_ANIMATION_KEYWORDS)
            is_blink_name = any(kw in name.lower() for kw in BLINK_ANIMATION_KEYWORDS)

            has_motion_change = False
            motion_properties = []
            for prop in MOTION_CHANGE_PROPERTIES:
                if re.search(rf"{prop}\s*:", content, re.IGNORECASE):
                    has_motion_change = True
                    motion_properties.append(prop)

            if is_motion_name or is_blink_name or has_motion_change:
                candidates.append(
                    {
                        "type": "keyframes",
                        "name": name,
                        "content": content[:500],
                        "is_motion_name": is_motion_name,
                        "is_blink_name": is_blink_name,
                        "has_motion_change": has_motion_change,
                        "motion_properties": motion_properties,
                        "auto_trigger": True,  # Les keyframes sont utilisées par des animations auto
                    }
                )

    # 4. JavaScript potentiellement source de mouvement auto
    scripts = soup.find_all("script")
    for i, script in enumerate(scripts):
        if not script.string:
            continue

        content = script.string
        matches = []

        # Initialiser motion_props_found avant la détection des timers
        motion_props_found = []

        # Vérifier présence de timer (setInterval, setTimeout, requestAnimationFrame)
        has_timer = False
        timer_patterns = [
            re.compile(r"setInterval\s*\(", re.IGNORECASE),
            re.compile(r"setTimeout\s*\(", re.IGNORECASE),
            re.compile(r"requestAnimationFrame\s*\(", re.IGNORECASE),
        ]
        for pattern in timer_patterns:
            if pattern.search(content):
                has_timer = True
                # Trouver la position pour le contexte
                match = pattern.search(content)
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                matches.append(
                    {
                        "pattern": "timer",
                        "match": match.group(),
                        "context": content[start:end],
                        "position": match.start(),
                    }
                )
                # Ajouter le type de timer détecté aux propriétés de mouvement
                if "requestAnimationFrame" in pattern.pattern:
                    motion_props_found.append("requestAnimationFrame")
                break

        # Vérifier présence de modification de propriétés de mouvement
        has_motion_style = False
        for prop in JS_STYLE_MOTION_PROPERTIES:
            # Chercher .style.property = ou element.style.property =
            prop_pattern = re.compile(rf"\.style\.{re.escape(prop)}\s*=", re.IGNORECASE)
            if prop_pattern.search(content):
                has_motion_style = True
                motion_props_found.append(prop)
                match = prop_pattern.search(content)
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                matches.append(
                    {
                        "pattern": f"style.{prop}",
                        "match": match.group(),
                        "context": content[start:end],
                        "position": match.start(),
                    }
                )

        # Aussi vérifier classList.toggle (peut déclencher mouvement/clignotement)
        if re.search(r"classList\.toggle\s*\(", content, re.IGNORECASE):
            has_motion_style = True
            motion_props_found.append("classList.toggle")
            match = re.search(r"classList\.toggle\s*\(", content, re.IGNORECASE)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 200)
            matches.append(
                {
                    "pattern": "classList.toggle",
                    "match": match.group(),
                    "context": content[start:end],
                    "position": match.start(),
                }
            )

        # Web Animation API
        if re.search(r"\.animate\s*\(", content, re.IGNORECASE):
            has_motion_style = True
            motion_props_found.append("animate()")
            match = re.search(r"\.animate\s*\(", content, re.IGNORECASE)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 200)
            matches.append(
                {
                    "pattern": "animate()",
                    "match": match.group(),
                    "context": content[start:end],
                    "position": match.start(),
                }
            )

        # IntersectionObserver
        if re.search(r"IntersectionObserver\s*\(", content, re.IGNORECASE):
            has_timer = True
            motion_props_found.append("IntersectionObserver")
            match = re.search(r"IntersectionObserver\s*\(", content, re.IGNORECASE)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 200)
            matches.append(
                {
                    "pattern": "IntersectionObserver",
                    "match": match.group(),
                    "context": content[start:end],
                    "position": match.start(),
                }
            )

        # Scroll manipulation
        if re.search(r"scroll(Top|Left)\s*=", content, re.IGNORECASE):
            has_motion_style = True
            motion_props_found.append("scrollTop/scrollLeft")
            match = re.search(r"scroll(Top|Left)\s*=", content, re.IGNORECASE)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 200)
            matches.append(
                {
                    "pattern": "scrollTop/scrollLeft",
                    "match": match.group(),
                    "context": content[start:end],
                    "position": match.start(),
                }
            )

        # scrollIntoView
        if re.search(r"scrollIntoView\s*\(", content, re.IGNORECASE):
            has_motion_style = True
            motion_props_found.append("scrollIntoView")
            match = re.search(r"scrollIntoView\s*\(", content, re.IGNORECASE)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 200)
            matches.append(
                {
                    "pattern": "scrollIntoView",
                    "match": match.group(),
                    "context": content[start:end],
                    "position": match.start(),
                }
            )

        # Un script est candidat s'il a un timer ET modifie des propriétés de mouvement
        # OU s'il a classList.toggle/animate/IntersectionObserver/requestAnimationFrame (qui impliquent mouvement)
        has_special_motion = (
            "classList.toggle" in motion_props_found
            or "animate()" in motion_props_found
            or "IntersectionObserver" in motion_props_found
            or "requestAnimationFrame" in motion_props_found
        )
        if (has_timer and has_motion_style) or has_special_motion:
            candidates.append(
                {
                    "type": "javascript",
                    "index": i,
                    "element": script,
                    "matches": matches,
                    "content_preview": content[:300],
                    "motion_properties": motion_props_found,
                    "auto_trigger": True,
                }
            )

    # 5. Marquee (déprécié mais encore utilisé)
    marquees = soup.find_all("marquee")
    for i, marquee in enumerate(marquees):
        candidates.append(
            {
                "type": "marquee",
                "index": i,
                "element": marquee,
                "attributes": dict(marquee.attrs),
                "auto_trigger": True,  # <marquee> démarre toujours automatiquement
            }
        )

    # Filtrer seulement ceux avec auto_trigger
    return [c for c in candidates if c.get("auto_trigger")]


def _check_user_controls(soup: BeautifulSoup, candidate: dict, is_blink: bool) -> dict:
    """
    Vérifie les mécanismes de contrôle utilisateur pour un candidat.
    Retourne un dict avec les contrôles trouvés.
    """
    if is_blink:
        control_keywords = [
            "arrêter le clignotement",
            "stop blinking",
            "pause clignotement",
            "masquer le clignotement",
            "hide blinking",
            "cacher clignotement",
            "afficher sans clignotement",
            "show without blinking",
            "version sans clignotement",
            "static version",
        ]
    else:
        control_keywords = [
            "arrêter le mouvement",
            "stop motion",
            "pause movement",
            "arrêter l'animation",
            "stop animation",
            "pause animation",
            "masquer le mouvement",
            "hide motion",
            "cacher animation",
            "afficher sans mouvement",
            "show without motion",
            "version sans animation",
            "version statique",
            "static version",
        ]

    has_stop_restart = _has_user_control_for_motion(soup, candidate.get("element"), control_keywords)
    has_hide_show = _has_user_control_for_motion(soup, candidate.get("element"), control_keywords)
    has_static_version = _has_user_control_for_motion(soup, candidate.get("element"), control_keywords)

    # Vérifier prefers-reduced-motion
    has_reduced_motion = False
    style_tags = soup.find_all("style")
    for style_tag in style_tags:
        if style_tag.string and "prefers-reduced-motion" in style_tag.string:
            has_reduced_motion = True
            break

    return {
        "has_stop_restart": has_stop_restart,
        "has_hide_show": has_hide_show,
        "has_static_version": has_static_version,
        "has_reduced_motion": has_reduced_motion,
        "has_any_control": has_stop_restart or has_hide_show or has_static_version or has_reduced_motion,
    }


class Test1381(RGAATest):
    """
    Test 13.8.1 : Dans chaque page web, chaque contenu en mouvement
    déclenché automatiquement vérifie-t-il une de ces conditions ?

    La durée du mouvement est inférieure ou égale à 5 secondes ;
    L'utilisateur peut arrêter et relancer le mouvement ;
    L'utilisateur peut afficher et masquer le contenu en mouvement ;
    L'utilisateur peut afficher la totalité de l'information sans le mouvement.
    """

    test_id = "13.8.1"
    criterion_id = "13.8"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    optional_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
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
                summary="Le DOM n'est pas disponible ; le test 13.8.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        candidates = _find_auto_motion_candidates(soup, context)

        # Filtrer pour ne garder que les mouvements (pas clignotement pur)
        motion_candidates = []
        for c in candidates:
            if c["type"] == "css_animation":
                is_motion = c.get("is_motion_animation") or c.get("has_motion_change")
                is_blink = c.get("is_blink_animation")

                # Aussi considérer comme mouvement potentiel si l'animation se répète (infinite ou count > 1)
                # et qu'elle n'est pas explicitement un clignotement
                if not is_motion and not is_blink:
                    iteration = c.get("animation_iteration", "")
                    if iteration == "infinite" or (iteration.isdigit() and int(iteration) > 1):
                        is_motion = True

                if is_motion and not is_blink:
                    motion_candidates.append(c)
            elif c["type"] == "keyframes":
                if c.get("is_motion_name") or c.get("has_motion_change"):
                    if not c.get("is_blink_name"):
                        motion_candidates.append(c)
            elif c["type"] == "media":
                # Vidéo, GIF, SVG, Canvas avec animation = mouvement potentiel
                if c.get("is_video") or c.get("is_animated") or c.get("potentially_animated"):
                    motion_candidates.append(c)
            elif c["type"] == "marquee":
                motion_candidates.append(c)
            elif c["type"] == "javascript":
                # JS qui bouge des éléments = mouvement
                motion_candidates.append(c)

        if not motion_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun contenu en mouvement déclenché automatiquement détecté.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for i, candidate in enumerate(motion_candidates):
            selector = self._get_candidate_selector(soup, candidate, i)
            ctype = candidate["type"]

            # Vérifier la durée si connue
            duration_seconds = None
            if ctype == "css_animation":
                duration_seconds = _parse_animation_duration(candidate.get("animation_duration", ""))
            elif ctype == "media" and candidate.get("is_video"):
                # Durée vidéo inconnue sans analyse
                pass

            # Vérifier les contrôles utilisateur
            controls = _check_user_controls(soup, candidate, is_blink=False)

            # Déterminer la conformité
            is_compliant = False
            compliance_reason = ""

            if duration_seconds is not None and duration_seconds <= MAX_AUTO_DURATION_SECONDS:
                is_compliant = True
                compliance_reason = f"duration_{duration_seconds}s_le_5s"
            elif controls["has_any_control"]:
                is_compliant = True
                if controls["has_stop_restart"]:
                    compliance_reason = "user_can_stop_restart"
                elif controls["has_hide_show"]:
                    compliance_reason = "user_can_hide_show"
                elif controls["has_static_version"]:
                    compliance_reason = "user_can_view_static"
                elif controls["has_reduced_motion"]:
                    compliance_reason = "prefers_reduced_motion"
            else:
                # Non conforme ou à vérifier
                if duration_seconds is not None and duration_seconds > MAX_AUTO_DURATION_SECONDS:
                    # Durée connue et > 5s sans contrôle -> FAIL
                    is_compliant = False
                    compliance_reason = f"duration_{duration_seconds}s_gt_5s_no_control"
                else:
                    # Durée inconnue ou pas de contrôle détecté -> NEEDS_REVIEW
                    is_compliant = None
                    compliance_reason = "needs_manual_verification"

            # Construire le message et recommandation
            if ctype == "css_animation":
                anim_name = candidate.get("animation_name", "sans nom")
                anim_dur = candidate.get("animation_duration", "inconnue")
                message = (
                    f"Animation CSS '{anim_name}' (durée: {anim_dur}) sur '{selector}' : mouvement automatique détecté."
                )
            elif ctype == "keyframes":
                kf_name = candidate.get("name", "sans nom")
                message = f"@keyframes '{kf_name}' utilisée pour un mouvement automatique."
            elif ctype == "media":
                tag = candidate.get("tag", "media")
                src = candidate.get("src", "")
                if candidate.get("is_video"):
                    media_type = "vidéo"
                elif candidate.get("is_animated"):
                    media_type = "image animée"
                else:
                    media_type = "élément"
                message = f"{media_type} {tag} détecté : {src}. Mouvement automatique possible."
            elif ctype == "marquee":
                message = "Balise <marquee> détectée : défilement automatique permanent."
            elif ctype == "javascript":
                match_count = len(candidate.get("matches", []))
                message = f"Script détecté avec {match_count} pattern(s) de mouvement automatique."
            else:
                message = f"Contenu en mouvement automatique détecté ({ctype})."

            if is_compliant is True:
                compliant_count += 1
                evidence = {
                    "type": ctype,
                    "duration_seconds": duration_seconds,
                    "controls": controls,
                    "condition_met": compliance_reason,
                }
                if ctype == "javascript" and candidate.get("motion_properties"):
                    evidence["motion_properties"] = candidate["motion_properties"]
                findings.append(
                    Finding(
                        element=selector,
                        message=message,
                        recommendation=f"Conforme au critère 13.8.1 ({compliance_reason}).",
                        evidence=evidence,
                    )
                )
            elif is_compliant is False:
                non_compliant_count += 1
                evidence = {
                    "type": ctype,
                    "duration_seconds": duration_seconds,
                    "controls": controls,
                    "condition_met": compliance_reason,
                }
                if ctype == "javascript" and candidate.get("motion_properties"):
                    evidence["motion_properties"] = candidate["motion_properties"]
                findings.append(
                    Finding(
                        element=selector,
                        message=message,
                        recommendation=(
                            f"Non conforme : durée {duration_seconds}s > {MAX_AUTO_DURATION_SECONDS}s "
                            "sans mécanisme de contrôle utilisateur détecté. "
                            "Ajouter : 1) bouton arrêt/relance ; 2) bouton masquer/afficher ; "
                            "3) version statique ; 4) respecter prefers-reduced-motion ; "
                            f"ou réduire la durée à ≤ {MAX_AUTO_DURATION_SECONDS}s."
                        ),
                        evidence=evidence,
                    )
                )
            else:
                needs_review_count += 1
                evidence = {
                    "type": ctype,
                    "duration_seconds": duration_seconds,
                    "controls": controls,
                    "condition_met": compliance_reason,
                    "needs_manual_check": True,
                    "checks_required": [
                        f"duration_le_{MAX_AUTO_DURATION_SECONDS}s",
                        "user_can_stop_restart_motion",
                        "user_can_hide_show_motion",
                        "user_can_view_static_version",
                        "not_focus_based_pause_only",
                        "not_progress_bar",
                    ],
                }
                if ctype == "javascript" and candidate.get("motion_properties"):
                    evidence["motion_properties"] = candidate["motion_properties"]
                findings.append(
                    Finding(
                        element=selector,
                        message=message,
                        recommendation=(
                            "Vérification manuelle requise pour le critère 13.8.1 : "
                            f"1) Durée du mouvement ≤ {MAX_AUTO_DURATION_SECONDS}s ? ; "
                            "2) L'utilisateur peut-il arrêter et relancer le mouvement ? ; "
                            "3) L'utilisateur peut-il masquer/afficher le contenu en mouvement ? ; "
                            "4) L'utilisateur peut-il accéder à l'information sans mouvement ? ; "
                            "Note : l'arrêt par prise de focus (hover/focus) N'EST PAS conforme. "
                            "Les barres de progression sont non applicables."
                        ),
                        evidence=evidence,
                    )
                )

        tested_elements = len(motion_candidates)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) en mouvement auto détecté(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) en mouvement auto détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) en mouvement auto détecté(s). "
                f"Tous sont conformes au critère 13.8.1."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "motion_candidates": len(motion_candidates),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    f"vérifier durée mouvement ≤ {MAX_AUTO_DURATION_SECONDS}s",
                    "vérifier présence bouton arrêt/relance mouvement",
                    "vérifier présence bouton masquer/afficher contenu en mouvement",
                    "vérifier version statique accessible",
                    "vérifier support prefers-reduced-motion",
                    "vérifier que l'arrêt n'est pas seulement au focus/hover",
                    "exclure les barres de progression (non applicable)",
                ],
            },
        )

    def _get_candidate_selector(self, soup: BeautifulSoup, candidate: dict, index: int) -> str:
        """Génère un sélecteur lisible pour un candidat."""
        element = candidate.get("element")
        ctype = candidate.get("type", "")

        if ctype == "css_animation":
            return candidate.get("selector", f"css-animation[index={index}]")
        elif ctype == "keyframes":
            return f"@keyframes {candidate.get('name', 'unknown')}"
        elif ctype == "marquee":
            if element is None:
                return f"marquee[index={index}]"
            element_id = element.get("id")
            if isinstance(element_id, str) and element_id:
                return f"#{element_id}"
            marquees = soup.find_all("marquee")
            if len(marquees) > 1:
                try:
                    return f"marquee[index={marquees.index(element)}]"
                except ValueError:
                    pass
            return f"marquee[index={index}]"
        elif element is None:
            return f"{ctype}[index={index}]"

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            return f"#{element_id}"

        classes = element.get("class", [])
        if isinstance(classes, list) and classes:
            tag = element.name or ctype
            return f"{tag}.{'.'.join(str(c) for c in classes[:2])}"

        tag = element.name or ctype
        same_tag = soup.find_all(tag)
        if len(same_tag) > 1:
            try:
                return f"{tag}[index={same_tag.index(element)}]"
            except ValueError:
                pass

        return f"{tag}[index={index}]"


class Test1382(RGAATest):
    """
    Test 13.8.2 : Dans chaque page web, chaque contenu clignotant
    déclenché automatiquement vérifie-t-il une de ces conditions ?

    La durée du clignotement est inférieure ou égale à 5 secondes ;
    L'utilisateur peut arrêter et relancer le clignotement ;
    L'utilisateur peut afficher et masquer le contenu clignotant ;
    L'utilisateur peut afficher la totalité de l'information sans le clignotement.
    """

    test_id = "13.8.2"
    criterion_id = "13.8"

    required_capabilities = frozenset(
        {
            Capability.DOM,
            Capability.HTML_SOURCE,
        }
    )

    optional_capabilities = frozenset(
        {
            Capability.COMPUTED_STYLES,
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
                summary="Le DOM n'est pas disponible ; le test 13.8.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        candidates = _find_auto_motion_candidates(soup, context)

        # Filtrer pour ne garder que le clignotement
        blink_candidates = []
        for c in candidates:
            if c["type"] == "css_animation":
                if c.get("is_blink_animation"):
                    blink_candidates.append(c)
                # Aussi détecter via opacity/filter changes rapides
                elif c.get("has_motion_change"):
                    # Vérifier si l'animation modifie opacity/filter de façon à clignoter
                    anim_name = c.get("animation_name", "").lower()
                    if any(kw in anim_name for kw in BLINK_ANIMATION_KEYWORDS):
                        blink_candidates.append(c)
            elif c["type"] == "keyframes":
                if c.get("is_blink_name") or c.get("has_motion_change"):
                    # Vérifier si keyframes modifie opacity/visibility/filter
                    motion_props = c.get("motion_properties", [])
                    blink_props = {"opacity", "visibility", "filter", "display"}
                    if any(p in blink_props for p in motion_props):
                        blink_candidates.append(c)
            elif c["type"] == "media":
                # Images animées peuvent clignoter
                if c.get("is_animated"):
                    blink_candidates.append(c)
            elif c["type"] == "javascript":
                # JS qui toggle opacity/visibility = clignotement
                blink_candidates.append(c)
            elif c["type"] == "marquee":
                # Marquee peut clignoter (alternance)
                pass  # Marquee est plutôt mouvement

        if not blink_candidates:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun contenu clignotant déclenché automatiquement détecté.",
                tested_elements=0,
                metadata={},
            )

        findings: list[Finding] = []
        compliant_count = 0
        non_compliant_count = 0
        needs_review_count = 0

        for i, candidate in enumerate(blink_candidates):
            selector = self._get_candidate_selector(soup, candidate, i)
            ctype = candidate["type"]

            # Vérifier la durée si connue
            duration_seconds = None
            if ctype == "css_animation":
                duration_seconds = _parse_animation_duration(candidate.get("animation_duration", ""))

            # Vérifier les contrôles utilisateur
            controls = _check_user_controls(soup, candidate, is_blink=True)

            # Déterminer la conformité
            is_compliant = False
            compliance_reason = ""

            if duration_seconds is not None and duration_seconds <= MAX_AUTO_DURATION_SECONDS:
                is_compliant = True
                compliance_reason = f"duration_{duration_seconds}s_le_5s"
            elif controls["has_any_control"]:
                is_compliant = True
                if controls["has_stop_restart"]:
                    compliance_reason = "user_can_stop_restart"
                elif controls["has_hide_show"]:
                    compliance_reason = "user_can_hide_show"
                elif controls["has_static_version"]:
                    compliance_reason = "user_can_view_static"
                elif controls["has_reduced_motion"]:
                    compliance_reason = "prefers_reduced_motion"
            else:
                if duration_seconds is not None and duration_seconds > MAX_AUTO_DURATION_SECONDS:
                    is_compliant = False
                    compliance_reason = f"duration_{duration_seconds}s_gt_5s_no_control"
                else:
                    is_compliant = None
                    compliance_reason = "needs_manual_verification"

            # Construire le message
            if ctype == "css_animation":
                anim_name = candidate.get("animation_name", "sans nom")
                anim_dur = candidate.get("animation_duration", "inconnue")
                message = (
                    f"Animation CSS '{anim_name}' (durée: {anim_dur}) sur '{selector}' : "
                    f"clignotement automatique détecté."
                )
            elif ctype == "keyframes":
                kf_name = candidate.get("name", "sans nom")
                message = f"@keyframes '{kf_name}' utilisée pour un clignotement automatique."
            elif ctype == "media":
                tag = candidate.get("tag", "media")
                src = candidate.get("src", "")
                message = f"Image animée {tag} détectée : {src}. Clignotement possible."
            elif ctype == "javascript":
                match_count = len(candidate.get("matches", []))
                message = f"Script détecté avec {match_count} pattern(s) de clignotement automatique."
            else:
                message = f"Contenu clignotant automatique détecté ({ctype})."

            if is_compliant is True:
                compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=message,
                        recommendation=f"Conforme au critère 13.8.2 ({compliance_reason}).",
                        evidence={
                            "type": ctype,
                            "duration_seconds": duration_seconds,
                            "controls": controls,
                            "condition_met": compliance_reason,
                        },
                    )
                )
            elif is_compliant is False:
                non_compliant_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=message,
                        recommendation=(
                            f"Non conforme : durée {duration_seconds}s > {MAX_AUTO_DURATION_SECONDS}s "
                            "sans mécanisme de contrôle utilisateur détecté. "
                            "Ajouter : 1) bouton arrêt/relance clignotement ; 2) bouton masquer/afficher ; "
                            "3) version sans clignotement ; 4) respecter prefers-reduced-motion ; "
                            f"ou réduire la durée à ≤ {MAX_AUTO_DURATION_SECONDS}s."
                        ),
                        evidence={
                            "type": ctype,
                            "duration_seconds": duration_seconds,
                            "controls": controls,
                            "condition_met": compliance_reason,
                        },
                    )
                )
            else:
                needs_review_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=message,
                        recommendation=(
                            "Vérification manuelle requise pour le critère 13.8.2 : "
                            f"1) Durée du clignotement ≤ {MAX_AUTO_DURATION_SECONDS}s ? ; "
                            "2) L'utilisateur peut-il arrêter et relancer le clignotement ? ; "
                            "3) L'utilisateur peut-il masquer/afficher le contenu clignotant ? ; "
                            "4) L'utilisateur peut-il accéder à l'information sans clignotement ? ; "
                            "Note : l'arrêt par prise de focus (hover/focus) N'EST PAS conforme."
                        ),
                        evidence={
                            "type": ctype,
                            "duration_seconds": duration_seconds,
                            "controls": controls,
                            "condition_met": compliance_reason,
                            "needs_manual_check": True,
                            "checks_required": [
                                f"duration_le_{MAX_AUTO_DURATION_SECONDS}s",
                                "user_can_stop_restart_blink",
                                "user_can_hide_show_blink",
                                "user_can_view_static_version",
                                "not_focus_based_pause_only",
                            ],
                        },
                    )
                )

        tested_elements = len(blink_candidates)

        if non_compliant_count > 0:
            status = TestStatus.FAIL
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) clignotant(s) auto détecté(s). "
                f"{non_compliant_count} non conforme(s), "
                f"{needs_review_count} à vérifier manuellement, "
                f"{compliant_count} conforme(s)."
            )
        elif needs_review_count > 0:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) clignotant(s) auto détecté(s). "
                f"{needs_review_count} nécessitent une vérification manuelle, "
                f"{compliant_count} conforme(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                f"Analyse terminée : {tested_elements} contenu(s) clignotant(s) auto détecté(s). "
                f"Tous sont conformes au critère 13.8.2."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=tested_elements,
            metadata={
                "blink_candidates": len(blink_candidates),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "needs_review_count": needs_review_count,
                "required_manual_checks": [
                    f"vérifier durée clignotement ≤ {MAX_AUTO_DURATION_SECONDS}s",
                    "vérifier présence bouton arrêt/relance clignotement",
                    "vérifier présence bouton masquer/afficher contenu clignotant",
                    "vérifier version sans clignotement accessible",
                    "vérifier support prefers-reduced-motion",
                    "vérifier que l'arrêt n'est pas seulement au focus/hover",
                ],
            },
        )

    def _get_candidate_selector(self, soup: BeautifulSoup, candidate: dict, index: int) -> str:
        """Génère un sélecteur lisible pour un candidat (réutilise la méthode de Test1381)."""
        # Code dupliqué pour éviter l'héritage complexe - on réutilise la logique
        element = candidate.get("element")
        ctype = candidate.get("type", "")

        if ctype == "css_animation":
            return candidate.get("selector", f"css-animation[index={index}]")
        elif ctype == "keyframes":
            return f"@keyframes {candidate.get('name', 'unknown')}"
        elif element is None:
            return f"{ctype}[index={index}]"

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            return f"#{element_id}"

        classes = element.get("class", [])
        if isinstance(classes, list) and classes:
            tag = element.name or ctype
            return f"{tag}.{'.'.join(str(c) for c in classes[:2])}"

        tag = element.name or ctype
        same_tag = soup.find_all(tag)
        if len(same_tag) > 1:
            try:
                return f"{tag}[index={same_tag.index(element)}]"
            except ValueError:
                pass

        return f"{tag}[index={index}]"

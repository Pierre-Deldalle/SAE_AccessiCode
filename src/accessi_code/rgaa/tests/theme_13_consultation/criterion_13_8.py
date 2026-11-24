"""
RGAA 4.1.2 — critère 13.8 : dans chaque page web, chaque contenu en mouvement
ou clignotant est-il contrôlable par l'utilisateur ?

Un contenu déclenché automatiquement est conforme si sa durée est de 5 secondes
au plus, ou si l'utilisateur peut l'arrêter et le relancer, l'afficher et le
masquer, ou afficher toute l'information sans le mouvement.

- 13.8.1 (mouvement) : animations CSS de position, ``<marquee>``, vidéos lues
  automatiquement, images animées, carrousels animés par script ;
- 13.8.2 (clignotement) : animations CSS répétées de la luminosité et
  minuteurs qui font apparaître et disparaître un élément.

Règles :
- durée totale connue ≤ 5 s → PASS ; vidéo avec l'attribut controls → PASS ;
- ``<marquee>`` ou vidéo automatique en boucle sans contrôles, alors qu'aucun
  bouton pause / arrêt n'existe dans la page → FAIL ;
- autres cas : un contrôle peut exister ou le contenu peut être exempté
  (indicateur de chargement) → NEEDS_REVIEW, avec les boutons trouvés.
Les animations lancées au survol ou au focus ne sont pas automatiques : ignorées.
"""

from __future__ import annotations

import math
import re
from html import escape
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.animations import (
    LIGHT_PROPERTIES,
    MOTION_DURATION_LIMIT,
    MOTION_PROPERTIES,
    CSSAnimation,
    css_animations,
    is_animated_image_file,
    local_file,
    pause_controls,
)
from accessi_code.analysis.components import component_identifier, normalize
from accessi_code.analysis.location import opening_tag
from accessi_code.analysis.scripts import page_scripts, timer_calls
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_7 import animation_place

CAROUSEL_SCRIPT = re.compile(
    r"slide|carousel|carrousel|slider|scroll(?:Left|By|To)|translate|\.style\s*\.\s*(?:left|marginLeft|transform)",
    re.IGNORECASE,
)
BLINK_SCRIPT = re.compile(
    r"\.style\s*\.\s*(?:visibility|display|opacity)\s*=|classList\s*\.\s*toggle\s*\(|\.hidden\s*=\s*!", re.IGNORECASE
)


def _recommendation(kind: str) -> str:
    return (
        f"Limiter le {kind} à 5 secondes, ou proposer un bouton pour l'arrêter et le relancer "
        "(ou pour masquer le contenu)."
    )


def marquee_example(marquee: Tag) -> str:
    """Texte défilant remplacé par un paragraphe fixe, avec le vrai texte."""
    text = escape(normalize(marquee.get_text(" ", strip=True))[:80], quote=False)
    return f"Exemple : {opening_tag(marquee)}{text}</marquee> → <p>{text}</p>"


def video_example(video: Tag) -> str:
    """Attribut controls ajouté à la vidéo."""
    return f"Exemple : {opening_tag(video)} → {opening_tag(video, controls='')}"


def iterations_example(animation: CSSAnimation) -> str:
    """Nombre de répétitions qui limite l'animation à 5 secondes ; vide si un seul cycle dépasse déjà 5 secondes."""
    if animation.duration_s <= 0:
        return ""
    count = math.floor((MOTION_DURATION_LIMIT - animation.delay_s) / animation.duration_s + 1e-9)
    if count < 1:
        return ""
    before = "infinite" if math.isinf(animation.iterations) else f"{animation.iterations:g}"
    return (
        f" Exemple pour limiter l'animation à 5 secondes : {animation_place(animation.selector)}, "
        f"animation-iteration-count: {before} → animation-iteration-count: {count}"
    )


def _review(
    element: str,
    message: str,
    controls: list[str],
    kind: str,
    location: dict[str, Any],
    example: str = "",
    **evidence: Any,
) -> Outcome:
    found = (
        f" Bouton(s) trouvé(s) : {', '.join(controls[:5])} — vérifier qu'ils arrêtent ce contenu."
        if controls
        else " Aucun bouton pause ou arrêt trouvé : vérifier s'il s'agit d'une exception (indicateur de chargement)."
    )
    return make_outcome(
        TestStatus.NEEDS_REVIEW,
        element,
        message + found,
        f"{_recommendation(kind)} {example}".strip(),
        **location,
        pause_controls=controls,
        **evidence,
    )


def _animation_outcome(animation: CSSAnimation, controls: list[str], kind: str) -> Outcome:
    if animation.total_s <= MOTION_DURATION_LIMIT:
        return make_outcome(TestStatus.PASS)
    duration = "en continu" if math.isinf(animation.total_s) else f"pendant {animation.total_s:g} secondes"
    return _review(
        animation.selector,
        f"L'animation CSS « {animation.keyframes.name} » produit un {kind} automatique {duration}.",
        controls,
        kind,
        animation.location,
        iterations_example(animation).strip(),
        keyframes=animation.keyframes.name,
        total_s=None if math.isinf(animation.total_s) else animation.total_s,
    )


class MotionTest(RGAATest):
    criterion_id = "13.8"
    required_capabilities = frozenset({Capability.DOM})

    def _soup(self, context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        return context.dom


class Test1381(MotionTest):
    """13.8.1 : contenus en mouvement déclenchés automatiquement."""

    test_id = "13.8.1"
    empty = "Aucun contenu en mouvement déclenché automatiquement."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._soup(context)
        controls = pause_controls(soup)
        outcomes: list[Outcome] = []

        for index, marquee in enumerate(soup.find_all("marquee")):
            if controls:
                outcomes.append(
                    _review(
                        component_identifier(marquee, index),
                        "Le texte défile en continu (balise marquee).",
                        controls,
                        "mouvement",
                        {"node": marquee},
                        marquee_example(marquee),
                    )
                )
            else:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        component_identifier(marquee, index),
                        "Le texte défile en continu (balise marquee) et aucun bouton ne permet de l'arrêter.",
                        f"{_recommendation('mouvement')} {marquee_example(marquee)}",
                        node=marquee,
                    )
                )

        for index, video in enumerate(soup.find_all("video")):
            if not video.has_attr("autoplay"):
                continue
            if video.has_attr("controls"):
                outcomes.append(make_outcome(TestStatus.PASS))
            elif video.has_attr("loop") and not controls:
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        component_identifier(video, index),
                        "La vidéo se lance automatiquement en boucle, sans contrôles ni bouton pour l'arrêter.",
                        "Ajouter l'attribut controls ou un bouton pause, ou supprimer la lecture automatique. "
                        + video_example(video),
                        node=video,
                    )
                )
            else:
                outcomes.append(
                    _review(
                        component_identifier(video, index),
                        "La vidéo se lance automatiquement sans l'attribut controls.",
                        controls,
                        "mouvement",
                        {"node": video},
                        video_example(video),
                    )
                )

        for index, image in enumerate(soup.find_all("img")):
            path = local_file(context, str(image.get("src") or ""))
            if path is not None and is_animated_image_file(path):
                outcomes.append(
                    _review(
                        component_identifier(image, index),
                        "L'image est animée : sa durée d'animation est inconnue.",
                        controls,
                        "mouvement",
                        {"node": image},
                    )
                )

        for animation in css_animations(context):
            if animation.animates(MOTION_PROPERTIES) and animation.duration_s > 0:
                outcomes.append(_animation_outcome(animation, controls, "mouvement"))

        for call in timer_calls(page_scripts(context)):
            if call.kind == "setInterval" and CAROUSEL_SCRIPT.search(call.callback):
                outcomes.append(
                    _review(
                        f"{call.source.label} ({call.kind})",
                        "Un script fait défiler un contenu automatiquement (carrousel).",
                        controls,
                        "mouvement",
                        call.source.location(call.position),
                        code=call.source.snippet(call.position),
                    )
                )

        return build_result(self, outcomes, empty_summary=self.empty, noun="contenu(s) en mouvement")


class Test1382(MotionTest):
    """13.8.2 : contenus clignotants déclenchés automatiquement."""

    test_id = "13.8.2"
    empty = "Aucun contenu clignotant déclenché automatiquement."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._soup(context)
        controls = pause_controls(soup)
        outcomes: list[Outcome] = []

        for animation in css_animations(context):
            repeated = animation.iterations > 1 or animation.keyframes.changes(LIGHT_PROPERTIES) >= 2
            if animation.animates(LIGHT_PROPERTIES) and repeated and animation.duration_s > 0:
                outcomes.append(_animation_outcome(animation, controls, "clignotement"))

        for call in timer_calls(page_scripts(context)):
            if call.kind == "setInterval" and BLINK_SCRIPT.search(call.callback):
                outcomes.append(
                    _review(
                        f"{call.source.label} ({call.kind})",
                        "Un script fait apparaître et disparaître un élément de façon répétée.",
                        controls,
                        "clignotement",
                        call.source.location(call.position),
                        code=call.source.snippet(call.position),
                    )
                )

        return build_result(self, outcomes, empty_summary=self.empty, noun="contenu(s) clignotant(s)")

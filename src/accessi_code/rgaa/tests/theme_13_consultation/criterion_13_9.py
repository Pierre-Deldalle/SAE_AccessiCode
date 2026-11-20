"""
RGAA 4.1.2 — critère 13.9 : dans chaque page web, le contenu proposé est-il
consultable quelle que soit l'orientation de l'écran (portrait ou paysage) ?

Le critère concerne toutes les pages. Blocages repérés :
- ``screen.orientation.lock()`` (ou ``lockOrientation``) → FAIL, sauf si
  l'orientation est essentielle (à signaler par l'auditeur) ;
- règle ``@media (orientation: …)`` qui masque ou fait pivoter toute la page
  (html, body, main) → FAIL ;
- règle ``@media (orientation: …)`` qui masque une partie du contenu, ou message
  invitant à tourner l'appareil → NEEDS_REVIEW (le contenu peut rester
  disponible autrement) ;
- aucun blocage → PASS.
Les règles qui ne font qu'adapter la mise en page (largeurs, colonnes) sont conformes.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from accessi_code.analysis.animations import block_end, css_texts
from accessi_code.analysis.components import normalize
from accessi_code.analysis.scripts import page_scripts
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

LOCK = re.compile(r"orientation\s*\.\s*lock\s*\(|\b(?:moz|ms)?[lL]ockOrientation\s*\(")
ORIENTATION_MEDIA = re.compile(r"@media[^{]*orientation\s*:\s*(portrait|landscape)[^{]*\{", re.IGNORECASE)
GLOBAL_SELECTOR = re.compile(r"^(?:html|body|main|\[role=['\"]?main['\"]?\]|\*|#app|#root)$", re.IGNORECASE)
HIDES = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)
ROTATES = re.compile(r"rotate\(\s*-?(?:90|270)deg\s*\)", re.IGNORECASE)
ROTATE_MESSAGE = re.compile(
    r"\b(?:tourn(?:ez|er)|pivot(?:ez|er)|fai(?:tes|re) pivoter|bascul(?:ez|er))\b"
    r"[^.]{0,40}\b(?:appareil|écran|téléphone|tablette|mobile)\b"
    r"|\b(?:mode|orientation|format)\s+(?:paysage|portrait)\s+(?:requis|obligatoire|uniquement)"
    r"|\brotate your (?:device|phone|screen)\b",
    re.IGNORECASE,
)
SUMMARY_OK = "Aucun blocage de l'orientation de l'écran repéré."
ORIENTATIONS = {"portrait": "portrait", "landscape": "paysage"}


def orientation_rules(context: AuditContext) -> list[tuple[str, str, str, str]]:
    """(source, orientation, sélecteur, déclarations) des règles placées dans @media (orientation: …)."""
    rules: list[tuple[str, str, str, str]] = []
    for label, text in css_texts(context):
        for media in ORIENTATION_MEDIA.finditer(text):
            body = text[media.end() : block_end(text, media.end() - 1)]
            for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
                for selector in rule.group(1).split(","):
                    rules.append((label, media.group(1).lower(), selector.strip(), rule.group(2)))
    return rules


class Test1391(RGAATest):
    test_id = "13.9.1"
    criterion_id = "13.9"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = context.dom
        if not isinstance(soup, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")

        outcomes: list[Outcome] = []
        for source in page_scripts(context):
            for match in LOCK.finditer(source.masked):
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        source.label,
                        "Le script verrouille l'orientation de l'écran : le contenu n'est consultable que dans une "
                        "orientation (non conforme sauf si l'orientation est essentielle, par exemple un jeu).",
                        "Retirer le verrouillage de l'orientation et adapter la page aux deux orientations.",
                        code=source.snippet(match.start()),
                    )
                )

        for label, orientation, selector, declarations in orientation_rules(context):
            name = ORIENTATIONS[orientation]
            global_rule = bool(GLOBAL_SELECTOR.match(selector))
            if global_rule and (HIDES.search(declarations) or ROTATES.search(declarations)):
                effect = "masque" if HIDES.search(declarations) else "fait pivoter"
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        f"{label} : @media (orientation: {orientation}) {selector}",
                        f"En mode {name}, la feuille de style {effect} toute la page.",
                        "Afficher le contenu dans les deux orientations en adaptant la mise en page.",
                        declarations=normalize(declarations),
                    )
                )
            elif HIDES.search(declarations):
                outcomes.append(
                    make_outcome(
                        TestStatus.NEEDS_REVIEW,
                        f"{label} : @media (orientation: {orientation}) {selector}",
                        f"En mode {name}, la feuille de style masque « {selector} » : vérifier que ce contenu reste "
                        "disponible autrement dans cette orientation.",
                        "Vérifier que tout le contenu et toutes les fonctionnalités restent disponibles en portrait "
                        "et en paysage.",
                        declarations=normalize(declarations),
                    )
                )

        text = normalize((soup.body or soup).get_text(" ", strip=True))
        message = ROTATE_MESSAGE.search(text)
        if message:
            outcomes.append(
                make_outcome(
                    TestStatus.NEEDS_REVIEW,
                    "body",
                    f"La page invite à changer l'orientation de l'écran (« {message.group(0)} ») : vérifier que le "
                    "contenu reste consultable dans les deux orientations.",
                    "Adapter la page aux deux orientations plutôt que demander de tourner l'appareil.",
                )
            )

        if not outcomes:
            outcomes.append(make_outcome(TestStatus.PASS))
        result = build_result(self, outcomes, empty_summary=SUMMARY_OK, noun="élément(s)")
        if result.status is TestStatus.PASS:
            result.summary = SUMMARY_OK
        return result

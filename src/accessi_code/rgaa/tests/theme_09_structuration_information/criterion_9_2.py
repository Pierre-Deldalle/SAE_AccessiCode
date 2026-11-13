"""
RGAA 4.1.2 — critère 9.2 : dans chaque page web, la structure du document
est-elle cohérente (hors cas particuliers) ?

9.2.1 (doctype HTML5 uniquement) :
- la zone d'en-tête est structurée avec <header> ;
- les zones de navigation principales et secondaires avec <nav>, et <nav>
  n'est utilisé que pour ces zones ;
- la zone de contenu principal avec <main>, un seul <main> visible ;
- la zone de pied de page avec <footer>.

Chaque condition ne s'applique que si la zone existe : une zone repérée
(role="banner", classe « header »…) sans la balise attendue est non conforme ;
une page sans zone d'en-tête n'est pas en défaut pour cette condition.
Toute page a un contenu principal : l'absence de <main> est non conforme.
Masquer un <main> par CSS seul ne suffit pas (note technique) : seul
l'attribut hidden est pris en compte.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.page import is_html5_doctype
from accessi_code.analysis.structure import is_hidden
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import build_result, make_outcome, not_applicable

_ZONE_MARKERS = {
    "header": (re.compile(r"\b(header|en-?tete|entête|banniere|bannière|masthead)\b", re.IGNORECASE), "banner"),
    "nav": (re.compile(r"\b(nav|navigation|menu|navbar)\b", re.IGNORECASE), "navigation"),
    "footer": (re.compile(r"\b(footer|pied(-de-page)?|bas-de-page)\b", re.IGNORECASE), "contentinfo"),
}
_ZONE_LABELS = {"header": "d'en-tête", "nav": "de navigation", "footer": "de pied de page"}


def _markers(tag: Tag) -> str:
    return " ".join([str(tag.get("id") or ""), " ".join(tag.get("class") or [])])


def unstructured_zones(soup: BeautifulSoup, zone: str) -> list[Tag]:
    """Zones repérées (rôle ARIA ou classe / id évocateurs) qui n'utilisent pas la balise attendue."""
    pattern, role = _ZONE_MARKERS[zone]
    zones: list[Tag] = []
    for tag in soup.find_all(["div", "section", "aside", "ul", "span"]):
        if is_hidden(tag) or tag.find_parent(zone) or tag.find(zone):
            continue
        has_role = str(tag.get("role") or "").strip().lower() == role
        if not has_role and not pattern.search(_markers(tag)):
            continue
        if zone == "nav" and len(tag.find_all("a", href=True)) < 2:
            continue  # Un « menu » sans liens n'est pas une zone de navigation.
        if any(tag in other.descendants for other in zones):
            continue
        zones.append(tag)
    # On ne garde que les zones de plus haut niveau.
    return [tag for tag in zones if not any(other is not tag and tag in other.descendants for other in zones)]


class Test921(RGAATest):
    """9.2.1 : structure du document (header, nav, main, footer)."""

    test_id = "9.2.1"
    criterion_id = "9.2"
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError("Le test 9.2.1 nécessite un DOM.")
        if not is_html5_doctype(context.doctype):
            return not_applicable(self, "Le doctype n'est pas HTML5 : le test 9.2.1 ne s'applique pas.")

        soup = context.dom
        outcomes = []

        for zone in ("header", "nav", "footer"):
            label = _ZONE_LABELS[zone]
            if any(not is_hidden(tag) for tag in soup.find_all(zone)):
                outcomes.append(make_outcome(TestStatus.PASS))
            for tag in unstructured_zones(soup, zone):
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        f"{tag.name}{'#' + tag['id'] if tag.get('id') else ''}",
                        f"La zone {label} n'est pas structurée avec la balise <{zone}>.",
                        f"Utiliser la balise <{zone}> pour la zone {label}.",
                        markers=_markers(tag),
                    )
                )

        for index, nav in enumerate(soup.find_all("nav")):
            if not nav.find_all("a", href=True):
                outcomes.append(
                    make_outcome(
                        TestStatus.FAIL,
                        f"nav#{nav['id']}" if nav.get("id") else f"nav[index={index}]",
                        "La balise <nav> ne contient aucun lien : elle ne structure pas une zone de navigation.",
                        "Réserver <nav> aux zones de navigation principales et secondaires.",
                    )
                )

        visible_mains = [main for main in soup.find_all("main") if not main.has_attr("hidden")]
        if not visible_mains:
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    "main",
                    "La zone de contenu principal n'est pas structurée avec la balise <main>.",
                    "Encadrer le contenu principal de la page avec une balise <main>.",
                )
            )
        elif len(visible_mains) > 1:
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    "main",
                    f"{len(visible_mains)} balises <main> sont visibles ; une seule doit l'être.",
                    "Conserver un seul <main> visible et ajouter l'attribut hidden aux autres.",
                )
            )
        else:
            outcomes.append(make_outcome(TestStatus.PASS))

        return build_result(self, outcomes, empty_summary="Aucune zone de structure analysée.", noun="zone(s)")

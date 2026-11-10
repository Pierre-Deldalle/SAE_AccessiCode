from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.page import (
    is_html5_doctype,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


def _is_visible_element(element: Tag) -> bool:
    """
    Vérifie si un élément est visible (pas caché par attribut hidden ou style display:none).
    """
    # Vérifier l'attribut hidden
    if element.has_attr('hidden'):
        return False

    # Vérifier le style display:none (simplifié)
    style = element.get('style', '')
    if isinstance(style, str) and 'display:none' in style.replace(' ', '').lower():
        return False

    return True


def _get_nav_navigation_elements(soup: BeautifulSoup) -> list[Tag]:
    """
    Retourne tous les éléments <nav> du document.
    """
    return soup.find_all('nav')


def _is_nav_used_for_navigation(nav_element: Tag) -> bool:
    """
    Vérifie si un élément <nav> est utilisé pour structurer une zone de navigation.
    Cette vérification est basée sur la présence de liens ou de listes typiques de navigation.
    """
    # Chercher des éléments typiquement présents dans une navigation
    has_links = bool(nav_element.find_all('a', href=True))
    has_lists = bool(nav_element.find_all(['ul', 'ol']))
    has_list_items = bool(nav_element.find_all('li'))

    # Si il y a des liens, c'est probablement une navigation
    if has_links:
        return True

    # Si il y a des listes avec des éléments, c'est probablement une navigation
    if has_lists and has_list_items:
        return True

    # Par défaut, on considère que c'est une navigation (approche permissive)
    # Dans une implémentation plus stricte, on pourrait retourner False ici
    return True


class Test921(RGAATest):
    test_id = "9.2.1"
    criterion_id = "9.2"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if not isinstance(
            context.dom,
            BeautifulSoup,
        ):
            raise ValueError("Le test 9.2.1 nécessite un DOM.")

        # Vérifier le doctype - si ce n'est pas HTML5, le test n'est pas applicable
        if not is_html5_doctype(context.doctype):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Le doctype n'est pas HTML5, le test 9.2.1 n'est pas applicable.",
            )

        soup = context.dom

        findings: list[Finding] = []

        # 1. Vérifier la présence d'un élément <header>
        header_elements = soup.find_all('header')
        visible_header_elements = [h for h in header_elements if _is_visible_element(h)]

        if not visible_header_elements:
            findings.append(
                Finding(
                    element="header",
                    message="Aucun élément <header> visible détecté pour structurer l'en-tête de la page.",
                    recommendation=("Ajouter un élément <header> visible pour structurer l'en-tête de la page."),
                )
            )

        # 2. Vérifier les éléments <nav>
        nav_elements = _get_nav_navigation_elements(soup)
        visible_nav_elements = [n for n in nav_elements if _is_visible_element(n)]

        if not visible_nav_elements:
            findings.append(
                Finding(
                    element="nav",
                    message="Aucun élément <nav> visible détecté pour structurer les zones de navigation.",
                    recommendation=("Ajouter des éléments <nav> visibles pour structurer les zones de navigation principales et/ou secondaires."),
                )
            )
        else:
            # Vérifier que chaque <nav> est bien utilisé pour une zone de navigation
            for index, nav_element in enumerate(visible_nav_elements):
                if not _is_nav_used_for_navigation(nav_element):
                    element_id = nav_element.get('id')
                    element_str = f"nav#{element_id}" if (isinstance(element_id, str) and element_id.strip()) else f"nav[index={index}]"
                    findings.append(
                        Finding(
                            element=element_str,
                            message=(
                                "L'élément <nav> est utilisé mais ne semble pas structurer une zone de navigation principale "
                                "ou secondaire."
                            ),
                            recommendation=(
                                "Utiliser l'élément <nav> uniquement pour structurer les zones de navigation principales "
                                "et/ou secondaires, ou modifier son utilisation si ce n'est pas une zone de navigation."
                            ),
                        )
                    )

        # 3. Vérifier la présence d'un élément <main> visible unique
        main_elements = soup.find_all('main')
        visible_main_elements = [m for m in main_elements if _is_visible_element(m)]

        if not visible_main_elements:
            findings.append(
                Finding(
                    element="main",
                    message="Aucun élément <main> visible détecté pour structurer le contenu principal de la page.",
                    recommendation=("Ajouter un élément <main> visible pour structurer le contenu principal de la page."),
                )
            )
        elif len(visible_main_elements) > 1:
            findings.append(
                Finding(
                    element="main",
                    message=f"{len(visible_main_elements)} éléments <main> visibles détectés. Il ne devrait y avoir qu'un seul élément <main> visible par document.",
                    recommendation="Conserver un seul élément <main> visible et masquer les autres avec l'attribut 'hidden' ou en les rendant invisibles via CSS.",
                )
            )

        # 4. Vérifier la présence d'un élément <footer>
        footer_elements = soup.find_all('footer')
        visible_footer_elements = [f for f in footer_elements if _is_visible_element(f)]

        if not visible_footer_elements:
            findings.append(
                Finding(
                    element="footer",
                    message="Aucun élément <footer> visible détecté pour structurer le pied de page de la page.",
                    recommendation=("Ajouter un élément <footer> visible pour structurer le pied de page de la page."),
                )
            )

        # Déterminer le statut final
        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"Analyse de la structure du document : "
                f"{len([h for h in soup.find_all('header') if _is_visible_element(h)])} header(s) visible(s), "
                f"{len([n for n in soup.find_all('nav') if _is_visible_element(n)])} nav(s) visible(s), "
                f"{len([m for m in soup.find_all('main') if _is_visible_element(m)])} main(s) visible(s), "
                f"{len([f for f in soup.find_all('footer') if _is_visible_element(f)])} footer(s) visible(s)."
            ),
            findings=findings,
            tested_elements=len([h for h in soup.find_all('header') if _is_visible_element(h)]) +
                        len([n for n in soup.find_all('nav') if _is_visible_element(n)]) +
                        len([m for m in soup.find_all('main') if _is_visible_element(m)]) +
                        len([f for f in soup.find_all('footer') if _is_visible_element(f)]),
            metadata={
                "visible_headers": len([h for h in soup.find_all('header') if _is_visible_element(h)]),
                "visible_navs": len([n for n in soup.find_all('nav') if _is_visible_element(n)]),
                "visible_mains": len([m for m in soup.find_all('main') if _is_visible_element(m)]),
                "visible_footers": len([f for f in soup.find_all('footer') if _is_visible_element(f)]),
                "doctype_html5": is_html5_doctype(context.doctype),
            },
        )
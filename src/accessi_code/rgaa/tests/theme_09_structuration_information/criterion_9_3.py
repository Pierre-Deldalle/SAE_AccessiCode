from __future__ import annotations

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import (
    Finding,
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest


def _is_visible_element(element) -> bool:
    """
    Vérifie si un élément est visible (pas caché par attribut hidden ou style display:none).
    """
    # Vérifier l'attribut hidden
    if hasattr(element, 'has_attr') and element.has_attr('hidden'):
        return False

    # Vérifier le style display:none (simplifié)
    style = getattr(element, 'get', lambda x, y: '')('style', '')
    if isinstance(style, str) and 'display:none' in style.replace(' ', '').lower():
        return False

    return True


class Test931(RGAATest):
    """
    Test 9.3.1 : Dans chaque page web, les informations regroupées visuellement sous forme de
    liste non ordonnée vérifient-elles une de ces conditions ?
    - La liste utilise les balises HTML <ul> et <li> ;
    - La liste utilise les attributs WAI-ARIA role="list" et role="listitem".
    """
    test_id = "9.3.1"
    criterion_id = "9.3"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: object | None = None,
    ) -> TestResult:
        if not hasattr(context, 'dom'):
            raise ValueError("Le test 9.3.1 nécessite un DOM.")

        soup = context.dom
        findings: list[Finding] = []

        # Trouver toutes les listes non ordonnées visuelles (éléments qui ressemblent à des listes non ordonnées)
        # On cherche des éléments qui contiennent des items de liste ou des éléments avec des rôles de liste
        unordered_list_containers = []

        # Recherche des <ul> visibles
        ul_elements = soup.find_all('ul')
        visible_ul_elements = [ul for ul in ul_elements if _is_visible_element(ul)]
        unordered_list_containers.extend(visible_ul_elements)

        # Recherche des éléments avec role="list" qui pourraient être des listes non ordonnées
        list_role_elements = soup.find_all(attrs={"role": "list"})
        visible_list_role_elements = [elem for elem in list_role_elements if _is_visible_element(elem)]
        unordered_list_containers.extend(visible_list_role_elements)

        # Pour chaque conteneur de liste non ordonnée, vérifier sa structure
        for container in unordered_list_containers:
            # Vérifier si c'est un <ul> avec des <li>
            if container.name == 'ul':
                # Si il y a des enfants non-<li> qui ne sont pas juste du texte, c'est un problème
                # Mais on sera tolérant : on vérifie surtout qu'il y a au moins un <li> si c'est censé être une liste
                li_elements = container.find_all('li', recursive=False)  # Seulement les enfants directs
                if not li_elements:
                    element_id = (
                        f"ul#{container.get('id')}"
                        if container.get('id')
                        else f"ul[{unordered_list_containers.index(container)}]"
                    )
                    findings.append(
                        Finding(
                            element=element_id,
                            message="L'élément <ul> ne contient aucun élément <li> direct.",
                            recommendation=(
                                "Chaque élément <ul> doit contenir un ou plusieurs éléments <li> "
                                "pour constituer une liste non ordonnée valide."
                            ),
                        )
                    )

            # Vérifier si c'est un élément avec role="list"
            elif container.get('role') == 'list':
                # Vérifier que les enfants ont role="listitem"
                listitem_elements = container.find_all(attrs={"role": "listitem"}, recursive=False)
                if not listitem_elements:
                    element_id = (
                        f'[role="list"]#{container.get("id")}'
                        if container.get('id')
                        else f'[role="list"][{unordered_list_containers.index(container)}]'
                    )
                    findings.append(
                        Finding(
                            element=element_id,
                            message="L'élément avec role='list' ne contient aucun élément avec role='listitem'.",
                            recommendation=(
                                "Chaque élément avec role='list' doit contenir un ou plusieurs éléments "
                                "avec role='listitem' pour constituer une liste non ordonnée valide."
                            ),
                        )
                    )

        # Déterminer le statut final
        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        visible_uls = len([ul for ul in soup.find_all('ul') if _is_visible_element(ul)])
        visible_list_roles = len([elem for elem in soup.find_all(attrs={'role': 'list'}) if _is_visible_element(elem)])

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"Analyse des listes non ordonnées : "
                f"{visible_uls} <ul> visible(s), "
                f"{visible_list_roles} élément(s) avec role='list' visible(s)."
            ),
            findings=findings,
            tested_elements=visible_uls + visible_list_roles,
        )


class Test932(RGAATest):
    """
    Test 9.3.2 : Dans chaque page web, les informations regroupées visuellement sous forme de
    liste ordonnée vérifient-elles une de ces conditions ?
    - La liste utilise les balises HTML <ol> et <li> ;
    - La liste utilise les attributs WAI-ARIA role="list" et role="listitem".
    """
    test_id = "9.3.2"
    criterion_id = "9.3"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: object | None = None,
    ) -> TestResult:
        if not hasattr(context, 'dom'):
            raise ValueError("Le test 9.3.2 nécessite un DOM.")

        soup = context.dom
        findings: list[Finding] = []

        # Trouver toutes les listes ordonnées visuelles
        ordered_list_containers = []

        # Recherche des <ol> visibles
        ol_elements = soup.find_all('ol')
        visible_ol_elements = [ol for ol in ol_elements if _is_visible_element(ol)]
        ordered_list_containers.extend(visible_ol_elements)

        # Recherche des éléments avec role="list" qui pourraient être des listes ordonnées
        # Note : On ne peut pas distinguer visuellement une liste ordonnée d'une non ordonnée avec seulement role="list"
        # Donc on vérifie tous les éléments role="list" pour les deux types de listes
        list_role_elements = soup.find_all(attrs={"role": "list"})
        visible_list_role_elements = [elem for elem in list_role_elements if _is_visible_element(elem)]
        ordered_list_containers.extend(visible_list_role_elements)

        # Pour chaque conteneur de liste ordonnée, vérifier sa structure
        for container in ordered_list_containers:
            # Vérifier si c'est un <ol> avec des <li>
            if container.name == 'ol':
                # Si il y a des enfants non-<li> qui ne sont pas juste du texte, c'est un problème
                li_elements = container.find_all('li', recursive=False)  # Seulement les enfants directs
                if not li_elements:
                    element_id = (
                        f"ol#{container.get('id')}"
                        if container.get('id')
                        else f"ol[{ordered_list_containers.index(container)}]"
                    )
                    findings.append(
                        Finding(
                            element=element_id,
                            message="L'élément <ol> ne contient aucun élément <li> direct.",
                            recommendation=(
                                "Chaque élément <ol> doit contenir un ou plusieurs éléments <li> "
                                "pour constituer une liste ordonnée valide."
                            ),
                        )
                    )

            # Vérifier si c'est un élément avec role="list"
            elif container.get('role') == 'list':
                # Vérifier que les enfants ont role="listitem"
                listitem_elements = container.find_all(attrs={"role": "listitem"}, recursive=False)
                if not listitem_elements:
                    element_id = (
                        f'[role="list"]#{container.get("id")}'
                        if container.get('id')
                        else f'[role="list"][{ordered_list_containers.index(container)}]'
                    )
                    findings.append(
                        Finding(
                            element=element_id,
                            message="L'élément avec role='list' ne contient aucun élément avec role='listitem'.",
                            recommendation=(
                                "Chaque élément avec role='list' doit contenir un ou plusieurs éléments "
                                "avec role='listitem' pour constituer une liste ordonnée valide."
                            ),
                        )
                    )

        # Déterminer le statut final
        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        visible_ols = len([ol for ol in soup.find_all('ol') if _is_visible_element(ol)])
        visible_list_roles = len([elem for elem in soup.find_all(attrs={'role': 'list'}) if _is_visible_element(elem)])

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"Analyse des listes ordonnées : "
                f"{visible_ols} <ol> visible(s), "
                f"{visible_list_roles} élément(s) avec role='list' visible(s)."
            ),
            findings=findings,
            tested_elements=visible_ols + visible_list_roles,
        )


class Test933(RGAATest):
    """
    Test 9.3.3 : Dans chaque page web, les informations regroupées sous forme de liste de description
    utilisent-elles les balises <dl> et <dt>/<dd> ?
    """
    test_id = "9.3.3"
    criterion_id = "9.3"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: object | None = None,
    ) -> TestResult:
        if not hasattr(context, 'dom'):
            raise ValueError("Le test 9.3.3 nécessite un DOM.")

        soup = context.dom
        findings: list[Finding] = []

        # Trouver toutes les listes de description visuelles (<dl> visibles)
        dl_elements = soup.find_all('dl')
        visible_dl_elements = [dl for dl in dl_elements if _is_visible_element(dl)]

        # Pour chaque <dl>, vérifier qu'il contient des <dt> ou <dd>
        # Une liste de description peut être vide (pas de dt/dd) mais reste valide
        for dl in visible_dl_elements:
            # Trouver les éléments dt et dd directs
            dt_elements = dl.find_all('dt', recursive=False)
            dd_elements = dl.find_all('dd', recursive=False)

            # Une liste de description doit avoir au moins un dt ou un dd pour être considérée comme valide
            # Une liste vide (<dl></dl>) n'est pas une violation en soi
            if not dt_elements and not dd_elements and str(dl).strip() != "<dl></dl>":
                findings.append(
                    Finding(
                        element=f"dl#{dl.get('id')}" if dl.get('id') else f"dl[{visible_dl_elements.index(dl)}]",
                        message="L'élément <dl> ne contient aucun élément <dt> ou <dd> direct.",
                        recommendation=(
                            "Chaque élément <dl> doit contenir un ou plusieurs éléments <dt> et/ou <dd> "
                            "pour constituer une liste de description valide."
                        ),
                    )
                )

        # Déterminer le statut final
        if findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        visible_dls = len([dl for dl in soup.find_all('dl') if _is_visible_element(dl)])

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"Analyse des listes de description : "
                f"{visible_dls} <dl> visible(s)."
            ),
            findings=findings,
            tested_elements=visible_dls,
        )

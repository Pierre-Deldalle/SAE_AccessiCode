from __future__ import annotations

from typing import Any
from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


class Test831(RGAATest):
    """Test 8.3.1 - Présence de l'indication de langue par défaut."""

    test_id = "8.3.1"
    criterion_id = "8.3"

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
        """
        Exécute le test 8.3.1 : présence de l'indication de langue par défaut.

        Vérifie que :
        Soit l'indication de langue est donnée sur l'élément html (attribut lang et/ou xml:lang)
        Soit l'indication de langue est donnée sur chaque élément de texte ou sur l'un de ses parents
        """
        # Utiliser le DOM directement depuis le contexte
        if not isinstance(context.dom, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.ERROR,
                summary="Le DOM n'est pas disponible ou n'est pas un objet BeautifulSoup.",
                tested_elements=0,
            )

        soup = context.dom
        html_element = soup.find('html')

        if not html_element:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.FAIL,
                summary="Aucun élément html trouvé dans le document.",
                tested_elements=0,
            )

        # Vérifier la présence de l'attribut lang et/ou xml:lang sur l'élément html
        lang_attr = html_element.get('lang')
        xml_lang_attr = html_element.get('xml:lang')

        # Déterminer le type de document pour appliquer les règles appropriées
        # Pour simplifier, on considère que si l'un des attributs est présent, c'est OK pour la première condition
        if lang_attr or xml_lang_attr:
            # Au moins un des attributs est présent sur l'élément html
            lang_value = lang_attr if lang_attr else xml_lang_attr
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary=f"Langue déclarée sur l'élément html : {'lang' if lang_attr else 'xml:lang'}='{lang_value}'",
                tested_elements=1,
            )

        # Si pas de déclaration sur l'élément html, vérifier chaque élément de texte
        # On considère comme élément de texte ceux qui contiennent du texte visible
        # On exclut le contenu de head, script, style, etc. qui ne sont pas du contenu perceptible
        text_elements = soup.find_all(string=True)
        # Filtrer pour ne garder que les nœuds de texte qui sont dans des éléments perceptibles
        # et qui ne sont pas vides après suppression des espaces blancs
        meaningful_text_elements = []
        for text_node in text_elements:
            parent_name = text_node.parent.name
            # Exclure les éléments qui ne contiennent pas de contenu perceptible
            if parent_name not in ['script', 'style', 'meta', 'link', 'noscript', 'head', 'title']:
                # Vérifier si le texte n'est pas juste des espaces blancs
                if text_node.strip():
                    meaningful_text_elements.append(text_node)

        if not meaningful_text_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucun élément de texte significatif trouvé dans le document.",
                tested_elements=0,
            )

        # Vérifier que chaque élément de texte a une indication de langue sur lui-même ou un parent
        elements_without_lang = 0
        checked_elements = 0

        for text_node in meaningful_text_elements:
            checked_elements += 1
            # Vérifier le nœud de texte lui-même (pas d'attribut lang sur les nœuds de texte)
            # Puis vérifier ses parents
            parent = text_node.parent
            has_lang_indication = False

            # Remonter dans l'arbre jusqu'à l'élément html pour vérifier la présence de lang ou xml:lang
            while parent and parent.name != 'html':
                if parent.get('lang') or parent.get('xml:lang'):
                    has_lang_indication = True
                    break
                parent = parent.parent

            # Vérifier aussi l'élément html lui-même
            if parent and parent.name == 'html':
                if parent.get('lang') or parent.get('xml:lang'):
                    has_lang_indication = True

            if not has_lang_indication:
                elements_without_lang += 1

        if elements_without_lang == 0:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary=f"Tous les {checked_elements} éléments de texte ont une indication de langue sur eux-mêmes ou un parent.",
                tested_elements=checked_elements,
            )
        else:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.FAIL,
                summary=f"Parmi {checked_elements} éléments de texte vérifiés, {elements_without_lang} n'ont pas d'indication de langue sur eux-mêmes ou un parent.",
                tested_elements=checked_elements,
            )
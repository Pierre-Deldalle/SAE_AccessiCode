from __future__ import annotations

from bs4 import Tag

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


class Test941(RGAATest):
    """
    Test 9.4.1 : Dans chaque page web, chaque citation courte utilise-t-elle une balise <q> ?
    """
    test_id = "9.4.1"
    criterion_id = "9.4"

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
            raise ValueError("Le test 9.4.1 nécessite un DOM.")

        soup = context.dom
        findings: list[Finding] = []

        # Trouver toutes les citations courtes potentielles dans le texte
        # On recherche du texte qui pourrait être une citation courte
        # Pour simplifier, on va chercher tous les éléments texte et appliquer une heuristique
        # Une approche plus précise nécessiterait de l'IA pour détecter les citations courtes
        # Mais on peut au moins vérifier que les balises <q> existantes sont bien utilisées

        # Vérifier que toutes les balises <q> sont bien utilisées (contiennent du texte)
        q_elements = soup.find_all('q')
        visible_q_elements = [q for q in q_elements if _is_visible_element(q)]

        for index, q_element in enumerate(visible_q_elements):
            # Vérifier que la balise <q> contient du texte
            q_text = q_element.get_text(strip=True)
            if not q_text:
                element_id = (
                    f"q#{q_element.get('id')}"
                    if q_element.get('id')
                    else f"q[{visible_q_elements.index(q_element)}]"
                )
                findings.append(
                    Finding(
                        element=element_id,
                        message="La balise <q> est vide.",
                        recommendation=(
                            "La balise <q> doit contenir le texte de la citation courte."
                        ),
                    )
                )

        # Note : Déterminer de manière déterministe quel texte devrait être une citation courte
        # nécessite une compréhension sémantique du contenu qui dépasse les capacités d'analyse
        # statique simple. Ce test se concentre donc sur la validation de l'utilisation correcte
        # des balises <q> lorsqu'elles sont présentes.
        # Pour une détection complète des citations courtes manquantes, une analyse IA serait nécessaire.

        # Déterminer le statut final
        if not visible_q_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune balise <q> détectée.",
                tested_elements=0,
            )
        elif findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"Analyse des balises <q> : "
                f"{len(visible_q_elements)} balise(s) <q> visible(s) détectée(s)."
            ),
            findings=findings,
            tested_elements=len(visible_q_elements),
            metadata={
                "total_q_tags": len(visible_q_elements),
                "empty_q_tags": len([f for f in findings if "La balise <q> est vide." in f.message]),
            },
        )


class Test942(RGAATest):
    """
    Test 9.4.2 : Dans chaque page web, chaque bloc de citation utilise-t-il une balise <blockquote> ?
    """
    test_id = "9.4.2"
    criterion_id = "9.4"

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
            raise ValueError("Le test 9.4.2 nécessite un DOM.")

        soup = context.dom
        findings: list[Finding] = []

        # Trouver toutes les balises <blockquote>
        blockquote_elements = soup.find_all('blockquote')
        visible_blockquote_elements = [bq for bq in blockquote_elements if _is_visible_element(bq)]

        for index, blockquote_element in enumerate(visible_blockquote_elements):
            # Vérifier que la balise <blockquote> contient du texte
            blockquote_text = blockquote_element.get_text(strip=True)
            if not blockquote_text:
                element_id = (
                    f"blockquote#{blockquote_element.get('id')}"
                    if blockquote_element.get('id')
                    else f"blockquote[{visible_blockquote_elements.index(blockquote_element)}]"
                )
                findings.append(
                    Finding(
                        element=element_id,
                        message="La balise <blockquote> est vide.",
                        recommendation=(
                            "La balise <blockquote> doit contenir le texte de la citation longue."
                        ),
                    )
                )

            # Vérifier que la balise <blockquote> contient bien du contenu de citation
            # On peut faire quelques vérifications basiques
            # Une balise <blockquote> devrait idéalement contenir soit du texte, soit des éléments blocs
            children = list(blockquote_element.children)
            non_whitespace_children = [
                child for child in children
                if not (isinstance(child, str) and child.strip() == "")
            ]

            if not non_whitespace_children:
                element_id = (
                    f"blockquote#{blockquote_element.get('id')}"
                    if blockquote_element.get('id')
                    else f"blockquote[{visible_blockquote_elements.index(blockquote_element)}]"
                )
                findings.append(
                    Finding(
                        element=element_id,
                        message="La balise <blockquote> ne contient aucun contenu.",
                        recommendation=(
                            "La balise <blockquote> doit contenir le texte de la citation longue "
                            "ou des éléments blocs représentant la citation."
                        ),
                    )
                )

        # Note : Déterminer de manière déterministe quel texte devrait être une citation longue
        # nécessite une compréhension sémantique du contenu qui dépasse les capacités d'analyse
        # statique simple. Ce test se concentre donc sur la validation de l'utilisation correcte
        # des balises <blockquote> lorsqu'elles sont présentes.
        # Pour une détection complète des citations longues manquantes, une analyse IA serait nécessaire.

        # Déterminer le statut final
        if not visible_blockquote_elements:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_APPLICABLE,
                summary="Aucune balise <blockquote> détectée.",
                tested_elements=0,
            )
        elif findings:
            status = TestStatus.FAIL
        else:
            status = TestStatus.PASS

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=(
                f"Analyse des balises <blockquote> : "
                f"{len(visible_blockquote_elements)} balise(s) <blockquote> visible(s) détectée(s)."
            ),
            findings=findings,
            tested_elements=len(visible_blockquote_elements),
            metadata={
                "total_blockquote_tags": len(visible_blockquote_elements),
                "empty_blockquote_tags": len(
                    [f for f in findings if "La balise <blockquote> est vide." in f.message]
                ),
                "blockquote_without_content": len(
                    [f for f in findings if "La balise <blockquote> ne contient aucun contenu." in f.message]
                ),
            },
        )

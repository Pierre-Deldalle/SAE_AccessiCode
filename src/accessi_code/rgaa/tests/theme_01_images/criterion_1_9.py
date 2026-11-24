"""
RGAA 4.1.2 — critère 1.9 : chaque légende d'image est-elle, si nécessaire,
correctement reliée à l'image correspondante ?

Image placée dans une <figure> avec <figcaption> : les conditions sont
vérifiées dans le DOM (role="figure" ou "group", aria-label identique à la
légende). Image suivie ou précédée d'un texte qui ressemble à une légende sans
être reliée par figure / figcaption : l'IA juge s'il s'agit bien d'une légende.
"""

from __future__ import annotations

import re
from html import escape

from bs4 import Tag

from accessi_code.ai.schemas import StructureCandidate, StructureCandidateAnalysis
from accessi_code.analysis.image_elements import ImageElement
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.ai_decision import analysis_evidence, get_analyzer, status_from_verdict
from accessi_code.rgaa.tests.theme_01_images._common import (
    Evaluation,
    ImageTest,
    Judgement,
    Outcome,
    attribute_example,
    html_example,
    outcome,
    unresolved,
)

RECOMMENDATION = (
    'Placer l\'image et sa légende dans <figure role="figure" aria-label="texte de la légende">, '
    "la légende dans <figcaption>."
)

_CAPTION_TAGS = {"p", "span", "div", "small", "em", "cite"}
_CAPTION_CLASS = re.compile(r"legend|légende|caption|credit|crédit|figure", re.IGNORECASE)
_CAPTION_TEXT = re.compile(
    r"^\s*(figure|fig\.|photo|illustration|image|schéma|graphique|source|crédit|credit|©)", re.IGNORECASE
)
_CAPTION_MAX_LENGTH = 250


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _caption_anchor(element: ImageElement) -> Tag:
    # Image seule dans son paragraphe : la légende est à côté du paragraphe.
    parent = element.tag.parent
    if isinstance(parent, Tag) and parent.name in {"p", "div", "a"} and not parent.get_text(strip=True):
        return parent
    return element.tag


def caption_candidate(element: ImageElement) -> Tag | None:
    """Texte adjacent qui ressemble à une légende, hors figure / figcaption."""
    if element.figure is not None:
        return None
    anchor = _caption_anchor(element)
    for sibling in (anchor.find_next_sibling(), anchor.find_previous_sibling()):
        if not isinstance(sibling, Tag) or sibling.name not in _CAPTION_TAGS:
            continue
        text = sibling.get_text(" ", strip=True)
        if not text or len(text) > _CAPTION_MAX_LENGTH:
            continue
        markers = " ".join([str(sibling.get("class") or ""), str(sibling.get("id") or "")])
        if _CAPTION_CLASS.search(markers) or _CAPTION_TEXT.search(text):
            return sibling
    return None


class _CaptionTest(ImageTest):
    """Légende d'image reliée à son image."""

    criterion_id = "1.9"
    empty_summary = "Aucune image légendée."

    def in_scope(self, element: ImageElement) -> bool:
        return element.has_caption or caption_candidate(element) is not None

    async def evaluate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        if element.has_caption:
            return self._check_figure(element)
        return await self._check_candidate(element, evaluation)

    def _check_figure(self, element: ImageElement) -> Outcome:
        figure, caption = element.figure, element.figcaption
        assert figure is not None and caption is not None

        problems = []
        role = str(figure.get("role") or "").strip().lower()
        if role not in {"figure", "group"}:
            problems.append('la balise <figure> n\'a pas role="figure" ou role="group"')
        caption_text = caption.get_text(" ", strip=True)
        label = str(figure.get("aria-label") or "")
        if _normalize(label) != _normalize(caption_text):
            problems.append("l'attribut aria-label de <figure> n'est pas identique à la légende")

        if not problems:
            return outcome(TestStatus.PASS)
        return outcome(
            TestStatus.FAIL,
            element,
            "La légende n'est pas correctement reliée à l'image : " + " ; ".join(problems) + ".",
            attribute_example(
                'Donner à <figure> le rôle "figure" ou "group" et copier la légende dans aria-label.',
                figure,
                {"role": role if role in {"figure", "group"} else "figure", "aria-label": caption_text},
            ),
            caption=caption_text[:200],
            aria_label=label[:200],
        )

    async def _check_candidate(self, element: ImageElement, evaluation: Evaluation) -> Outcome:
        candidate = caption_candidate(element)
        assert candidate is not None
        text = candidate.get_text(" ", strip=True)

        verified = evaluation.evidence(element, "is_caption")
        if verified is False:
            return outcome(TestStatus.NOT_APPLICABLE)
        if verified is True:
            return self._unlinked(element, candidate, text, source="evidence")

        analyzer = get_analyzer(evaluation.services, "structure_analyzer")
        if analyzer is None:
            return unresolved(
                element,
                Judgement(None, "unavailable"),
                "Un texte adjacent ressemble à une légende non reliée.",
                RECOMMENDATION,
            )
        if not evaluation.budget.take():
            return unresolved(element, Judgement(None, "budget"), "", RECOMMENDATION)

        evaluation.ai_calls += 1
        try:
            results = await analyzer.classify_candidates(
                "caption",
                [
                    StructureCandidate(
                        text=text,
                        element_html=f"{element.html[:500]}\n{str(candidate)[:500]}",
                        context=element.context_text,
                    )
                ],
            )
            analysis = results[0]
            if not isinstance(analysis, StructureCandidateAnalysis):
                raise TypeError("StructureCandidateAnalysis attendu.")
        except Exception as error:
            return unresolved(
                element, Judgement(None, "error", error=f"{type(error).__name__}: {error}"), "", RECOMMENDATION
            )

        status = status_from_verdict(
            analysis.should_be_marked,
            analysis.confidence,
            when_true=TestStatus.FAIL,
            when_false=TestStatus.NOT_APPLICABLE,
        )
        if status is TestStatus.NOT_APPLICABLE:
            return outcome(TestStatus.NOT_APPLICABLE)
        if status is TestStatus.FAIL:
            return self._unlinked(element, candidate, text, analysis=analysis_evidence(analysis))
        return outcome(
            TestStatus.NEEDS_REVIEW,
            element,
            f"Le texte adjacent « {text[:100]} » pourrait être une légende non reliée. {analysis.explanation}".strip(),
            RECOMMENDATION,
            analysis=analysis_evidence(analysis),
        )

    @staticmethod
    def _unlinked(element: ImageElement, candidate: Tag, text: str, **evidence) -> Outcome:
        anchor = _caption_anchor(element)
        caption_first = candidate is anchor.find_previous_sibling()
        before = f"{candidate} {anchor}" if caption_first else f"{anchor} {candidate}"
        caption = f"<figcaption>{candidate.decode_contents()}</figcaption>"
        body = f"{caption}{anchor}" if caption_first else f"{anchor}{caption}"
        corrected = f'<figure role="figure" aria-label="{escape(text)}">{body}</figure>'
        return outcome(
            TestStatus.FAIL,
            element,
            f"La légende « {text[:100]} » n'est pas reliée à l'image par <figure> et <figcaption>.",
            html_example(
                "Relier la légende avec <figure> et <figcaption>.",
                before,
                corrected,
            ),
            **evidence,
        )


class Test191(_CaptionTest):
    """1.9.1 : image (img, input type="image" ou role="img") pourvue d'une légende."""

    test_id = "1.9.1"
    kinds = ("img", "input", "role_img")


class Test192(_CaptionTest):
    """1.9.2 : image objet (object) pourvue d'une légende."""

    test_id = "1.9.2"
    kinds = ("object",)


class Test193(_CaptionTest):
    """1.9.3 : image embarquée (embed) pourvue d'une légende."""

    test_id = "1.9.3"
    kinds = ("embed",)


class Test194(_CaptionTest):
    """1.9.4 : image vectorielle (svg) pourvue d'une légende."""

    test_id = "1.9.4"
    kinds = ("svg",)


class Test195(_CaptionTest):
    """1.9.5 : image bitmap (canvas) pourvue d'une légende."""

    test_id = "1.9.5"
    kinds = ("canvas",)

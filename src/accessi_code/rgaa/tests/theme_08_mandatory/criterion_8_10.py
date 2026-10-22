from __future__ import annotations

from typing import Any
import re

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest


def _field(value: Any, name: str, default: Any = None) -> Any:
    """Lit un champ de résultat IA, sous forme d'objet ou de dictionnaire."""
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _summary(value: Any, fallback: str) -> str:
    explanation = _field(value, "explanation")
    if isinstance(explanation, str) and explanation.strip():
        return explanation
    return fallback


def _metadata(value: Any) -> dict[str, Any]:
    metadata = _field(value, "metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _convert_findings(raw_findings: Any) -> list[Finding]:
    """Convertit les observations IA en objets Finding du projet."""
    if not isinstance(raw_findings, (list, tuple)):
        raise TypeError("Le champ findings doit être une liste.")

    converted: list[Finding] = []
    for raw in raw_findings:
        if isinstance(raw, Finding):
            converted.append(raw)
            continue

        element = _field(raw, "element", "unknown")
        message = _field(raw, "message", "")
        recommendation = _field(raw, "recommendation")
        evidence = _field(raw, "evidence", {})

        if not isinstance(element, str) or not isinstance(message, str):
            raise TypeError("Les champs element et message doivent être textuels.")
        if not isinstance(recommendation, str):
            recommendation = None
        if not isinstance(evidence, dict):
            evidence = {}

        converted.append(
            Finding(
                element=element,
                message=message,
                recommendation=recommendation,
                evidence=evidence,
            )
        )
    return converted


class _TextDirectionTest(RGAATest):
    """Comportement commun aux deux vérifications du critère 8.10."""

    required_capabilities = frozenset({Capability.DOM})
    analyzer_attribute: str
    analyzer_method: str
    count_attribute: str
    failure_attribute: str
    success_summary: str
    failure_summary: str
    error_summary: str

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        if getattr(context, "dom", None) is None:
            return self._result(TestStatus.ERROR, "Le DOM n'est pas disponible.")

        
        if self.test_id == "8.10.1":
            rtl_languages = {"ar", "he", "fa", "ur", "ps"}
            rtl_pattern = re.compile(
                r"[\u0590-\u05FF\u0600-\u06FF"
                r"\u0750-\u077F\u08A0-\u08FF]"
            )

            rtl_candidates = []
            missing_direction = []

            for element in context.dom.find_all(True):
                lang = str(
                    element.get("lang", "")
                ).strip().lower().split("-")[0]

                if lang not in rtl_languages:
                    continue

                text = element.get_text(" ", strip=True)

                if not rtl_pattern.search(text):
                    continue

                rtl_candidates.append(element)

                # Un dir placé sur un ancêtre peut suffire.
                has_direction = any(
                    ancestor.has_attr("dir")
                    for ancestor in [element, *element.parents]
                    if getattr(ancestor, "attrs", None) is not None
                )

                if not has_direction:
                    missing_direction.append(element)

            if missing_direction:
                findings = []

                for element in missing_direction:
                    text = element.get_text(" ", strip=True)

                    findings.append(
                        Finding(
                            element=(
                                f'{element.name}'
                                f'[lang="{element.get("lang")}"]'
                            ),
                            message=(
                                "Ce passage contient du texte RTL "
                                "sans indication explicite de direction "
                                "sur l'élément ou ses ancêtres. "
                                f"Texte : « {text[:100]} »."
                            ),
                            recommendation=(
                                'Vérifier le changement de direction '
                                'et ajouter dir="rtl" sur le passage '
                                "si nécessaire."
                            ),
                            evidence={
                                "lang": element.get("lang"),
                                "text": text[:150],
                                "dir": None,
                            },
                        )
                    )

                return self._result(
                    TestStatus.NEEDS_REVIEW,
                    (
                        f"{len(missing_direction)} passage(s) RTL "
                        "sans direction explicite détecté(s). "
                        "Vérifier si ces changements de sens "
                        "de lecture nécessitent un attribut dir."
                    ),
                    tested_elements=len(rtl_candidates),
                    findings=findings,
                    metadata={
                        "validation": "dom",
                        "rtl_candidates": len(rtl_candidates),
                        "missing_direction": len(missing_direction),
                    },
                )

        if self.test_id == "8.10.2":
            direction_elements = [
                element
                for element in context.dom.find_all(True)
                if element.name != "html"
                and element.has_attr("dir")
            ]

            if not direction_elements:
                return self._result(
                    TestStatus.NOT_APPLICABLE,
                    "Aucun attribut dir sur un passage interne "
                    "du document n'est à vérifier.",
                )

        analyzer = (
            getattr(services, self.analyzer_attribute, None)
            if services is not None
            else None
        )
        if analyzer is None:
            return self._result(
                TestStatus.NEEDS_REVIEW,
                "Service d'analyse de la direction du texte non disponible : "
                "vérification manuelle nécessaire.",
            )

        try:
            method = getattr(analyzer, self.analyzer_method)
            analysis = await method(
                context.dom,
                getattr(context, "html_source", None),
            )
            if analysis is None:
                raise TypeError("L'analyseur n'a retourné aucun résultat.")

            confidence = _field(analysis, "confidence")
            count = _field(analysis, self.count_attribute)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise TypeError(f"Compteur IA invalide : {self.count_attribute}.")

            # Une conclusion de faible confiance ne doit jamais produire PASS/FAIL.
            if confidence not in ("high", "medium"):
                return self._result(
                    TestStatus.NEEDS_REVIEW,
                    _summary(
                        analysis,
                        "L'analyse automatique n'est pas suffisamment fiable.",
                    ),
                    metadata=_metadata(analysis),
                )

            failure = _field(analysis, self.failure_attribute)
            if failure is None or (
                self.failure_attribute == "has_errors"
                and not isinstance(failure, bool)
            ) or (
                self.failure_attribute == "missing_dir_count"
                and (
                    not isinstance(failure, int)
                    or isinstance(failure, bool)
                    or failure < 0
                )
            ):
                return self._result(
                    TestStatus.NEEDS_REVIEW,
                    "L'analyse ne permet pas de conclure sur ce test.",
                    metadata=_metadata(analysis),
                )

            
            has_failure = (
                failure if isinstance(failure, bool) else failure > 0
            )

            if has_failure:
                findings = _convert_findings(
                    _field(analysis, "findings", [])
                )

                valid_findings = [
                    finding
                    for finding in findings
                    if isinstance(finding.element, str)
                    and finding.element.strip()
                    and finding.element.strip().lower() != "unknown"
                    and isinstance(finding.message, str)
                    and finding.message.strip()
                    and isinstance(finding.recommendation, str)
                    and finding.recommendation.strip()
                ]

                if not findings or len(valid_findings) != len(findings):
                    return self._result(
                        TestStatus.NEEDS_REVIEW,
                        (
                            "Une anomalie de direction du texte a été "
                            "signalée, mais les éléments concernés "
                            "et les corrections ne sont pas "
                            "suffisamment détaillés."
                        ),
                        tested_elements=count,
                        findings=valid_findings,
                        metadata=_metadata(analysis),
                    )

                details = " ".join(
                    f"{finding.element} : {finding.message} "
                    f"Correction : {finding.recommendation}"
                    for finding in valid_findings
                )

                return self._result(
                    TestStatus.FAIL,
                    (
                        f"{len(valid_findings)} anomalie(s) "
                        f"de direction détectée(s). {details}"
                    ),
                    tested_elements=count,
                    findings=valid_findings,
                    metadata=_metadata(analysis),
                )

            if count == 0:
                return self._result(
                    TestStatus.NOT_APPLICABLE,
                    "Aucun élément concerné par ce test n'a été détecté.",
                    metadata=_metadata(analysis),
                )

            return self._result(
                TestStatus.PASS,
                self.success_summary,
                tested_elements=count,
                metadata=_metadata(analysis),
            )

        
        except ValueError as error:
            return self._result(
                TestStatus.NEEDS_REVIEW,
                "La réponse de l'IA est incomplète ou invalide. "
                "Vérification manuelle de la direction du texte nécessaire.",
                metadata={"analysis_error": str(error)},
            )

        except Exception as error:
            return self._result(
                TestStatus.ERROR,
                f"{self.error_summary} : {error}",
                metadata={"error": str(error)},
            )

    def _result(
        self,
        status: TestStatus,
        summary: str,
        *,
        tested_elements: int = 0,
        findings: list[Finding] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TestResult:
        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            tested_elements=tested_elements,
            findings=findings if findings is not None else [],
            metadata=metadata if metadata is not None else {},
        )


class Test8101(_TextDirectionTest):
    """8.10.1 : présence de dir sur les passages de sens de lecture différent."""

    test_id = "8.10.1"
    criterion_id = "8.10"
    analyzer_attribute = "text_direction_analyzer"
    analyzer_method = "analyze_text_direction_presence"
    count_attribute = "total_rtl_segments_checked"
    failure_attribute = "missing_dir_count"
    success_summary = "Tous les segments RTL concernés possèdent un attribut dir."
    failure_summary = "Des segments RTL concernés n'ont pas d'attribut dir."
    error_summary = "L'analyse de la présence de l'attribut dir a échoué"


class Test8102(_TextDirectionTest):
    """8.10.2 : validité et pertinence des attributs dir."""

    test_id = "8.10.2"
    criterion_id = "8.10"
    analyzer_attribute = "text_direction_validity_analyzer"
    analyzer_method = "analyze_text_direction_validity"
    count_attribute = "total_dir_attributes_checked"
    failure_attribute = "has_errors"
    success_summary = "Tous les attributs dir concernés sont valides et pertinents."
    failure_summary = "Certains attributs dir sont invalides ou non pertinents."
    error_summary = "L'analyse de la validité de l'attribut dir a échoué"
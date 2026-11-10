"""
Orchestration d'un audit demandé depuis l'interface.

Cette couche relie une demande utilisateur (fichiers, URL, thématiques) au
moteur existant :

    AuditRequest
      -> registre filtré par thématique
      -> AuditContextBuilder
      -> AuditService
      -> AuditOutcome

Elle ne dépend pas de Gradio et ne contient aucune logique RGAA.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.input.file_classifier import is_html_file
from accessi_code.models.audit_result import AuditResult
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.default_registry import build_default_registry
from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.themes import (
    THEMES_BY_NUMBER,
    filter_registry_by_themes,
    implemented_themes,
)
from accessi_code.service.audit_progress import (
    AuditProgress,
    AuditProgressCallback,
    AuditStep,
    notify_progress,
)
from accessi_code.service.audit_service import AuditService
from accessi_code.service.audit_services import AuditServices


class AuditRequestError(ValueError):
    """Demande d'audit invalide. Le message est destiné à l'utilisateur."""


@dataclass(frozen=True, slots=True)
class AuditRequest:
    """Ce que l'utilisateur a fourni pour lancer un audit."""

    files: tuple[Path, ...] = ()
    url: str | None = None
    themes: frozenset[int] = frozenset()


@dataclass(slots=True)
class AuditOutcome:
    """Résultat d'un audit, enrichi des informations utiles à l'affichage."""

    request: AuditRequest
    result: AuditResult
    # Thématiques possédant au moins un test dans le registre complet.
    implemented_themes: frozenset[int]
    # Thématiques demandées ET possédant au moins un test exécuté.
    executed_themes: frozenset[int]
    # Informations à signaler à l'utilisateur (URL ignorée, etc.).
    notices: list[str] = field(default_factory=list)


ServicesFactory = Callable[[], AuditServices]


def build_services_from_settings() -> AuditServices:
    """
    Construit les services IA réels à partir de la configuration (.env).

    L'import de la configuration est différé : il échoue si le .env est
    absent, ce qui ne doit pas empêcher l'import de ce module.
    """
    from accessi_code.config import settings
    from accessi_code.service.default_services import build_default_audit_services

    return build_default_audit_services(
        ollama_host=settings.OLLAMA_HOST,
        llm_model=settings.LLM_MODEL,
        vlm_model=settings.VLM_MODEL,
    )


class AuditOrchestrator:
    """Prépare et exécute un audit à partir d'une AuditRequest."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        registry_factory: Callable[[], TestRegistry] = build_default_registry,
        services_factory: ServicesFactory | None = build_services_from_settings,
    ):
        self.workspace_root = Path(workspace_root)
        self.registry_factory = registry_factory
        self.services_factory = services_factory
        self._services: AuditServices | None = None
        self._services_notice: str | None = None

    async def run(
        self,
        request: AuditRequest,
        on_progress: AuditProgressCallback | None = None,
    ) -> AuditOutcome:
        """
        Exécute l'audit demandé.

        ``on_progress`` reçoit l'avancement réel (étape, tests terminés).

        Raises:
            AuditRequestError: si la demande ne permet pas de lancer un audit.
        """
        notices = self._validate(request)

        full_registry = self.registry_factory()
        available = implemented_themes(full_registry)
        executed = frozenset(request.themes & available)
        if not executed:
            raise AuditRequestError(
                "Aucun test automatisé n'existe encore pour les thématiques "
                f"sélectionnées ({_format_themes(request.themes)}). "
                f"Thématiques disponibles : {_format_themes(available)}."
            )

        missing = request.themes - available
        if missing:
            notices.append(
                f"Thématiques sélectionnées sans test automatisé (non auditées) : {_format_themes(missing)}."
            )

        registry = filter_registry_by_themes(full_registry, executed)
        services = self._get_services()
        if self._services_notice:
            notices.append(self._services_notice)

        total = len(registry)
        await notify_progress(on_progress, AuditProgress(AuditStep.PREPARATION, total_tests=total))

        # Copie et analyse des fichiers : opérations bloquantes, hors boucle asyncio.
        builder = AuditContextBuilder(workspace_root=self.workspace_root)
        context = await asyncio.to_thread(builder.build, list(request.files))

        await notify_progress(on_progress, AuditProgress(AuditStep.TESTS, total_tests=total))
        errors: list[str] = []

        async def on_test_done(done: int, total_tests: int, test_result: TestResult) -> None:
            if test_result.status == TestStatus.ERROR:
                errors.append(test_result.test_id)
            await notify_progress(
                on_progress,
                AuditProgress(
                    AuditStep.TESTS,
                    done_tests=done,
                    total_tests=total_tests,
                    last_test_id=test_result.test_id,
                    error_test_ids=tuple(errors),
                ),
            )

        result = await AuditService(registry=registry, services=services).audit(context, on_test_done)

        await notify_progress(
            on_progress,
            AuditProgress(AuditStep.DONE, done_tests=total, total_tests=total, error_test_ids=tuple(errors)),
        )

        return AuditOutcome(
            request=request,
            result=result,
            implemented_themes=available,
            executed_themes=executed,
            notices=notices,
        )

    @staticmethod
    def _validate(request: AuditRequest) -> list[str]:
        """Vérifie la demande et retourne les avertissements non bloquants."""
        notices: list[str] = []

        if not request.themes:
            raise AuditRequestError("Sélectionnez au moins une thématique RGAA.")
        unknown = sorted(number for number in request.themes if number not in THEMES_BY_NUMBER)
        if unknown:
            raise AuditRequestError(f"Thématiques inconnues : {unknown}.")

        absent = [path.name for path in request.files if not path.is_file()]
        if absent:
            raise AuditRequestError(f"Fichiers introuvables : {', '.join(absent)}.")

        html_files = [path for path in request.files if is_html_file(path)]
        url = (request.url or "").strip()

        if not html_files:
            if url:
                raise AuditRequestError(
                    "L'audit d'une URL n'est pas encore disponible. Importez le fichier HTML de la page à auditer."
                )
            raise AuditRequestError("Importez au moins un fichier HTML (.html ou .htm).")

        if url:
            notices.append("L'URL saisie n'a pas été analysée : seuls les fichiers importés sont audités.")
        if len(html_files) > 1:
            notices.append(
                f"{len(html_files)} fichiers HTML importés : seul le premier "
                f"({html_files[0].name}) est analysé pour le moment."
            )
        return notices

    def _get_services(self) -> AuditServices:
        """Construit les services IA une seule fois, avec repli sans IA."""
        if self._services is not None:
            return self._services

        if self.services_factory is None:
            self._services = AuditServices()
            return self._services

        try:
            self._services = self.services_factory()
        except Exception as error:
            self._services = AuditServices()
            self._services_notice = (
                "Services IA indisponibles (configuration Ollama invalide ou absente) : "
                f"les contrôles qui en dépendent ne sont pas réalisés. Détail : {error}"
            )
        return self._services


def _format_themes(numbers: Iterable[int]) -> str:
    labels = [THEMES_BY_NUMBER[n].label for n in sorted(numbers) if n in THEMES_BY_NUMBER]
    return ", ".join(labels) if labels else "aucune"

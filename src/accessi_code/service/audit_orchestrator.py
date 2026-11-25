"""
Orchestration d'un audit demandé depuis l'interface.

Cette couche relie une demande utilisateur (fichiers, URL, thématiques) au
moteur existant :

    AuditRequest
      -> registre filtré par thématique
      -> AuditContextBuilder              (préparation des documents)
      -> ContextEnricher, si nécessaire   (analyse du rendu avec Playwright)
      -> AuditService                     (tests RGAA)
      -> AuditOutcome

Elle suit la progression réelle, mesure la durée de chaque test et
estime le temps restant (voir service.audit_timing).

Elle ne dépend pas de Gradio et ne contient aucune logique RGAA.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from accessi_code.ai.token_usage import TokenUsage, track_tokens
from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.input.file_classifier import is_html_file, pick_main_html
from accessi_code.models.audit_result import AuditResult
from accessi_code.models.capabilities import Capability
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
from accessi_code.service.audit_timing import AuditEstimate, AuditTimingStore, RemainingTimeTracker

# Fichier des durées mesurées, dans l'espace de travail.
TIMINGS_FILENAME = "audit_timings.json"

# Données produites par l'analyse du rendu (styles calculés, contrastes).
RENDER_CAPABILITIES = frozenset(
    {
        Capability.COMPUTED_STYLES,
        Capability.TEXT_CONTRAST,
        Capability.NON_TEXT_CONTRAST,
        # Preuves navigateur : accolement des étiquettes (11.4), navigation (12.x).
        Capability.BROWSER_INTERACTION,
    }
)


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
    # Tokens consommés par les appels à l'IA et durée totale de l'audit, en secondes.
    tokens_used: int = 0
    duration_seconds: float = 0.0


ServicesFactory = Callable[[], AuditServices]
EnricherFactory = Callable[[], object]


# Délai maximal de la vérification du serveur d'IA avant l'audit.
AI_CHECK_TIMEOUT_SECONDS = 3.0
AI_UNAVAILABLE_NOTICE = (
    "IA non disponible : les contrôles qui en dépendent n'ont pas été évalués. "
    "Vérifiez la connexion au serveur Ollama puis relancez l'audit."
)

AiCheck = Callable[[], Awaitable[bool]]


async def check_ai_available() -> bool:
    """
    Vérifie en quelques secondes que le serveur Ollama répond et propose le modèle de langage.

    Évite que chaque test IA attende l'échec de sa propre connexion.
    """
    try:
        import aiohttp

        from accessi_code.config import settings

        url = settings.OLLAMA_HOST.rstrip("/") + "/api/tags"
        timeout = aiohttp.ClientTimeout(total=AI_CHECK_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return False
                data = await response.json()
    except Exception:
        return False

    names = {str(model.get("name", "")) for model in data.get("models", []) if isinstance(model, dict)}
    wanted = settings.LLM_MODEL
    return wanted in names or f"{wanted}:latest" in names


def build_context_enricher() -> object:
    """Analyse du rendu avec Playwright (import différé : dépendance lourde)."""
    from accessi_code.input.context_enricher import ContextEnricher

    return ContextEnricher()


def needs_rendering(registry: TestRegistry) -> bool:
    """Vrai si un test du registre exploite les données de l'analyse du rendu."""
    for test in registry:
        capabilities = test.required_capabilities | getattr(test, "optional_capabilities", frozenset())
        if capabilities & RENDER_CAPABILITIES:
            return True
    return False


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
        enricher_factory: EnricherFactory | None = build_context_enricher,
        timing_store: AuditTimingStore | None = None,
        ai_check: AiCheck | None = None,
    ):
        self.workspace_root = Path(workspace_root)
        self.registry_factory = registry_factory
        self.services_factory = services_factory
        self.enricher_factory = enricher_factory
        self.timing = timing_store or AuditTimingStore(self.workspace_root / TIMINGS_FILENAME)
        self._services: AuditServices | None = None
        self._services_notice: str | None = None
        # Vérification du serveur d'IA avant chaque audit (None : pas de vérification).
        self.ai_check = ai_check

    def estimate(self, themes: frozenset[int]) -> AuditEstimate | None:
        """Durée estimée d'un audit des thématiques données, ou None si aucun test."""
        full_registry = self.registry_factory()
        registry = filter_registry_by_themes(full_registry, themes & implemented_themes(full_registry))
        if len(registry) == 0:
            return None
        return self.timing.estimate(
            [test.test_id for test in registry],
            with_enrichment=self._uses_enrichment(registry),
        )

    async def run(
        self,
        request: AuditRequest,
        on_progress: AuditProgressCallback | None = None,
        *,
        token_usage: TokenUsage | None = None,
    ) -> AuditOutcome:
        """
        Exécute l'audit demandé.

        ``on_progress`` reçoit l'avancement réel (étape, tests terminés),
        le temps écoulé, le temps restant estimé et les tokens consommés.
        ``token_usage`` : compteur à remplir (l'appelant peut le lire pendant l'audit).

        Raises:
            AuditRequestError: si la demande ne permet pas de lancer un audit.
        """
        with track_tokens(token_usage) as usage:
            return await self._run(request, on_progress, usage)

    async def _run(
        self,
        request: AuditRequest,
        on_progress: AuditProgressCallback | None,
        usage: TokenUsage,
    ) -> AuditOutcome:
        started = time.perf_counter()
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

        # Vérification de l'IA, en parallèle de la préparation des documents.
        ai_task = asyncio.create_task(self._check_ai()) if self._should_check_ai() else None
        ai_available: bool | None = None

        test_ids = [test.test_id for test in registry]
        total = len(test_ids)
        with_enrichment = self._uses_enrichment(registry)
        tracker = RemainingTimeTracker(self.timing, test_ids)
        errors: list[str] = []

        async def report(
            step: AuditStep,
            *,
            done: int = 0,
            last: str | None = None,
            remaining: float | None = None,
            floor: float | None = None,
        ) -> None:
            await notify_progress(
                on_progress,
                AuditProgress(
                    step,
                    done_tests=done,
                    total_tests=total,
                    last_test_id=last,
                    error_test_ids=tuple(errors),
                    elapsed_seconds=time.perf_counter() - started,
                    remaining_seconds=remaining,
                    remaining_floor_seconds=floor,
                    enrichment_needed=with_enrichment,
                    ai_available=ai_available,
                    tokens_used=usage.total,
                ),
            )

        # 1. Préparation : copie et analyse des fichiers, hors boucle asyncio.
        estimate = self.timing.estimate(test_ids, with_enrichment=with_enrichment)
        await report(
            AuditStep.PREPARATION,
            remaining=estimate.seconds,
            floor=estimate.seconds - self.timing.preparation_seconds(),
        )
        step_start = time.perf_counter()
        builder = AuditContextBuilder(workspace_root=self.workspace_root)
        try:
            context = await asyncio.to_thread(builder.build, list(request.files))
            if ai_task is not None:
                ai_available = await ai_task
        except BaseException:
            if ai_task is not None:
                ai_task.cancel()
            raise
        self.timing.record_preparation(time.perf_counter() - step_start)

        if ai_available is False:
            # Les tests IA concluent aussitôt « non testé » au lieu d'attendre l'échec de connexion :
            # le temps restant s'appuie donc sur les durées mesurées sans IA.
            services = AuditServices()
            notices.append(AI_UNAVAILABLE_NOTICE)
            tracker = RemainingTimeTracker(self.timing, test_ids, with_ai=False)
        else:
            services = self._get_services()
            if self._services_notice:
                notices.append(self._services_notice)

        # 2. Analyse du rendu, uniquement si une thématique cochée en a besoin.
        if with_enrichment:
            await report(
                AuditStep.ENRICHMENT,
                remaining=self.timing.enrichment_seconds() + tracker.remaining_seconds(0),
                floor=tracker.remaining_seconds(0),
            )
            step_start = time.perf_counter()
            enrichment_notice = await self._enrich(context)
            if enrichment_notice is None:
                self.timing.record_enrichment(time.perf_counter() - step_start)
            else:
                notices.append(enrichment_notice)

        # 3. Tests RGAA, chronométrés un par un.
        await report(AuditStep.TESTS, remaining=tracker.remaining_seconds(0), floor=tracker.remaining_after_current(0))
        last_tick = time.perf_counter()

        async def on_test_done(done: int, total_tests: int, test_result: TestResult) -> None:
            nonlocal last_tick
            now = time.perf_counter()
            duration = now - last_tick
            last_tick = now

            tracker.record(done - 1, duration)
            # Un test en erreur ne reflète pas sa durée normale. Sans IA, les tests IA concluent
            # aussitôt « non testé » : leurs durées sont conservées à part (audits sans IA).
            if ai_available is False:
                if test_result.status != TestStatus.ERROR:
                    self.timing.record_test(test_result.test_id, duration, with_ai=False)
            elif test_result.status not in (TestStatus.NOT_TESTED, TestStatus.ERROR):
                self.timing.record_test(test_result.test_id, duration)
            if test_result.status == TestStatus.ERROR:
                errors.append(test_result.test_id)

            await report(
                AuditStep.TESTS,
                done=done,
                last=test_result.test_id,
                remaining=tracker.remaining_seconds(done),
                floor=tracker.remaining_after_current(done),
            )

        result = await AuditService(registry=registry, services=services).audit(context, on_test_done)

        # 4. Synthèse puis enregistrement des durées mesurées.
        await report(AuditStep.SYNTHESIS, done=total, remaining=0.0)
        await asyncio.to_thread(self.timing.save)
        await report(AuditStep.DONE, done=total, remaining=0.0)

        return AuditOutcome(
            request=request,
            result=result,
            implemented_themes=available,
            executed_themes=executed,
            notices=notices,
            tokens_used=usage.total,
            duration_seconds=time.perf_counter() - started,
        )

    def _should_check_ai(self) -> bool:
        return self.ai_check is not None and self.services_factory is not None

    async def _check_ai(self) -> bool:
        try:
            return bool(await self.ai_check())
        except asyncio.CancelledError:
            raise
        except Exception:
            return False

    def _uses_enrichment(self, registry: TestRegistry) -> bool:
        return self.enricher_factory is not None and needs_rendering(registry)

    async def _enrich(self, context) -> str | None:
        """Lance l'analyse du rendu ; retourne un avertissement en cas de problème."""
        try:
            enricher = self.enricher_factory()
            enrichment = await enricher.enrich(context)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            return (
                "L'analyse du rendu de la page (styles calculés) n'a pas pu être réalisée "
                f"({type(error).__name__} : {error}). Les contrôles de contraste "
                "devront être vérifiés manuellement."
            )

        problems = [
            str(problem)
            for problem in (
                getattr(enrichment, "error", None),
                getattr(enrichment, "non_text_error", None),
                getattr(enrichment, "browser_evidence_error", None),
            )
            if problem
        ]
        if problems:
            return (
                "L'analyse du rendu de la page est incomplète : "
                + " ; ".join(problems)
                + ". Certains contrôles (contrastes, navigation au clavier, disposition des "
                "étiquettes) devront être vérifiés manuellement."
            )
        return None

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
            main_page = html_files[pick_main_html(html_files)]
            notices.append(
                f"{len(html_files)} fichiers HTML importés : la page principale analysée est "
                f"{main_page.name}. Les autres pages servent aux critères qui comparent "
                "plusieurs pages (cohérence des formulaires et de la navigation)."
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

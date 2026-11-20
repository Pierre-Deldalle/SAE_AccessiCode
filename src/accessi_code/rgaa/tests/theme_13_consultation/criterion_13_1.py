"""
RGAA 4.1.2 — critère 13.1 : pour chaque page web, l'utilisateur a-t-il le
contrôle de chaque limite de temps modifiant le contenu ?

Procédés repérés (``analysis/scripts.py``) :
- balise ``<meta http-equiv="refresh">`` : sans URL c'est un rafraîchissement
  (13.1.1), avec une URL une redirection (13.1.2) ;
- minuteurs (setTimeout / setInterval) qui rechargent la page (13.1.1),
  redirigent (13.1.3) ou mettent fin à une session (13.1.4).

Règles :
- une limite de 20 heures ou plus est conforme ;
- une balise meta ne laisse aucun contrôle à l'utilisateur : rafraîchissement
  ou fin de session de moins de 20 heures → FAIL ;
- 13.1.2 : redirection meta immédiate (délai 0) → PASS, sinon FAIL ;
- par script, l'utilisateur peut disposer d'un moyen d'arrêter, de prolonger
  ou d'être averti : cela ne se vérifie qu'à l'usage → NEEDS_REVIEW.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.scripts import TimerCall, page_scripts, timer_calls
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.outcomes import Outcome, build_result, make_outcome

# 20 heures, en secondes.
LIMIT_SECONDS = 20 * 3600

RELOAD = re.compile(
    r"location\s*\.\s*reload\s*\(|history\s*\.\s*go\s*\(\s*0?\s*\)"
    r"|location\s*\.\s*href\s*=\s*(?:window\s*\.\s*)?location\s*\.\s*href"
)
REDIRECT = re.compile(
    r"(?<![\w$])(?:window\s*\.\s*|document\s*\.\s*)?location(?:\s*\.\s*href)?\s*=(?!=)|location\s*\.\s*(?:assign|replace)\s*\("
)
SESSION = re.compile(r"logout|log-out|signout|sign-out|d[ée]connex|deconnect|session|expir", re.IGNORECASE)
REVIEW_RECOMMENDATION = (
    "Vérifier que l'utilisateur peut arrêter ou relancer le procédé, augmenter la limite d'au moins dix fois, "
    "ou qu'il est averti et dispose d'au moins vingt secondes pour la prolonger."
)


@dataclass
class MetaRefresh:
    element: Tag
    index: int
    delay: float
    url: str


def meta_refreshes(soup: BeautifulSoup) -> list[MetaRefresh]:
    refreshes: list[MetaRefresh] = []
    metas = soup.find_all("meta")
    for index, meta in enumerate(metas):
        if str(meta.get("http-equiv") or "").strip().lower() != "refresh":
            continue
        content = str(meta.get("content") or "")
        match = re.match(r"\s*(\d+(?:\.\d+)?)\s*(?:[;,]\s*(?:url\s*=\s*)?['\"]?([^'\"]*)['\"]?)?", content, re.I)
        if match:
            refreshes.append(MetaRefresh(meta, index, float(match.group(1)), (match.group(2) or "").strip()))
    return refreshes


def _meta_identifier(meta: MetaRefresh) -> str:
    return f"meta[http-equiv=refresh][index={meta.index}]"


def _timer_identifier(call: TimerCall) -> str:
    return f"{call.source.label} ({call.kind})"


def _timer_outcome(call: TimerCall, what: str) -> Outcome:
    evidence = {"delay_ms": call.delay_ms, "code": call.source.snippet(call.position)}
    if call.kind == "setTimeout" and call.delay_ms is not None and call.delay_ms / 1000 >= LIMIT_SECONDS:
        return make_outcome(TestStatus.PASS)
    if call.delay_ms is None:
        delay = "après un délai calculé"
    elif call.kind == "setInterval":
        # Souvent un compte à rebours : l'intervalle n'est pas la limite de temps elle-même.
        delay = f"depuis un minuteur répété toutes les {call.delay_ms / 1000:g} s"
    else:
        delay = f"après {call.delay_ms / 1000:g} s"
    return make_outcome(
        TestStatus.NEEDS_REVIEW,
        _timer_identifier(call),
        f"Un script {what} {delay} : le contrôle laissé à l'utilisateur reste à vérifier.",
        REVIEW_RECOMMENDATION,
        **evidence,
    )


class TimeLimitTest(RGAATest):
    criterion_id = "13.1"
    required_capabilities = frozenset({Capability.DOM})

    def _soup(self, context: AuditContext) -> BeautifulSoup:
        if not isinstance(context.dom, BeautifulSoup):
            raise ValueError(f"Le test {self.test_id} nécessite un DOM.")
        return context.dom


class Test1311(TimeLimitTest):
    """13.1.1 : rafraîchissements (meta sans URL, rechargement par script)."""

    test_id = "13.1.1"
    empty = "Aucun rafraîchissement automatique de la page."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._soup(context)
        outcomes: list[Outcome] = []
        for meta in meta_refreshes(soup):
            if meta.url:
                continue
            if meta.delay >= LIMIT_SECONDS:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    _meta_identifier(meta),
                    f"La page se rafraîchit toutes les {meta.delay:g} secondes par une balise meta, "
                    "sans que l'utilisateur puisse arrêter ni prolonger ce délai.",
                    "Supprimer le rafraîchissement automatique ou le remplacer par un bouton « Actualiser ».",
                    delay_seconds=meta.delay,
                )
            )
        for call in timer_calls(page_scripts(context)):
            if RELOAD.search(call.callback):
                outcomes.append(_timer_outcome(call, "recharge la page"))
        return build_result(self, outcomes, empty_summary=self.empty, noun="rafraîchissement(s)")


class Test1312(TimeLimitTest):
    """13.1.2 : redirections par balise meta (doivent être immédiates)."""

    test_id = "13.1.2"
    empty = "Aucune redirection par balise meta."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        outcomes: list[Outcome] = []
        for meta in meta_refreshes(self._soup(context)):
            if not meta.url:
                continue
            if meta.delay == 0:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    _meta_identifier(meta),
                    f"La balise meta redirige vers « {meta.url} » après {meta.delay:g} secondes : "
                    "la redirection n'est pas immédiate.",
                    'Rendre la redirection immédiate (content="0; url=…") ou faire la redirection côté serveur.',
                    delay_seconds=meta.delay,
                    url=meta.url,
                )
            )
        return build_result(self, outcomes, empty_summary=self.empty, noun="redirection(s)")


class Test1313(TimeLimitTest):
    """13.1.3 : redirections par script après un délai."""

    test_id = "13.1.3"
    empty = "Aucune redirection différée par script."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        self._soup(context)
        outcomes = [
            _timer_outcome(call, "redirige l'utilisateur")
            for call in timer_calls(page_scripts(context))
            if REDIRECT.search(call.callback)
            and not RELOAD.search(call.callback)
            and not SESSION.search(call.callback)
            and call.delay_ms != 0
        ]
        return build_result(self, outcomes, empty_summary=self.empty, noun="redirection(s)")


class Test1314(TimeLimitTest):
    """13.1.4 : limites de temps de session."""

    test_id = "13.1.4"
    empty = "Aucune limite de temps de session repérée."

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        soup = self._soup(context)
        outcomes: list[Outcome] = []
        for meta in meta_refreshes(soup):
            if not (meta.url and SESSION.search(meta.url)):
                continue
            if meta.delay >= LIMIT_SECONDS:
                outcomes.append(make_outcome(TestStatus.PASS))
                continue
            outcomes.append(
                make_outcome(
                    TestStatus.FAIL,
                    _meta_identifier(meta),
                    f"La session se termine après {meta.delay:g} secondes par une balise meta "
                    f"(« {meta.url} ») : l'utilisateur ne peut ni la supprimer ni la prolonger.",
                    "Avertir l'utilisateur avant la fin de session et lui permettre de la prolonger.",
                    delay_seconds=meta.delay,
                    url=meta.url,
                )
            )
        for call in timer_calls(page_scripts(context)):
            if SESSION.search(call.callback) and (
                REDIRECT.search(call.callback) or "submit" in call.callback or "fetch" in call.callback
            ):
                outcomes.append(_timer_outcome(call, "met fin à la session"))
        return build_result(self, outcomes, empty_summary=self.empty, noun="limite(s) de session")

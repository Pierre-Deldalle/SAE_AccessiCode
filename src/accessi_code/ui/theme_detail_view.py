"""
Détail HTML d'une thématique, indépendant de Gradio.

Les critères sont rangés par gravité (non conformes, à vérifier, non évalués,
conformes, non applicables). Chaque critère affiche son intitulé officiel,
ce qu'un défaut change pour les utilisateurs et le lien vers sa fiche RGAA
(rgaa/criteria_info.py). Chaque observation affiche son emplacement (fichier,
ligne, extrait de code), le problème et la correction : recommandation,
proposition de l'IA et exemple « avant / après ».

Tout le texte vient de la page auditée ou d'une IA : il est échappé.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

from accessi_code.models.audit_result import CriterionResult
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.criteria_info import criterion_info
from accessi_code.service.theme_summary import STATE_LABELS, STATUS_LABELS, ThemeState, ThemeSummary

# Nombre maximal d'observations détaillées par test, pour garder la page lisible.
MAX_FINDINGS_PER_TEST = 15

# Groupes de critères, du plus urgent au moins urgent : (classe, titre, statuts).
# Chaque critère est replié : son titre indique le statut, l'intitulé officiel et le
# nombre d'observations ; l'utilisateur ouvre ceux qu'il veut corriger.
CRITERIA_GROUPS: tuple[tuple[str, str, tuple[TestStatus, ...]], ...] = (
    ("fail", "Critères non conformes", (TestStatus.FAIL,)),
    ("review", "Critères à vérifier manuellement", (TestStatus.NEEDS_REVIEW,)),
    ("unevaluated", "Critères non évalués", (TestStatus.ERROR, TestStatus.NOT_TESTED)),
    ("pass", "Critères conformes", (TestStatus.PASS,)),
    ("na", "Critères non applicables", (TestStatus.NOT_APPLICABLE,)),
)

_STATUS_CLASS = {
    TestStatus.FAIL: "fail",
    TestStatus.NEEDS_REVIEW: "review",
    TestStatus.ERROR: "unevaluated",
    TestStatus.NOT_TESTED: "unevaluated",
    TestStatus.PASS: "pass",
    TestStatus.NOT_APPLICABLE: "na",
}


def score_category(score: int) -> str:
    """Détermine la couleur associée à un pourcentage."""
    if not 0 <= score <= 100:
        raise ValueError("Le score doit être compris entre 0 et 100.")
    if score <= 35:
        return "danger"
    if score <= 65:
        return "warning"
    return "success"


def priority_label(score: int) -> str:
    """Retourne une indication compréhensible sans la couleur."""
    category = score_category(score)
    if category == "danger":
        return "Priorité élevée"
    if category == "warning":
        return "À surveiller"
    return "Satisfaisant"


def _escape(text: str) -> str:
    """HTML échappé ; « $ » aussi, pour qu'aucune formule ne soit interprétée par l'interface."""
    return escape(text).replace("$", "&#36;")


def _text(value: object, limit: int = 2000) -> str:
    """Texte échappé, espaces normalisés, tronqué à ``limit`` caractères."""
    text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return _escape(text)


def _code(value: object, limit: int = 1000) -> str:
    """Code échappé, retours à la ligne conservés."""
    text = str(value).strip()
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return _escape(text)


# ---------------------------------------------------------------------------
# Recommandation : texte, proposition de l'IA, exemple « avant / après »
# ---------------------------------------------------------------------------

_PROPOSAL = re.compile(r"\s*Proposition : « (?P<text>.*?) »\.(?=\s|$)", re.S)
_EXAMPLE = re.compile(r"\s*Exemple : (?P<before>.+?) → (?P<after>.+)$", re.S)
_BEFORE_AFTER = re.compile(r"\n\s*Avant : (?P<before>.*?)\n\s*Après : (?P<after>.*)$", re.S)


@dataclass(frozen=True, slots=True)
class RecommendationParts:
    """Recommandation découpée pour l'affichage."""

    text: str
    proposal: str | None = None
    before: str | None = None
    after: str | None = None


def split_recommendation(recommendation: str | None) -> RecommendationParts:
    """
    Sépare la consigne, la proposition de l'IA (« Proposition : « … ». ») et
    l'exemple de correction, écrit « Exemple : avant → après » ou, sur deux
    lignes, « Avant : … » puis « Après : … ».
    """
    text = (recommendation or "").strip()
    before = after = proposal = None
    match = _BEFORE_AFTER.search(text) or _EXAMPLE.search(text)
    if match:
        before, after = match.group("before").strip(), match.group("after").strip()
        text = text[: match.start()].rstrip()
    match = _PROPOSAL.search(text)
    if match:
        proposal = match.group("text").strip()
        text = (text[: match.start()] + text[match.end() :]).strip()
    return RecommendationParts(text, proposal, before, after)


def _same_code(first: str | None, second: str | None) -> bool:
    return bool(first and second) and " ".join(str(first).split()) == " ".join(str(second).split())


def _recommendation_html(recommendation: str | None, *, shared_text: str = "", snippet: str | None = None) -> str:
    """
    Correction d'une observation. ``shared_text`` : consigne déjà affichée pour le test
    (elle n'est pas répétée). Si le code « avant » est l'extrait déjà affiché, seul le
    code corrigé est montré.
    """
    parts = split_recommendation(recommendation)
    text = "" if parts.text == shared_text else parts.text
    if not (text or parts.proposal or parts.before):
        return ""
    html = ['<div class="ac-fix">']
    if text:
        html.append(f'<p class="ac-fix-text"><strong>Comment corriger :</strong> {_text(text)}</p>')
    if parts.proposal:
        html.append(
            '<div class="ac-proposal"><p class="ac-label">Proposition de l\'IA (à relire)</p>'
            f"<p>{_text(parts.proposal)}</p></div>"
        )
    if parts.before and parts.after and _same_code(parts.before, snippet):
        html.append(
            '<div class="ac-example"><p class="ac-label">Code corrigé (exemple)</p>'
            f'<pre class="ac-code ac-code-after"><code>{_code(parts.after)}</code></pre></div>'
        )
    elif parts.before and parts.after:
        html.append(
            '<div class="ac-example"><p class="ac-label">Exemple de correction</p>'
            f'<p class="ac-step">Avant</p><pre class="ac-code"><code>{_code(parts.before)}</code></pre>'
            f'<p class="ac-step">Après</p><pre class="ac-code ac-code-after"><code>{_code(parts.after)}</code></pre>'
            "</div>"
        )
    html.append("</div>")
    return "".join(html)


# ---------------------------------------------------------------------------
# Observations, tests et critères
# ---------------------------------------------------------------------------


def location_text(finding: Finding) -> str:
    """« index.html, ligne 35 », « app.js », « ligne 12 » ou « Emplacement non précisé »."""
    if finding.file and finding.line is not None:
        return f"{finding.file}, ligne {finding.line}"
    if finding.file:
        return finding.file
    if finding.line is not None:
        return f"ligne {finding.line}"
    return "Emplacement non précisé"


def _finding_html(finding: Finding, shared_text: str = "") -> str:
    html = [
        '<li class="ac-finding">',
        '<p class="ac-location">'
        f'<span class="ac-place">{_text(location_text(finding))}</span>'
        f' <span class="ac-element">· <code>{_text(finding.element, 160)}</code></span></p>',
    ]
    if finding.message:
        html.append(f'<p class="ac-message">{_text(finding.message, 800)}</p>')
    if finding.snippet:
        html.append(
            f'<p class="ac-label">Code concerné</p><pre class="ac-code"><code>{_code(finding.snippet)}</code></pre>'
        )
    html.append(_recommendation_html(finding.recommendation, shared_text=shared_text, snippet=finding.snippet))
    html.append("</li>")
    return "".join(html)


def _test_html(test: TestResult) -> str:
    status = STATUS_LABELS.get(test.status, test.status.value)
    html = [
        f'<div class="ac-test ac-status-{_STATUS_CLASS.get(test.status, "na")}">',
        f'<p class="ac-test-title"><strong>Test {_text(test.test_id)}</strong> — {escape(status)} : '
        f'{_text(test.summary, 600)} <span class="ac-muted">({test.tested_elements} élément(s) analysé(s))</span></p>',
    ]
    if test.status == TestStatus.ERROR:
        error = test.metadata.get("error") or test.metadata.get("error_type")
        if error:
            html.append(f'<p class="ac-muted">Détail de l\'erreur : {_text(error, 400)}</p>')
    elif test.status == TestStatus.NOT_TESTED:
        missing = test.metadata.get("missing_capabilities")
        if missing:
            html.append(f'<p class="ac-muted">Données manquantes : {_text(", ".join(map(str, missing)))}</p>')

    if test.findings:
        # Consigne identique pour toutes les observations du test : affichée une seule fois.
        texts = {split_recommendation(finding.recommendation).text for finding in test.findings}
        shared = texts.pop() if len(texts) == 1 and len(test.findings) > 1 else ""
        if shared:
            html.append(f'<p class="ac-fix-text"><strong>Comment corriger :</strong> {_text(shared)}</p>')
        html.append('<ul class="ac-findings">')
        html += [_finding_html(finding, shared) for finding in test.findings[:MAX_FINDINGS_PER_TEST]]
        html.append("</ul>")
        hidden = len(test.findings) - MAX_FINDINGS_PER_TEST
        if hidden > 0:
            html.append(f'<p class="ac-muted">… et {hidden} autre(s) observation(s) pour ce test.</p>')
    html.append("</div>")
    return "".join(html)


def _criterion_html(criterion: CriterionResult) -> str:
    info = criterion_info(criterion.criterion_id)
    status = STATUS_LABELS.get(criterion.status, criterion.status.value)
    css = _STATUS_CLASS.get(criterion.status, "na")
    findings = sum(len(test.findings) for test in criterion.tests)
    count = f' <span class="ac-muted">· {findings} observation(s)</span>' if findings else ""
    title = f" — {_text(info.title, 400)}" if info else ""
    html = [
        f'<details class="ac-criterion ac-status-{css}">',
        f'<summary><span class="ac-badge ac-badge-{css}">{escape(status)}</span> '
        f"<strong>Critère {_text(criterion.criterion_id)}</strong>{title}{count}</summary>",
        '<div class="ac-criterion-body">',
    ]
    if info:
        html.append(f'<p class="ac-impact"><strong>Pourquoi c\'est important :</strong> {_text(info.impact)}</p>')
        html.append(
            f'<p class="ac-link"><a href="{escape(info.url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"Fiche officielle du critère {_text(criterion.criterion_id)} (nouvel onglet)</a></p>"
        )
    html += [_test_html(test) for test in criterion.tests]
    html.append("</div></details>")
    return "".join(html)


def _overview_html(summary: ThemeSummary) -> str:
    counts = summary.criteria_counts
    parts = []
    if summary.score is not None:
        parts.append(f"<p><strong>Score :</strong> {summary.score} % — {escape(priority_label(summary.score))}</p>")
    parts.append(f"<p><strong>État :</strong> {escape(STATE_LABELS[summary.state])}</p>")
    listed = ", ".join(f"{counts[st]} {label.lower()}" for st, label in STATUS_LABELS.items() if counts.get(st))
    parts.append(f"<p>{len(summary.criteria)} critère(s) examiné(s) : {escape(listed)}</p>")
    if summary.state == ThemeState.SCORED:
        parts.append(
            f"<p>Le pourcentage est calculé sur <strong>{summary.decided} critère(s) tranché(s)</strong> "
            f"parmi les {summary.applicable} critère(s) qui concernent la page.</p>"
        )
    if summary.state not in (ThemeState.NOT_SELECTED, ThemeState.NOT_IMPLEMENTED) and summary.incomplete:
        parts.append(
            f'<p class="ac-warning"><strong>⚠ Résultat incomplet : {summary.not_evaluated} critère(s) n\'ont pas '
            "pu être évalués</strong> (erreur d'exécution, IA indisponible ou données manquantes). "
            "Ils ne sont pas comptés dans le pourcentage.</p>"
        )
    if summary.pending_review:
        parts.append(
            f"<p><strong>{summary.pending_review} critère(s) restent à vérifier par une personne</strong> "
            "et ne sont pas comptés dans le pourcentage.</p>"
        )
    return '<div class="ac-overview">' + "".join(parts) + "</div>"


def build_theme_detail(summary: ThemeSummary) -> str:
    """HTML du détail d'une thématique."""
    header = f'<h2 class="ac-theme-title">{_text(summary.theme.label)}</h2>'

    if summary.state in (ThemeState.NOT_SELECTED, ThemeState.NOT_IMPLEMENTED):
        reason = (
            "Cette thématique n'a pas été sélectionnée pour cet audit."
            if summary.state == ThemeState.NOT_SELECTED
            else "AccessiCode ne possède pas encore de test automatisé pour cette thématique."
        )
        return (
            f'<div class="ac-detail">{header}<p><strong>État :</strong> {escape(STATE_LABELS[summary.state])}</p>'
            f"<p>{escape(reason)} Elle n'a donc pas été auditée.</p></div>"
        )

    sections = []
    for css, title, statuses in CRITERIA_GROUPS:
        criteria = [criterion for criterion in summary.criteria if criterion.status in statuses]
        if not criteria:
            continue
        sections.append(
            f'<section class="ac-group ac-group-{css}"><h3>{escape(title)} ({len(criteria)})</h3>'
            + "".join(_criterion_html(criterion) for criterion in criteria)
            + "</section>"
        )
    return f'<div class="ac-detail">{header}{_overview_html(summary)}{"".join(sections)}</div>'

"""Détail HTML d'une thématique : rangement des critères, emplacement et correction des observations."""

import pytest

from accessi_code.models.audit_result import CriterionResult
from accessi_code.models.result import Finding, TestStatus
from accessi_code.models.result import TestResult as Result
from accessi_code.rgaa.themes import THEMES_BY_NUMBER
from accessi_code.service.theme_summary import ThemeState, ThemeSummary
from accessi_code.ui.theme_detail_view import build_theme_detail, location_text, split_recommendation


def _summary(*criteria: CriterionResult) -> ThemeSummary:
    counts: dict[TestStatus, int] = {}
    for criterion in criteria:
        counts[criterion.status] = counts.get(criterion.status, 0) + 1
    return ThemeSummary(THEMES_BY_NUMBER[2], ThemeState.SCORED, score=50, criteria=criteria, criteria_counts=counts)


def _criterion(criterion_id: str, status: TestStatus, *findings: Finding) -> CriterionResult:
    test = Result(f"{criterion_id}.1", criterion_id, status, "Résumé du test", findings=list(findings))
    return CriterionResult(criterion_id, status, "", [test])


@pytest.mark.parametrize(
    ("recommendation", "text", "proposal", "before", "after"),
    [
        (
            'Ajouter un titre. Exemple : <iframe src="a"> → <iframe src="a" title="Carte">',
            "Ajouter un titre.",
            None,
            '<iframe src="a">',
            '<iframe src="a" title="Carte">',
        ),
        (
            "Rédiger un titre. Proposition : « Plan d'accès ». Exemple : <iframe> → <iframe title=\"Plan d'accès\">",
            "Rédiger un titre.",
            "Plan d'accès",
            "<iframe>",
            '<iframe title="Plan d\'accès">',
        ),
        (
            'Donner un rôle.\nAvant : <figure>\nAprès : <figure role="figure">',
            "Donner un rôle.",
            None,
            "<figure>",
            '<figure role="figure">',
        ),
        (
            "Rédiger un intitulé. Proposition : « Envoyer le message ».",
            "Rédiger un intitulé.",
            "Envoyer le message",
            None,
            None,
        ),
        ("Vérifier manuellement.", "Vérifier manuellement.", None, None, None),
    ],
    ids=["exemple", "proposition et exemple", "avant / après sur deux lignes", "proposition seule", "texte seul"],
)
def test_split_recommendation(recommendation, text, proposal, before, after):
    parts = split_recommendation(recommendation)
    assert (parts.text, parts.proposal, parts.before, parts.after) == (text, proposal, before, after)


@pytest.mark.parametrize(
    ("file", "line", "expected"),
    [
        ("pages/contact.html", 12, "pages/contact.html, ligne 12"),
        ("app.js", None, "app.js"),
        (None, None, "Emplacement non précisé"),
    ],
)
def test_location_text(file, line, expected):
    assert location_text(Finding("x", "m", file=file, line=line)) == expected


def test_finding_shows_location_code_and_correction():
    finding = Finding(
        element="iframe[index=0]",
        message="Le cadre n'a pas de titre.",
        recommendation=(
            'Ajouter un titre. Proposition : « Carte ». Exemple : <iframe src="m"> → <iframe src="m" title="Carte">'
        ),
        file="pages/contact.html",
        line=42,
        snippet='<iframe src="m"></iframe>',
    )
    detail = build_theme_detail(_summary(_criterion("2.1", TestStatus.FAIL, finding)))

    assert "pages/contact.html, ligne 42" in detail
    assert "&lt;iframe src=&quot;m&quot;&gt;&lt;/iframe&gt;" in detail  # extrait de code, échappé
    assert "Proposition de l'IA" in detail and "Carte" in detail
    assert "Avant" in detail and "Après" in detail
    assert "<iframe" not in detail  # aucun HTML de la page auditée n'est interprété


def test_criterion_shows_official_title_impact_and_link():
    detail = build_theme_detail(_summary(_criterion("2.1", TestStatus.FAIL)))
    assert "Chaque cadre a-t-il un titre de cadre ?" in detail
    assert "Pourquoi c'est important" in detail
    assert 'href="https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/#2.1"' in detail
    assert 'rel="noopener noreferrer"' in detail


def test_criteria_are_grouped_by_severity():
    detail = build_theme_detail(
        _summary(
            _criterion("2.2", TestStatus.PASS),
            _criterion("2.1", TestStatus.FAIL),
        )
    )
    assert detail.index("Critères non conformes (1)") < detail.index("Critères conformes (1)")
    # Critères repliés : leur titre donne le statut, l'intitulé officiel et le nombre d'observations.
    assert '<details class="ac-criterion ac-status-fail">' in detail
    assert '<details class="ac-criterion ac-status-pass">' in detail
    assert " open" not in detail


def test_shared_instruction_is_shown_once_per_test():
    findings = [
        Finding(f"input[index={n}]", "Champ sans étiquette.", recommendation="Associer une étiquette.")
        for n in range(3)
    ]
    detail = build_theme_detail(_summary(_criterion("2.1", TestStatus.FAIL, *findings)))
    assert detail.count("Associer une étiquette.") == 1


def test_example_does_not_repeat_the_code_already_shown():
    finding = Finding(
        "iframe[index=0]",
        "Le cadre n'a pas de titre.",
        recommendation='Ajouter un titre. Exemple : <iframe src="m"> → <iframe src="m" title="[titre]">',
        snippet='<iframe src="m">',
    )
    detail = build_theme_detail(_summary(_criterion("2.1", TestStatus.FAIL, finding)))
    assert detail.count("&lt;iframe src=&quot;m&quot;&gt;") == 1  # extrait affiché une fois
    assert "Code corrigé (exemple)" in detail
    assert ">Avant<" not in detail


def test_long_finding_lists_are_truncated():
    findings = [Finding(f"a[index={n}]", "Lien vide.") for n in range(20)]
    detail = build_theme_detail(_summary(_criterion("2.1", TestStatus.FAIL, *findings)))
    assert detail.count('<li class="ac-finding">') == 15
    assert "… et 5 autre(s) observation(s)" in detail

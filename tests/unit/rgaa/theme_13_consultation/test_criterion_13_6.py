from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_6 import (
    Test1361 as RGAA1361,
)

# ---------------------------------------------------------------------------
# 13.6.1 : Contenu cryptique avec alternative - pertinence de l'alternative
# ---------------------------------------------------------------------------


def test_1361_no_cryptic_with_alternative_not_applicable(context_factory, run_rgaa):
    """Aucun contenu cryptique avec alternative -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu normal sans art ASCII ni émoticônes.</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_cryptic_without_alternative_not_tested(context_factory, run_rgaa):
    """Contenu cryptique SANS alternative -> NOT_APPLICABLE (testé dans 13.5.1)."""
    html = "<!DOCTYPE html><html><body><p>Je suis content :-) aujourd'hui.</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    # Ce test ne s'applique qu'aux contenus cryptiques AVEC alternative
    # Les contenus sans alternative sont couverts par 13.5.1
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_ascii_art_with_relevant_title_passes(context_factory, run_rgaa):
    """Art ASCII avec title pertinent -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<pre title="Chat en art ASCII représentant un chat assis">'
        "  |\\\\      _,,,---,,_\n"
        "ZZZzz /,`.-'`'    -.  ;-;;,_\n"
        "     |,4-  ) )-,_. \\\\ (  `'-'\n"
        "    '---''(_/--'  `-'\\_)</pre>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any(f.evidence.get("condition_met") == "relevant_alternative" for f in result.findings)


def test_1361_emoticon_with_relevant_adjacent_definition_passes(context_factory, run_rgaa):
    """Émoticône avec définition adjacente pertinente -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<p>Le symbole :-) signifie un visage souriant.</p>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    assert any(f.evidence.get("condition_met") == "relevant_alternative" for f in result.findings)


def test_1361_ascii_art_with_irrelevant_title_fails(context_factory, run_rgaa):
    """Art ASCII avec title non pertinent (générique) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<pre title="image">'
        "  |\\\\      _,,,---,,_\n"
        "ZZZzz /,`.-'`'    -.  ;-;;,_\n"
        "     |,4-  ) )-,_. \\\\ (  `'-'\n"
        "    '---''(_/--'  `-'\\_)</pre>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert any(f.evidence.get("condition_met") == "irrelevant_alternative" for f in result.findings)


def test_1361_emoticon_with_irrelevant_definition_fails(context_factory, run_rgaa):
    """Émoticône avec définition non pertinente (générique) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<p>Je suis content :-) (symbole) aujourd'hui.</p>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    assert any(f.evidence.get("condition_met") == "irrelevant_alternative" for f in result.findings)


def test_1361_cryptic_syntax_with_relevant_abbr_passes(context_factory, run_rgaa):
    """Syntaxe cryptique (acronyme) avec <abbr> pertinent -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<p>Le <abbr title="Système de Gestion de Base de Données">SGBD</abbr> est installé.</p>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any(f.evidence.get("condition_met") == "relevant_alternative" for f in result.findings)


def test_1361_cryptic_syntax_with_irrelevant_abbr_fails(context_factory, run_rgaa):
    """Syntaxe cryptique avec <abbr> non pertinent (générique) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<p>Le <abbr title="acronyme">SGBD</abbr> est installé.</p>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert any(f.evidence.get("condition_met") == "irrelevant_alternative" for f in result.findings)


def test_1361_alternative_cannot_determine_needs_review(context_factory, run_rgaa):
    """Alternative ambiguë qui ne peut pas être déterminée automatiquement -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<pre title="xyz">'
        "  |\\\\      _,,,---,,_\n"
        "ZZZzz /,`.-'`'    -.  ;-;;,_</pre>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any(f.evidence.get("needs_manual_check") is True for f in result.findings)


def test_1361_empty_title_is_not_alternative_not_applicable(context_factory, run_rgaa):
    """Title vide ou espaces seulement n'est pas une alternative -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<pre title="   ">'
        "  |\\\\      _,,,---,,_\n"
        "ZZZzz /,`.-'`'    -.  ;-;;,_</pre>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    # Title vide/espaces est ignoré, donc pas d'alternative détectée
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_multiple_cryptic_mixed_results(context_factory, run_rgaa):
    """Plusieurs contenus cryptiques, certains pertinents d'autres non -> FAIL (priority)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<pre title="image">'
        "  |\\\\      _,,,---,,_\n"
        "ZZZzz /,`.-'`'    -.  ;-;;,_</pre>"
        "<p>Le symbole :-) signifie un visage souriant.</p>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    conditions = [f.evidence.get("condition_met") for f in result.findings]
    assert "relevant_alternative" in conditions
    assert "irrelevant_alternative" in conditions


def test_1361_kaomoji_with_relevant_definition_passes(context_factory, run_rgaa):
    """Kaomoji (émoticône orientale) avec définition pertinente -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<p>(^_^) signifie un visage heureux.</p>"
        "<p>Je vais bien (^_^) aujourd'hui.</p>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1


def test_1361_shrug_emoticon_with_relevant_title_passes(context_factory, run_rgaa):
    """¯\\_(ツ)_/¯ avec title pertinent -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<p><span title=\"haussement d'épaules indifférent\">¯\\_(ツ)_/¯</span></p>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1361_parent_title_inheritance_passes(context_factory, run_rgaa):
    """Title sur élément parent -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div title="Art ASCII représentant un chat assis">'
        "<pre>"
        "  |\\\\      _,,,---,,_\n"
        "ZZZzz /,`.-'`'    -.  ;-;;,_</pre>"
        "</div>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1361_metadata_contains_type_counts(context_factory, run_rgaa):
    """Metadata contient les compteurs par type."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<pre title="Art">  |\\\\      _,,,---,,_\nZZZzz /,`.-\\`    -.  ;-;;,_</pre>'
        '<p><span title="Sourire">:-)</span></p>'
        '<p>Le <abbr title="Système de Gestion de Base de Données">SGBD</abbr> est utilisé.</p>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert "ascii_art_count" in result.metadata
    assert "emoticon_count" in result.metadata
    assert "cryptic_syntax_count" in result.metadata


# ---------------------------------------------------------------------------
# Tests de régression : cas limites
# ---------------------------------------------------------------------------


def test_1361_empty_page_not_applicable(context_factory, run_rgaa):
    """Page vide -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_noscript_content_ignored(context_factory, run_rgaa):
    """Contenu dans <noscript> ignoré -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><noscript>:-) JavaScript requis</noscript></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_template_content_ignored(context_factory, run_rgaa):
    """Contenu dans <template> ignoré -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><template>:-) Contenu template</template></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_text_in_script_ignored(context_factory, run_rgaa):
    """Contenu dans <script> ignoré -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><script>var API_ENDPOINT = 'test'; // :-) commentaire</script></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_text_in_style_ignored(context_factory, run_rgaa):
    """Contenu dans <style> ignoré -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><style>/* ASCII art comment */ .class { content: ':-)'; }</style></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_cryptic_without_alternative_not_tested_by_1361(context_factory, run_rgaa):
    """Contenu cryptique SANS alternative -> NOT_APPLICABLE pour 13.6.1 (c'est 13.5.1 qui le teste)."""
    html = "<!DOCTYPE html><html><body><p>Je suis content :-) aujourd'hui.</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    # 13.6.1 ne teste que les contenus cryptiques AYANT une alternative
    # Ceux sans alternative sont couverts par 13.5.1
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1361_generic_alternatives_are_failures(context_factory, run_rgaa):
    """Test que les alternatives génériques courantes échouent."""
    generic_titles = ["image", "icon", "symbole", "emoji", "smiley", "ascii", "ascii art", "art ascii", "drawing", "dessin"]

    for generic_title in generic_titles:
        html = (
            "<!DOCTYPE html><html><body>"
            f'<pre title="{generic_title}">'
            "  |\\\\      _,,,---,,_\n"
            "ZZZzz /,`.-'`'    -.  ;-;;,_</pre>"
            "</body></html>"
        )
        context = context_factory(html)
        result = run_rgaa(RGAA1361(), context)

        assert result.status == Status.FAIL, f"Title '{generic_title}' should fail but got {result.status}"
        assert result.tested_elements == 1


def test_1361_emoticon_with_signifie_passes(context_factory, run_rgaa):
    """Émoticône avec 'signifie' dans la définition -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<p>Je suis content :-) cela signifie que je vais bien.</p>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    assert any(f.evidence.get("condition_met") == "relevant_alternative" for f in result.findings)


def test_1361_cryptic_syntax_with_descriptive_title_passes(context_factory, run_rgaa):
    """Syntaxe cryptique avec title descriptif -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<p><span title="Système de Gestion de Base de Données relationnelle">SGBD</span> est utilisé.</p>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1361(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any(f.evidence.get("condition_met") == "relevant_alternative" for f in result.findings)
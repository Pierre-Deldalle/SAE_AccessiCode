"""Tests unitaires du RGAA 6.1.1 — Liens textuels explicites."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test611 as RGAA611,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test612 as RGAA612,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test613 as RGAA613,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test614 as RGAA614,
)
from accessi_code.rgaa.tests.theme_06_links.criterion_6_1 import (
    Test615 as RGAA615,
)


def test_611_no_links_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main><p>Aucun lien.</p></main>")

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


@pytest.mark.parametrize(
    "html",
    [
        '<a href="/contact">Contact</a>',
        '<a href="/guide">Consulter le guide</a>',
        '<a href="/rapport">Cliquez ici</a>',
        '<a href="/rapport">En savoir plus</a>',
    ],
)
def test_611_text_links_require_semantic_review(
    context_factory,
    run_rgaa,
    html,
):
    context = context_factory(html)

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_611_extracts_link_text(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/rapport">Télécharger le rapport PDF</a>')

    result = run_rgaa(RGAA611(), context)

    evidence = result.findings[0].evidence

    assert evidence["label"] == "Télécharger le rapport PDF"
    assert evidence["visible_text"] == "Télécharger le rapport PDF"
    assert evidence["label_source"] == "content"


def test_611_extracts_paragraph_context(
    context_factory,
    run_rgaa,
):
    context = context_factory('<p>Pour consulter les résultats, <a href="/rapport">cliquez ici</a>.</p>')

    result = run_rgaa(RGAA611(), context)

    evidence = result.findings[0].evidence

    assert evidence["label"] == "cliquez ici"
    assert "consulter les résultats" in (evidence["context"]["paragraph"])


def test_611_extracts_list_context(
    context_factory,
    run_rgaa,
):
    context = context_factory('<ul><li>Rapport d\'accessibilité : <a href="/rapport">Télécharger</a></li></ul>')

    result = run_rgaa(RGAA611(), context)

    assert "Rapport d'accessibilité" in result.findings[0].evidence["context"]["list_item"]


def test_611_extracts_table_cell_context(
    context_factory,
    run_rgaa,
):
    context = context_factory('<table><tr><td>Rapport annuel : <a href="/rapport">Consulter</a></td></tr></table>')

    result = run_rgaa(RGAA611(), context)

    assert "Rapport annuel" in result.findings[0].evidence["context"]["table_cell"]


def test_611_extracts_previous_sibling_heading(
    context_factory,
    run_rgaa,
):
    context = context_factory('<section><h2>Documentation RGAA</h2><a href="/guide">En savoir plus</a></section>')

    result = run_rgaa(RGAA611(), context)

    assert result.findings[0].evidence["context"]["preceding_heading"] == "Documentation RGAA"


def test_611_aria_label_has_priority(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/contact" aria-label="Nous contacter">Contact</a>')

    result = run_rgaa(RGAA611(), context)

    evidence = result.findings[0].evidence

    assert evidence["label"] == "Nous contacter"
    assert evidence["label_source"] == "aria-label"
    assert evidence["visible_text"] == "Contact"


def test_611_aria_labelledby_has_priority(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<span id="link-label">Consulter le rapport</span><a href="/rapport" aria-labelledby="link-label">Rapport</a>'
    )

    result = run_rgaa(RGAA611(), context)

    evidence = result.findings[0].evidence

    assert evidence["label"] == "Consulter le rapport"
    assert evidence["label_source"] == "aria-labelledby"


def test_611_missing_labelledby_reference_is_uncertain(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/rapport" aria-labelledby="missing">Rapport</a>')

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["label_source"] == "aria-labelledby_incomplete"


def test_611_image_link_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/home"><img src="home.png" alt="Accueil"></a>')

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_611_composite_link_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/home"><img src="home.png" alt="">Accueil</a>')

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_611_svg_link_content_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/home"><svg><title>Accueil</title></svg></a>')

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_611_role_link_is_included(
    context_factory,
    run_rgaa,
):
    context = context_factory('<span role="link" aria-label="Consulter le rapport">Rapport</span>')

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_611_position_anchor_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a id="section">Point de repère</a>')

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_611_multiple_links_are_reported(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/contact">Contact</a><a href="/guide">En savoir plus</a><a href="/rapport">Télécharger</a>'
    )

    result = run_rgaa(RGAA611(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 3
    assert len(result.findings) == 3
    assert result.metadata["candidate_text_links"] == 3


def test_611_finding_contains_identifier(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a id="report-link" href="/rapport">Rapport</a>')

    result = run_rgaa(RGAA611(), context)

    assert result.findings[0].element == "a#report-link"


def test_611_no_false_semantic_pass(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/contact">Contact</a>')

    result = run_rgaa(RGAA611(), context)

    assert result.status != Status.PASS
    assert result.metadata["semantic_analysis_performed"] is False


# ---------------------------------------------------------------------------
# RGAA 6.1.2 — Liens images explicites
# ---------------------------------------------------------------------------


def test_612_no_image_links_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/contact">Contact</a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_612_img_link_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><img src="home.png" alt="Accueil"></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1

    evidence = result.findings[0].evidence

    assert evidence["label"] == "Accueil"
    assert evidence["images"][0]["source"] == "alt"


def test_612_img_without_alt_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><img src="home.png"></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["without_label_candidate"] == 1


def test_612_empty_alt_is_not_a_label(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><img src="home.png" alt=""></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.metadata["without_label_candidate"] == 1


def test_612_img_aria_label_is_extracted(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><img src="home.png" aria-label="Accueil"></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.findings[0].evidence["label"] == "Accueil"


def test_612_link_aria_label_has_priority(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/accueil" aria-label="Retour à l’accueil"><img src="home.png" alt="Maison"></a>'
    )

    result = run_rgaa(RGAA612(), context)

    evidence = result.findings[0].evidence

    assert evidence["label"] == "Retour à l’accueil"
    assert evidence["label_source"] == "link_aria-label"


def test_612_link_aria_labelledby_is_extracted(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<span id="home-label">Retour à l’accueil</span>'
        '<a href="/accueil" aria-labelledby="home-label">'
        '<img src="home.png" alt="">'
        "</a>"
    )

    result = run_rgaa(RGAA612(), context)

    assert result.findings[0].evidence["label"] == "Retour à l’accueil"


def test_612_img_link_has_paragraph_context(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<p>Retourner à la page principale : <a href="/accueil"><img src="home.png" alt="Accueil"></a></p>'
    )

    result = run_rgaa(RGAA612(), context)

    evidence = result.findings[0].evidence

    assert "page principale" in evidence["context"]["paragraph"]


def test_612_area_with_href_is_included(
    context_factory,
    run_rgaa,
):
    context = context_factory('<map name="navigation"><area href="/accueil" alt="Accueil"></map>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings[0].evidence["label"] == "Accueil"


def test_612_area_without_href_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<map name="navigation"><area alt="Accueil"></map>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_612_role_img_link_is_included(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><span role="img" aria-label="Accueil"></span></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["label"] == "Accueil"


def test_612_svg_image_link_is_included(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><svg><title>Accueil</title></svg></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["label"] == "Accueil"


def test_612_object_image_link_is_included(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/rapport"><object type="image/svg+xml" data="report.svg" title="Consulter le rapport"></object></a>'
    )

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_612_canvas_image_link_is_included(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/graphique"><canvas aria-label="Consulter le graphique"></canvas></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_612_composite_link_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><img src="home.png" alt="">Accueil</a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_612_svg_internal_link_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<svg><a href="/accueil"><text>Accueil</text></a></svg>')

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_612_multiple_image_links(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/accueil"><img src="home.png" alt="Accueil"></a><a href="/aide"><img src="help.png" alt="Aide"></a>'
    )

    result = run_rgaa(RGAA612(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert len(result.findings) == 2
    assert result.metadata["candidate_image_links"] == 2


def test_612_never_returns_false_semantic_pass(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><img src="home.png" alt="Accueil"></a>')

    result = run_rgaa(RGAA612(), context)

    assert result.status != Status.PASS
    assert result.metadata["semantic_analysis_performed"] is False


# ---------------------------------------------------------------------------
# RGAA 6.1.3 — Liens composites
# ---------------------------------------------------------------------------


def test_613_no_composite_link_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/contact">Contact</a>')

    result = run_rgaa(RGAA613(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_613_image_and_text_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/rapport"><img src="pdf.png" alt="Document PDF">Télécharger le rapport</a>')

    result = run_rgaa(RGAA613(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_613_combines_text_and_image_alt(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/rapport"><img src="pdf.png" alt="Document PDF">Télécharger le rapport</a>')

    result = run_rgaa(RGAA613(), context)
    evidence = result.findings[0].evidence

    assert evidence["combined_content"] == ("Document PDF Télécharger le rapport")
    assert evidence["label_source"] == "combined_content"


def test_613_preserves_dom_order(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/rapport">Télécharger<img src="pdf.png" alt="PDF">maintenant</a>')

    result = run_rgaa(RGAA613(), context)

    assert result.findings[0].evidence["combined_content"] == ("Télécharger PDF maintenant")


def test_613_empty_image_alt_is_ignored(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/rapport"><img src="pdf.png" alt="">Télécharger le rapport</a>')

    result = run_rgaa(RGAA613(), context)
    evidence = result.findings[0].evidence

    assert evidence["combined_content"] == ("Télécharger le rapport")
    assert evidence["images"][0]["alternative"] == ""


def test_613_multiple_images_are_combined(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/rapport"><img src="pdf.png" alt="PDF">Télécharger<img src="download.png" alt="le document"></a>'
    )

    result = run_rgaa(RGAA613(), context)
    evidence = result.findings[0].evidence

    assert evidence["combined_content"] == ("PDF Télécharger le document")
    assert len(evidence["images"]) == 2


def test_613_link_aria_label_has_priority(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/rapport" aria-label="Télécharger le rapport annuel"><img src="pdf.png" alt="PDF">Télécharger</a>'
    )

    result = run_rgaa(RGAA613(), context)
    evidence = result.findings[0].evidence

    assert evidence["label"] == ("Télécharger le rapport annuel")
    assert evidence["label_source"] == "aria-label"


def test_613_aria_labelledby_has_priority(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<span id="label">Consulter le rapport</span>'
        '<a href="/rapport" aria-labelledby="label">'
        '<img src="pdf.png" alt="PDF">'
        "Rapport"
        "</a>"
    )

    result = run_rgaa(RGAA613(), context)

    assert result.findings[0].evidence["label"] == ("Consulter le rapport")


def test_613_invalid_labelledby_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/rapport" aria-labelledby="missing"><img src="pdf.png" alt="PDF">Télécharger</a>'
    )

    result = run_rgaa(RGAA613(), context)
    evidence = result.findings[0].evidence

    assert result.status == Status.NEEDS_REVIEW
    assert evidence["label_source"] == ("aria-labelledby_incomplete")


def test_613_extracts_paragraph_context(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<p>Rapport d\'accessibilité : <a href="/rapport"><img src="pdf.png" alt="PDF">Télécharger</a></p>'
    )

    result = run_rgaa(RGAA613(), context)
    evidence = result.findings[0].evidence

    assert "Rapport d'accessibilité" in (evidence["context"]["paragraph"])


def test_613_image_only_link_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/accueil"><img src="home.png" alt="Accueil"></a>')

    result = run_rgaa(RGAA613(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_613_text_only_link_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/contact">Contact</a>')

    result = run_rgaa(RGAA613(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_613_hidden_text_is_not_counted(
    context_factory,
    run_rgaa,
):
    context = context_factory('<a href="/rapport"><img src="pdf.png" alt="PDF"><span hidden>Télécharger</span></a>')

    result = run_rgaa(RGAA613(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_613_svg_internal_link_is_excluded(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<svg><a href="/rapport"><image href="pdf.png"></image><text>Télécharger</text></a></svg>'
    )

    result = run_rgaa(RGAA613(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_613_multiple_composite_links(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<a href="/rapport">'
        '<img src="pdf.png" alt="PDF">'
        "Télécharger"
        "</a>"
        '<a href="/aide">'
        '<img src="help.png" alt="Aide">'
        "Consulter l'aide"
        "</a>"
    )

    result = run_rgaa(RGAA613(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert len(result.findings) == 2
    assert result.metadata["candidate_composite_links"] == 2
    assert result.metadata["semantic_analysis_performed"] is False


# ---------------------------------------------------------------------------
# RGAA 6.1.4 — Liens SVG
# ---------------------------------------------------------------------------


def test_614_no_svg_links_is_not_applicable(context_factory, run_rgaa):
    context = context_factory('<a href="/contact">Contact</a>')
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_614_svg2_href_requires_review(context_factory, run_rgaa):
    context = context_factory('<svg><a href="/contact"><text>Contact</text></a></svg>')
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings[0].evidence["label"] == "Contact"
    assert result.findings[0].evidence["label_source"] == "svg_text"


def test_614_svg11_xlink_href(context_factory, run_rgaa):
    context = context_factory(
        '<svg xmlns:xlink="http://www.w3.org/1999/xlink"><a xlink:href="/contact"><text>Contact</text></a></svg>'
    )
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings[0].evidence["href"] == "/contact"


def test_614_svg_without_link_is_excluded(context_factory, run_rgaa):
    context = context_factory("<svg><text>Contact</text></svg>")
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_614_svg_anchor_without_href_is_excluded(context_factory, run_rgaa):
    context = context_factory("<svg><a><text>Contact</text></a></svg>")
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_614_html_link_containing_svg_is_excluded(context_factory, run_rgaa):
    context = context_factory('<a href="/contact"><svg><title>Contact</title></svg></a>')
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_614_aria_label_takes_priority(context_factory, run_rgaa):
    context = context_factory('<svg><a href="/contact" aria-label="Nous contacter"><text>Contact</text></a></svg>')
    result = run_rgaa(RGAA614(), context)
    evidence = result.findings[0].evidence

    assert evidence["label"] == "Nous contacter"
    assert evidence["label_source"] == "aria-label"
    assert evidence["label_evidence"]["visible_svg_text"] == "Contact"


def test_614_aria_labelledby(context_factory, run_rgaa):
    context = context_factory(
        "<svg>"
        '<text id="label">Consulter le rapport</text>'
        '<a href="/rapport" aria-labelledby="label">'
        "<text>Rapport</text>"
        "</a>"
        "</svg>"
    )
    result = run_rgaa(RGAA614(), context)

    assert result.findings[0].evidence["label"] == ("Consulter le rapport")
    assert result.findings[0].evidence["label_source"] == ("aria-labelledby")


def test_614_missing_labelledby_reference(context_factory, run_rgaa):
    context = context_factory('<svg><a href="/rapport" aria-labelledby="missing"><text>Rapport</text></a></svg>')
    result = run_rgaa(RGAA614(), context)
    evidence = result.findings[0].evidence

    assert result.status == Status.NEEDS_REVIEW
    assert evidence["label_source"] == ("aria-labelledby_incomplete")


def test_614_nested_tspan_text(context_factory, run_rgaa):
    context = context_factory(
        '<svg><a href="/rapport"><text><tspan>Consulter</tspan><tspan>le rapport</tspan></text></a></svg>'
    )
    result = run_rgaa(RGAA614(), context)

    assert result.findings[0].evidence["label"] == ("Consulter le rapport")


def test_614_link_title(context_factory, run_rgaa):
    context = context_factory(
        "<svg><a href=\"/rapport\"><title>Consulter le rapport</title><path d='M0 0 L10 10'/></a></svg>"
    )
    result = run_rgaa(RGAA614(), context)

    assert result.findings[0].evidence["label"] == ("Consulter le rapport")
    assert result.findings[0].evidence["label_source"] == ("link_svg_title")


def test_614_empty_link_requires_review(context_factory, run_rgaa):
    context = context_factory("<svg><a href=\"/rapport\"><path d='M0 0 L10 10'/></a></svg>")
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["without_label_candidate"] == 1


def test_614_svg_description_context(context_factory, run_rgaa):
    context = context_factory(
        '<svg><desc>Navigation vers les rapports</desc><a href="/rapport"><text>Rapport</text></a></svg>'
    )
    result = run_rgaa(RGAA614(), context)

    assert result.findings[0].evidence["context"]["svg_description"] == "Navigation vers les rapports"


def test_614_multiple_svg_links(context_factory, run_rgaa):
    context = context_factory(
        '<svg><a href="/contact"><text>Contact</text></a><a href="/aide"><text>Aide</text></a></svg>'
    )
    result = run_rgaa(RGAA614(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert len(result.findings) == 2
    assert result.metadata["candidate_svg_links"] == 2


def test_614_identifies_link_by_id(context_factory, run_rgaa):
    context = context_factory('<svg><a id="svg-contact" href="/contact"><text>Contact</text></a></svg>')
    result = run_rgaa(RGAA614(), context)

    assert result.findings[0].element == "a#svg-contact"


def test_614_does_not_claim_semantic_conformity(context_factory, run_rgaa):
    context = context_factory('<svg><a href="/contact"><text>Contact</text></a></svg>')
    result = run_rgaa(RGAA614(), context)

    assert result.status != Status.PASS
    assert result.metadata["semantic_analysis_performed"] is False


# ---------------------------------------------------------------------------
# RGAA 6.1.5 — Intitulé visible contenu dans le nom accessible
# ---------------------------------------------------------------------------


def test_615_no_links_not_applicable(context_factory, run_rgaa):
    context = context_factory("<p>Bonjour</p>")
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_615_simple_text_link_passes(context_factory, run_rgaa):
    context = context_factory(
        '<a href="/contact">Contact</a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_615_aria_label_contains_visible_text(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/contact" aria-label="Contacter notre équipe">'
        "Contact</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_aria_label_missing_visible_text_fails(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/contact" aria-label="Envoyer un message">'
        "Contact</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert (
        result.findings[0].evidence["visible_label"]
        == "Contact"
    )


def test_615_words_must_remain_contiguous(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/achat" '
        'aria-label="Commander le produit maintenant">'
        "Commander maintenant</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.FAIL


def test_615_case_difference_allowed(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/contact" aria-label="CONTACTER">'
        "Contacter</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_punctuation_difference_allowed(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/contact" aria-label="Contact notre équipe">'
        "Contact : notre équipe</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_valid_aria_labelledby_passes(
    context_factory, run_rgaa
):
    context = context_factory(
        '<span id="label">Contacter le service client</span>'
        '<a href="/contact" aria-labelledby="label">'
        "Contacter</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS


def test_615_invalid_aria_labelledby_requires_review(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/contact" aria-labelledby="unknown">'
        "Contacter</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_symbol_requires_review(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/suite" aria-label="Suivant">&gt;</a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_css_styled_link_requires_review(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a class="link" href="/contact" '
        'aria-label="Envoyer un message">Contact</a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_image_link_requires_review(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/accueil">'
        '<img src="home.png" alt="Accueil">'
        "</a>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_svg_link_requires_review(
    context_factory, run_rgaa
):
    context = context_factory(
        '<svg><a href="/contact">'
        "<text>Contact</text>"
        "</a></svg>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NEEDS_REVIEW


def test_615_hidden_link_not_applicable(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/contact" hidden>Contact</a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_615_missing_visible_text_not_applicable(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/contact" aria-label="Contact"></a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_615_fail_takes_priority(
    context_factory, run_rgaa
):
    context = context_factory(
        '<a href="/ok">Contact</a>'
        '<a href="/bad" aria-label="Envoyer un message">'
        "Contact</a>"
        '<a class="dynamic" href="/review">Aide</a>'
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 3
    assert result.metadata["passed_links"] == 1
    assert result.metadata["failed_links"] == 1
    assert result.metadata["needs_review"] == 1


def test_615_role_link_is_checked(
    context_factory, run_rgaa
):
    context = context_factory(
        '<span role="link" aria-label="Contacter notre équipe">'
        "Contact</span>"
    )
    result = run_rgaa(RGAA615(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# Régression : un lien interne au SVG relève de 6.1.4, pas de 6.1.1.
# ---------------------------------------------------------------------------


def test_611_svg_internal_link_is_not_counted(
    context_factory, run_rgaa
):
    context = context_factory(
        '<svg><a href="/aide"><text>Consulter l’aide</text></a></svg>'
    )

    text_result = run_rgaa(RGAA611(), context)
    svg_result = run_rgaa(RGAA614(), context)

    assert text_result.status == Status.NOT_APPLICABLE
    assert text_result.tested_elements == 0
    assert svg_result.status == Status.NEEDS_REVIEW
    assert svg_result.tested_elements == 1

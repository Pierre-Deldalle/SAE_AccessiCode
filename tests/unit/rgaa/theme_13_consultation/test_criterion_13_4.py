from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_4 import (
    Test1341 as RGAA1341,
)

# ---------------------------------------------------------------------------
# 13.4.1 : Document bureautique avec version accessible - même information
# ---------------------------------------------------------------------------


def test_1341_no_download_links_not_applicable(context_factory, run_rgaa):
    """Aucun lien de téléchargement de document bureautique -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1341_downloads_but_no_alternatives_not_applicable(context_factory, run_rgaa):
    """Documents en téléchargement mais aucune alternative -> NOT_APPLICABLE."""
    html = '<!DOCTYPE html><html><body><a href="document.pdf">Télécharger le PDF</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.metadata.get("download_count") == 1
    assert "alternative_count" not in result.metadata


def test_1341_pdf_with_html_alternative_needs_review(context_factory, run_rgaa):
    """PDF avec version HTML alternative détectée -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.pdf">Télécharger le PDF</a>'
        '<a href="document.html">Version HTML accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.metadata.get("pairs_found") == 1
    assert any("même information" in f.message for f in result.findings)
    assert any(f.evidence.get("needs_manual_check") is True for f in result.findings)
    assert any(f.evidence.get("alternative_is_html") is True for f in result.findings)


def test_1341_pdf_with_accessible_pdf_alternative_needs_review(context_factory, run_rgaa):
    """PDF avec version PDF accessible alternative détectée -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.pdf">Télécharger le PDF</a>'
        '<a href="document-accessible.pdf">Version PDF accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.metadata.get("pairs_found") == 1
    assert any("même information" in f.message for f in result.findings)
    assert any(f.evidence.get("alternative_is_html") is False for f in result.findings)


def test_1341_docx_with_html_alternative_needs_review(context_factory, run_rgaa):
    """DOCX avec version HTML alternative -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.docx">Télécharger le document Word</a>'
        '<a href="document.html">Version HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("DOCX" in f.evidence.get("download_format", "") for f in result.findings)


def test_1341_odt_with_accessible_pdf_needs_review(context_factory, run_rgaa):
    """ODT avec version PDF accessible -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.odt">Télécharger le document OpenOffice</a>'
        '<a href="document-accessible.pdf">Version PDF accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("ODT" in f.evidence.get("download_format", "") for f in result.findings)


def test_1341_multiple_pairs_all_needs_review(context_factory, run_rgaa):
    """Plusieurs couples document/alternative -> tous NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="doc1.pdf">PDF 1</a>'
        '<a href="doc1.html">Version HTML</a>'
        '<a href="doc2.pdf">PDF 2</a>'
        '<a href="doc2.html">Version HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert result.metadata.get("pairs_found") == 2
    assert result.metadata.get("unmatched_downloads") == 0


def test_1341_some_with_alternatives_some_without(context_factory, run_rgaa):
    """Certains avec alternative, d'autres sans -> NEEDS_REVIEW pour tous."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="doc1.pdf">PDF avec alternative</a>'
        '<a href="doc1.html">Version HTML</a>'
        '<a href="doc2.pdf">PDF sans alternative</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert result.metadata.get("pairs_found") == 1
    assert result.metadata.get("unmatched_downloads") == 1
    # Both paired and unmatched should generate NEEDS_REVIEW findings
    review_findings = [f for f in result.findings if f.evidence.get("needs_manual_check") is True]
    assert len(review_findings) == 2


def test_1341_alternative_same_base_filename(context_factory, run_rgaa):
    """Alternative avec même nom de base de fichier."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="rapport-annuel.pdf">Rapport annuel PDF</a>'
        '<a href="rapport-annuel.html">Rapport annuel HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.metadata.get("pairs_found") == 1


def test_1341_alternative_similar_base_filename(context_factory, run_rgaa):
    """Alternative avec nom de base similaire (ex: document-accessible)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.pdf">Document</a>'
        '<a href="document-accessible.html">Version accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.metadata.get("pairs_found") == 1


def test_1341_alternative_link_text_variations(context_factory, run_rgaa):
    """Diverses formulations pour les liens alternatifs HTML."""
    alternative_texts = [
        "Version accessible",
        "version accessible",
        "Version HTML",
        "version html",
        "HTML accessible",
        "Texte seul",
        "Version texte",
        "Alternative accessible",
    ]

    for alt_text in alternative_texts:
        html = (
            f"<!DOCTYPE html><html><body>"
            f'<a href="doc.pdf">Document PDF</a>'
            f'<a href="doc.html">{alt_text}</a>'
            f"</body></html>"
        )
        context = context_factory(html)

        result = run_rgaa(RGAA1341(), context)

        assert result.status == Status.NEEDS_REVIEW, f"Failed for alternative text: {alt_text}"
        assert result.tested_elements == 1
        assert result.metadata.get("pairs_found") == 1


def test_1341_non_office_links_ignored(context_factory, run_rgaa):
    """Liens vers formats non bureautiques ignorés."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="image.png">Image</a>'
        '<a href="page.html">Page HTML</a>'
        '<a href="script.js">Script</a>'
        '<a href="style.css">Style</a>'
        '<a href="data.json">JSON</a>'
        '<a href="archive.zip">Archive</a>'
        '<a href="video.mp4">Vidéo</a>'
        '<a href="audio.mp3">Audio</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1341_case_insensitive_extensions(context_factory, run_rgaa):
    """Extensions insensibles à la casse."""
    variations = [".PDF", ".Pdf", ".pDf", ".pdf", ".DOCX", ".Docx"]
    for ext in variations:
        html = (
            f"<!DOCTYPE html><html><body>"
            f'<a href="doc{ext}">Document</a>'
            f'<a href="doc.html">Version HTML</a>'
            f"</body></html>"
        )
        context = context_factory(html)

        result = run_rgaa(RGAA1341(), context)

        assert result.status == Status.NEEDS_REVIEW, f"Failed for extension: {ext}"
        assert result.tested_elements == 1


def test_1341_relative_urls_resolved(context_factory, run_rgaa):
    """URLs relatives résolues correctement."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="documents/report.pdf">Rapport</a>'
        '<a href="documents/report.html">Version HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("report.pdf" in f.evidence.get("download_url", "") for f in result.findings)
    assert any("report.html" in f.evidence.get("alternative_url", "") for f in result.findings)


def test_1341_url_with_query_params(context_factory, run_rgaa):
    """URL avec paramètres de requête."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.pdf?download=1">PDF</a>'
        '<a href="document.html?accessible=1">HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1341_button_download_with_alternative(context_factory, run_rgaa):
    """Bouton de téléchargement avec alternative."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<form action="document.pdf" method="get">'
        '<button type="submit">Télécharger PDF</button>'
        "</form>"
        '<a href="document.html">Version HTML accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1341_onclick_window_open_with_alternative(context_factory, run_rgaa):
    """window.open vers document avec alternative."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<button onclick=\"window.open('document.pdf')\">Ouvrir PDF</button>"
        '<a href="document.html">Version HTML accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1341_daisy_format_detected(context_factory, run_rgaa):
    """Format DAISY détecté avec alternative."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="book.daisy">Livre DAISY</a>'
        '<a href="book.html">Version HTML accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("DAISY" in f.evidence.get("download_format", "") for f in result.findings)


def test_1341_mixed_formats_all_detected(context_factory, run_rgaa):
    """Tous les formats bureautiques détectés avec alternatives."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="doc.pdf">PDF</a><a href="doc.html">HTML</a>'
        '<a href="doc.doc">DOC</a><a href="doc.html">HTML</a>'
        '<a href="doc.docx">DOCX</a><a href="doc.html">HTML</a>'
        '<a href="doc.odt">ODT</a><a href="doc.html">HTML</a>'
        '<a href="doc.epub">EPUB</a><a href="doc.html">HTML</a>'
        '<a href="doc.daisy">DAISY</a><a href="doc.html">HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 6
    formats_found = result.metadata.get("download_formats", [])
    assert "PDF" in formats_found
    assert "DOC" in formats_found
    assert "DOCX" in formats_found
    assert "ODT" in formats_found
    assert "EPUB" in formats_found
    assert "DAISY" in formats_found


def test_1341_alternative_with_title_attribute(context_factory, run_rgaa):
    """Lien avec attribut title pour l'alternative."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="doc.pdf">Document</a>'
        '<a href="doc.html" title="Version HTML accessible">HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1341_tagged_pdf_alternative(context_factory, run_rgaa):
    """Alternative PDF taggé (accessible)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.pdf">Document PDF</a>'
        '<a href="document-tagged.pdf">PDF taggé accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("taggé" in f.evidence.get("alternative_text", "").lower() for f in result.findings)


def test_1341_alternatives_exist_but_no_matching_pairs(context_factory, run_rgaa):
    """Alternatives et téléchargements présents mais non appariables."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="report1.pdf">Rapport 1</a>'
        '<a href="report2.html">Rapport 2 HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert result.metadata.get("download_count") == 1
    assert result.metadata.get("alternative_count") == 1


# ---------------------------------------------------------------------------
# Tests de régression : cas limites
# ---------------------------------------------------------------------------


def test_1341_empty_href_ignored(context_factory, run_rgaa):
    """Lien avec href vide ignoré."""
    html = '<!DOCTYPE html><html><body><a href="">Lien vide</a><a href="doc.html">HTML</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_1341_javascript_href_ignored(context_factory, run_rgaa):
    """Lien javascript: ignoré."""
    html = '<!DOCTYPE html><html><body><a href="javascript:void(0)">JS</a><a href="doc.html">HTML</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_1341_mailto_href_ignored(context_factory, run_rgaa):
    """Lien mailto: ignoré."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="mailto:test@example.com">Email</a>'
        '<a href="doc.html">HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_1341_anchor_only_href_ignored(context_factory, run_rgaa):
    """Lien ancre seulement ignoré."""
    html = '<!DOCTYPE html><html><body><a href="#section">Section</a><a href="doc.html">HTML</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1341(), context)

    assert result.status == Status.NOT_APPLICABLE

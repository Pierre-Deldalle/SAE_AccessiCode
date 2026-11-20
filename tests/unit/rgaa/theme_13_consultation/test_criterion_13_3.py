from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_3 import (
    Test1331 as RGAA1331,
)

# ---------------------------------------------------------------------------
# 13.3.1 : Document bureautique en téléchargement - version accessible
# ---------------------------------------------------------------------------


def test_1331_no_download_links_not_applicable(context_factory, run_rgaa):
    """Aucun lien de téléchargement de document bureautique -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1331_pdf_download_no_alternative_needs_review(context_factory, run_rgaa):
    """Lien PDF sans alternative détectée -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><a href="document.pdf">Télécharger le PDF</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("PDF" in f.message for f in result.findings)
    assert any("Aucune version alternative" in f.message for f in result.findings)
    assert any(f.evidence.get("needs_manual_check") is True for f in result.findings)


def test_1331_docx_download_no_alternative_needs_review(context_factory, run_rgaa):
    """Lien DOCX sans alternative détectée -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><a href="document.docx">Télécharger le document Word</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("DOCX" in f.message for f in result.findings)


def test_1331_odt_download_no_alternative_needs_review(context_factory, run_rgaa):
    """Lien ODT sans alternative détectée -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><a href="document.odt">Télécharger le document OpenOffice</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("ODT" in f.message for f in result.findings)


def test_1331_epub_download_no_alternative_needs_review(context_factory, run_rgaa):
    """Lien EPUB sans alternative détectée -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><a href="book.epub">Télécharger l\'EPUB</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("EPUB" in f.message for f in result.findings)


def test_1331_pdf_with_html_alternative_passes(context_factory, run_rgaa):
    """PDF avec version HTML alternative détectée -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.pdf">Télécharger le PDF</a>'
        '<a href="document.html">Version HTML accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any("version alternative HTML" in f.message for f in result.findings)
    assert any(f.evidence.get("condition_met") == "alternative_found" for f in result.findings)


def test_1331_pdf_with_accessible_pdf_alternative_passes(context_factory, run_rgaa):
    """PDF avec version PDF accessible alternative détectée -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="document.pdf">Télécharger le PDF</a>'
        '<a href="document-accessible.pdf">Version PDF accessible</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any("version alternative" in f.message for f in result.findings)
    assert any(f.evidence.get("condition_met") == "alternative_found" for f in result.findings)


def test_1331_multiple_downloads_some_with_alternatives(context_factory, run_rgaa):
    """Plusieurs téléchargements : certains avec alternative, d'autres sans -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="doc1.pdf">PDF avec alternative</a>'
        '<a href="doc1.html">Version HTML</a>'
        '<a href="doc2.pdf">PDF sans alternative</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    # Priority: NEEDS_REVIEW > PASS (no FAIL in this test)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    # One PASS finding, one NEEDS_REVIEW finding
    pass_findings = [f for f in result.findings if f.evidence.get("condition_met") == "alternative_found"]
    review_findings = [f for f in result.findings if f.evidence.get("needs_manual_check") is True]
    assert len(pass_findings) == 1
    assert len(review_findings) == 1


def test_1331_case_insensitive_extensions(context_factory, run_rgaa):
    """Extensions insensibles à la casse (PDF, Pdf, pDf, etc.)."""
    variations = [".PDF", ".Pdf", ".pDf", ".pdf"]
    for ext in variations:
        html = f'<!DOCTYPE html><html><body><a href="doc{ext}">Document</a></body></html>'
        context = context_factory(html)

        result = run_rgaa(RGAA1331(), context)

        assert result.status == Status.NEEDS_REVIEW
        assert result.tested_elements == 1


def test_1331_relative_urls_resolved(context_factory, run_rgaa):
    """URLs relatives résolues correctement."""
    html = '<!DOCTYPE html><html><body><a href="documents/report.pdf">Rapport</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("report.pdf" in f.evidence.get("download_url", "") for f in result.findings)


def test_1331_url_with_query_params(context_factory, run_rgaa):
    """URL avec paramètres de requête."""
    html = '<!DOCTYPE html><html><body><a href="document.pdf?download=1">PDF</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1331_button_download_triggers(context_factory, run_rgaa):
    """Bouton de téléchargement détecté."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<form action="document.pdf" method="get">'
        '<button type="submit">Télécharger</button>'
        "</form>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1331_onclick_window_open_download(context_factory, run_rgaa):
    """window.open vers un document bureautique dans onclick."""
    html = (
        "<!DOCTYPE html><html><body><button onclick=\"window.open('document.pdf')\">Ouvrir PDF</button></body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1331_alternative_link_text_variations(context_factory, run_rgaa):
    """Diverses formulations pour les liens alternatifs."""
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

        result = run_rgaa(RGAA1331(), context)

        assert result.status == Status.PASS, f"Failed for alternative text: {alt_text}"
        assert result.tested_elements == 1


def test_1331_non_office_links_ignored(context_factory, run_rgaa):
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

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1331_daisy_format_detected(context_factory, run_rgaa):
    """Format DAISY détecté."""
    html = '<!DOCTYPE html><html><body><a href="book.daisy">Livre DAISY</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("DAISY" in f.message for f in result.findings)


def test_1331_mixed_formats_all_detected(context_factory, run_rgaa):
    """Tous les formats bureautiques détectés."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="doc.pdf">PDF</a>'
        '<a href="doc.doc">DOC</a>'
        '<a href="doc.docx">DOCX</a>'
        '<a href="doc.odt">ODT</a>'
        '<a href="doc.epub">EPUB</a>'
        '<a href="doc.daisy">DAISY</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 6
    formats_found = result.metadata.get("formats_found", [])
    assert "PDF" in formats_found
    assert "DOC" in formats_found
    assert "DOCX" in formats_found
    assert "ODT" in formats_found
    assert "EPUB" in formats_found
    assert "DAISY" in formats_found


def test_1331_alternative_same_base_filename(context_factory, run_rgaa):
    """Alternative avec même nom de base de fichier."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="rapport-annuel.pdf">Rapport annuel PDF</a>'
        '<a href="rapport-annuel.html">Rapport annuel HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert any("version alternative HTML" in f.message for f in result.findings)


def test_1331_download_with_title_attribute(context_factory, run_rgaa):
    """Lien avec attribut title pour l'alternative."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<a href="doc.pdf">Document</a>'
        '<a href="doc.html" title="Version HTML accessible">HTML</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# Tests de régression : cas limites
# ---------------------------------------------------------------------------


def test_1331_empty_href_ignored(context_factory, run_rgaa):
    """Lien avec href vide ignoré."""
    html = '<!DOCTYPE html><html><body><a href="">Lien vide</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_1331_javascript_href_ignored(context_factory, run_rgaa):
    """Lien javascript: ignoré."""
    html = '<!DOCTYPE html><html><body><a href="javascript:void(0)">JS</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_1331_mailto_href_ignored(context_factory, run_rgaa):
    """Lien mailto: ignoré."""
    html = '<!DOCTYPE html><html><body><a href="mailto:test@example.com">Email</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_1331_anchor_only_href_ignored(context_factory, run_rgaa):
    """Lien ancre seulement ignoré."""
    html = '<!DOCTYPE html><html><body><a href="#section">Section</a></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1331(), context)

    assert result.status == Status.NOT_APPLICABLE

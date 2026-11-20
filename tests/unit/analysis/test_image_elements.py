from bs4 import BeautifulSoup

from accessi_code.analysis.image_elements import (
    find_image_elements,
    image_kind,
    is_alternative_reference,
    referenced_text,
    svg_has_only_real_text,
)


def elements(html: str, **kwargs):
    return find_image_elements(BeautifulSoup(html, "html.parser"), **kwargs)


def test_kinds_are_detected_in_document_order() -> None:
    html = (
        '<img src="a.png"><div role="img"></div><map><area href="/"></map><input type="image" src="b.png">'
        '<input type="text"><object type="image/png" data="c.png"></object><object data="doc.pdf"></object>'
        '<embed src="d.svg"><svg><svg></svg></svg><canvas></canvas>'
    )
    assert [element.kind for element in elements(html)] == [
        "img",
        "role_img",
        "area",
        "input",
        "object",
        "embed",
        "svg",
        "canvas",
    ]


def test_image_kind_ignores_non_image_resources() -> None:
    soup = BeautifulSoup('<object type="application/pdf" data="a.pdf"></object>', "html.parser")
    assert image_kind(soup.object) is None


def test_stable_keys_use_unique_id_or_rank() -> None:
    found = elements('<img id="logo" src="a.png"><img src="b.png"><p id="x"></p><img id="x" src="c.png">')
    assert [element.key for element in found] == ["img#logo", "img[1]", "img[2]"]


def test_alternatives_by_source() -> None:
    html = '<p id="l">Libellé</p><img src="a.png" alt="Alt" title="Titre" aria-label="Aria" aria-labelledby="l">'
    element = elements(html)[0]
    assert element.alternatives == {"alt": "Alt", "title": "Titre", "aria-label": "Aria", "aria-labelledby": "Libellé"}


def test_svg_title_and_canvas_content_are_alternatives() -> None:
    svg, canvas = elements("<svg><title>Plan</title></svg><canvas>Ventes</canvas>")
    assert svg.alternatives == {"svg-title": "Plan"}
    assert canvas.alternatives == {"content": "Ventes"}


def test_broken_labelledby_is_reported() -> None:
    element = elements('<img src="a.png" aria-labelledby="absent">')[0]
    assert element.broken_labelledby is True
    assert "aria-labelledby" not in element.alternatives


def test_decorative_marking() -> None:
    empty_alt, hidden, presentation, alt_and_title, plain = elements(
        '<img src="a" alt=""><img src="b" aria-hidden="true"><img src="c" role="presentation">'
        '<img src="d" alt="" title="Info"><img src="e">'
    )
    assert empty_alt.marked_decorative
    assert hidden.marked_decorative
    assert presentation.marked_decorative
    assert not alt_and_title.marked_decorative
    assert not plain.marked_decorative


def test_functional_images() -> None:
    linked, button, area, alone = elements(
        '<a href="/"><img src="a"></a><input type="image" src="b"><map><area href="/x"></map><img src="c">'
    )
    assert linked.functional and button.functional and area.functional
    assert not alone.functional


def test_captcha_and_logo_markers() -> None:
    captcha, logo, home = elements(
        '<img class="captcha" src="a"><img src="logo.png" alt="Société">'
        '<header><a href="/"><img src="m.png"></a></header>'
    )
    assert captcha.captcha_marker
    assert logo.logo_marker
    assert home.logo_marker


def test_figure_and_caption() -> None:
    element = elements("<figure><img src='a'><figcaption>Légende</figcaption></figure>")[0]
    assert element.has_caption
    assert element.figcaption.get_text() == "Légende"


def test_figcaption_is_not_a_detailed_description() -> None:
    element = elements("<figure><img src='a'><figcaption>Légende</figcaption></figure>")[0]
    assert element.descriptions == []


def test_detailed_descriptions(tmp_path) -> None:
    (tmp_path / "desc.txt").write_text("Description longue.", encoding="utf-8")
    from accessi_code.analysis.images import make_local_resource_loader

    element = elements(
        '<img src="a.png" longdesc="desc.txt" aria-describedby="d"><p id="d">Passage.</p>',
        base_dir=tmp_path,
        resource_loader=make_local_resource_loader(tmp_path),
    )[0]
    sources = {description.source: description.content for description in element.descriptions}
    assert sources == {"longdesc": "Description longue.", "aria-describedby": "Passage."}


def test_svg_desc_and_two_labelledby_passages() -> None:
    element = elements('<p id="t">Titre</p><p id="d">Détail</p><svg aria-labelledby="t d"><desc>Desc SVG</desc></svg>')[
        0
    ]
    sources = {description.source: description.content for description in element.descriptions}
    assert sources == {"svg-desc": "Desc SVG", "aria-labelledby": "Détail"}


def test_image_file_resolution(tmp_path) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    img, svg = elements('<img src="a.png"><svg></svg>', base_dir=tmp_path)
    assert img.image_info is not None and img.image_info.image_path.endswith("a.png")
    assert svg.image_info is None


def test_referenced_text_validity() -> None:
    soup = BeautifulSoup('<p id="a">A</p><p id="b"></p><img aria-labelledby="a b">', "html.parser")
    assert referenced_text(soup.img, soup, "aria-labelledby") == ("A", False)


def test_alternative_reference_detection() -> None:
    assert is_alternative_reference("Graphique des ventes, description détaillée ci-dessous")
    assert not is_alternative_reference("Graphique des ventes")


def test_svg_real_text() -> None:
    soup = BeautifulSoup("<svg><text>Titre</text></svg><svg><text>A</text><path/></svg>", "html.parser")
    first, second = soup.find_all("svg")
    assert svg_has_only_real_text(first)
    assert not svg_has_only_real_text(second)

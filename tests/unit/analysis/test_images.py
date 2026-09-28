from bs4 import BeautifulSoup

from accessi_code.analysis.images import extract_images


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(
        html,
        "html.parser",
    )


def test_extract_images_keeps_detailed_description_sources_separate():
    html = """
    <figure>
        <img
            src="graph.png"
            alt="Graphique"
            longdesc="graph.html"
            aria-describedby="aria-description"
        >
        <figcaption>
            Le chiffre d'affaires augmente au premier trimestre.
        </figcaption>
    </figure>

    <p id="aria-description">
        Les valeurs progressent de janvier à mars.
    </p>
    """

    soup = parse_html(html)

    images = extract_images(
        soup,
        page_url="https://example.test/page.html",
        resource_loader=lambda url: "Description externe du graphique.",
    )

    assert len(images) == 1

    sources = {description.source for description in images[0].descriptions}

    assert "longdesc" in sources
    assert "aria-describedby" in sources

    longdesc = next(description for description in images[0].descriptions if description.source == "longdesc")

    assert longdesc.reference == "https://example.test/graph.html"

    assert longdesc.content == "Description externe du graphique."


def test_adjacent_link_is_kept_as_description_evidence():
    html = '<img src="graph.png" alt="Graphique"><a href="details.html">Détails du graphique</a>'

    soup = parse_html(html)

    descriptions = extract_images(
        soup,
    )[0].descriptions

    adjacent_link = next(description for description in descriptions if description.source == "adjacent_link")

    assert adjacent_link.reference == "details.html"
    assert adjacent_link.content == ""
    assert adjacent_link.available is False


def test_adjacent_link_resource_content_is_loaded():
    html = '<img src="graph.png" alt="Graphique"><a href="details.html">Détails du graphique</a>'

    soup = parse_html(html)

    descriptions = extract_images(
        soup,
        resource_loader=lambda reference: "Le graphique présente une hausse de 10 à 25 unités entre janvier et mars.",
    )[0].descriptions

    adjacent_link = next(description for description in descriptions if description.source == "adjacent_link")

    assert adjacent_link.reference == "details.html"
    assert adjacent_link.available is True
    assert adjacent_link.content == ("Le graphique présente une hausse de 10 à 25 unités entre janvier et mars.")

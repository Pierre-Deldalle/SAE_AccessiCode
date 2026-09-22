from accessi_code.ai.schemas import DescriptionAnalysis
from accessi_code.analysis.images import extract_images
from accessi_code.models.result import TestStatus as ResultStatus
from accessi_code.tests.theme_01_images.criterion_1_7_1 import Criterion17


# Vérifie que les sources de descriptions sont extraites séparément et que
# l'adresse longdesc est résolue relativement à l'URL de la page.
def test_extracts_all_detailed_description_sources():
    html = """
    <figure>
        <img src="graph.png" alt="Graphique" longdesc="graph.html"
             aria-describedby="aria-description">
        <figcaption>Le chiffre d'affaires augmente au premier trimestre.</figcaption>
    </figure>
    <p id="aria-description">Les valeurs progressent de janvier à mars.</p>
    <a href="details.html">Voir les données détaillées</a>
    """

    images = extract_images(
        html,
        page_url="https://example.test/page.html",
        resource_loader=lambda url: "Description externe du graphique.",
    )

    assert len(images) == 1
    assert {description.source for description in images[0].descriptions} == {
        "longdesc", "in_page", "aria-describedby"
    }
    assert images[0].descriptions[0].reference == "https://example.test/graph.html"


# Un lien placé immédiatement après l'image doit rester identifiable comme
# preuve distincte, avec son texte et sa référence href.
def test_adjacent_link_is_kept_as_evidence():
    html = '<img src="graph.png" alt="Graphique"><a href="details.html">Détails du graphique</a>'

    descriptions = extract_images(html)[0].descriptions

    assert descriptions[0].source == "adjacent_link"
    assert descriptions[0].content == "Détails du graphique"
    assert descriptions[0].reference == "details.html"


# Une ressource longdesc non chargée ne doit jamais être déclarée conforme.
def test_missing_longdesc_is_inconclusive_not_passed():
    result = Criterion17().run('<img src="graph.png" alt="Graphique" longdesc="missing.html">')

    assert result.status == ResultStatus.INCONCLUSIVE
    assert result.findings[0].evidence["error"] == "Ressource longdesc non chargée."


# Le faux analyseur simule l'IA et vérifie qu'un verdict positif est agrégé
# sans produire de finding.
def test_analyzer_result_is_aggregated_without_guessing():
    def analyzer(image, description):
        return DescriptionAnalysis(relevant=True, explanation="La description couvre les données visibles.", confidence="medium")

    result = Criterion17(analyzer=analyzer).run(
        '<img src="graph.png" alt="Graphique" aria-describedby="details">'
        '<p id="details">Le graphique montre une hausse régulière.</p>'
    )

    assert result.status == ResultStatus.PASS
    assert result.findings == []


# Un verdict IA négatif rend le test non conforme et conserve les informations
# manquantes dans les preuves du rapport.
def test_false_analyzer_result_fails():
    result = Criterion17(
        analyzer=lambda image, description: DescriptionAnalysis(
            relevant=False,
            explanation="Les valeurs importantes ne sont pas décrites.",
            missing_information=["valeurs"],
        )
    ).run('<img src="graph.png" alt="Graphique" aria-describedby="details"><p id="details">Un graphique.</p>')

    assert result.status == ResultStatus.FAIL
    assert "valeurs" in result.findings[0].message
    assert result.findings[0].evidence["analysis"]["missing_information"] == ["valeurs"]
from accessi_code.ai.schemas import LanguageAnalysis, TitleAnalysis
from accessi_code.ai.ollama_client.page_analyzer import OllamaPageAnalyzer
from accessi_code.models.result import TestStatus as ResultStatus
from accessi_code.tests.theme_08_elements_obligatoires.criterion_8_4_1 import Criterion841
from accessi_code.tests.theme_08_elements_obligatoires.criterion_8_6_1 import Criterion861


def test_language_analysis_passes_when_declared_language_matches_content():
    """Un verdict positif IA produit un résultat PASS sans finding."""
    calls = []

    def analyzer(lang, content):
        calls.append((lang, content))
        return LanguageAnalysis(True, "fr", "Le contenu est en français.", confidence="high")

    result = Criterion841(analyzer=analyzer).run(
        '<html lang="fr"><body><main>Bienvenue sur notre service.</main></body></html>'
    )

    assert result.status == ResultStatus.PASS
    assert calls[0][0] == "fr"
    assert calls[0][1] == "Bienvenue sur notre service."
    assert result.findings == []


def test_language_analysis_fails_when_declared_language_is_incorrect():
    """Un verdict négatif conserve la langue détectée dans les preuves."""
    result = Criterion841(
        analyzer=lambda lang, content: LanguageAnalysis(
            False, "en", "Le contenu principal est en anglais."
        )
    ).run('<html lang="fr"><body><p>Welcome to our service.</p></body></html>')

    assert result.status == ResultStatus.FAIL
    assert result.findings[0].evidence["analysis"]["detected_language"] == "en"


def test_missing_language_is_a_deterministic_failure():
    """Une page sans lang échoue avant toute sollicitation de l'IA."""
    result = Criterion841().run('<html><body><p>Bienvenue.</p></body></html>')

    assert result.status == ResultStatus.FAIL
    assert "lang" in result.findings[0].message


def test_title_analysis_compares_title_heading_and_page_content():
    """Le titre, le h1 et le contenu sont transmis ensemble à l'analyseur."""
    calls = []

    def analyzer(title, heading, content):
        calls.append((title, heading, content))
        return TitleAnalysis(True, "Le titre décrit la page.", confidence="high")

    result = Criterion861(analyzer=analyzer).run(
        "<html><head><title>Inscription au service</title></head>"
        "<body><main><h1>Inscription au service</h1>"
        "<p>Créez votre compte.</p></main></body></html>"
    )

    assert result.status == ResultStatus.PASS
    assert calls[0][0:2] == ("Inscription au service", "Inscription au service")
    assert "Créez votre compte." in calls[0][2]


def test_title_analysis_fails_when_title_is_not_relevant():
    """Un titre incohérent avec le h1 rend le critère non conforme."""
    result = Criterion861(
        analyzer=lambda title, heading, content: TitleAnalysis(
            False, "Le titre ne correspond pas à l'objectif de la page."
        )
    ).run(
        "<html><head><title>Accueil</title></head>"
        "<body><h1>Réinitialiser son mot de passe</h1></body></html>"
    )

    assert result.status == ResultStatus.FAIL
    assert "objectif" in result.findings[0].message
    assert result.findings[0].evidence["heading"] == "Réinitialiser son mot de passe"


def test_missing_title_is_a_deterministic_failure():
    """Une page sans title échoue de façon déterministe."""
    result = Criterion861().run(
        "<html><body><h1>Accueil</h1><p>Bienvenue.</p></body></html>"
    )

    assert result.status == ResultStatus.FAIL
    assert result.findings[0].element == "title"


def test_corrupted_title_explanation_uses_a_short_fallback():
    """Une réponse IA répétitive ne doit pas polluer le rapport CSV."""
    fallback = "Le titre est trop générique."
    corrupted = "Le titre est trop générique undineer" * 40

    assert OllamaPageAnalyzer._explanation(corrupted, fallback) == fallback

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_4 import (
    Test941 as RGAA941,
)
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_4 import (
    Test942 as RGAA942,
)


def test_941_empty_q_tag_fails(context_factory, run_rgaa):
    """Test 9.4.1: Balise <q> vide doit échouer."""
    html = """
    <p>Voici une citation <q></q> qui est vide.</p>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA941(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Vérifier qu'il y a un finding indiquant que la balise <q> est vide
    empty_q_findings = [f for f in result.findings if "La balise <q> est vide" in f.message]
    assert len(empty_q_findings) >= 1
    assert result.tested_elements == 1  # Une balise <q> testée


def test_941_proper_q_tag_passes(context_factory, run_rgaa):
    """Test 9.4.1: Balise <q> avec contenu doit passer."""
    html = """
    <p>Comme dirait <q>citation courte</q>, c'est une vraie citation.</p>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA941(), context)

    assert result.status == Status.PASS
    assert result.findings == []  # Pas d'erreurs
    assert result.tested_elements == 1  # Une balise <q> testée


def test_941_multiple_q_tags_mixed(context_factory, run_rgaa):
    """Test 9.4.1: Plusieurs balises <q> avec certaines vides et d'autres valides."""
    html = """
    <p>Premier <q>citation valide</q> et deuxième <q></q> vide.</p>
    <p>Troisième <q>autre citation valide</q>.</p>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA941(), context)

    assert result.status == Status.FAIL  # À cause de la balise vide
    assert len(result.findings) >= 1
    empty_q_findings = [f for f in result.findings if "La balise <q> est vide" in f.message]
    assert len(empty_q_findings) >= 1
    assert result.tested_elements == 3  # Trois balises <q> testées


def test_941_no_q_tags_not_applicable(context_factory, run_rgaa):
    """Test 9.4.1: Absence de balises <q> doit retourner NOT_APPLICABLE."""
    html = """
    <p>Paragraphe sans balise q.</p>
    <div>Autre contenu</div>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA941(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert "aucune balise <q> détectée" in result.summary.lower()


def test_941_q_tag_with_whitespace_only_passes(context_factory, run_rgaa):
    """Test 9.4.1: Balise <q> avec seulement des espaces blancs - on vérifie get_text(strip=True)."""
    html = """
    <p>Citation <q>   </q> avec seulement des espaces.</p>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA941(), context)

    # Comme on utilise get_text(strip=True), une balise avec seulement des espaces sera considérée comme vide
    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    empty_q_findings = [f for f in result.findings if "La balise <q> est vide" in f.message]
    assert len(empty_q_findings) >= 1


def test_942_empty_blockquote_fails(context_factory, run_rgaa):
    """Test 9.4.2: Balise <blockquote> vide doit échouer."""
    html = """
    <blockquote></blockquote>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA942(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Vérifier qu'il y a un finding indiquant que la balise <blockquote> est vide
    empty_blockquote_findings = [f for f in result.findings if "La balise <blockquote> est vide" in f.message]
    assert len(empty_blockquote_findings) >= 1
    assert result.tested_elements == 1  # Une balise <blockquote> testée


def test_942_proper_blockquote_passes(context_factory, run_rgaa):
    """Test 9.4.2: Balise <blockquote> avec contenu doit passer."""
    html = """
    <blockquote>Ceci est une longue citation qui devrait utiliser la balise blockquote.</blockquote>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA942(), context)

    assert result.status == Status.PASS
    assert result.findings == []  # Pas d'erreurs
    assert result.tested_elements == 1  # Une balise <blockquote> testée


def test_942_blockquote_with_only_whitespace_fails(context_factory, run_rgaa):
    """Test 9.4.2: Balise <blockquote> avec seulement des espaces blancs doit échouer."""
    html = """
    <blockquote>   </blockquote>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA942(), context)

    # Comme on utilise get_text(strip=True), une balise avec seulement des espaces sera considérée comme vide
    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    empty_blockquote_findings = [f for f in result.findings if "La balise <blockquote> est vide" in f.message]
    assert len(empty_blockquote_findings) >= 1


def test_942_blockquote_with_block_content_passes(context_factory, run_rgaa):
    """Test 9.4.2: Balise <blockquote> contenant des éléments blocs doit passer."""
    html = """
    <blockquote>
        <p>Ceci est un paragraphe à l'intérieur d'une citation longue.</p>
        <p>Deuxième paragraphe de la citation.</p>
    </blockquote>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA942(), context)

    assert result.status == Status.PASS
    assert result.findings == []  # Pas d'erreurs
    assert result.tested_elements == 1  # Une balise <blockquote> testée


def test_942_multiple_blockquotes_mixed(context_factory, run_rgaa):
    """Test 9.4.2: Plusieurs balises <blockquote> avec certaines vides et d'autres valides."""
    html = """
    <blockquote>Première citation longue valide.</blockquote>
    <blockquote></blockquote>
    <blockquote>Troisième citation longue également valide.</blockquote>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA942(), context)

    assert result.status == Status.FAIL  # À cause de la balise vide
    assert len(result.findings) >= 1
    empty_blockquote_findings = [f for f in result.findings if "La balise <blockquote> est vide" in f.message]
    assert len(empty_blockquote_findings) >= 1
    assert result.tested_elements == 3  # Trois balises <blockquote> testées


def test_942_no_blockquotes_not_applicable(context_factory, run_rgaa):
    """Test 9.4.2: Absence de balises <blockquote> doit retourner NOT_APPLICABLE."""
    html = """
    <p>Paragraphe sans balise blockquote.</p>
    <div>Autre contenu</div>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA942(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert "aucune balise <blockquote> détectée" in result.summary.lower()


def test_941_and_942_together(context_factory, run_rgaa):
    """Test combiné: Vérifier que les deux tests fonctionnent indépendamment."""
    html = """
    <p>Citation courte <q>valide</q>.</p>
    <blockquote>Citation longue valide.</blockquote>
    <p>Autre citation courte <q></q> vide.</p>
    """
    context = context_factory(html)

    # Test 9.4.1
    result_941 = run_rgaa(RGAA941(), context)
    assert result_941.status == Status.FAIL  # À cause de la balise <q> vide
    empty_q_findings = [f for f in result_941.findings if "La balise <q> est vide" in f.message]
    assert len(empty_q_findings) >= 1

    # Test 9.4.2
    result_942 = run_rgaa(RGAA942(), context)
    assert result_942.status == Status.PASS  # La balise <blockquote> est valide
    assert result_942.findings == []
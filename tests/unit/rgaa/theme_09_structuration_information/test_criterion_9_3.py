from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_3 import (
    Test931 as RGAA931,
    Test932 as RGAA932,
    Test933 as RGAA933,
)


def test_931_unordered_list_with_ul_li_passes(context_factory, run_rgaa):
    """Test 9.3.1: Liste non ordonnée avec <ul> et <li> doit passer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA931(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements > 0


def test_931_unordered_list_with_wai_aria_passes(context_factory, run_rgaa):
    """Test 9.3.1: Liste non ordonnée avec role="list"/role="listitem" doit passer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <div role="list">
            <div role="listitem">Item 1</div>
            <div role="listitem">Item 2</div>
            <div role="listitem">Item 3</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA931(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements > 0


def test_931_unordered_list_missing_structure_fails(context_factory, run_rgaa):
    """Test 9.3.1: Liste non ordonnée sans structure appropriée doit échouer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <ul>
            <div>Item 1</div>
            <div>Item 2</div>
        </ul>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA931(), context)

    # Selon notre implémentation, ceci pourrait échouer car les <div> ne sont pas des <li>
    # Mais on est permissif dans notre implémentation actuelle - on vérifie juste qu'il y a des <li>
    # Dans ce cas, il n'y a pas de <li> donc ça devrait échouer
    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    assert result.tested_elements > 0


def test_931_unordered_list_wai_aria_missing_listitem_fails(context_factory, run_rgaa):
    """Test 9.3.1: Élément role="list" sans role="listitem" doit échouer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <div role="list">
            <div>Item 1</div>
            <div>Item 2</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA931(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Vérifier qu'il y a bien une finding concernant le manque de role="listitem"
    listitem_findings = [f for f in result.findings if "listitem" in f.message]
    assert len(listitem_findings) >= 1
    assert result.tested_elements > 0


def test_932_ordered_list_with_ol_li_passes(context_factory, run_rgaa):
    """Test 9.3.2: Liste ordonnée avec <ol> et <li> doit passer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <ol>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ol>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA932(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements > 0


def test_932_ordered_list_with_wai_aria_passes(context_factory, run_rgaa):
    """Test 9.3.2: Liste ordonnée avec role="list"/role="listitem" doit passer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <div role="list">
            <div role="listitem">Item 1</div>
            <div role="listitem">Item 2</div>
            <div role="listitem">Item 3</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA932(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements > 0


def test_932_ordered_list_missing_structure_fails(context_factory, run_rgaa):
    """Test 9.3.2: Liste ordonnée sans structure appropriée doit échouer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <ol>
            <div>Item 1</div>
            <div>Item 2</div>
        </ol>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA932(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    assert result.tested_elements > 0


def test_932_ordered_list_wai_aria_missing_listitem_fails(context_factory, run_rgaa):
    """Test 9.3.2: Élément role="list" sans role="listitem" doit échouer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <div role="list">
            <div>Item 1</div>
            <div>Item 2</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA932(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Vérifier qu'il y a bien une finding concernant le manque de role="listitem"
    listitem_findings = [f for f in result.findings if "listitem" in f.message]
    assert len(listitem_findings) >= 1
    assert result.tested_elements > 0


def test_933_description_list_with_dl_dt_dd_passes(context_factory, run_rgaa):
    """Test 9.3.3: Liste de description avec <dl>, <dt> et <dd> doit passer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <dl>
            <dt>Terme 1</dt>
            <dd>Description 1</dd>
            <dt>Terme 2</dt>
            <dd>Description 2</dd>
        </dl>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA933(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements > 0


def test_933_description_list_missing_elements_fails(context_factory, run_rgaa):
    """Test 9.3.3: Liste de description sans <dt> ou <dd> doit échouer."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <dl>
            <div>Terme 1</div>
            <div>Description 1</div>
        </dl>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA933(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Vérifier qu'il y a bien une finding concernant le manque de dt/dd
    dt_dd_findings = [f for f in result.findings if "dt" in f.message or "dd" in f.message]
    assert len(dt_dd_findings) >= 1
    assert result.tested_elements > 0


def test_933_empty_description_list_passes(context_factory, run_rgaa):
    """Test 9.3.3: Liste de description vide doit passer (pas de violation)."""
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <body>
        <dl></dl>
    </body>
    </html>
    """
    context = context_factory(html)

    result = run_rgaa(RGAA933(), context)

    # Une liste de description vide n'est pas une violation en soi
    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements > 0  # On teste quand même l'élément dl
from accessi_code.ai.text_safety import clean_explanation


def test_repetitive_explanation_is_rejected():
    cleaned, corrupted = clean_explanation('accessibility-driven ' * 30)
    assert corrupted is True
    assert 'vérification' in cleaned


def test_normal_explanation_kept():
    cleaned, corrupted = clean_explanation('Le titre décrit correctement la page.')
    assert corrupted is False
    assert cleaned == 'Le titre décrit correctement la page.'

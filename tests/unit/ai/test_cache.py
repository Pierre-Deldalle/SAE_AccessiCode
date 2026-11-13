import pytest

from accessi_code.ai.cache import AnalysisCache, make_key


def test_make_key_is_stable_and_content_based() -> None:
    assert make_key("a", {"x": 1, "y": 2}) == make_key("a", {"y": 2, "x": 1})
    assert make_key("a", "texte") != make_key("a", "autre texte")


def test_cache_returns_stored_value() -> None:
    cache: AnalysisCache[str] = AnalysisCache()
    cache.set("k", "valeur")
    assert cache.get("k") == "valeur"
    assert cache.get("absent") is None


def test_cache_evicts_least_recently_used_entry() -> None:
    cache: AnalysisCache[int] = AnalysisCache(max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # « a » devient le plus récent.
    cache.set("c", 3)

    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3
    assert len(cache) == 2


def test_cache_rejects_invalid_size() -> None:
    with pytest.raises(ValueError):
        AnalysisCache(max_entries=0)

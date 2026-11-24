"""Animations CSS : sources de style localisées et emplacement de chaque animation."""

from accessi_code.analysis.animations import css_animations, css_texts

BLINK = "@keyframes blink { 50% { opacity: 0 } }"


def test_css_texts_blank_comments_without_moving_lines(context_factory):
    context = context_factory("<html><head><style>/* a\nb */ p { color: red }</style></head></html>")
    [sheet] = css_texts(context)
    assert sheet.text == "    \n     p { color: red }"
    assert sheet.location(sheet.text.index("p {"))["line"] == 2


def test_animation_in_style_tag_is_located_in_the_page(context_factory):
    html = f"<html><head>\n<style>\n{BLINK}\n.x {{ animation: blink 0.2s infinite }}\n</style></head>"
    html += '<body><p class="x">Promo</p></body></html>'
    [animation] = css_animations(context_factory(html))
    assert animation.location == {"file": None, "line": 4, "snippet": ".x { animation: blink 0.2s infinite }"}


def test_animation_in_stylesheet_file_is_located_in_that_file(context_factory, tmp_path):
    context = context_factory('<p class="x">Promo</p>')
    css = f"{BLINK}\n\n@media screen {{\n  .x {{ animation: blink 1s }}\n}}"
    context.css_sources[tmp_path / "css" / "promo.css"] = css
    [animation] = css_animations(context)
    assert animation.location == {"file": "promo.css", "line": 4, "snippet": ".x { animation: blink 1s }"}


def test_animation_in_style_attribute_is_located_on_the_element(context_factory):
    html = f'<style>{BLINK}</style>\n\n<p style="animation: blink 1s">Promo</p>'
    [animation] = css_animations(context_factory(html))
    assert animation.location == {"file": None, "line": 3, "snippet": '<p style="animation: blink 1s">Promo</p>'}

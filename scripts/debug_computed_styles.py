"""Teste l'extraction des styles calculés des textes."""

import asyncio
from pathlib import Path

from accessi_code.input.extractors.computed_styles import (
    extract_text_styles,
)


async def main() -> None:
    html_path = Path("test_files/color_site/index.html")

    observations = await extract_text_styles(html_path)

    print(f"Fragments de texte détectés : {len(observations)}")

    for observation in observations:
        print(f"\nÉlément : {observation.element}")
        print(f"Texte : {observation.text[:100]}")
        print(f"Couleur : {observation.color}")
        print(f"Fond : {observation.background_color}")
        print(f"Taille : {observation.font_size_px}px")
        print(f"Graisse : {observation.font_weight}")

        if observation.review_reason:
            print(
                "Vérification nécessaire :",
                observation.review_reason,
            )


if __name__ == "__main__":
    asyncio.run(main())

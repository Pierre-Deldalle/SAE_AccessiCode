"""Exemples courts de correction HTML pour les éléments obligatoires."""


def html_example(recommendation: str, before: str, after: str) -> str:
    example = f"{recommendation}\nAvant : {before}\nAprès : {after}"
    # Le rapport limite la longueur des recommandations affichées.
    if len(" ".join(example.split())) > 300:
        return recommendation
    return example

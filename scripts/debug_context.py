"""Affiche le contenu extrait d'un audit local pour faciliter le debug."""

from pathlib import Path

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.models.audit_context import AuditContext


def build_debug_context(
    site_name: str = "basic_site",
) -> AuditContext:
    """
    Construit un AuditContext à partir d'un site présent dans test_files.
    """
    site_directory = (
        Path("test_files")
        / site_name
    )

    index_path = (
        site_directory
        / "index.html"
    )

    if not index_path.is_file():
        raise FileNotFoundError(
            f"Fichier principal introuvable : {index_path}"
        )

    files = [
        index_path,
    ]

    files.extend(
        sorted(
            path
            for path
            in site_directory.iterdir()
            if (
                path.is_file()
                and path != index_path
            )
        )
    )

    builder = AuditContextBuilder(
        workspace_root=Path(
            "workspace"
        ),
    )

    return builder.build(
        files
    )


def print_debug_context(
    context: AuditContext,
) -> None:
    """
    Affiche les principales informations extraites de l'AuditContext.
    """
    print("=== AUDIT CONTEXT ===")
    print(f"Audit ID : {context.audit_id}")
    print(f"Workspace : {context.workspace_path}")
    print(f"HTML : {context.html_path}")
    print(f"DOCTYPE : {context.doctype}")

    print("\n=== FICHIERS ===")

    for file in context.files:
        print(f"- {file.original_name} ({file.mime_type}) -> {file.path}")

    print("\n=== IMAGES ===")

    for image in context.image_files:
        print(f"- {image}")

    print("\n=== CAPACITÉS ===")

    for capability in context.get_capabilities():
        print(f"- {capability.value}")

    print("\n=== DOM ===")

    if context.dom is not None:
        print(f"Images trouvées : {len(context.dom.find_all('img'))}")
        print(f"Formulaires trouvés : {len(context.dom.find_all('form'))}")
        print(f"Inputs trouvés : {len(context.dom.find_all('input'))}")


def main() -> None:
    context = build_debug_context()

    print_debug_context(context)


if __name__ == "__main__":
    main()

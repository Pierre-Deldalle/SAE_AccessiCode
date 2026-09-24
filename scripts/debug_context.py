"""Affiche le contenu extrait d'un audit local pour faciliter le debug."""

from pathlib import Path

from accessi_code.input.context_builder import AuditContextBuilder
from accessi_code.models.audit_context import AuditContext


def build_debug_context() -> AuditContext:
    """
    Construit un AuditContext à partir des fichiers du site de test local.

    Cette fonction peut être réutilisée par d'autres scripts de debug.
    """
    builder = AuditContextBuilder(
        workspace_root=Path("workspace"),
    )

    return builder.build(
        [
            Path("test_files/basic_site/index.html"),
            Path("test_files/basic_site/logo.png"),
        ]
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

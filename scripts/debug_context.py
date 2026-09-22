"""Affiche le contenu extrait d'un audit local pour faciliter le debug."""

from pathlib import Path

from accessi_code.input.context_builder import (
    AuditContextBuilder,
)


builder = AuditContextBuilder(
    workspace_root=Path("workspace"),
)

context = builder.build(
    [
        Path("test_files/basic_site/index.html"),
        Path("test_files/basic_site/logo.png"),
    ]
)

print("=== AUDIT CONTEXT ===")
print(f"Audit ID : {context.audit_id}")
print(f"Workspace : {context.workspace_path}")
print(f"HTML : {context.html_path}")
print(f"DOCTYPE : {context.doctype}")

print("\n=== FICHIERS ===")
for file in context.files:
    print(
        f"- {file.original_name} "
        f"({file.mime_type}) -> {file.path}"
    )

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
from pathlib import Path

from accessi_code.input.extractors.html import extract_html
from accessi_code.input.file_classifier import (
    is_html_file,
    is_image_file,
)
from accessi_code.input.file_collector import FileCollector
from accessi_code.models.audit_context import AuditContext


class AuditContextBuilder:
    """
    Construit un AuditContext à partir de fichiers fournis
    par l'utilisateur.
    """

    def __init__(
        self,
        workspace_root: Path,
    ):
        self.collector = FileCollector(
            workspace_root=workspace_root
        )

    def build(
        self,
        input_files: list[Path],
    ) -> AuditContext:
        """
        Construit un contexte complet à partir
        des fichiers reçus.
        """

        (
            audit_id,
            workspace_path,
            files,
        ) = self.collector.collect(input_files)

        context = AuditContext(
            audit_id=audit_id,
            workspace_path=workspace_path,
            files=files,
        )

        self._extract_files(context)

        return context

    def _extract_files(
        self,
        context: AuditContext,
    ) -> None:
        """
        Extrait les informations utiles de chaque fichier.
        """

        html_files = [
            file
            for file in context.files
            if is_html_file(file.path)
        ]

        image_files = [
            file
            for file in context.files
            if is_image_file(file.path)
        ]

        context.image_files = [
            file.path
            for file in image_files
        ]

        if html_files:
            self._extract_main_html(
                context,
                html_files[0].path,
            )

    @staticmethod
    def _extract_main_html(
        context: AuditContext,
        html_path: Path,
    ) -> None:
        """
        Extrait le document HTML principal.

        Pour le prototype, le premier fichier HTML
        rencontré est considéré comme la page principale.
        """

        extraction = extract_html(
            html_path
        )

        context.html_path = html_path
        context.html_source = extraction.source
        context.dom = extraction.dom
        context.doctype = extraction.doctype
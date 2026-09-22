"""Import et isolation des fichiers d'un audit."""

import mimetypes
import shutil
import uuid
from pathlib import Path

from accessi_code.models.audit_file import AuditFile


class FileCollector:
    """
    Prépare les fichiers d'un audit dans un workspace dédié.

    Le collecteur ne déplace ni ne modifie les fichiers d'origine : il crée
    une copie dans ``<workspace_root>/audits/<audit_id>/source``.

    Attributes:
        workspace_root: Répertoire parent des workspaces d'audit.
    """

    def __init__(self, workspace_root: Path):
        """Initialise un collecteur utilisant le workspace indiqué."""

        self.workspace_root = workspace_root

    def collect(
        self,
        input_files: list[Path],
    ) -> tuple[str, Path, list[AuditFile]]:
        """
        Copie les fichiers reçus dans un nouveau workspace.

        Args:
            input_files: Chemins des fichiers à importer. L'ordre est
                conservé dans la liste retournée.

        Returns:
            Un tuple contenant l'identifiant d'audit, le chemin du workspace
            créé et les métadonnées des fichiers copiés.

        Raises:
            FileNotFoundError: Si l'un des fichiers d'entrée n'existe pas.
        """

        audit_id = uuid.uuid4().hex

        workspace_path = (
            self.workspace_root
            / "audits"
            / audit_id
        )

        source_path = workspace_path / "source"

        source_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        audit_files: list[AuditFile] = []

        for input_path in input_files:
            input_path = Path(input_path)

            if not input_path.exists():
                raise FileNotFoundError(
                    f"Le fichier n'existe pas : {input_path}"
                )

            destination = self._get_unique_destination(
                source_path,
                input_path.name,
            )

            shutil.copy2(
                input_path,
                destination,
            )

            mime_type, _ = mimetypes.guess_type(
                destination
            )

            audit_files.append(
                AuditFile(
                    original_name=input_path.name,
                    path=destination,
                    extension=destination.suffix.lower(),
                    mime_type=mime_type,
                )
            )

        return (
            audit_id,
            workspace_path,
            audit_files,
        )

    @staticmethod
    def _get_unique_destination(
        directory: Path,
        filename: str,
    ) -> Path:
        """
        Retourne un chemin libre sans écraser un fichier existant.

        En cas de collision, un suffixe numérique est ajouté au nom de base
        (par exemple ``style.css``, puis ``style_1.css``).
        """

        destination = directory / filename

        if not destination.exists():
            return destination

        original = Path(filename)

        index = 1

        while True:
            candidate = directory / (
                f"{original.stem}_{index}{original.suffix}"
            )

            if not candidate.exists():
                return candidate

            index += 1

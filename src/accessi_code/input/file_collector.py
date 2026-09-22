import mimetypes
import shutil
import uuid
from pathlib import Path

from accessi_code.models.audit_file import AuditFile


class FileCollector:
    """
    Prépare les fichiers d'un audit dans un workspace dédié.
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def collect(
        self,
        input_files: list[Path],
    ) -> tuple[str, Path, list[AuditFile]]:
        """
        Copie les fichiers reçus dans un nouveau workspace.

        Returns:
            audit_id
            workspace_path
            liste des AuditFile créés
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
        Évite d'écraser un fichier si plusieurs fichiers
        possèdent le même nom.
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
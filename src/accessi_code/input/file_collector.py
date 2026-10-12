"""Import et isolation des fichiers d'un audit."""

import mimetypes
import shutil
import uuid
from pathlib import Path

from accessi_code.models.audit_file import AuditFile


class FileCollector:
    """
    Prépare les fichiers d'un audit dans un workspace dédié.

    Les fichiers d'origine ne sont ni déplacés ni modifiés.

    Deux modes sont disponibles :
    - import individuel : fichiers copiés à la racine de source/ ;
    - import de site : arborescence relative à site_root préservée.
    """

    def __init__(self, workspace_root: Path):
        """Initialise un collecteur utilisant le workspace indiqué."""

        self.workspace_root = workspace_root

    def collect(
        self,
        input_files: list[Path],
        site_root: Path | None = None,
    ) -> tuple[str, Path, list[AuditFile]]:
        """
        Copie les fichiers reçus dans un nouveau workspace.

        Args:
            input_files: Chemins des fichiers à importer.
            site_root: Dossier racine du site, facultatif. Lorsqu'il est
                fourni, les chemins relatifs sont conservés.

        Returns:
            Identifiant de l'audit, chemin du workspace et fichiers copiés.

        Raises:
            FileNotFoundError: Si un fichier est introuvable.
            NotADirectoryError: Si site_root n'est pas un dossier.
            ValueError: Si un fichier est hors du site_root, ou si
                plusieurs entrées désignent le même chemin du site.
        """

        root = None

        if site_root is not None:
            root = Path(site_root).resolve(strict=True)

            if not root.is_dir():
                raise NotADirectoryError(
                    f"La racine du site n'est pas un dossier : {root}"
                )

        # Valider les fichiers avant de créer le workspace.
        inputs: list[tuple[Path, Path | None]] = []
        relative_paths: set[Path] = set()

        for input_path in input_files:
            input_path = Path(input_path)

            if not input_path.is_file():
                raise FileNotFoundError(
                    f"Le fichier n'existe pas : {input_path}"
                )

            resolved_path = input_path.resolve(strict=True)
            relative_path = None

            if root is not None:
                try:
                    relative_path = resolved_path.relative_to(root)
                except ValueError as error:
                    raise ValueError(
                        f"Le fichier est extérieur à la racine du site : "
                        f"{input_path}"
                    ) from error

                if relative_path in relative_paths:
                    raise ValueError(
                        f"Fichier présent plusieurs fois dans l'import : "
                        f"{relative_path}"
                    )

                relative_paths.add(relative_path)

            inputs.append((resolved_path, relative_path))

        audit_id = uuid.uuid4().hex

        workspace_path = self.workspace_root / "audits" / audit_id
        source_path = workspace_path / "source"

        source_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        audit_files: list[AuditFile] = []

        for input_path, relative_path in inputs:
            if relative_path is None:
                # Mode historique : import de fichiers individuels.
                destination = self._get_unique_destination(
                    source_path,
                    input_path.name,
                )
            else:
                # Mode site complet : préserver l'arborescence.
                destination = source_path / relative_path

                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                if destination.exists():
                    raise FileExistsError(
                        f"Destination déjà existante : {destination}"
                    )

            shutil.copy2(
                input_path,
                destination,
            )

            mime_type, _ = mimetypes.guess_type(destination)

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

        En cas de collision, un suffixe numérique est ajouté au nom.
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
from __future__ import annotations

from collections.abc import (
    Iterable,
    Iterator,
)

from accessi_code.rgaa.base import RGAATest


class TestRegistry:
    """
    Registre ordonné des tests RGAA disponibles.

    Les tests sont conservés dans leur ordre d'enregistrement.
    Deux tests ne peuvent pas avoir le même test_id.
    """

    def __init__(
        self,
        tests: Iterable[RGAATest] | None = None,
    ):
        self._tests: dict[
            str,
            RGAATest,
        ] = {}

        if tests is not None:
            self.register_many(tests)

    def register(
        self,
        test: RGAATest,
    ) -> None:
        """
        Enregistre un test RGAA.
        """
        self._validate_test(test)

        if test.test_id in self._tests:
            raise ValueError(f"Un test avec l'identifiant {test.test_id!r} est déjà enregistré.")

        self._tests[test.test_id] = test

    def register_many(
        self,
        tests: Iterable[RGAATest],
    ) -> None:
        """
        Enregistre plusieurs tests de manière atomique.

        Si l'un des tests est invalide ou dupliqué, aucun des nouveaux
        tests n'est ajouté.
        """
        pending = list(tests)

        pending_ids: set[str] = set()

        for test in pending:
            self._validate_test(test)

            if test.test_id in pending_ids:
                raise ValueError(f"Plusieurs tests à enregistrer utilisent l'identifiant {test.test_id!r}.")

            if test.test_id in self._tests:
                raise ValueError(f"Un test avec l'identifiant {test.test_id!r} est déjà enregistré.")

            pending_ids.add(test.test_id)

        for test in pending:
            self._tests[test.test_id] = test

    def get(
        self,
        test_id: str,
    ) -> RGAATest | None:
        """
        Retourne un test à partir de son identifiant.
        """
        return self._tests.get(test_id)

    def get_all(
        self,
    ) -> tuple[RGAATest, ...]:
        """
        Retourne tous les tests dans leur ordre d'enregistrement.
        """
        return tuple(self._tests.values())

    def __iter__(
        self,
    ) -> Iterator[RGAATest]:
        return iter(self._tests.values())

    def __len__(
        self,
    ) -> int:
        return len(self._tests)

    def __contains__(
        self,
        test_id: str,
    ) -> bool:
        return test_id in self._tests

    @staticmethod
    def _validate_test(
        test: RGAATest,
    ) -> None:
        """
        Vérifie qu'un objet respecte le contrat minimal du registre.
        """
        if not isinstance(
            test,
            RGAATest,
        ):
            raise TypeError("Le registre accepte uniquement des instances de RGAATest.")

        if (
            not isinstance(
                test.test_id,
                str,
            )
            or not test.test_id.strip()
        ):
            raise ValueError("Un test RGAA doit posséder un test_id non vide.")

        if (
            not isinstance(
                test.criterion_id,
                str,
            )
            or not test.criterion_id.strip()
        ):
            raise ValueError("Un test RGAA doit posséder un criterion_id non vide.")

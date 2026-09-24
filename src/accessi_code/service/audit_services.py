from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AuditServices:
    """
    Conteneur des services optionnels utilisables par les tests RGAA.

    Le moteur ne dépend d'aucune implémentation concrète.
    Les services réels seront injectés par l'application.
    """

    image_analyzer: Any | None = None
    page_analyzer: Any | None = None


"""from __future__ import annotations

from dataclasses import dataclass

from accessi_code.ai.analyzers.image_analyzer import (
    OllamaImageAnalyzer,
)
from accessi_code.ai.analyzers.page_analyzer import (
    OllamaPageAnalyzer,
)"""


"""@dataclass(slots=True)
class AuditServices:
    
    Services externes utilisables par les tests RGAA.

    Ils sont optionnels afin que les contrôles déterministes puissent
    fonctionner même lorsque les modèles IA ne sont pas disponibles.
    

    image_analyzer: OllamaImageAnalyzer | None = None

    page_analyzer: OllamaPageAnalyzer | None = None"""


"""def build_default_audit_services() -> AuditServices:
    
    Construit les services IA configurés pour l'application.

    Les imports de configuration sont volontairement réalisés ici afin
    que l'import du moteur n'exige pas immédiatement un fichier .env.
    
    from accessi_code.ai.clients.llm import (
        OllamaLLM,
    )
    from accessi_code.ai.clients.vlm import (
        OllamaVLM,
    )

    from accessi_code.config import settings

    llm = OllamaLLM(
        host=settings.OLLAMA_HOST,
        model=settings.LLM_MODEL,
    )

    vlm = OllamaVLM(
        host=settings.OLLAMA_HOST,
        model=settings.VLM_MODEL,
    )

    return AuditServices(
        image_analyzer=(
            OllamaImageAnalyzer(
                vlm=vlm,
                llm=llm,
            )
        ),
        page_analyzer=(
            OllamaPageAnalyzer(
                llm=llm,
            )
        ),
    )"""

from __future__ import annotations

from accessi_code.ai.analyzers.image_analyzer import (
    OllamaImageAnalyzer,
)
from accessi_code.ai.analyzers.page_analyzer import (
    OllamaPageAnalyzer,
)
from accessi_code.ai.clients.llm import OllamaLLM
from accessi_code.ai.clients.vlm import OllamaVLM
from accessi_code.service.audit_services import (
    AuditServices,
)


def build_default_audit_services(
    *,
    ollama_host: str,
    llm_model: str,
    vlm_model: str,
) -> AuditServices:
    """
    Construit les services IA réels utilisés par l'application.
    """
    llm = OllamaLLM(
        host=ollama_host,
        model=llm_model,
    )

    vlm = OllamaVLM(
        host=ollama_host,
        model=vlm_model,
    )

    return AuditServices(
        image_analyzer=OllamaImageAnalyzer(
            vlm=vlm,
            llm=llm,
        ),
        page_analyzer=OllamaPageAnalyzer(
            llm=llm,
        ),
    )

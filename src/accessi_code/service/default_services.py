from __future__ import annotations

from accessi_code.ai.analyzers.image_analyzer import (
    OllamaImageAnalyzer,
)
from accessi_code.ai.analyzers.page_analyzer import (
    OllamaPageAnalyzer,
)
from accessi_code.ai.analyzers.sensory_analyzer import OllamaSensoryAnalyzer
from accessi_code.ai.analyzers.structure_analyzer import OllamaStructureAnalyzer
from accessi_code.ai.analyzers.text_relevance_analyzer import OllamaTextRelevanceAnalyzer
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

    # Partagé : l'analyse sensorielle des images réutilise ses observations visuelles.
    image_analyzer = OllamaImageAnalyzer(
        vlm=vlm,
        llm=llm,
    )

    return AuditServices(
        image_analyzer=image_analyzer,
        page_analyzer=OllamaPageAnalyzer(
            llm=llm,
        ),
        text_relevance_analyzer=OllamaTextRelevanceAnalyzer(llm),
        sensory_analyzer=OllamaSensoryAnalyzer(llm, image_analyzer),
        structure_analyzer=OllamaStructureAnalyzer(llm),
    )

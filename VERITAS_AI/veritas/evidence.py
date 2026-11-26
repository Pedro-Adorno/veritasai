"""Gancho para uma FUTURA camada de verificação de evidências (não implementada nesta versão).

Nesta fase o VERITAS AI só classifica padrões linguísticos. A interface abaixo define onde uma camada de
fact-checking poderia entrar (ver docs/FACTCHECK_FUTURO.md) sem alterar o classificador: o provedor recebe o
texto e devolve evidências; a aplicação apenas as exibiria ao lado do resultado. Nenhuma chamada externa é feita aqui.
"""
from dataclasses import dataclass, field
from typing import List, Protocol


@dataclass
class Evidence:
    claim: str                      # afirmação extraída do texto
    source: str                     # origem identificável (URL/instituição)
    stance: str                     # "apoia" | "contradiz" | "inconclusivo"
    excerpt: str = ""
    retrieved_at: str = ""


@dataclass
class EvidenceReport:
    items: List[Evidence] = field(default_factory=list)
    provider: str = "none"


class EvidenceProvider(Protocol):
    def check(self, text: str) -> EvidenceReport: ...


class NullEvidenceProvider:
    """Padrão desta versão: nenhuma verificação externa."""
    def check(self, text: str) -> EvidenceReport:
        return EvidenceReport(items=[], provider="none")

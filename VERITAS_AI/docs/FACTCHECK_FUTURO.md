# Preparação para verificação de fatos (versão futura)

**Não implementado na 2.0** (sem APIs externas, buscas ou serviços pagos). O classificador estima padrões de estilo; verificar fatos exige evidências.

## Onde a camada entraria
`veritas/evidence.py` define `EvidenceProvider.check(text) -> EvidenceReport` e `NullEvidenceProvider` (padrão). Fluxo proposto:
1. **Extração de afirmações** (frases verificáveis) a partir do texto — módulo novo, independente do classificador.
2. **Recuperação de evidências** por um `EvidenceProvider` (ex.: base de checagens de agências, bases oficiais, busca em fontes confiáveis), sempre com procedência e data.
3. **Comparação** afirmação × evidência (apoia / contradiz / inconclusivo), com os trechos exibidos ao usuário.
4. **Combinação na interface**: um novo bloco "Evidências" ao lado do resultado; o rótulo do classificador **não é alterado** e continua separado da checagem.

## Mudanças necessárias quando for implementado
- Novo campo `evidence` em `/api/analyze` (hoje o contrato não muda).
- Decisão de produto sobre latência, custo, privacidade (o texto sairia do computador) e licença das fontes.
- Avaliação própria (precisão/recall das evidências), separada das métricas do classificador.

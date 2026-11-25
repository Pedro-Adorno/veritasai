# IMPLEMENTATION_PLAN — VERITAS AI 2.0

Branch: `evolucao-v2` (base: tag `v1.0-baseline`). Estado v1 preservado em `model/v1/` e no Git.

## Auditoria (resumo — fatos verificados no código e nos dados)
- Fake.br Corpus **disponível localmente** (extraído de `full_texts.zip` em `data/full_texts/`, ignorado pelo Git). 7.200 textos (3.600/3.600).
- Fontes (domínio registrável): FAKE = diariodobrasil 3.337, afolhabrasil 174, thejornalbrasil 66, outras 23. TRUE = g1 2.300, estadao (vários subdomínios) ~1.090, folha 91+.
- Anos (campo `date`): FAKE 2015–2018 (pico 2016–2017); TRUE majoritariamente 2017–2018 → **confusão temporal** além da de fonte.
- V1: pipeline TF-IDF(1-2) + LR C=100, truncado em 200 palavras; teste aleatório 95,05%; entre fontes: acc 78,14%, recall FAKE 58,17%, TRUE 82,23%.
- Frontend: `EXAMPLES` fixo (2 sintéticos) em `app/static/js/app.js`; explicabilidade via `veritas.pipeline.explain_full`.

## Fases e status
| Fase | Escopo | Status |
|---|---|---|
| 1 | Auditoria, Git, arquivos de acompanhamento | feito |
| 2 | Exemplos dinâmicos reais (JSON controlado + API) | feito |
| 3 | Viés de fonte, protocolo leave-source-out, comparação de modelos/estratégias | feito |
| 4 | Calibração + abstenção (INCONCLUSIVO) | feito |
| 5 | UX: estado inconclusivo, avisos de cobertura/curto/fora do padrão | feito |
| 6 | Testes, documentação, relatório comparativo v1 x v2 | feito |
| — | Gancho para fact-checking futuro (somente interface + doc) | feito |

## Decisões de método (fixadas antes dos experimentos)
1. Seleção de modelo por **desempenho em fontes não vistas** (leave-one-source-out por classe), não pela acurácia aleatória.
2. Calibração e limiares de abstenção **ajustados em previsões out-of-fold entre fontes** (treino+validação), nunca no teste.
3. Teste aleatório (mesma divisão de 2026, semente 42) mantido só para comparação com a v1.
4. Sem APIs externas; sem novos dados sem licença/procedência verificável (nenhum outro corpus está disponível offline).

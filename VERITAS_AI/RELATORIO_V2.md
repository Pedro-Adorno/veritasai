# Relatório final — VERITAS AI 2.0 x 1.0

_Todos os números abaixo vêm de `model/metricas.json` (v2), `model/v1/metricas.json` (v1) e `model/experiments_v2.json`. Nada foi digitado à mão._

## 1. Resumo
- O objetivo era **melhorar a generalização** (notícias de fontes que o modelo não viu), com avaliação honesta. A melhoria foi **real, porém modesta**; o teto é imposto pelos dados: 92,7% das FAKE vêm de um único site.
- A acurácia no **teste aleatório caiu** de 95,05% (v1) para 94,02% (v2): esperado, pois a v2 remove atalhos (pistas de fonte, dígitos) e regulariza mais. Não é uma regressão de qualidade.
- Entre fontes (leave-one-source-out, comprimento controlado): 57,3% → 61,7%. Separação temporal: 81,9% → 86,2%.
- **Descoberta importante:** um classificador que usa só o tamanho do texto atinge 89,0% no protocolo entre fontes (83,4% com comprimento controlado), mais que qualquer modelo de linguagem testado. O tamanho é um atalho do corpus (FAKE curtas, TRUE longas, em todas as fontes).
- **Inconclusivo:** implementado e validado; ajuda dentro da distribuição do treino, **mas não resolve** erros confiantes em fontes novas (ver seção 5).

## 2. Modelo selecionado
`LR C=1 + máscara` — Regressão Logística (C = 1), TF-IDF 1–2 gramas, truncamento em 200 palavras, máscara de pistas de fonte e dígitos. Versão 2.0.0. Regressão Logística mantida (explicabilidade preservada: contribuição = TF-IDF × coeficiente).

**Como foi escolhido (3 etapas, registradas com transparência):**
1. Critério planejado: LOSO simples. Ele apontou "sem truncar" (0,837) como melhor.
2. Ao incluir o baseline só-comprimento (0,890), ficou claro que o LOSO simples premia o atalho de tamanho. Revisão: LOSO com **comprimento controlado** (faixas 200–800 palavras).
3. Mesmo controlado, o baseline só-comprimento (83,4%) supera todas as configurações sem truncar (0,69–0,73): elas **não demonstram sinal linguístico além do tamanho**. Regra final: considerar só configurações com entrada de tamanho limitado e escolher a de maior LOSO controlado. As revisões foram motivadas pela evidência, não por conveniência.

## 3. Resultados
### 3.1 Teste aleatório (mesma divisão da v1, n = 1071)
| Métrica | v1 | v2 |
|---|---|---|
| Acurácia | 95,05% | 94,02% |
| F1 macro | 95,05% | 94,02% |
| Recall FAKE | 93,32% | 92,58% |
| Recall TRUE | 96,80% | 95,49% |
| Falsos negativos (FAKE→TRUE) | 36 | 40 |
| Falsos positivos (TRUE→FAKE) | 17 | 24 |
| ROC-AUC | 0.992 | 0.987 |

### 3.2 Generalização entre fontes (leave-one-source-out)
| Config | Recall FAKE (média) | Recall TRUE (média) | Balanceado | Comprimento controlado |
|---|---|---|---|---|
| v1 (LR C=100) | 40,4% | 84,1% | 62,2% | 57,3% |
| **v2 (LR C=1 + máscara)** | 43,1% | 86,4% | 64,7% | 61,7% |
| Baseline só comprimento | 88,8% | 89,2% | 89,0% | 83,4% |

Recall por fonte deixada de fora (v2): afolhabrasil 36,2% (n=174); diariodobrasil 17,8% (n=3329); estadao 79,3% (n=1186); g1 84,9% (n=2262); minor_fake 75,3% (n=89); minor_true 94,8% (n=97). Ao deixar de fora a fonte dominante de FAKE, restam ~260 FAKE no treino e o recall despenca: nenhuma técnica de modelagem substitui mais fontes FAKE.
Todas as 20 configurações (inclusive as que não ajudaram: pesos por fonte, stopwords, 100 palavras, Naive Bayes, SVM) estão em `model/experiments_v2.json` e no dashboard.

### 3.3 Separação temporal (treino ≤ 2016, teste 2017–2018)
| | Recall FAKE | Recall TRUE | Balanceado |
|---|---|---|---|
| v1 | 95,9% | 67,9% | 81,9% |
| v2 | 91,5% | 80,9% | 86,2% |
Atenção: o período está confundido com a fonte (as TRUE são mais recentes).

### 3.4 Famílias de modelo (v2, mesmo pré-processamento)
| Modelo | F1 macro validação | F1 macro teste | Balanceado entre fontes |
|---|---|---|---|
| Regressão Logística | 92,53% | 94,02% | 64,7% |
| Multinomial Naive Bayes | 88,42% | 89,73% | 49,8% |
| Linear SVM | 92,81% | 93,46% | 63,8% |

Tempo de treino: 7.7 s; inferência: 1.364 ms por texto.

## 4. Calibração
Platt (a = 0.499, b = 0.261) ajustado em previsões out-of-fold entre fontes, com pesos por fonte e classes equilibradas. ECE entre fontes (calibrador avaliado sem ver a fonte testada): bruta 0.168 → calibrada 0.220; Brier 0.262 → 0.280. **A calibração entre fontes não melhorou essas métricas** (o modelo é confiante e errado em fontes novas, e o calibrador não consegue corrigir isso); no teste aleatório: ECE 0.202 → 0.294. A interface exibe a probabilidade bruta (ligada à explicação) e a calibrada (usada na decisão), sem apresentar nenhuma como "chance de ser verdadeira".

## 5. Classificação inconclusiva
Regra: FAKE se P(FAKE) calibrada ≥ 0.55, TRUE se ≤ 0.5, senão inconclusivo. Política declarada antes dos resultados: maior cobertura com acurácia seletiva ≥ 80% entre fontes (cobertura ≥ 20%). **Meta NÃO atingida**: entre fontes, a acurácia nas decididas foi 51,5% (sem abstenção: 50,0%), com cobertura 81,4%. Usou-se a banda que maximiza acurácia × cobertura.
No teste aleatório: cobertura 91,4%, acurácia nas decididas 94,0% → 95,8%, FN 40 → 7, FP 24 → 34.
**Conclusão:** a abstenção reduz erros em textos parecidos com os do treino, mas **não protege contra fontes novas**, onde os erros são confiantes. A banda é estreita e assimétrica por causa da calibração; revisar quando houver mais fontes.

## 6. Exemplos dinâmicos
52 trechos reais do Fake.br (somente do conjunto de teste; ≤ 120 palavras; sem links/autores), gerados por `scripts/build_examples.py`; `/api/example` alterna FAKE/TRUE sem repetir o último. Sem o arquivo, o app usa exemplos sintéticos rotulados como tais. **Confirme a licença do corpus antes de publicar `app/examples/examples.json`** (ou remova-o do repositório e rode o script localmente).

## 7. Outras bases de dados
Nenhuma foi incorporada: o ambiente não tem acesso à internet e não há outra base em português com procedência e licença verificáveis disponível localmente. Registrado como principal limitação restante.

## 8. Testes executados
`tests/test_veritas.py` (14), `tests/test_explicabilidade.py` (7), `tests/test_v2.py` (12) — todos aprovados; verificações em navegador (desktop e celular): fluxo anterior 36/36 e 28/28, e novas 20/20 (exemplos, inconclusivo, dashboard, histórico, tecnologia).

## 9. Limitações restantes
Uma única fonte domina as FAKE; confusão entre fonte, período e tamanho; atalho de comprimento não eliminado (apenas limitado por truncamento); probabilidades pouco confiáveis em fontes novas; sem teste com notícias reais fora do corpus; rótulos por fonte, não por checagem individual.

## 10. Arquivos
Criados: `veritas/data.py`, `veritas/evidence.py`, `scripts/{experiments_v2,analyze_v2,train_v2,build_examples}.py`, `app/examples/examples.json`, `tests/test_v2.py`, `docs/FACTCHECK_FUTURO.md`, `model/{experiments_v2.json,oof_v2.npz,v1/}`, IMPLEMENTATION_PLAN/PROGRESS/TECHNICAL_NOTES.
Modificados: `veritas/{preprocess,pipeline,inference}.py`, `app/app.py`, `app/templates/index.html`, `app/static/{js/app.js,css/style.css}`, `model/{modelo_veritas.joblib,metadata.json,metricas.json}`, README.

## 11. Como executar
`pip install -r requirements.txt` · `python app/app.py` · reproduzir: `python scripts/experiments_v2.py && python scripts/analyze_v2.py && python scripts/train_v2.py` (requer `data/full_texts/`; ≈ 25 min em 1 CPU).

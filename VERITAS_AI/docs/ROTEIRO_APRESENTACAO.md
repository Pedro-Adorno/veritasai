# Roteiro de apresentação — VERITAS AI (5 minutos)

*Todos os números abaixo vêm de `model/metricas.json` (teste isolado, n = 1.071).*

**1. Problema e motivação — 40 s**
Notícias falsas se espalham rápido (Vosoughi et al., 2018) e checar tudo manualmente não escala. Perguntamos: o que um classificador de PLN clássico consegue aprender sobre notícias falsas em português — e o quanto disso é linguagem, e não atalho do conjunto de dados?

**2. Objetivo e proposta — 40 s**
Construímos o VERITAS AI: uma aplicação web que classifica um texto em "padrões associados a FAKE ou TRUE", mostra probabilidades e os termos que pesaram. Ponto central: **não é verificador de fatos**, classifica padrões de estilo aprendidos no Fake.br Corpus.

**3. Metodologia e técnicas de PLN — 1 min**
Base: Fake.br, 7.200 notícias (3.600/3.600); removemos 63 duplicatas/quase-duplicatas (7.137 restantes). Pré-processamento: normalização de caracteres, URLs e espaços, preservando pontuação e negações; truncamento em 200 palavras. TF-IDF com unigramas e bigramas. Modelos: Regressão Logística (principal), Naive Bayes (baseline) e SVM linear. Divisão estratificada 70/15/15 (4.995/1.071/1.071); hiperparâmetros escolhidos no treino/validação; teste só no fim.

**4. Resultados experimentais — 1 min**
No teste: acurácia 95,05%, F1 macro 95,05%, ROC-AUC 0,992; 36 falsos negativos e 17 falsos positivos. SVM chegou perto (95,42% no teste, diferença < 1 p.p. na validação) e o Naive Bayes ficou em 90,76%. **Mas** medimos os atalhos: só o tamanho do texto já dá 94,1% de F1 na validação, e treinando em um par de fontes e testando em outras o recall de FAKE cai para 58,2% (TRUE 82,2%). Conclusão honesta: o teste principal superestima o desempenho em fontes novas.

**5. Demonstração — 1 min**
`python app/app.py` → Central de análise → "Usar exemplo" → Analisar: classe, barra de probabilidades, margem do classificador com aviso de não calibração, termos que empurram para FAKE/TRUE. Dashboard: métricas lidas do `metricas.json`, matriz de confusão, comparação de modelos, leitura crítica. Histórico local (não guarda o texto).

**6. Conclusão — 40 s**
Pipeline completo, reproduzível e testado (14 testes automatizados, 36 verificações em navegador). Contribuição: mostrar, com experimentos, que o modelo capta estilo e fonte. Futuro: outras fontes e épocas, calibração, modelos contextuais (BERTimbau) e checagem factual com fontes externas.

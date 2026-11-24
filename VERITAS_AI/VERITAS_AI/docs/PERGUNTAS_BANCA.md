# Perguntas prováveis da banca e respostas (alinhadas à implementação)

**Por que TF-IDF?** Representa cada texto por pesos de termos e n-gramas, reduz o peso de palavras comuns, é rápido, funciona bem com classificadores lineares e mantém a interpretabilidade (cada dimensão é um termo). Em validação cruzada, uni+bigramas (F1 macro 0,9353) superaram só unigramas (0,9235).

**Por que Regressão Logística?** Dá probabilidades e coeficientes por termo (explicabilidade exigida pelo produto), é robusta em alta dimensão e teve desempenho equivalente ao SVM (F1 macro de validação 0,9468 vs 0,9477; diferença < 1 p.p., nossa regra de decisão) e muito melhor que o Naive Bayes (0,8889).

**Diferença entre classificação e verificação factual?** Classificamos o *estilo* do texto, com base em exemplos rotulados. Verificar fatos exigiria consultar fontes e evidências. Nosso modelo não faz isso; por isso a interface diz "padrões associados a".

**Como funciona o treinamento supervisionado?** Cada notícia tem um rótulo (FAKE/TRUE); a Regressão Logística ajusta os coeficientes para minimizar o erro de classificação nos dados de treino, com regularização (C).

**Como evitamos overfitting?** Divisão estratificada treino/validação/teste com o teste isolado até o fim; hiperparâmetros escolhidos na validação; validação cruzada de 3 dobras no treino; regularização; remoção de duplicatas e quase-duplicatas antes da divisão; TF-IDF ajustado só no treino. Ainda assim, há risco de superestimar em fontes novas (ver abaixo).

**Precisão vs. recall?** Precisão: dos textos que o modelo chamou de FAKE, quantos eram FAKE (FAKE: 96,73%). Recall: das FAKE reais, quantas ele achou (93,32%). O F1 é a média harmônica.

**Por que a acurácia sozinha não basta?** Esconde o tipo de erro (36 falsos negativos x 17 falsos positivos têm custos diferentes), depende do balanceamento e pode refletir atalhos. Por isso usamos F1 macro, métricas por classe, matriz de confusão e testes de robustez.

**Limitações do dataset?** Notícias de 2015–2018 (maioria em 2016–2017); fontes concentradas (92,7% das FAKE de um site; 63,9% das TRUE do g1); rótulos por fonte; TRUE ~6x mais longas; aspas curvas só nas TRUE. Tratamos parte disso (normalização, truncamento), mas não tudo.

**Como o modelo interpreta os textos?** Não "entende": soma pesos de termos. Cada termo contribui com valor TF-IDF × coeficiente; a soma mais o intercepto é a decisão (verificado em teste). Termos como "feira", "nesta", "segundo" e "g1" pesam para TRUE; "!", "dilma", "lula" para FAKE — associações do corpus, não prova.

**O sistema identifica uma fake news inédita?** Não sabemos: não testamos com notícias fora do corpus. O teste entre fontes (recall de FAKE 58,2%) sugere que o desempenho cai em fontes novas. Não devemos afirmar que detecta notícias inéditas.

**As probabilidades são confiáveis?** Não foram calibradas formalmente (ECE 0,027 no teste, válido só para este corpus). A interface avisa e usa o termo "margem do classificador".

**Isso é o mesmo modelo do app?** Sim: notebook e app importam o pacote `veritas/`; o app carrega o `.joblib` exportado e um teste confere que o modelo recarregado reproduz as predições.

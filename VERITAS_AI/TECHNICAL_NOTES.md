# TECHNICAL_NOTES — VERITAS AI 2.0

## Estrutura real
`app/app.py` (Flask: /, /api/health, /api/metrics, /api/analyze) · `veritas/{preprocess,pipeline,inference}.py` · `model/` (joblib, metricas.json, metadata.json; v1 em `model/v1/`) · `notebooks/VERITAS_AI_Pipeline_PNL.ipynb` (v1) · `tests/`.
Versões (requirements.txt): scikit-learn 1.9.1, pandas 3.0.6, numpy 2.5.4, flask 3.1.3, joblib 1.6.0.

## Ambiente de execução desta evolução
1 CPU, ~4 GB RAM, sem internet (não é possível baixar outras bases). Treinos LR com bigramas levam ~5–8 s.
Processos longos: usar `setsid nohup ... &` (processos presos à shell são encerrados).

## Armadilhas conhecidas
- `pkill -f app/app.py` mata a própria shell; use PID.
- Flask ordena chaves do JSON (ordem de dicts não é preservada).
- O `.joblib` referencia `veritas.preprocess.TextPreprocessor`; mudanças nessa classe exigem retreino.

## Achados da Fase 3 (experimentos LOSO; `model/experiments_v2.json`)
Protocolo: leave-one-source-out — cada fonte (diariodobrasil, afolhabrasil, minor_fake, g1, estadao, minor_true) sai inteira do treino e é avaliada pelo recall da sua classe. Resumo = média dos recalls FAKE e TRUE (`balanced`).
- v1 (LR C=100): balanced 0,622 (recall FAKE 0,404 / TRUE 0,841). Regularizar mais (C=1) e mascarar pistas de fonte/dígitos dão ganhos pequenos (0,639–0,651).
- **Achado crítico:** "sem truncar" sobe para 0,837, mas o tamanho do texto separa as classes em TODAS as fontes (FAKE curtas, TRUE longas); o LOSO simples não detecta esse atalho. Por isso foi criada a avaliação com **comprimento controlado** (`scripts/analyze_v2.py`: só faixas de tamanho com ambas as classes, 200–800 palavras) e o baseline "só comprimento".
- **Critério de seleção REVISADO** (após ver esse achado, e por causa dele — não por conveniência): usar `length_matched.balanced` (LOSO com comprimento controlado) em vez do LOSO simples. O critério original está registrado nos resultados para transparência.
- Limitação estrutural: 93% das FAKE vêm de uma única fonte; ao deixá-la fora, restam ~260 FAKE no treino. Nenhum ajuste de modelo substitui dados de mais fontes FAKE.
- Rodada 2 (reponderação por faixa de tamanho `length_weights` + pesos por fonte, pesos limitados a 10x) em andamento; log `/home/claude/exp_v2b.log`.

## Calibração e abstenção (planejado em `scripts/train_v2.py`)
Platt sobre previsões out-of-fold entre fontes (só treino+validação); avaliação leave-one-group-out do calibrador; grade de limiares (lo,hi); política fixada antes do resultado final: maior cobertura com acurácia seletiva ponderada por fonte >= 0,80 (cobertura >= 0,20); se inatingível, banda que maximiza acurácia×cobertura e limitação documentada. Teste aleatório (semente 42) só para comparar com a v1.

## v3
- `TextPreprocessor(mode="mask_names")`: remove palavras capitalizadas que não abrem frase (heurística, sem NER) antes de minúsculas; modelo atual = "LR C=1 + máscara + sem nomes próprios".
- Política de inconclusivo (v3): faixa [lo,hi] sobre P(FAKE) calibrada = maior cobertura com precisão ≥ 95% por veredito NA VALIDAÇÃO (substitui a meta de acurácia entre fontes da v2, inatingível). Regras extras: n_words < p1 do treino, cobertura do vocabulário < p1, < 5 termos. Níveis de confiança = tercis da confiança das decididas; acurácia por nível em `metadata.json`.
- Entre fontes os níveis de confiança não se sustentam (acerto ≈ 41–51%): a UI mostra o acerto médio entre fontes (LOSO ≈ 66%).
- `model/term_stats.json` (gerado por `scripts/build_term_stats.py`): nº de textos FAKE/TRUE do treino por termo, concentração em uma fonte e indício de nome próprio. Sem ele, `Analyzer` funciona, mas sem frequências nas explicações.
- Armadilha: `pkill -f` e `kill` por padrão de nome podem matar a própria shell; usar `ps -eo pid,args | awk` com âncora no início dos argumentos.

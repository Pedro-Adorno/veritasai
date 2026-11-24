# VERITAS AI

Plataforma acadêmica de Processamento de Linguagem Natural que analisa notícias em português e estima se o texto se assemelha às notícias **FAKE** ou **TRUE** (verdadeiras) do *Fake.br Corpus*, mostrando probabilidades, **por que o modelo chegou à conclusão** (termos e pesos reais da Regressão Logística) e as limitações do resultado.

> **Não é um verificador de fatos.** O sistema reconhece padrões estatísticos de estilo aprendidos em um corpus rotulado; não consulta fontes nem checa informações de forma independente.

| Análise com explicação | Conheça a tecnologia |
|---|---|
| ![Explicabilidade](docs/screenshots/02-explicabilidade.png) | ![Tecnologia](docs/screenshots/03-tecnologia.png) |

## Funcionalidades
- **Central de análise:** classe estimada, probabilidades, margem do classificador (com aviso de que não são calibradas) e indicadores descritivos do texto.
- **“Por que o VERITAS AI chegou a essa conclusão?”:** decomposição real da decisão. Para cada termo, *contribuição = valor TF-IDF × coeficiente*; a soma das contribuições mais o intercepto é o log-odds *z*, e `P(TRUE) = 1/(1+e^-z)` reproduz exatamente a probabilidade do modelo. Termos que favoreceram FAKE e TRUE aparecem separados.
- **Conheça a tecnologia:** página educativa sobre TF-IDF, Regressão Logística, pipeline de 6 etapas, treinamento e o papel do Fake.br Corpus, com números lidos do modelo carregado.
- **Dashboard de inteligência:** métricas, matriz de confusão, comparação de modelos e leitura crítica, lidas de `model/metricas.json`.
- **Histórico local** (no navegador): título, resultado, probabilidades e alguns termos; **não** guarda o texto da notícia.
- Interface responsiva (desktop, tablet e celular), 100% offline, sem API externa.

## Versão 2.0 — o que mudou
- **Exemplos reais:** botões *Exemplo / FAKE / TRUE* carregam trechos reais do Fake.br (conjunto de teste), alternando classes e mostrando categoria, fonte e rótulo original (`/api/example`; gerado por `scripts/build_examples.py`).
- **Generalização entre fontes:** avaliação leave-one-source-out, separação temporal e controle do atalho de tamanho; modelo escolhido por esses critérios (ver `RELATORIO_V2.md`).
- **Resultado inconclusivo:** probabilidades calibradas (Platt) e banda de abstenção definida por experimentos; a interface explica que *inconclusivo não significa verdadeiro nem falso*.
- **Avisos:** texto curto, truncado, baixa cobertura do vocabulário (limiares vindos do treino).
- **Preparado para fact-checking futuro:** `veritas/evidence.py` e `docs/FACTCHECK_FUTURO.md` (não implementado).

## Resultados reais (v1 → v2)
| | v1 | v2 |
|---|---|---|
| Teste aleatório, acurácia (n = 1071) | 95,05% | 94,02% |
| Entre fontes, recall FAKE / TRUE (média) | 40,4% / 84,1% | 43,1% / 86,4% |
| Entre fontes, comprimento controlado | 57,3% | 61,7% |

A acurácia aleatória caiu um pouco (a v2 remove atalhos) e a generalização melhorou de forma **modesta**: 92,7% das FAKE vêm de um único site e um classificador só com o tamanho do texto já atinge 89,0% entre fontes. Detalhes, falhas e limitações em **`RELATORIO_V2.md`**.

## Tecnologias
Python · Flask · scikit-learn (TF-IDF, Regressão Logística, Naive Bayes, Linear SVM) · pandas · NumPy · Joblib · HTML/CSS/JavaScript (SVG nativo) · Jupyter.

## Estrutura
```
app/         servidor Flask (app.py), template e estáticos (CSS/JS/logo)
veritas/     pacote compartilhado: pré-processamento, pipeline, explicabilidade, inferência
model/       modelo_veritas.joblib, metricas.json, metadata.json (gerados pelo notebook)
notebooks/   VERITAS_AI_Pipeline_PNL.ipynb (com saídas)
data/        README.md (o corpus vai em data/full_texts/, ignorado pelo Git)
docs/        artigo, planilha de uso de IA, roteiro, perguntas da banca, figuras, screenshots
tests/       testes do modelo, da API e da explicabilidade
```

## Instalação e execução
Requer Python 3.10+. Documentos de acompanhamento: `IMPLEMENTATION_PLAN.md`, `PROGRESS.md`, `TECHNICAL_NOTES.md`.
```bash
git clone <url-do-repositorio> && cd VERITAS_AI
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app/app.py                                      # http://127.0.0.1:5000
```
O modelo já vem treinado em `model/`; o servidor **não treina nada ao iniciar**. Porta alternativa: `PORT=8000 python app/app.py`.

### Testes
```bash
python tests/test_veritas.py            # 14 testes: modelo e API
python tests/test_explicabilidade.py    # 7 testes: a explicação vem do modelo real
python tests/test_v2.py                 # 12 testes: exemplos, calibração, inconclusivo, avisos
```

### Retreinar / reproduzir
1. Obtenha o Fake.br Corpus e extraia em `data/full_texts/` (ver `data/README.md`; confira a licença antes de redistribuir).
2. **v2:** `python scripts/experiments_v2.py && python scripts/analyze_v2.py && python scripts/train_v2.py && python scripts/build_examples.py` (≈ 25 min em 1 CPU; regrava `model/` e os exemplos). O notebook `notebooks/VERITAS_AI_Pipeline_PNL.ipynb` documenta o pipeline **v1**; artefatos v1 em `model/v1/`.
3. O `.joblib` depende da versão do scikit-learn (1.9.1 em `requirements.txt`); com outra versão, retreine pelo notebook.

## Decisões e limitações
- Notebook e app usam o mesmo pacote `veritas/` (mesmo pré-processamento, vetorização e modelo).
- Pré-processamento: aspas/BOM/URLs normalizados e textos truncados a 200 palavras para reduzir atalhos do corpus; pontuação e negações preservadas.
- Gráficos e ícones em SVG/CSS nativos (funciona offline).
- Limitações: corpus de 2015–2018 com fontes muito concentradas; rótulos por fonte; probabilidades não calibradas formalmente; sem teste com notícias reais fora do corpus; o modelo aprende estilo e fonte, não verdade factual.

## Licença
Defina a licença do código antes de publicar (por exemplo, MIT) e adicione o arquivo `LICENSE`. O Fake.br Corpus tem licença própria, definida pelos autores originais.

## Referência
Monteiro, R. A. et al. (2018). *Contributions to the Study of Fake News in Portuguese: New Corpus and Automatic Detection Results.* PROPOR 2018, LNCS 11122, Springer, pp. 324–334.

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

## Versão 3 — resultado simples para qualquer pessoa
- **Um único resultado em destaque:** POSSIVELMENTE FALSA, POSSIVELMENTE VERDADEIRA ou RESULTADO INCONCLUSIVO, com nível de confiança e uma explicação em linguagem natural gerada a partir dos dados reais da análise.
- **"O que chamou a atenção":** cada destaque usa a frequência real do termo nas notícias falsas e verdadeiras do treino. **Nomes próprios nunca são tratados como evidência** (o modelo é treinado sem eles); termos raros ou de um único veículo são declarados sem interpretação confiável.
- **"Pontos que merecem verificação":** números, datas, declarações e nomes citados no texto (extração por regras). **Verificação em fontes externas: não realizada** (não há integração; a tela informa isso).
- **Inconclusivo com política validada:** probabilidade calibrada + faixa de incerteza escolhida na validação + regras para texto curto/fora do domínio.
- **Detalhes técnicos recolhidos** e página "Como a tecnologia funciona" para quem quiser aprofundar.
- Mantidos: exemplos reais do Fake.br, histórico local, dashboard, explicabilidade técnica, tema visual e responsividade.

## Resultados reais (v1 → v2 → v3)
Entre fontes que o modelo nunca viu, o acerto médio é de **≈ 66%** (contra ≈ 93% em notícias parecidas com as do treino): 92,7% das FAKE do corpus vêm de um único site. Comparação completa, auditoria, política de inconclusivo e limitações em **`RELATORIO_V3.md`** (e `RELATORIO_V2.md`).

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
python tests/test_v3.py                 # 12 testes: resultado único, nomes próprios, pontos de verificação
```

### Retreinar / reproduzir
1. Obtenha o Fake.br Corpus e extraia em `data/full_texts/` (ver `data/README.md`; confira a licença antes de redistribuir).
2. **v2:** `python scripts/experiments_v2.py && python scripts/analyze_v2.py && python scripts/train_v2.py && python scripts/build_term_stats.py && python scripts/build_examples.py` (≈ 25 min em 1 CPU; regrava `model/` e os exemplos). O notebook `notebooks/VERITAS_AI_Pipeline_PNL.ipynb` documenta o pipeline **v1**; artefatos v1 em `model/v1/`.
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

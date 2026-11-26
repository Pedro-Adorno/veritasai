# Relatório — VERITAS AI v3 (resultado em linguagem simples, nomes próprios, política de inconclusivo)

_Números lidos de `model/metricas.json` (v3), `model/v1/metricas.json` (v1), da branch `evolucao-v2` (v2) e `model/audit_v3.json`._

## 1. Limites desta sessão (leia primeiro)
- **Não tive acesso ao site (veritasai-six.vercel.app) nem ao repositório GitHub**: o ambiente não tem rede e o projeto local não tem remote nem `vercel.json`. Trabalhei no projeto local (v2). **A compatibilidade com o Vercel não foi testada**; nenhuma dependência nova foi adicionada.
- **Verificação factual externa NÃO foi implementada** (não há integração/fonte disponível; não inventei nenhuma). O que existe: extração, por regras, de números, datas, declarações e nomes citados no texto, para o leitor conferir. A tela diz claramente que a verificação externa não foi realizada.

## 2. Problemas relatados e o que foi feito
| Problema | Auditoria | Correção |
|---|---|---|
| "Duas respostas" | A barra de probabilidade bruta discordava do veredito final em 10 de 52 exemplos reais (19%) | Um único resultado em destaque (POSSIVELMENTE FALSA / VERDADEIRA / INCONCLUSIVO); probabilidades só em "Detalhes técnicos" |
| Explicação técnica | Pesos (+0,84), TF-IDF, coeficientes na tela principal | Linguagem natural; técnica recolhida e página "Como a tecnologia funciona" |
| Nomes próprios como fator | Termos como "lula", "dilma" entre os de maior peso | Nomes/siglas só aparecem como "citados no texto, NÃO são evidência"; o modelo passou a ser treinado **sem nomes próprios** |
| Termos sem sentido | Palavras soltas com peso | Cada destaque usa a **frequência real** do termo nas notícias falsas e verdadeiras do treino; termos raros ou de um único veículo são declarados como sem interpretação confiável |
| Generalização | LOSO e período | ver seção 3 |

## 3. Modelo: v1 → v2 → v3
| | v1 | v2 | **v3** |
|---|---|---|---|
| Teste aleatório, acurácia | 95,05% | 94,02% | 93,37% |
| Entre fontes (LOSO), recall FAKE / TRUE | 40,4% / 84,1% | 43,1% / 86,4% | 44,7% / 87,4% |
| LOSO, comprimento controlado | 57,3% | 61,7% | 62,7% |
| Separação temporal (≤2016 → 2017–18) | 81,9% | 86,2% | 87,5% |
| Previsões que mudam sem os nomes próprios (teste, n=400) | — | 3,5% | 0,5% |
v3 = `LR C=1 + máscara + sem nomes próprios` (Regressão Logística C = 1; texto truncado em 200 palavras; sem nomes próprios; pistas de fonte e dígitos mascarados). **Ganho entre fontes: pequeno** (≈ 1–2 p.p. sobre a v2 e ≈ 5 p.p. sobre a v1 com comprimento controlado). A acurácia aleatória caiu em relação à v1 porque atalhos foram retirados.
**O limite é dos dados:** 92,7% das FAKE vêm de um único site; um modelo só com o tamanho do texto chega a 89,0% entre fontes. **Com fontes que o modelo nunca viu, o acerto médio é de ≈ 66%**, e a interface informa isso ao usuário.

### Auditoria pedida (resposta objetiva)
- **Base:** Fake.br Corpus (7.200 textos; 7.137 após remover 63 duplicatas e quase-duplicatas ≥ 0,90). **Divisão:** 70/15/15 estratificada, semente 42; duplicatas removidas antes; teste isolado.
- **Vazamento:** não encontrado entre treino/validação/teste (textos únicos, verificado por teste). A calibração usa previsões out-of-fold só de treino+validação.
- **Aprende fonte?** Sim, em parte: a v1 caía para ≈ 40% de recall FAKE ao deixar uma fonte de fora; foram mascarados nomes de portais e dígitos.
- **Dependência de nomes próprios:** 3,5% das previsões mudavam sem eles; na v3 0,5%.
- **Assuntos (teste):** política 93,2%, TV/celebridades 93,4%, sociedade 95,6%; ciência/tecnologia, economia e religião têm poucos exemplos (23, 9, 9) e resultados menos confiáveis; 96% dos textos de teste são de política, TV e sociedade.
- **Calibração:** Platt sobre previsões entre fontes; ECE entre fontes 0.143 → 0.122 (v2: 0.168 → 0.220).
- **Alternativas comparadas:** 15 configurações (LR com vários C, pesos de fonte, comprimento, máscara, nomes próprios, stopwords, Naive Bayes, SVM, baseline só-comprimento) em `model/experiments_v2.json`. Regressão Logística mantida.

## 4. Política de resultado inconclusivo (revisada, com justificativa)
O resultado vira INCONCLUSIVO quando: (a) a probabilidade calibrada cai na faixa de incerteza; (b) o texto é mais curto que o 1º percentil do treino; (c) a cobertura do vocabulário é menor que o 1º percentil do treino (provável outro idioma/conteúdo fora do domínio); (d) há menos de 5 termos analisáveis.
- **Faixa de incerteza:** [0.49, 0.62] na probabilidade calibrada de FAKE, escolhida na **validação**: maior cobertura com precisão ≥ 95% em cada veredito (FAKE 95,6%, TRUE 97,4%, cobertura 86,4% na validação). O alvo de 95% é uma política declarada; a curva completa está em `metricas.json`.
- **Revisão:** na v2 a meta era acurácia seletiva ≥ 80% *entre fontes*, inatingível (≈ 56%), o que gerou uma banda quase nula e muitos falsos positivos (com a banda antiga, o modelo v3 marcava 45 notícias TRUE como FAKE no teste). A v3 usa precisão por veredito na validação.
- **Teste aleatório (n = 1071):** sem abstenção 93,4% (FN 54, FP 17); com abstenção 97,3% nas decididas, cobertura 86,2%, FN 11, FP 14.
- **Níveis de confiança** (tercis da confiança das decididas, validação): baixa 91,2%, moderada 98,1%, alta >99% de acerto **em notícias parecidas com as do treino**. **Entre fontes, esses níveis NÃO se sustentam** (acerto ≈ 51%/50%/41%): a confiança alta pode estar errada em fonte nova. Por isso a tela exibe também "acerto médio de ≈ 66% com fontes nunca vistas".

## 5. Testes executados (todos aprovados)
Python: `test_veritas` 14, `test_explicabilidade` 7, `test_v2` 12, `test_v3` 12 (veredito único coerente, texto curto e fora do domínio → inconclusivo, nomes nunca como evidência, destaques ⊂ termos reais e com frequências reais, pontos de verificação só com o que existe no texto, verificação externa "não realizada", assuntos diferentes, API). Navegador (desktop e celular): 40/40 (um único veredito, sem jargão técnico na tela principal, ordem das seções, detalhes técnicos recolhidos, histórico, dashboard, página de tecnologia, sem overflow horizontal, sem erros de console).

## 6. Pendências
1. Mais fontes de notícias FAKE e VERDADEIRAS (maior ganho possível), com licença verificada.
2. Verificação factual externa (ver `docs/FACTCHECK_FUTURO.md`; gancho em `veritas/evidence.py`).
3. Testar o deploy no Vercel (sklearn + modelo de 1 MB + 1,8 MB de estatísticas de termos; verificar limite de tamanho das funções).
4. Artigo, pitch e planilha de IA ainda descrevem a v1.
5. Ciência/tecnologia, economia e religião precisam de mais exemplos para serem avaliadas.

## 7. Como reproduzir
`python scripts/experiments_v2.py && python scripts/analyze_v2.py && python scripts/train_v2.py && python scripts/build_term_stats.py && python scripts/build_examples.py && python scripts/audit_v3.py` (requer `data/full_texts/`).

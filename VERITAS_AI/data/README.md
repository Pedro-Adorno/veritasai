# Dados — Fake.br Corpus

**Base utilizada:** Fake.br Corpus (Monteiro et al., 2018), notícias em português brasileiro rotuladas como falsas (FAKE) ou verdadeiras (TRUE).

**Como obter:** repositório público do corpus no GitHub (`roneysco/Fake.br-Corpus`, pasta `full_texts`). **Confira a licença e as condições de uso no repositório original antes de redistribuir os dados.**
Neste projeto, o arquivo `full_texts.zip` foi fornecido pelo grupo.

**Onde colocar:** extraia para `data/full_texts/`, de modo que existam:

```
data/full_texts/fake/                  (3.600 arquivos .txt)
data/full_texts/true/                  (3.600 arquivos .txt)
data/full_texts/fake-meta-information/ (metadados: autor, link, categoria, data, métricas)
data/full_texts/true-meta-information/
```

**Verificado nos arquivos recebidos:** 7.200 textos (3.600 por classe), 1 duplicata exata, 67 pares de quase-duplicatas (similaridade ≥ 0,90, todos dentro da mesma classe), categorias alinhadas entre as classes, 92,7% das FAKE de um único domínio e 63,9% das TRUE do g1. Artefatos: aspas curvas em 57,8% das TRUE e 0% das FAKE. Detalhes no notebook (seções 5 e 6).

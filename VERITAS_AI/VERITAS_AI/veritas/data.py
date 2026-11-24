"""Carga, limpeza e divisão do Fake.br Corpus (mesma lógica do notebook v1, agora reutilizável)."""
import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from .pipeline import load_dataset
from .preprocess import normalize_text

SEED = 42


def source_group(link, label):
    """Agrupa subdomínios do mesmo veículo (ex.: *.estadao.com.br -> estadao)."""
    d = re.sub(r"^https?://", "", str(link)).split("/")[0].lower().replace("www1.", "").replace("www.", "")
    for key, name in [("g1.globo.com", "g1"), ("estadao.com.br", "estadao"), ("folha.uol.com.br", "folha"),
                      ("diariodobrasil.org", "diariodobrasil"), ("afolhabrasil.com.br", "afolhabrasil"),
                      ("thejornalbrasil.com.br", "thejornalbrasil")]:
        if d.endswith(key):
            return name
    return f"outros_{str(label).lower()}"


def load_clean(root, near_dup_threshold=0.90):
    """Retorna (df_limpo, info). Remove duplicatas exatas (pós-normalização) e quase-duplicatas (cosseno >= limiar)."""
    df = load_dataset(root)
    df["source"] = [source_group(l, y) for l, y in zip(df.link, df.label)]
    df["year"] = pd.to_numeric(df.date.astype(str).str.extract(r"((?:19|20)\d\d)")[0], errors="coerce")
    df["norm"] = df.text.map(normalize_text)
    df["n_words_raw"] = df.text.str.split().str.len()
    X = TfidfVectorizer(min_df=2, dtype=np.float32).fit_transform(df.norm)
    drop = set(df.index[df.duplicated("norm")])
    for s in range(0, X.shape[0], 1000):
        S = (X[s:s + 1000] @ X.T).toarray()
        for r in range(S.shape[0]):
            i = s + r
            for j in np.where(S[r] >= near_dup_threshold)[0]:
                if j > i:
                    drop.add(df.index[j])
    clean = df.drop(index=sorted(drop)).reset_index(drop=True)
    return clean, {"n_raw": int(len(df)), "n_removed": int(len(drop)), "n_clean": int(len(clean))}


def random_split(df):
    """Divisão estratificada 70/15/15 idêntica à v1 (semente 42)."""
    trainval, test = train_test_split(df, test_size=0.15, stratify=df.label, random_state=SEED)
    train, val = train_test_split(trainval, test_size=0.15 / 0.85, stratify=trainval.label, random_state=SEED)
    return train, val, test


def source_weights(df, power=0.5):
    """Peso por amostra ~ 1/n_fonte^power dentro de cada classe (reduz a dominância de fontes grandes)."""
    n = df.groupby(["label", "source"]).source.transform("size").astype(float)
    w = 1.0 / n ** power
    return (w / w.groupby(df.label).transform("mean")).values


def loso_group(source):
    """Fontes agrupadas para validação leave-one-source-out (fontes pequenas unidas)."""
    return {"thejornalbrasil": "minor_fake", "outros_fake": "minor_fake", "folha": "minor_true", "outros_true": "minor_true"}.get(source, source)


_LEN_BINS = [0, 50, 100, 200, 400, 800, 1600, 10**9]


def length_weights(df, cap=5.0):
    """Reponderação para equilibrar as classes DENTRO de cada faixa de tamanho (reduz o atalho de comprimento).
    Faixas dominadas por uma só classe recebem pesos limitados a [1/cap, cap]."""
    b = pd.cut(df.n_words_raw, _LEN_BINS, right=False)
    ct = pd.crosstab(b, df.label)
    tot = b.map(ct.sum(axis=1)).astype(float).values
    cls = np.array([ct.loc[bi, l] for bi, l in zip(b, df.label)], dtype=float)
    w = np.clip((tot / 2) / np.maximum(cls, 1), 1 / cap, cap)
    return w / pd.Series(w).groupby(df.label.values).transform("mean").values


def sample_weights(df, mode):
    """mode: None | 'src' | 'len' | 'src+len'. Normalizado para média 1 por classe."""
    if not mode: return None
    w = np.ones(len(df))
    if "src" in mode: w = w * source_weights(df)
    if "len" in mode: w = w * length_weights(df)
    w = w / pd.Series(w).groupby(df.label.values).transform("mean").values
    w = np.minimum(w, 10.0)            # evita que poucas amostras dominem o ajuste
    return w / pd.Series(w).groupby(df.label.values).transform("mean").values

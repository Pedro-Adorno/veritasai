"""Estatísticas reais dos termos no corpus de TREINO, para explicar a influência de cada termo em linguagem simples.
Para cada termo do vocabulário: nº de textos FAKE/TRUE do treino que o contêm, concentração em uma única fonte e
se aparece quase sempre capitalizado no meio das frases (indício de nome próprio). Saída: model/term_stats.json
Uso: python scripts/build_term_stats.py   (requer data/full_texts)"""
import json, os, re, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import joblib
from veritas.data import load_clean, random_split, loso_group

CAP = re.compile(r"(?<![.!?:]\s)(?<!^)\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+)\b")

if __name__ == "__main__":
    pipe = joblib.load(os.path.join(ROOT, "model", "modelo_veritas.joblib")); vec = pipe.named_steps["tfidf"]; voc = vec.vocabulary_
    df, _ = load_clean(os.path.join(ROOT, "data", "full_texts")); train, _, _ = random_split(df)
    X = vec.transform(train.text); X.data[:] = 1; X = X.tocsc()
    y = (train.label == "FAKE").values; src = train.source.map(loso_group).values; groups = sorted(set(src))
    nF, nT = int(y.sum()), int((~y).sum())
    dfF = np.asarray(X[y].sum(0)).ravel(); dfT = np.asarray(X[~y].sum(0)).ravel()
    conc = np.zeros(X.shape[1]); top = np.array([""] * X.shape[1], dtype=object)
    per = np.vstack([np.asarray(X[src == g].sum(0)).ravel() for g in groups]); tot = np.maximum(per.sum(0), 1)
    conc = per.max(0) / tot; top = np.array(groups)[per.argmax(0)]
    # capitalização no meio de frase (texto original do treino), por palavra
    caps, total = {}, {}
    for t in train.text:
        for m in re.finditer(r"(?<=[a-zà-ÿ0-9,;)\"”] )([A-Za-zÀ-ÿ][\wÀ-ÿ]+)", t):
            w = m.group(1); k = w.lower(); total[k] = total.get(k, 0) + 1; caps[k] = caps.get(k, 0) + (w[0].isupper())
    out = {"n_fake": nF, "n_true": nT, "terms": {}}
    for term, i in voc.items():
        words = term.split(); ratios = [caps.get(w, 0) / total[w] for w in words if total.get(w, 0) >= 3]
        proper = bool(ratios) and len(ratios) == len(words) and min(ratios) >= 0.7
        out["terms"][term] = [int(dfF[i]), int(dfT[i]), round(float(conc[i]), 2), str(top[i]), int(proper)]
    json.dump(out, open(os.path.join(ROOT, "model", "term_stats.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("termos:", len(out["terms"]), "| nomes próprios prováveis:", sum(v[4] for v in out["terms"].values()), "| tamanho:", os.path.getsize(os.path.join(ROOT, "model", "term_stats.json")) // 1024, "KB")

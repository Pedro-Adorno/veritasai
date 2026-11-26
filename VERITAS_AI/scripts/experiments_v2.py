"""Experimentos de generalização (v2): leave-one-source-out (LOSO) + comparação de estratégias.
Uso: python scripts/experiments_v2.py   (requer data/full_texts; ~10-15 min em 1 CPU)
Saídas: model/experiments_v2.json, model/oof_v2.npz"""
import json, os, sys, time
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from sklearn.metrics import f1_score
from veritas.data import load_clean, source_weights, sample_weights, loso_group, random_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.linear_model import LogisticRegression
from veritas.pipeline import build_pipeline

CFG = {  # nome: (modelo, kwargs build_pipeline, usa_pesos_de_fonte)
    "v1 (LR C=100)":            ("logreg", dict(C=100), False),
    "LR C=10":                  ("logreg", dict(C=10), False),
    "LR C=1":                   ("logreg", dict(C=1), False),
    "LR C=1 + pesos de fonte":  ("logreg", dict(C=1), True),
    "LR C=1 + máscara":         ("logreg", dict(C=1, mode="mask"), False),
    "LR C=1 + máscara + pesos": ("logreg", dict(C=1, mode="mask"), True),
    "LR C=0,3 + máscara + pesos": ("logreg", dict(C=0.3, mode="mask"), True),
    "LR unigramas C=1 + máscara + pesos": ("logreg", dict(C=1, mode="mask", ngram=(1, 1)), True),
    "LR C=1 + máscara + pesos + 100 palavras": ("logreg", dict(C=1, mode="mask", max_words=100), True),
    "LR C=1 + máscara + pesos + sem truncar": ("logreg", dict(C=1, mode="mask", max_words=None), True),
    "LR C=1 + máscara + pesos + stopwords": ("logreg", dict(C=1, mode="mask", stopwords=True), True),
    "Naive Bayes + máscara + pesos": ("nb", dict(C=0.1, mode="mask"), True),
    "Linear SVM C=0,1 + máscara + pesos": ("svm", dict(C=0.1, mode="mask"), True),
    # --- rodada 2: controle do atalho de comprimento (reponderação por faixa de tamanho) ---
    "LR C=1 + máscara + fonte+comprimento + sem truncar": ("logreg", dict(C=1, mode="mask", max_words=None), "src+len"),
    "LR C=1 + máscara + fonte+comprimento + 200 palavras": ("logreg", dict(C=1, mode="mask"), "src+len"),
    "LR C=1 + máscara + fonte+comprimento + 400 palavras": ("logreg", dict(C=1, mode="mask", max_words=400), "src+len"),
    "LR C=1 + máscara + comprimento + sem truncar": ("logreg", dict(C=1, mode="mask", max_words=None), "len"),
    "LR unigramas C=1 + máscara + fonte+comprimento + sem truncar": ("logreg", dict(C=1, mode="mask", max_words=None, ngram=(1, 1)), "src+len"),
    "LR C=0,3 + máscara + fonte+comprimento + sem truncar": ("logreg", dict(C=0.3, mode="mask", max_words=None), "src+len"),
    "Baseline: só comprimento do texto": ("lengthonly", {}, None),
    # --- rodada 3 (v3): remoção de nomes próprios (dependência de nomes de pessoas/partidos/instituições) ---
    "LR C=1 + máscara + sem nomes próprios": ("logreg", dict(C=1, mode="mask_names"), False),
    "LR C=1 + máscara + sem nomes próprios + pesos de fonte": ("logreg", dict(C=1, mode="mask_names"), True),
}


def _logwords(texts):
    return np.log1p(np.array([len(str(t).split()) for t in texts])).reshape(-1, 1)


def fit(cfg, d):
    model, kw, use_w = CFG[cfg]
    if model == "lengthonly":  # baseline: apenas log(nº de palavras)
        pipe = Pipeline([("feat", FunctionTransformer(_logwords)), ("clf", LogisticRegression(class_weight="balanced"))])
        return pipe.fit(d.text, d.label)
    pipe = build_pipeline(model, **kw)
    sw = sample_weights(d, "src" if use_w is True else use_w)
    pipe.fit(d.text, d.label, **({"clf__sample_weight": sw} if sw is not None else {}))
    return pipe


def p_fake(pipe, texts):
    clf = pipe.named_steps["clf"]
    i = list(clf.classes_).index("FAKE")
    if hasattr(pipe, "predict_proba"):
        return pipe.predict_proba(texts)[:, i]
    z = pipe.decision_function(texts)  # SVM: sigmoide do escore (apenas p/ ordenar; sem calibração)
    return 1 / (1 + np.exp(z)) if i == 0 else 1 / (1 + np.exp(-z))


if __name__ == "__main__":
    df, info = load_clean(os.path.join(ROOT, "data", "full_texts"))
    df["grp"] = df.source.map(loso_group)
    groups = sorted(df.grp.unique())
    res, oof = {}, {}
    jp, zp = os.path.join(ROOT, "model", "experiments_v2.json"), os.path.join(ROOT, "model", "oof_v2.npz")
    if os.path.exists(jp) and os.path.exists(zp):   # retoma: não refaz configurações já concluídas
        res = json.load(open(jp, encoding="utf-8"))["results"]; z = np.load(zp, allow_pickle=True); oof = {k: z[k] for k in res if k in z.files}
    for name in CFG:
        if name in res and name in oof: continue
        t0 = time.time(); folds = {}; pf = np.full(len(df), np.nan)
        for g in groups:
            te = df.grp == g
            pipe = fit(name, df[~te])
            pf[te.values] = p_fake(pipe, df[te].text)
            lab = df[te].label.iloc[0]
            pred_fake = pf[te.values] >= 0.5
            rec = pred_fake.mean() if lab == "FAKE" else 1 - pred_fake.mean()
            folds[g] = {"class": lab, "n": int(te.sum()), "recall": float(rec)}
        rf = np.mean([v["recall"] for v in folds.values() if v["class"] == "FAKE"])
        rt = np.mean([v["recall"] for v in folds.values() if v["class"] == "TRUE"])
        ex = [v["recall"] for g, v in folds.items() if g != "diariodobrasil"]
        res[name] = {"folds": folds, "recall_FAKE_mean": float(rf), "recall_TRUE_mean": float(rt), "balanced": float((rf + rt) / 2),
                     "balanced_sem_diariodobrasil": float(np.mean(ex)), "seconds": round(time.time() - t0, 1)}
        oof[name] = pf
        print(f"{name:45s} bal={res[name]['balanced']:.3f} recF={rf:.3f} recT={rt:.3f} ({res[name]['seconds']}s)", flush=True)
        json.dump({"corpus": info, "groups": groups, "results": res}, open(os.path.join(ROOT, "model", "experiments_v2.json"), "w"), ensure_ascii=False, indent=1)
    np.savez_compressed(os.path.join(ROOT, "model", "oof_v2.npz"), ids=df.id.values, label=df.label.values, grp=df.grp.values, **{k: v for k, v in oof.items()})
    print("DONE", flush=True)

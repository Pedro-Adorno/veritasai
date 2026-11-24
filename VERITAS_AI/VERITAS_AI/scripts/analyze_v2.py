"""Pós-análise dos experimentos LOSO: avaliação com COMPRIMENTO CONTROLADO + baseline só-comprimento.
Motivo: a métrica LOSO simples premia configurações que exploram o tamanho do texto (atalho comum a todas as fontes).
Uso: python scripts/analyze_v2.py  (usa model/oof_v2.npz; atualiza model/experiments_v2.json)"""
import json, os, sys
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from veritas.data import load_clean, loso_group

BINS = [0, 50, 100, 200, 400, 800, 1600, 10**9]


def length_window(df, min_per_class=60):
    """Faixas de tamanho (nº de palavras brutas) em que AMBAS as classes têm >= min_per_class textos."""
    b = pd.cut(df.n_words_raw, BINS, right=False)
    ct = pd.crosstab(b, df.label)
    ok = ct[(ct.FAKE >= min_per_class) & (ct.TRUE >= min_per_class)].index
    return b.isin(ok).values, [str(i) for i in ok]


if __name__ == "__main__":
    df, _ = load_clean(os.path.join(ROOT, "data", "full_texts")); df["grp"] = df.source.map(loso_group)
    z = np.load(os.path.join(ROOT, "model", "oof_v2.npz"), allow_pickle=True)
    assert (z["ids"] == df.id.values).all() and (z["label"] == df.label.values).all()
    win, bins = length_window(df); print("faixas com ambas as classes:", bins, "| textos na janela:", int(win.sum()), flush=True)
    path = os.path.join(ROOT, "model", "experiments_v2.json"); exp = json.load(open(path, encoding="utf-8"))
    for name in exp["results"]:
        if name not in z.files: continue
        p = z[name]; fold = {}
        for g in sorted(df.grp.unique()):
            m = (df.grp == g).values & win
            lab = df.label[m].iloc[0] if m.any() else None
            if lab is None: continue
            pf = p[m] >= 0.5; fold[g] = {"class": lab, "n": int(m.sum()), "recall": float(pf.mean() if lab == "FAKE" else 1 - pf.mean())}
        rf = np.mean([v["recall"] for v in fold.values() if v["class"] == "FAKE"]); rt = np.mean([v["recall"] for v in fold.values() if v["class"] == "TRUE"])
        exp["results"][name]["length_matched"] = {"folds": fold, "recall_FAKE_mean": float(rf), "recall_TRUE_mean": float(rt), "balanced": float((rf + rt) / 2)}
    exp["length_window_bins"] = bins
    json.dump(exp, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rows = sorted(((v["length_matched"]["balanced"], v["balanced"], k) for k, v in exp["results"].items() if "length_matched" in v), reverse=True)
    for lm, b, k in rows: print(f"{k:60s} LOSO={b:.3f}  LOSO(comprimento controlado)={lm:.3f}")

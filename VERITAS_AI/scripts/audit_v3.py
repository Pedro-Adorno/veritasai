"""Auditoria v3 do modelo atual: desempenho por tamanho, cobertura, assunto, confiança e dependência de nomes próprios.
Usa o modelo exportado (model/) e a divisão idêntica da v1/v2. Saída: model/audit_v3.json"""
import json, os, sys
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from veritas.data import load_clean, random_split, loso_group
from veritas.inference import Analyzer
from veritas.pipeline import explain_full
from veritas.preprocess import strip_proper_names

if __name__ == "__main__":
    an = Analyzer(os.path.join(ROOT, "model"))
    df, _ = load_clean(os.path.join(ROOT, "data", "full_texts")); tr, va, te = random_split(df); out = {}
    def run(d):
        rows = []
        for t, y in zip(d.text, d.label):
            r = an.analyze(t); rows.append({"y": y, "raw": r["raw_label"], "final": r["label"], "q": r["calibrated"]["FAKE"], "cobv": r["vocab_coverage"], "n": len(t.split())})
        return pd.DataFrame(rows)
    for name, d in (("validacao", va), ("teste", te)):
        r = run(d); r["cat"] = d.category.values; r["ok_raw"] = r.y == r.raw; dec = r.final != "INCONCLUSIVE"; r["ok"] = (r.y == r.final) & dec
        res = {"n": len(r), "inconclusivo": float((~dec).mean()), "acc_decididas": float(r.ok[dec].mean())}
        res["por_tamanho"] = {str(k): {"n": int(len(g)), "acc_bruta": float(g.ok_raw.mean()), "inconclusivo": float((g.final == 'INCONCLUSIVE').mean())} for k, g in r.groupby(pd.cut(r.n, [0, 60, 120, 250, 600, 10**9]), observed=True)}
        res["por_cobertura"] = {str(k): {"n": int(len(g)), "acc_bruta": float(g.ok_raw.mean())} for k, g in r.groupby(pd.cut(r.cobv, [0, .6, .7, .8, .9, 1.01]), observed=True)}
        res["por_assunto"] = {k: {"n": int(len(g)), "acc_bruta": float(g.ok_raw.mean()), "inconclusivo": float((g.final == 'INCONCLUSIVE').mean())} for k, g in r.groupby("cat")}
        conf = (r.q - 0.5).abs() * 2; r["conf"] = conf
        res["por_confianca"] = {str(k): {"n": int(len(g)), "acc_decididas": float(g.ok[g.final != 'INCONCLUSIVE'].mean()) if (g.final != 'INCONCLUSIVE').any() else None} for k, g in r.groupby(pd.cut(conf, [0, .1, .2, .4, .6, 1.01], include_lowest=True), observed=True)}
        out[name] = res
    # dependência de nomes próprios (teste): quantas previsões mudam ao remover nomes; fração da evidência vinda de termos capitalizados
    flips = 0; sh = []
    for t in te.text.head(400):
        a = an.pipe.predict([t])[0]; b = an.pipe.predict([strip_proper_names(t)])[0]; flips += a != b
    out["nomes_proprios"] = {"n": 400, "previsoes_que_mudam_sem_nomes": int(flips), "fracao": flips / 400}
    json.dump(out, open(os.path.join(ROOT, "model", "audit_v3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])

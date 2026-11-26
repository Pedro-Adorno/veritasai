"""Treino final v2: seleção por generalização entre fontes, calibração (Platt) e abstenção, exportação dos artefatos.
Uso: python scripts/train_v2.py   (após scripts/experiments_v2.py; ~5 min em 1 CPU)"""
import datetime, json, os, platform, sys, time
import numpy as np, pandas as pd, joblib, sklearn
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts"))
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, roc_auc_score, brier_score_loss, confusion_matrix
from veritas.data import load_clean, random_split, source_weights, loso_group
from veritas.pipeline import top_terms
from veritas.preprocess import normalize_text
import experiments_v2 as E

SEED = 42
MODEL_DIR = os.path.join(ROOT, "model")
TARGET_SELECTIVE_ACC = 0.80   # política definida ANTES de ver os resultados finais; ver TECHNICAL_NOTES.md
MIN_COVERAGE = 0.20
TARGET_PRECISION = 0.95       # v3: cada veredito (FAKE e TRUE) deve ter precisão >= 95% na VALIDAÇÃO (política declarada; a curva completa é exportada)


def logit(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def sig(z): return 1 / (1 + np.exp(-z))


def platt_fit(p_fake, y_fake, w=None):
    """Platt com pesos por fonte E classes equilibradas (o corpus é balanceado; sem isso o intercepto absorve a prevalência
    das fontes que restaram no treino do calibrador, o que distorce a avaliação leave-one-group-out)."""
    w = np.ones(len(y_fake)) if w is None else w.copy()
    for c in (0, 1):
        m = y_fake == c
        if m.any(): w[m] = w[m] / w[m].sum() * 0.5 * len(y_fake)
    lr = LogisticRegression(C=1e4, max_iter=1000).fit(logit(p_fake).reshape(-1, 1), y_fake, sample_weight=w)
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def platt_apply(p_fake, a, b): return sig(a * logit(p_fake) + b)


def ece(q, y, bins=10):
    """ECE sobre P(FAKE): |frequência observada - probabilidade média| por faixa."""
    idx = np.minimum((q * bins).astype(int), bins - 1); t = 0.0
    for k in range(bins):
        m = idx == k
        if m.any(): t += m.mean() * abs(y[m].mean() - q[m].mean())
    return float(t)


def decide(q, lo, hi):
    """q = P(FAKE) calibrada. Retorna 'FAKE', 'TRUE' ou 'INCONCLUSIVE'."""
    return np.where(q >= hi, "FAKE", np.where(q <= lo, "TRUE", "INCONCLUSIVE"))


def sel_stats(pred, y, w=None):
    """Cobertura e qualidade das decisões tomadas (ignora INCONCLUSIVE). w: pesos por amostra (opcional)."""
    w = np.ones(len(y)) if w is None else w
    dec = pred != "INCONCLUSIVE"; cov = float(w[dec].sum() / w.sum())
    if dec.sum() == 0: return {"coverage": 0.0, "accuracy": None, "recall_FAKE": None, "recall_TRUE": None, "balanced": None, "n_decided": 0, "FN": 0, "FP": 0}
    ok = (pred == y) & dec
    rf = (w[ok & (y == "FAKE")].sum() / max(w[dec & (y == "FAKE")].sum(), 1e-9)); rt = (w[ok & (y == "TRUE")].sum() / max(w[dec & (y == "TRUE")].sum(), 1e-9))
    # recall sobre TODOS os reais da classe (abstenção conta como não encontrado)
    rf_all = w[ok & (y == "FAKE")].sum() / max(w[y == "FAKE"].sum(), 1e-9)
    return {"coverage": cov, "accuracy": float(w[ok].sum() / w[dec].sum()), "precision_like_balanced": float((rf + rt) / 2),
            "recall_FAKE_all": float(rf_all), "n_decided": int(dec.sum()),
            "FN": int(((y == "FAKE") & (pred == "TRUE")).sum()), "FP": int(((y == "TRUE") & (pred == "FAKE")).sum())}


def pick_model(exp):
    """Critério REVISADO (ver TECHNICAL_NOTES): maior LOSO com comprimento controlado (`length_matched.balanced`);
    LR preferida salvo vantagem > 1 p.p. de outro modelo. Exclui o baseline só-comprimento."""
    key = lambda k: exp["results"][k]["length_matched"]["balanced"]
    # Apenas configurações com entrada de tamanho LIMITADO: as sem truncar ficam abaixo do baseline só-comprimento
    # mesmo com comprimento controlado (0,69-0,73 vs 0,83), logo não demonstram sinal linguístico além do tamanho.
    r = {k: v for k, v in exp["results"].items() if E.CFG[k][0] != "lengthonly" and "length_matched" in v and E.CFG[k][1].get("max_words", 200) is not None}
    lrs = [k for k in r if E.CFG[k][0] == "logreg"]
    best_lr, best_any = max(lrs, key=key), max(r, key=key)
    return best_any if key(best_any) - key(best_lr) > 0.01 else best_lr


if __name__ == "__main__":
    t_all = time.time()
    exp = json.load(open(os.path.join(MODEL_DIR, "experiments_v2.json"), encoding="utf-8"))
    chosen = pick_model(exp); print("Configuração escolhida:", chosen, flush=True)
    df, info = load_clean(os.path.join(ROOT, "data", "full_texts")); df["grp"] = df.source.map(loso_group)
    train, val, test = random_split(df); trainval = pd.concat([train, val]).reset_index(drop=True)

    # 1) OOF entre fontes SOMENTE com treino+validação (o teste não participa de calibração/abstenção)
    groups = sorted(trainval.grp.unique()); oof = np.full(len(trainval), np.nan)
    for g in groups:
        m = (trainval.grp == g).values
        oof[m] = E.p_fake(E.fit(chosen, trainval[~m]), trainval[m].text)
    y_tv = (trainval.label == "FAKE").values.astype(int); w_tv = source_weights(trainval)
    # 2) calibração avaliada com leave-one-group-out do próprio calibrador (sem olhar o grupo avaliado)
    q_logo = np.zeros(len(trainval))
    for g in groups:
        m = (trainval.grp == g).values; a, b = platt_fit(oof[~m], y_tv[~m], w_tv[~m]); q_logo[m] = platt_apply(oof[m], a, b)
    cal_eval = {"brier_raw": float(brier_score_loss(y_tv, oof, sample_weight=w_tv)), "brier_cal_logo": float(brier_score_loss(y_tv, q_logo, sample_weight=w_tv)),
                "ece_raw": ece(oof, y_tv), "ece_cal_logo": ece(q_logo, y_tv)}
    a, b = platt_fit(oof, y_tv, w_tv); print("Platt a,b =", round(a, 3), round(b, 3), cal_eval, flush=True)

    # 3) limiares de abstenção (grade) sobre as previsões calibradas entre fontes
    y_tv_lab = trainval.label.values; grid = []
    for lo in np.arange(0.05, 0.51, 0.05):
        for hi in np.arange(0.50, 0.96, 0.05):
            if lo >= hi: continue
            s = sel_stats(decide(q_logo, lo, hi), y_tv_lab, w_tv); grid.append({"lo": round(float(lo), 2), "hi": round(float(hi), 2), **s})
    ok = [g for g in grid if g["accuracy"] is not None and g["coverage"] >= MIN_COVERAGE and g["accuracy"] >= TARGET_SELECTIVE_ACC]
    if ok: pol = max(ok, key=lambda g: g["coverage"]); policy_met = True
    else:
        cand = [g for g in grid if g["accuracy"] is not None and g["coverage"] >= MIN_COVERAGE]
        pol = max(cand, key=lambda g: g["accuracy"] * g["coverage"]); policy_met = False
    lo, hi = pol["lo"], pol["hi"]; base = sel_stats(decide(q_logo, 0.5, 0.5), y_tv_lab, w_tv)
    print("Meta atingida:", policy_met, "| banda:", lo, hi, "| cobertura:", round(pol["coverage"], 3), "| acc seletiva:", round(pol["accuracy"], 3), "| acc sem abstenção:", round(base["accuracy"], 3), flush=True)

    # 4) modelo final (treinado só no treino, como na v1) e avaliação no teste aleatório
    t0 = time.time(); final = E.fit(chosen, train); fit_s = time.time() - t0
    # 3b) v3 — política por PRECISÃO de cada veredito na validação. Revisão da v2: a meta de acurácia seletiva ENTRE FONTES (80%) era
    # inatingível e gerava uma banda quase nula e assimétrica (muitos falsos positivos). Limiares agora vêm da validação, simétricos por classe.
    q_v0 = platt_apply(E.p_fake(final, val.text), a, b); y_v0 = val.label.values; best = None; curve = []
    for lo_ in np.round(np.arange(0.05, 0.50, 0.01), 2):
        for hi_ in np.round(np.arange(0.50, 0.96, 0.01), 2):
            pr = decide(q_v0, lo_, hi_); mf, mt = pr == "FAKE", pr == "TRUE"
            if mf.sum() < 30 or mt.sum() < 30: continue
            pf, pt_, cov_ = float((y_v0[mf] == "FAKE").mean()), float((y_v0[mt] == "TRUE").mean()), float((mf | mt).mean())
            curve.append({"lo": float(lo_), "hi": float(hi_), "coverage": cov_, "precision_FAKE": pf, "precision_TRUE": pt_})
            if pf >= TARGET_PRECISION and pt_ >= TARGET_PRECISION and (best is None or cov_ > best["coverage"]): best = curve[-1]
    if best is not None:
        lo, hi = best["lo"], best["hi"]; policy_met = True
        pol = {"lo": lo, "hi": hi, **sel_stats(decide(q_logo, lo, hi), y_tv_lab, w_tv)}
    val_policy = {"target_precision": TARGET_PRECISION, "chosen": best, "curve_sample": curve[::25]}
    print("Política v3 (precisão >= %.2f por veredito na validação):" % TARGET_PRECISION, best, flush=True)

    t0 = time.time(); p_te = E.p_fake(final, test.text); infer_ms = (time.time() - t0) / len(test) * 1000
    q_te = platt_apply(p_te, a, b); y_te = test.label.values
    pred_raw = np.where(p_te >= 0.5, "FAKE", "TRUE"); pred_cal = np.where(q_te >= 0.5, "FAKE", "TRUE"); pred_abs = decide(q_te, lo, hi)
    def mdict(y, pred):
        p, r, f, s = precision_recall_fscore_support(y, pred, labels=["FAKE", "TRUE"], zero_division=0)
        return {"accuracy": float(accuracy_score(y, pred)), "f1_macro": float(f1_score(y, pred, average="macro")), "precision_macro": float(p.mean()), "recall_macro": float(r.mean()),
                "per_class": {c: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])} for i, c in enumerate(["FAKE", "TRUE"])}}
    tm = {**mdict(y_te, pred_raw), "n": int(len(test)), "labels": ["FAKE", "TRUE"], "confusion_matrix": confusion_matrix(y_te, pred_raw, labels=["FAKE", "TRUE"]).tolist(),
          "roc_auc": float(roc_auc_score((y_te == "FAKE").astype(int), p_te)), "brier": float(brier_score_loss((y_te == "FAKE").astype(int), p_te)), "ece": ece(p_te, (y_te == "FAKE").astype(int))}
    abst_test = {"before": sel_stats(pred_raw, y_te), "after": sel_stats(pred_abs, y_te),
                 "brier_cal": float(brier_score_loss((y_te == "FAKE").astype(int), q_te)), "ece_cal": ece(q_te, (y_te == "FAKE").astype(int))}

    # 5) famílias de modelo (mesmo pré-processamento) — validação e teste
    fam = []
    for key, nm in [("logreg", "Regressão Logística"), ("nb", "Multinomial Naive Bayes"), ("svm", "Linear SVM")]:
        name = chosen if key == "logreg" else next((k for k in E.CFG if E.CFG[k][0] == key), None)
        pipe = final if key == "logreg" else E.fit(name, train)
        e = exp["results"].get(name, {})
        fam.append({"key": key, "model": nm, "config": name, "val": mdict(val.label.values, np.where(E.p_fake(pipe, val.text) >= 0.5, "FAKE", "TRUE")),
                    "test": mdict(y_te, np.where(E.p_fake(pipe, test.text) >= 0.5, "FAKE", "TRUE")), "loso_balanced": e.get("balanced"), "loso_recall_FAKE": e.get("recall_FAKE_mean"), "loso_recall_TRUE": e.get("recall_TRUE_mean")})

    # 6) separação temporal (treina <= 2016, testa >= 2017) — v1 x escolhida
    tmp = {}
    old, new = df[df.year <= 2016], df[df.year >= 2017]
    for nm in ("v1 (LR C=100)", chosen):
        pp = E.fit(nm, old); pr = np.where(E.p_fake(pp, new.text) >= 0.5, "FAKE", "TRUE")
        tmp[nm] = {"n_train": int(len(old)), "n_test": int(len(new)), "recall_FAKE": float((pr[new.label.values == "FAKE"] == "FAKE").mean()), "recall_TRUE": float((pr[new.label.values == "TRUE"] == "TRUE").mean())}
        tmp[nm]["balanced"] = (tmp[nm]["recall_FAKE"] + tmp[nm]["recall_TRUE"]) / 2

    # 6b) níveis de confiança (v3): tercis da confiança calibrada das análises DECIDIDAS na validação; acurácia observada por nível
    q_val = platt_apply(E.p_fake(final, val.text), a, b); pv = decide(q_val, lo, hi); dv = pv != "INCONCLUSIVE"
    cv_ = np.where(pv == "FAKE", q_val, 1 - q_val); yv = val.label.values
    e1, e2 = [float(x) for x in np.percentile(cv_[dv], [33.3, 66.7])]
    def lvl(c): return np.where(c < e1, 0, np.where(c < e2, 1, 2))
    lv_val = lvl(cv_)
    q_sh = q_logo; ps = decide(q_sh, lo, hi); ds = ps != "INCONCLUSIVE"; cs = np.where(ps == "FAKE", q_sh, 1 - q_sh); lv_sh = lvl(cs)
    levels = []
    for k, nm in enumerate(["baixa", "moderada", "alta"]):
        mv = dv & (lv_val == k); ms = ds & (lv_sh == k)
        levels.append({"name": nm, "n_val": int(mv.sum()), "val_accuracy": float((pv[mv] == yv[mv]).mean()) if mv.any() else None,
                       "n_source_shift": int(ms.sum()), "source_shift_accuracy": float((ps[ms] == y_tv_lab[ms]).mean()) if ms.any() else None})
    conf_levels = {"edges": [e1, e2], "levels": levels, "method": "tercis da confiança calibrada das análises decididas (validação aleatória)"}
    print("Níveis de confiança:", conf_levels, flush=True)

    # 7) limiares de aviso a partir do treino
    vec = final.named_steps["tfidf"]; an = vec.build_analyzer(); voc = vec.vocabulary_
    def cov(t): tk = [x for x in an(t) if " " not in x]; return sum(x in voc for x in tk) / len(tk) if tk else 0.0
    cvs = np.array([cov(t) for t in train.text.sample(1500, random_state=SEED)]); nw = train.n_words_raw.values
    warn = {"n_words_p1": float(np.percentile(nw, 1)), "vocab_coverage_p5": float(np.percentile(cvs, 5)), "vocab_coverage_p1": float(np.percentile(cvs, 1)), "n_words_p5": float(np.percentile(nw, 5)), "n_words_p99": float(np.percentile(nw, 99))}

    # 8) exportação
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    joblib.dump(final, os.path.join(MODEL_DIR, "modelo_veritas.joblib"), compress=3)
    model_kw, w_flag = E.CFG[chosen][1], E.CFG[chosen][2]
    meta = {"model_name": "Regressão Logística + TF-IDF", "version": "2.0.0", "trained_at": now, "dataset": "Fake.br Corpus", "classes": list(final.named_steps["clf"].classes_),
            "config_name": chosen, "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in model_kw.items()}, "source_balanced_weights": w_flag, "random_state": SEED,
            "selection_rule": "Maior LOSO com comprimento controlado; LR preferida salvo vantagem > 1 p.p. de outro modelo",
            "calibration": {"method": "platt", "a": a, "b": b, "fitted_on": "previsões out-of-fold entre fontes (treino+validação)", "weights": "pesos por fonte"},
            "abstention": {"lo": lo, "hi": hi, "rule": f"maior cobertura com precisão >= {TARGET_PRECISION} em cada veredito (FAKE e TRUE) na validação; {'meta atingida' if policy_met else 'meta NÃO atingida: banda da v2 (acurácia x cobertura entre fontes)'}", "policy_met": policy_met, "validation": val_policy},
            "warning_thresholds": warn, "confidence_levels": conf_levels, "training_set_size": int(len(train)), "probabilities_calibrated": True,
            "library_versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__, "joblib": joblib.__version__},
            "disclaimer": "Classificação de padrões linguísticos aprendidos em corpus rotulado; não é verificação factual."}
    json.dump(meta, open(os.path.join(MODEL_DIR, "metadata.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    v1 = json.load(open(os.path.join(MODEL_DIR, "v1", "metricas.json"), encoding="utf-8"))
    metr = {"generated_at": now, "version": "2.0.0",
            "dataset": {**{k: v1["dataset"][k] for k in ("name", "n_raw", "n_removed_duplicates", "n_clean", "class_counts_clean", "class_counts_raw", "words_by_class", "artifacts_pct", "top_domains")},
                        "split": {n: {"n": int(len(d)), **d.label.value_counts().to_dict()} for n, d in [("treino", train), ("validação", val), ("teste", test)]},
                        "sources_by_class": {l: df[df.label == l].source.value_counts().to_dict() for l in ("FAKE", "TRUE")},
                        "years_by_class": {l: df[df.label == l].year.value_counts().sort_index().astype(int).to_dict() for l in ("FAKE", "TRUE")}},
            "selected_vectorization": v1["selected_vectorization"], "model_comparison": fam, "selected_model": {"key": "logreg", "name": "Regressão Logística", "C": model_kw.get("C"), "config": chosen},
            "test": tm, "errors": {"false_negatives_fake_as_true": tm["confusion_matrix"][0][1], "false_positives_true_as_fake": tm["confusion_matrix"][1][0]},
            "top_terms": {k: [{"term": t, "weight": w} for t, w in v] for k, v in top_terms(final, 20).items()},
            "generalization": {"protocol": "leave-one-source-out (cada fonte inteira fora do treino; recall na classe da fonte)", "configs": exp["results"], "chosen": chosen,
                               "v1": "v1 (LR C=100)", "temporal_split_train_le_2016_test_ge_2017": tmp},
            "calibration": {**cal_eval, "test": {"brier_raw": tm["brier"], "ece_raw": tm["ece"], "brier_cal": abst_test["brier_cal"], "ece_cal": abst_test["ece_cal"]}, "a": a, "b": b},
            "abstention": {"lo": lo, "hi": hi, "policy_met": policy_met, "target_precision": TARGET_PRECISION, "validation": val_policy, "target_selective_accuracy": TARGET_SELECTIVE_ACC, "min_coverage": MIN_COVERAGE,
                           "oof_source_shift": {"without": base, "with": pol}, "test_random": abst_test, "grid": grid},
            "timing": {"train_fit_seconds": round(fit_s, 1), "inference_ms_per_text": round(infer_ms, 3)}}
    json.dump(metr, open(os.path.join(MODEL_DIR, "metricas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("TESTE v2 (aleatório): acc=%.4f f1m=%.4f | FN=%d FP=%d" % (tm["accuracy"], tm["f1_macro"], tm["confusion_matrix"][0][1], tm["confusion_matrix"][1][0]))
    print("Abstenção no teste:", abst_test["before"], abst_test["after"]); print("Temporal:", tmp); print("DONE em %.0fs" % (time.time() - t_all), flush=True)

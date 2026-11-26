"""Camada de inferência compartilhada (notebook e aplicação Flask): carrega o modelo exportado e analisa textos."""
import json
import os
import re
import math
import numpy as np
import joblib
from .pipeline import explain, explain_full
from .plain import build_plain
from .preprocess import normalize_text, MAX_WORDS

MIN_WORDS_RELIABLE = 30  # abaixo disso o modelo vê muito pouco texto
LABEL_PT = {"FAKE": "Padrões associados a FAKE", "TRUE": "Padrões associados a TRUE", "INCONCLUSIVE": "Resultado inconclusivo"}


class Analyzer:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.pipe = joblib.load(os.path.join(model_dir, "modelo_veritas.joblib"))
        with open(os.path.join(model_dir, "metadata.json"), encoding="utf-8") as f:
            self.metadata = json.load(f)
        with open(os.path.join(model_dir, "metricas.json"), encoding="utf-8") as f:
            self.metrics = json.load(f)
        self.classes = list(self.pipe.named_steps["clf"].classes_)
        self.cal = self.metadata.get("calibration")          # v2: Platt sobre P(FAKE) bruta
        self.abst = self.metadata.get("abstention")          # v2: banda de abstenção sobre P(FAKE) calibrada
        self.warn_thr = self.metadata.get("warning_thresholds", {})
        self.levels = self.metadata.get("confidence_levels")
        try:  # estatísticas reais dos termos no treino (scripts/build_term_stats.py); opcional
            with open(os.path.join(model_dir, "term_stats.json"), encoding="utf-8") as f:
                self.term_stats = json.load(f)
        except (OSError, ValueError):
            self.term_stats = None

    def _shift_acc(self):
        """Acerto médio (recall médio FAKE/TRUE) ao deixar uma fonte inteira fora do treino — valor real de model/metricas.json."""
        try:
            g = self.metrics["generalization"]; return float(g["configs"][g["chosen"]]["balanced"])
        except (KeyError, TypeError):
            return None

    def _calibrated_fake(self, p_fake):
        p = min(max(p_fake, 1e-6), 1 - 1e-6)
        z = self.cal["a"] * math.log(p / (1 - p)) + self.cal["b"]
        return 1 / (1 + math.exp(-z))

    @staticmethod
    def descriptive_indicators(text):
        words = re.findall(r"\w+", text, flags=re.UNICODE)
        letters = [c for c in text if c.isalpha()]
        upper = sum(1 for c in letters if c.isupper())
        return {
            "palavras": len(words),
            "exclamacoes": text.count("!"),
            "interrogacoes": text.count("?"),
            "proporcao_maiusculas": round(upper / len(letters), 3) if letters else 0.0,
            "palavras_analisadas": min(len(words), MAX_WORDS),
            "texto_truncado": len(words) > MAX_WORDS,
        }

    def analyze(self, text, title=""):
        full = (title.strip() + ". " if title and title.strip() else "") + (text or "")
        if not normalize_text(full):
            raise ValueError("Conteúdo vazio.")
        proba = self.pipe.predict_proba([full])[0]
        probs = {c: float(p) for c, p in zip(self.classes, proba)}
        raw_label = max(probs, key=probs.get)
        label, calibrated, reasons = raw_label, None, []
        if self.cal and self.abst:
            q = self._calibrated_fake(probs["FAKE"])
            calibrated = {"FAKE": q, "TRUE": 1 - q}
            label = "FAKE" if q >= self.abst["hi"] else ("TRUE" if q <= self.abst["lo"] else "INCONCLUSIVE")
        reasons = ["ambiguo"] if label == "INCONCLUSIVE" else []
        exp = explain(self.pipe, full, k=8)
        full_exp = explain_full(self.pipe, full, k=8)
        ind = self.descriptive_indicators(full)
        warnings = []
        if ind["palavras"] < MIN_WORDS_RELIABLE:
            warnings.append(f"Texto curto ({ind['palavras']} palavras): o modelo foi treinado com notícias completas; o resultado é pouco informativo.")
        if ind["texto_truncado"]:
            warnings.append(f"Somente as primeiras {MAX_WORDS} palavras foram analisadas (mesma regra usada no treino).")
        cov, thr = full_exp["vocab_coverage"], self.warn_thr
        if thr and cov < thr.get("vocab_coverage_p5", 0):
            warnings.append(f"Baixa cobertura do vocabulário: só {cov * 100:.0f}% das palavras do texto são conhecidas pelo modelo (95% dos textos de treino têm mais que {thr['vocab_coverage_p5'] * 100:.0f}%). O texto pode estar fora do padrão do treinamento (outro idioma, muitos símbolos ou tema atípico).")
        # fora do domínio validado: abaixo do 1º percentil do treino (não há como validar a confiança nessa faixa)
        if self.cal and self.abst:
            n_min = thr.get("n_words_p1")
            if n_min and ind["palavras"] < n_min:
                reasons.append("curto")
            if thr.get("vocab_coverage_p1") and cov < thr["vocab_coverage_p1"]:
                reasons.append("fora_dominio")
            if full_exp["n_terms"] < 5:
                reasons.append("poucos_termos")
            if any(r in reasons for r in ("curto", "fora_dominio", "poucos_termos")):
                label = "INCONCLUSIVE"
        if label == "INCONCLUSIVE":
            warnings.append("Inconclusivo não significa verdadeiro nem falso: o modelo não encontrou sinais estatísticos suficientes para uma classificação confiável.")
        q_fake = calibrated["FAKE"] if calibrated else None
        plain = build_plain(label, q_fake, reasons, full_exp, full, self.term_stats, self.levels, ind["palavras"], self._shift_acc())
        return {
            "plain": plain, "reasons": reasons,
            "label": label, "raw_label": raw_label, "abstained": label == "INCONCLUSIVE", "calibrated": calibrated,
            "abstention": ({"lo": self.abst["lo"], "hi": self.abst["hi"]} if self.abst else None), "vocab_coverage": cov,
            "label_pt": LABEL_PT[label],
            "probabilities": probs,
            "margin": abs(probs["FAKE"] - probs["TRUE"]),
            "terms": {"FAKE": [{"term": t, "weight": w} for t, w in exp["FAKE"]],
                      "TRUE": [{"term": t, "weight": w} for t, w in exp["TRUE"]]},
            "terms_found": exp["n_features_used"],
            "explanation": full_exp,
            "indicators": ind,
            "warnings": warnings,
            "model": {k: self.metadata.get(k) for k in ("model_name", "version", "trained_at")},
        }

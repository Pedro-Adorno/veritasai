"""Camada de inferência compartilhada (notebook e aplicação Flask): carrega o modelo exportado e analisa textos."""
import json
import os
import re
import numpy as np
import joblib
from .pipeline import explain, explain_full
from .preprocess import normalize_text, MAX_WORDS

MIN_WORDS_RELIABLE = 30  # abaixo disso o modelo vê muito pouco texto
LABEL_PT = {"FAKE": "Padrões associados a FAKE", "TRUE": "Padrões associados a TRUE"}


class Analyzer:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.pipe = joblib.load(os.path.join(model_dir, "modelo_veritas.joblib"))
        with open(os.path.join(model_dir, "metadata.json"), encoding="utf-8") as f:
            self.metadata = json.load(f)
        with open(os.path.join(model_dir, "metricas.json"), encoding="utf-8") as f:
            self.metrics = json.load(f)
        self.classes = list(self.pipe.named_steps["clf"].classes_)

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
        label = max(probs, key=probs.get)
        exp = explain(self.pipe, full, k=8)
        full_exp = explain_full(self.pipe, full, k=8)
        ind = self.descriptive_indicators(full)
        warnings = []
        if ind["palavras"] < MIN_WORDS_RELIABLE:
            warnings.append(f"Texto curto ({ind['palavras']} palavras): o modelo foi treinado com notícias completas; o resultado é pouco informativo.")
        if ind["texto_truncado"]:
            warnings.append(f"Somente as primeiras {MAX_WORDS} palavras foram analisadas (mesma regra usada no treino).")
        return {
            "label": label,
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

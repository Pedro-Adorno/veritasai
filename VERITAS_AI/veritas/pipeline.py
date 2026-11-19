"""Pipeline scikit-learn e utilitários (compartilhados entre notebook e aplicação web)."""
import os
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from .preprocess import TextPreprocessor, STOPWORDS_PT, MAX_WORDS

TOKEN_PATTERN = r"(?u)\b\w+\b|[!?]"


def build_pipeline(model_name="logreg", ngram=(1, 2), min_df=3, max_df=0.9, max_features=50000,
                   C=1.0, max_words=MAX_WORDS, mode="full", stopwords=False):
    vec = TfidfVectorizer(preprocessor=TextPreprocessor(max_words, mode), lowercase=False,
                          ngram_range=ngram, min_df=min_df, max_df=max_df, max_features=max_features,
                          sublinear_tf=True, token_pattern=TOKEN_PATTERN,
                          stop_words=STOPWORDS_PT if stopwords else None)
    if model_name == "logreg":
        clf = LogisticRegression(C=C, max_iter=2000, class_weight="balanced")
    elif model_name == "nb":
        clf = MultinomialNB(alpha=C)
    elif model_name == "svm":
        clf = LinearSVC(C=C, class_weight="balanced")
    else:
        raise ValueError(model_name)
    return Pipeline([("tfidf", vec), ("clf", clf)])


def load_dataset(root):
    """Lê o Fake.br Corpus (full_texts/{fake,true} + {fake,true}-meta-information)."""
    rows = []
    for lab in ["fake", "true"]:
        d = os.path.join(root, lab)
        for f in sorted(os.listdir(d), key=lambda x: int(x.split(".")[0])):
            i = int(f.split(".")[0])
            t = open(os.path.join(d, f), encoding="utf-8", errors="replace", newline="").read()
            mp = os.path.join(root, f"{lab}-meta-information", f"{i}-meta.txt")
            m = open(mp, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(mp) else []
            rows.append(dict(id=i, label=lab.upper(), text=t,
                             link=m[1] if len(m) > 1 else None,
                             category=m[2] if len(m) > 2 else None,
                             date=m[3] if len(m) > 3 else None))
    return pd.DataFrame(rows)


def top_terms(pipe, n=20):
    """Termos de maior coeficiente por classe (Regressão Logística / SVM linear)."""
    vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
    names = np.array(vec.get_feature_names_out())
    coef = clf.coef_[0]
    classes = list(clf.classes_)
    order = np.argsort(coef)
    return {classes[0]: [(str(names[i]), float(coef[i])) for i in order[:n]],
            classes[1]: [(str(names[i]), float(coef[i])) for i in order[::-1][:n]]}


def explain(pipe, text, k=8):
    """Contribuição de cada termo (valor TF-IDF x coeficiente) para a decisão da Regressão Logística.

    Contribuição > 0 empurra para classes_[1] (TRUE); < 0 empurra para classes_[0] (FAKE).
    A soma das contribuições + intercepto = função de decisão (log-odds).
    """
    vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
    x = vec.transform([text])
    names = vec.get_feature_names_out()
    idx = x.indices
    contrib = x.data * clf.coef_[0][idx]
    order = np.argsort(contrib)
    classes = list(clf.classes_)
    toward0 = [(str(names[idx[i]]), float(contrib[i])) for i in order[:k] if contrib[i] < 0]
    toward1 = [(str(names[idx[i]]), float(contrib[i])) for i in order[::-1][:k] if contrib[i] > 0]
    return {classes[0]: toward0, classes[1]: toward1,
            "intercept": float(clf.intercept_[0]), "n_features_used": int(len(idx))}


def explain_full(pipe, text, k=8):
    """Explicação completa de uma predição da Regressão Logística (mesma decomposição de `explain`).

    decision (log-odds de TRUE) = intercepto + soma(contribuições positivas) + soma(contribuições negativas)
    P(TRUE) = 1 / (1 + exp(-decision)).  Contribuição = valor TF-IDF (normalizado) x coeficiente.
    """
    vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
    classes = list(clf.classes_)
    x = vec.transform([text])
    names = vec.get_feature_names_out()
    idx = x.indices
    contrib = x.data * clf.coef_[0][idx]
    ev_neg = float(-contrib[contrib < 0].sum())   # evidência a favor de classes_[0] (FAKE)
    ev_pos = float(contrib[contrib > 0].sum())    # evidência a favor de classes_[1] (TRUE)
    total_abs = ev_neg + ev_pos
    intercept = float(clf.intercept_[0])
    order = np.argsort(contrib)

    def item(i):
        term = str(names[idx[i]])
        return {"term": term, "weight": float(contrib[i]), "coef": float(clf.coef_[0][idx[i]]),
                "tfidf": float(x.data[i]), "ngram": len(term.split()),
                "share": float(abs(contrib[i]) / total_abs) if total_abs else 0.0}
    top0 = [item(i) for i in order[:k] if contrib[i] < 0]
    top1 = [item(i) for i in order[::-1][:k] if contrib[i] > 0]
    tokens = [t for t in vec.build_analyzer()(text) if " " not in t]
    vocab = vec.vocabulary_
    coverage = (sum(1 for t in tokens if t in vocab) / len(tokens)) if tokens else 0.0
    return {
        "classes": classes, classes[0]: top0, classes[1]: top1,
        "evidence": {classes[0]: ev_neg, classes[1]: ev_pos},
        "intercept": intercept, "decision": intercept + ev_pos - ev_neg,
        "n_terms": int(len(idx)),
        "n_terms_toward": {classes[0]: int((contrib < 0).sum()), classes[1]: int((contrib > 0).sum())},
        "n_bigrams": int(sum(1 for i in idx if " " in str(names[i]))),
        "vocab_coverage": float(coverage), "tokens_analyzed": len(tokens),
        "top_share": {classes[0]: float(sum(t["share"] for t in top0)), classes[1]: float(sum(t["share"] for t in top1))},
    }

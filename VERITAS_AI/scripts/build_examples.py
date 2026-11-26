"""Gera app/examples/examples.json: seleção controlada de trechos do Fake.br Corpus (somente do conjunto de TESTE).
Uso: python scripts/build_examples.py  (requer data/full_texts). Reprodutível (semente fixa)."""
import json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import numpy as np
from veritas.data import load_clean, random_split

PER_CLASS, MAX_WORDS, MIN_WORDS, SEED = 24, 120, 40, 7
PRETTY = {"g1": "g1", "estadao": "Estadão", "folha": "Folha", "diariodobrasil": "Diário do Brasil", "afolhabrasil": "A Folha Brasil",
          "thejornalbrasil": "The Jornal Brasil", "outros_fake": "outras fontes", "outros_true": "outras fontes"}


def excerpt(text):
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    if len(words) <= MAX_WORDS:
        return " ".join(words), False
    cut = " ".join(words[:MAX_WORDS])
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", cut)]
    ok = [e for e in ends if len(cut[:e].split()) >= MIN_WORDS]
    return (cut[:ok[-1]] if ok else cut.rstrip(",;:") + "…"), True


if __name__ == "__main__":
    df, _ = load_clean(os.path.join(ROOT, "data", "full_texts"))
    _, _, test = random_split(df)
    rng = np.random.default_rng(SEED); items = []
    for lab in ("FAKE", "TRUE"):
        d = test[(test.label == lab) & (test.n_words_raw >= MIN_WORDS)]
        share = (d.category.value_counts(normalize=True) * PER_CLASS).round().clip(lower=1).astype(int)
        for cat, k in share.items():
            sub = d[d.category == cat]
            for _, r in sub.sample(min(k, len(sub)), random_state=int(rng.integers(1e6))).iterrows():
                t, trunc = excerpt(r.text)
                items.append({"id": f"{lab[0]}{int(r.id)}", "label": lab, "category": cat, "source": PRETTY.get(r.source, r.source),
                              "year": int(r.year) if r.year == r.year else None, "n_words": int(r.n_words_raw), "truncated": trunc, "text": t})
    out = {"origin": "Fake.br Corpus (Monteiro et al., 2018) — trechos do conjunto de teste (não usados no treinamento)",
           "license_note": "Confirme a licença do corpus antes de redistribuir estes trechos.", "items": items}
    json.dump(out, open(os.path.join(ROOT, "app", "examples", "examples.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import collections
    print(len(items), collections.Counter((i["label"]) for i in items), collections.Counter(i["category"] for i in items))

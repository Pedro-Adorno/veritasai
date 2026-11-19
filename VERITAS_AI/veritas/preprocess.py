"""Pré-processamento textual do VERITAS AI (usado no treino e na inferência).

Decisões (justificadas no notebook, seções 6 a 8):
- minúsculas, normalização Unicode (NFKC), remoção de BOM/caracteres de controle e URLs;
- aspas/travessões tipográficos -> ASCII: no Fake.br as aspas curvas aparecem em ~58% das
  notícias TRUE e em 0% das FAKE (artefato de coleta, não traço linguístico de veracidade);
- pontuação e negações são PRESERVADAS; stopwords são opcionais (lista própria sem negações);
- truncamento às primeiras `max_words` palavras para reduzir o atalho de tamanho (as notícias
  TRUE têm ~6x mais palavras que as FAKE no corpus).
"""
import re
import unicodedata

MAX_WORDS = 200

_URL = re.compile(r"https?://\S+|www\.\S+")
_SPACES = re.compile(r"\s+")
_TRANSLATE = str.maketrans({
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u00ab": '"', "\u00bb": '"',
    "\u2018": "'", "\u2019": "'", "\u201a": "'",
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2026": "...",
    "\u00a0": " ", "\ufeff": "", "\u200b": "",
})

# Lista própria (não é a do NLTK). NÃO inclui negações: não, nem, nunca, jamais, sem, nenhum.
STOPWORDS_PT = sorted(set("""a o as os um uma uns umas de do da dos das em no na nos nas por para com e ou que se ao aos
à às pelo pela pelos pelas é foi são ser era como mais mas já também ele ela eles elas seu sua seus suas isso este esta
esse essa isto aquele aquela entre até sobre após quando onde há tem têm ter foram será está estão estava lhe me te
muito muitos muita muitas só então porque pois ainda depois antes cada outro outra outros outras""".split()))


def normalize_text(text: str) -> str:
    """Normaliza caracteres e espaços, sem remover pontuação nem negações."""
    if not isinstance(text, str):
        return ""
    t = unicodedata.normalize("NFKC", text).translate(_TRANSLATE)
    t = _URL.sub(" ", t)
    t = "".join(ch if unicodedata.category(ch)[0] != "C" else " " for ch in t)
    return _SPACES.sub(" ", t).strip().lower()


def truncate_words(text: str, max_words=MAX_WORDS) -> str:
    if max_words is None:
        return text
    return " ".join(text.split()[:max_words])


def preprocess_text(text: str, max_words=MAX_WORDS) -> str:
    """Pré-processamento completo: normalização + truncamento."""
    return truncate_words(normalize_text(text), max_words)


class TextPreprocessor:
    """Objeto chamável e serializável (joblib) usado como `preprocessor` do TfidfVectorizer.

    mode='raw'  -> apenas minúsculas (sem normalizar aspas/BOM) [usado só na ablação]
    mode='full' -> normalização + truncamento em `max_words`
    """
    def __init__(self, max_words=MAX_WORDS, mode="full"):
        self.max_words = max_words
        self.mode = mode

    def __call__(self, text):
        if self.mode == "raw":
            return text.lower() if isinstance(text, str) else ""
        return preprocess_text(text, self.max_words)

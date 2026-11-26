"""Pacote compartilhado entre notebook e aplicação web (mesmo pré-processamento e mesmo pipeline)."""
from .preprocess import normalize_text, truncate_words, preprocess_text, TextPreprocessor, STOPWORDS_PT, MAX_WORDS
from .pipeline import build_pipeline, load_dataset, top_terms, explain, explain_full
from .inference import Analyzer

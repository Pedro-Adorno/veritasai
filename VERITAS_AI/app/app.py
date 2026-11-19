"""VERITAS AI — servidor Flask local. Carrega o pipeline exportado (joblib); não treina nada na inicialização."""
import os
import sys

from flask import Flask, jsonify, render_template, request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)  # permite `import veritas` (mesmo pacote usado pelo notebook)
from veritas import Analyzer  # noqa: E402

MODEL_DIR = os.path.join(ROOT, "model")
MAX_CHARS = 20000

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024  # 256 KB por requisição
app.config["JSON_AS_ASCII"] = False

analyzer = Analyzer(MODEL_DIR)  # falha explicitamente se o modelo não existir


def _model_info():
    """Fatos reais do pipeline carregado (usados na página educativa)."""
    vec = analyzer.pipe.named_steps["tfidf"]
    clf = analyzer.pipe.named_steps["clf"]
    return {
        "n_features": int(len(vec.vocabulary_)),
        "ngram_range": list(vec.ngram_range),
        "min_df": vec.min_df, "max_df": vec.max_df, "sublinear_tf": bool(vec.sublinear_tf),
        "C": float(clf.C), "class_weight": clf.class_weight, "classes": [str(c) for c in clf.classes_],
        "n_nonzero_coefs": int((clf.coef_[0] != 0).sum()),
    }


MODEL_INFO = _model_info()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", model=analyzer.metadata["model_name"], version=analyzer.metadata["version"])


@app.get("/api/metrics")
def metrics():
    return jsonify(metrics=analyzer.metrics, metadata=analyzer.metadata, model_info=MODEL_INFO)


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Requisição inválida: envie JSON com os campos 'text' e (opcional) 'title'."), 400
    text, title = data.get("text", ""), data.get("title", "")
    if not isinstance(text, str) or not isinstance(title, str):
        return jsonify(error="Os campos 'text' e 'title' devem ser texto."), 400
    if not text.strip():
        return jsonify(error="Cole o conteúdo da notícia para analisar."), 400
    if len(text) + len(title) > MAX_CHARS:
        return jsonify(error=f"Texto muito longo (máximo de {MAX_CHARS:,} caracteres).".replace(",", ".")), 413
    try:
        return jsonify(analyzer.analyze(text, title))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:  # não expõe detalhes internos ao cliente
        app.logger.exception("Falha na inferência")
        return jsonify(error="Falha interna ao processar o texto."), 500


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Conteúdo grande demais para ser enviado."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)

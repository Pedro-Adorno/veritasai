"""Testes reais do modelo exportado e da API Flask. Execute: python tests/test_veritas.py"""
import json, os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "app"))
from veritas import Analyzer, normalize_text  # noqa: E402
import app as appmod  # noqa: E402

FACTUAL = "O Ministério da Fazenda informou nesta quarta-feira que a arrecadação federal cresceu no trimestre, segundo dados divulgados pela Receita. De acordo com o órgão, o resultado foi puxado pela retomada da atividade econômica, mas a pasta não detalhou projeções para os próximos meses."
SENSA = "URGENTE!!! Compartilhe antes que apaguem! Políticos tentam esconder a verdade e a mídia não quer que você saiba o que aconteceu hoje. Divulgue para todos os seus contatos, o Brasil precisa acordar!"


class TestModelo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.an = Analyzer(os.path.join(ROOT, "model"))

    def test_carrega_e_classes(self):
        self.assertEqual(sorted(self.an.classes), ["FAKE", "TRUE"])
        self.assertIn("modelo_veritas.joblib", os.listdir(os.path.join(ROOT, "model")))

    def test_probabilidades_somam_um(self):
        r = self.an.analyze(FACTUAL)
        self.assertAlmostEqual(sum(r["probabilities"].values()), 1.0, places=6)
        self.assertIn(r["label"], ("FAKE", "TRUE", "INCONCLUSIVE"))

    def test_estilos_distintos_dao_resultados_diferentes(self):
        self.assertNotEqual(self.an.analyze(FACTUAL)["probabilities"], self.an.analyze(SENSA)["probabilities"])

    def test_vazio_levanta_erro(self):
        for t in ["", "   ", "\n\t"]:
            with self.assertRaises(ValueError):
                self.an.analyze(t)

    def test_texto_curto_gera_aviso(self):
        self.assertTrue(any("curto" in w for w in self.an.analyze("oi")["warnings"]))

    def test_caracteres_especiais_e_emojis(self):
        r = self.an.analyze("🔥🔥 ### @@@ !!! ??? “aspas” — travessão <script>alert(1)</script>")
        self.assertIn(r["label"], ("FAKE", "TRUE", "INCONCLUSIVE"))

    def test_texto_longo_truncado(self):
        r = self.an.analyze("o governo anunciou medidas " * 400)
        self.assertTrue(r["indicators"]["texto_truncado"])

    def test_aspas_curvas_nao_alteram_resultado(self):
        a = self.an.analyze('Ele disse: "isso é verdade" ' + FACTUAL)["probabilities"]["FAKE"]
        b = self.an.analyze('Ele disse: \u201cisso é verdade\u201d ' + FACTUAL)["probabilities"]["FAKE"]
        self.assertAlmostEqual(a, b, places=9)

    def test_contribuicoes_somam_decisao(self):
        from veritas import explain
        p = self.an.pipe; e = explain(p, FACTUAL, k=10**6)
        tot = sum(w for c in ("FAKE", "TRUE") for _, w in e[c]) + e["intercept"]
        self.assertAlmostEqual(tot, float(p.decision_function([FACTUAL])[0]), places=6)

    def test_metricas_coerentes(self):
        m = self.an.metrics["test"]; cm = m["confusion_matrix"]
        self.assertEqual(sum(map(sum, cm)), m["n"])
        self.assertAlmostEqual(m["accuracy"], (cm[0][0] + cm[1][1]) / m["n"], places=9)


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = appmod.app.test_client()

    def test_index_e_estaticos(self):
        r = self.c.get("/"); self.assertEqual(r.status_code, 200); self.assertIn("VERITAS", r.get_data(as_text=True))
        for p in ("/static/css/style.css", "/static/js/app.js", "/static/assets/logo.svg"):
            self.assertEqual(self.c.get(p).status_code, 200, p)

    def test_health_e_metrics(self):
        self.assertEqual(self.c.get("/api/health").get_json()["status"], "ok")
        j = self.c.get("/api/metrics").get_json()
        self.assertIn("test", j["metrics"]); self.assertIn("version", j["metadata"])

    def test_analyze_ok(self):
        r = self.c.post("/api/analyze", json={"title": "Teste", "text": FACTUAL}); j = r.get_json()
        self.assertEqual(r.status_code, 200); self.assertIn("probabilities", j); self.assertIn("terms", j)

    def test_analyze_erros(self):
        self.assertEqual(self.c.post("/api/analyze", json={"text": "   "}).status_code, 400)
        self.assertEqual(self.c.post("/api/analyze", data="não é json", content_type="text/plain").status_code, 400)
        self.assertEqual(self.c.post("/api/analyze", json={"text": 123}).status_code, 400)
        self.assertEqual(self.c.post("/api/analyze", json={"text": "a" * 30000}).status_code, 413)
        self.assertEqual(self.c.post("/api/analyze", json={"text": "a" * 300000}).status_code, 413)
        self.assertEqual(self.c.get("/api/analyze").status_code, 405)


if __name__ == "__main__":
    unittest.main(verbosity=2)

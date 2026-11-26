"""Testes da explicabilidade: a explicação deve vir do modelo real (não de texto fixo). Execute: python tests/test_explicabilidade.py"""
import math, os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "app"))
import app as appmod  # noqa: E402
from veritas import explain_full  # noqa: E402

FACTUAL = "O Ministério da Fazenda informou nesta quarta-feira que a arrecadação federal cresceu no trimestre, segundo dados divulgados pela Receita. De acordo com o órgão, o resultado foi puxado pela retomada da atividade econômica, mas a pasta não detalhou projeções."
SENSA = "URGENTE!!! Compartilhe antes que apaguem! Políticos tentam esconder a verdade e a mídia não quer que você saiba o que aconteceu hoje. Divulgue para todos os seus contatos!"


class TestExplicabilidade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.an = appmod.analyzer; cls.c = appmod.app.test_client()

    def test_logit_reproduz_probabilidade_do_modelo(self):
        for t in (FACTUAL, SENSA):
            r = self.an.analyze(t); e = r["explanation"]
            self.assertAlmostEqual(1 / (1 + math.exp(-e["decision"])), r["probabilities"]["TRUE"], places=9)
            self.assertAlmostEqual(e["intercept"] + e["evidence"]["TRUE"] - e["evidence"]["FAKE"], e["decision"], places=9)

    def test_direcao_dos_termos(self):
        e = self.an.analyze(SENSA)["explanation"]
        self.assertTrue(all(x["weight"] < 0 for x in e["FAKE"]) and all(x["weight"] > 0 for x in e["TRUE"]))
        for x in e["FAKE"] + e["TRUE"]:
            self.assertAlmostEqual(x["tfidf"] * x["coef"], x["weight"], places=9)

    def test_termos_pertencem_ao_vocabulario_do_modelo(self):
        vocab = self.an.pipe.named_steps["tfidf"].vocabulary_
        e = self.an.analyze(FACTUAL)["explanation"]
        self.assertTrue(all(x["term"] in vocab for x in e["FAKE"] + e["TRUE"]))

    def test_explicacao_muda_com_o_texto(self):
        a = self.an.analyze(FACTUAL)["explanation"]; b = self.an.analyze(SENSA)["explanation"]
        self.assertNotEqual([x["term"] for x in a["TRUE"]], [x["term"] for x in b["TRUE"]])

    def test_campos_anteriores_preservados(self):
        r = self.an.analyze(FACTUAL)
        for k in ("label", "probabilities", "margin", "terms", "indicators", "warnings", "model"):
            self.assertIn(k, r)

    def test_api_expoe_explicacao_e_info_do_modelo(self):
        j = self.c.post("/api/analyze", json={"text": FACTUAL}).get_json()
        self.assertIn("evidence", j["explanation"])
        mi = self.c.get("/api/metrics").get_json()["model_info"]
        self.assertEqual(mi["n_features"], len(self.an.pipe.named_steps["tfidf"].vocabulary_))

    def test_texto_sem_termos_conhecidos_nao_quebra(self):
        e = self.an.analyze("zzzz qqqq xxxx")["explanation"]
        self.assertGreaterEqual(e["n_terms"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

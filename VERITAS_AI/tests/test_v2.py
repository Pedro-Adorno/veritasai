"""Testes da evolução 2.0: exemplos dinâmicos, calibração/abstenção, avisos de cobertura. Execute: python tests/test_v2.py"""
import os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "app"))
import app as appmod  # noqa: E402

EN = "The president said on Tuesday that the new policy will be announced soon and the government agreed to the plan."


class TestV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.an = appmod.analyzer; cls.c = appmod.app.test_client()

    def test_exemplos_alternam_e_nao_repetem(self):
        last, labels = "", []
        for _ in range(8):
            j = self.c.get(f"/api/example?label=ANY&exclude={last}").get_json()
            self.assertNotEqual(j["id"], last); labels.append(j["label"]); last = j["id"]
        self.assertTrue(all(a != b for a, b in zip(labels, labels[1:])))

    def test_exemplos_por_classe_e_campos(self):
        for lab in ("FAKE", "TRUE"):
            j = self.c.get(f"/api/example?label={lab}").get_json()
            self.assertEqual(j["label"], lab)
            for k in ("id", "category", "source", "text", "origin"): self.assertIn(k, j)
            self.assertNotIn("link", j); self.assertLessEqual(len(j["text"].split()), 125)

    def test_exemplos_ausentes_retornam_fallback(self):
        old = appmod.EXAMPLES; appmod.EXAMPLES = None
        try:
            r = self.c.get("/api/example"); self.assertEqual(r.status_code, 404); self.assertTrue(r.get_json()["fallback"])
        finally: appmod.EXAMPLES = old

    def test_resultado_tem_campos_de_calibracao(self):
        r = self.an.analyze(EN + " " + EN)
        self.assertIn(r["label"], ("FAKE", "TRUE", "INCONCLUSIVE"))
        self.assertAlmostEqual(sum(r["calibrated"].values()), 1.0, places=9)
        self.assertEqual(r["abstained"], r["label"] == "INCONCLUSIVE")

    def test_regra_de_abstencao_usa_os_limiares_do_metadata(self):
        lo, hi = self.an.abst["lo"], self.an.abst["hi"]
        mid = (lo + hi) / 2; cal = self.an.cal
        import math
        p = 1 / (1 + math.exp(-((math.log(mid / (1 - mid)) - cal["b"]) / cal["a"])))  # P(FAKE) bruta que gera q = mid
        self.assertAlmostEqual(self.an._calibrated_fake(p), mid, places=6)

    def test_inconclusivo_quando_probabilidade_na_banda(self):
        orig = self.an._calibrated_fake; lo, hi = self.an.abst["lo"], self.an.abst["hi"]
        try:
            self.an._calibrated_fake = lambda p: (lo + hi) / 2
            r = self.an.analyze("O governo anunciou nesta quarta-feira novas medidas para a economia do país.")
            self.assertEqual(r["label"], "INCONCLUSIVE"); self.assertTrue(r["abstained"])
            self.assertTrue(any("Inconclusivo não significa" in w for w in r["warnings"]))
            self.assertIn("explanation", r)
        finally: self.an._calibrated_fake = orig

    def test_forca_fake_e_true_fora_da_banda(self):
        orig = self.an._calibrated_fake
        try:
            t = ("O governo federal anunciou nesta semana um conjunto de medidas para a área da saúde, que prevê a ampliação de unidades de atendimento em várias cidades do país, "
                 "segundo informou o ministério em nota, e a contratação de profissionais para reforçar as equipes que atuam nas regiões mais afastadas dos grandes centros urbanos.")
            self.an._calibrated_fake = lambda p: 0.99; self.assertEqual(self.an.analyze(t)["label"], "FAKE")
            self.an._calibrated_fake = lambda p: 0.01; self.assertEqual(self.an.analyze(t)["label"], "TRUE")
        finally: self.an._calibrated_fake = orig

    def test_baixa_cobertura_gera_aviso(self):
        r = self.an.analyze(EN)
        self.assertLess(r["vocab_coverage"], self.an.warn_thr["vocab_coverage_p5"])
        self.assertTrue(any("cobertura do vocabulário" in w for w in r["warnings"]))

    def test_portugues_normal_nao_gera_aviso_de_cobertura(self):
        t = ("O Ministério da Fazenda informou nesta quarta-feira que a arrecadação federal cresceu no trimestre, segundo dados divulgados pela Receita. "
             "De acordo com o órgão, o resultado foi puxado pela retomada da atividade econômica, mas a pasta não detalhou projeções para os próximos meses.")
        self.assertFalse(any("cobertura do vocabulário" in w for w in self.an.analyze(t)["warnings"]))

    def test_acentos_maiusculas_e_longo(self):
        for t in ("ÇÃO ÃÕ ÉÊ áéíóú ç ñ ü " * 20, "Notícia número 1.234, R$ 5,6 mil — “aspas”. " * 300):
            self.assertIn(self.an.analyze(t)["label"], ("FAKE", "TRUE", "INCONCLUSIVE"))

    def test_metricas_v2_presentes(self):
        m = self.an.metrics
        for k in ("generalization", "abstention", "calibration", "timing"): self.assertIn(k, m)
        g = m["generalization"]; self.assertIn(g["chosen"], g["configs"]); self.assertIn("length_matched", g["configs"][g["chosen"]])

    def test_api_expoe_novos_campos(self):
        j = self.c.post("/api/analyze", json={"text": "O governo anunciou medidas para a economia, segundo o ministério, nesta semana."}).get_json()
        for k in ("calibrated", "abstained", "abstention", "vocab_coverage", "raw_label"): self.assertIn(k, j)


if __name__ == "__main__":
    unittest.main(verbosity=2)

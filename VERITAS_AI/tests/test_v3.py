"""Testes da v3: resultado único em linguagem simples, nomes próprios, inconclusivo, pontos de verificação. Execute: python tests/test_v3.py"""
import os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "app"))
import app as appmod  # noqa: E402
from veritas.claims import extract_checkpoints  # noqa: E402

LONG = ("O governo federal anunciou nesta semana um conjunto de medidas para a área da saúde, que prevê a ampliação de unidades de atendimento em várias cidades do país, "
        "segundo informou o ministério em nota, e a contratação de profissionais para reforçar as equipes que atuam nas regiões mais afastadas dos grandes centros urbanos.")
SENSA = ("URGENTE!!! Compartilhe antes que apaguem! Lula e Dilma tentam esconder a verdade e a mídia não quer que você saiba o que aconteceu hoje. "
         "Divulgue para todos os seus contatos agora mesmo, o Brasil precisa acordar! Isso é um absurdo e ninguém fala nada sobre o assunto.")
HEADS = ("POSSIVELMENTE FALSA", "POSSIVELMENTE VERDADEIRA", "RESULTADO INCONCLUSIVO")


class TestV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.an = appmod.analyzer; cls.c = appmod.app.test_client()

    def test_um_unico_veredito_coerente_com_o_rotulo(self):
        for t in (LONG, SENSA, "oi"):
            r = self.an.analyze(t); P = r["plain"]
            self.assertIn(P["headline"], HEADS)
            self.assertEqual(P["headline"], {"FAKE": HEADS[0], "TRUE": HEADS[1], "INCONCLUSIVE": HEADS[2]}[r["label"]])
            self.assertEqual(P["tone"], {"FAKE": "fake", "TRUE": "true", "INCONCLUSIVE": "inc"}[r["label"]])

    def test_texto_curto_e_inconclusivo_com_motivo(self):
        r = self.an.analyze("O governo anunciou medidas."); self.assertEqual(r["label"], "INCONCLUSIVE"); self.assertIn("curto", r["reasons"])
        self.assertIn("não significa que a notícia seja verdadeira nem falsa", r["plain"]["explanation"])
        self.assertEqual(r["plain"]["confidence"]["level"], "insuficiente")

    def test_texto_fora_do_dominio_e_inconclusivo(self):
        en = "The president said on Tuesday that the new policy will be announced soon and the government agreed to the plan after a long meeting with the ministers. " * 3
        r = self.an.analyze(en); self.assertEqual(r["label"], "INCONCLUSIVE"); self.assertIn("fora_dominio", r["reasons"])

    def test_nomes_proprios_nunca_aparecem_como_evidencia(self):
        P = self.an.analyze(SENSA)["plain"]; ev = " ".join(i["text"] for i in P["highlights"]["falsa"] + P["highlights"]["verdadeira"]).lower()
        for nome in ("lula", "dilma"): self.assertNotIn(nome, ev)
        for n in P["highlights"]["notas"]:
            if n["kind"] == "nomes": self.assertIn("NÃO indica", n["text"])

    def test_destaques_vem_de_frequencias_reais_do_treino(self):
        P = self.an.analyze(SENSA)["plain"]; ts = self.an.term_stats["terms"]
        for i in P["highlights"]["falsa"] + P["highlights"]["verdadeira"]:
            dfF, dfT = ts[i["term"]][:2]
            self.assertIn(f"{round(dfF / self.an.term_stats['n_fake'] * 100)}%", i["text"]) if dfF / self.an.term_stats["n_fake"] >= 0.01 else None

    def test_termos_destacados_pertencem_a_explicacao_real(self):
        r = self.an.analyze(SENSA); real = {t["term"] for t in r["explanation"]["FAKE"] + r["explanation"]["TRUE"]}
        for i in r["plain"]["highlights"]["falsa"] + r["plain"]["highlights"]["verdadeira"]: self.assertIn(i["term"], real)

    def test_pontos_de_verificacao_so_com_o_que_existe_no_texto(self):
        c = extract_checkpoints("Segundo o deputado João Silva, 35% dos casos subiram em 12 de março de 2018.")
        self.assertEqual(c["numeros"], ["35%"]); self.assertIn("João Silva", c["atribuicoes"]); self.assertTrue(c["datas"])
        vazio = extract_checkpoints("O céu está azul hoje e as pessoas passeiam pela cidade.")
        self.assertEqual((vazio["numeros"], vazio["datas"], vazio["citacoes"], vazio["atribuicoes"]), ([], [], [], []))

    def test_verificacao_externa_declarada_como_nao_realizada(self):
        e = self.an.analyze(LONG)["plain"]["external"]; self.assertFalse(e["performed"]); self.assertIn("não foi realizada", e["message"])

    def test_confianca_usa_acuracia_real_da_validacao(self):
        r = self.an.analyze(SENSA)["plain"]["confidence"]
        if r["empirical"] is not None: self.assertIn(r["level"], ("baixa", "moderada", "alta")); self.assertIn("nunca viu", r["text"])

    def test_assuntos_diferentes_sao_analisados(self):
        ts = ["O time venceu a partida por dois a zero e garantiu a classificação para a fase final do campeonato, segundo a federação, diante de um estádio lotado e de uma torcida que apoiou a equipe durante todo o jogo. " * 2,
              "A economia brasileira cresceu no trimestre, segundo dados divulgados pelo instituto, impulsionada pelo consumo das famílias e pela retomada dos investimentos em infraestrutura em diversas regiões do país. " * 2,
              "Cientistas publicaram um estudo sobre o comportamento de aves migratórias e afirmam que as rotas mudaram nas últimas décadas por causa de alterações no clima e na disponibilidade de alimentos. " * 2]
        for t in ts: self.assertIn(self.an.analyze(t)["label"], ("FAKE", "TRUE", "INCONCLUSIVE"))

    def test_api_retorna_plain(self):
        j = self.c.post("/api/analyze", json={"text": LONG}).get_json(); self.assertIn("plain", j); self.assertIn("checkpoints", j["plain"])

    def test_mascara_de_nomes_proprios_no_preprocessamento(self):
        from veritas.preprocess import strip_proper_names as f
        self.assertNotIn("Lula", f("O presidente Lula falou ao STF.")); self.assertIn("presidente", f("O presidente Lula falou."))


if __name__ == "__main__":
    unittest.main(verbosity=2)

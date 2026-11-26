"""Explicação em linguagem simples, construída SOMENTE a partir de dados reais da análise e do corpus de treino.

Regras de honestidade:
- nomes próprios/siglas nunca são apresentados como evidência (só como "aparecem no texto");
- para palavras comuns, a única justificativa usada é a frequência REAL delas nas notícias FAKE e TRUE do treino;
- termos raros ou concentrados em um veículo são declarados como tal; sem interpretação confiável, dizemos isso.
"""
import re
from .claims import extract_checkpoints, checkpoints_messages

HEAD = {"FAKE": "POSSIVELMENTE FALSA", "TRUE": "POSSIVELMENTE VERDADEIRA", "INCONCLUSIVE": "RESULTADO INCONCLUSIVO"}
SENT = {
    "FAKE": "O sistema identificou características semelhantes às encontradas em notícias classificadas como falsas durante seu treinamento.",
    "TRUE": "O sistema identificou características semelhantes às encontradas em notícias classificadas como verdadeiras durante seu treinamento.",
    "INCONCLUSIVE": "Não foi possível chegar a uma conclusão confiável com o conteúdo enviado.",
}
REASONS = {
    "ambiguo": "As características do texto apontam em direções opostas ou são pouco marcantes.",
    "curto": "O texto é curto demais para uma análise confiável.",
    "fora_dominio": "Poucas palavras do texto são conhecidas pelo sistema; ele pode estar fora do tipo de conteúdo usado no treinamento.",
    "poucos_termos": "O texto tem poucas características que o sistema consegue analisar.",
}
LIMITS = ("Esta análise reconhece padrões de linguagem aprendidos em notícias rotuladas de 2015 a 2018. Ela não verifica fatos, não consulta fontes "
          "e pode errar com notícias de outras fontes, épocas ou assuntos. Use como apoio à leitura crítica, nunca como veredito.")
EXTERNAL = ("A verificação em fontes externas não foi realizada: esta versão não está conectada a nenhuma base de checagem. "
            "Para confirmar os fatos, consulte as fontes originais e agências de checagem.")


def pct(x):
    p = x * 100
    return "menos de 1%" if 0 < p < 1 else f"{p:.0f}%".replace(".", ",")


def _is_style(term):
    return bool(re.fullmatch(r"[!?](?:\s[!?])*", term.strip()))


def _label_term(term):
    return "o sinal de exclamação (!)" if "!" in term else ("o ponto de interrogação (?)" if "?" in term else f"“{term}”")


def confidence(label, q_fake, levels, shift_acc=None):
    """Nível de confiança com a acurácia OBSERVADA na validação para aquele nível (quando disponível)."""
    if label == "INCONCLUSIVE" or q_fake is None:
        return {"level": "insuficiente", "text": "A confiança foi insuficiente para uma classificação.", "empirical": None}
    c = q_fake if label == "FAKE" else 1 - q_fake
    if not levels:
        return {"level": "não avaliada", "text": "", "empirical": None}
    e1, e2 = levels["edges"]; k = 0 if c < e1 else (1 if c < e2 else 2); lv = levels["levels"][k]
    acc = lv.get("val_accuracy")
    txt = ""
    if acc is not None:
        acc_txt = "mais de 99%" if acc >= 0.995 else f"cerca de {acc * 100:.0f}%"
        txt = f"Em testes com notícias parecidas com as do treinamento, análises com esse nível de confiança acertaram {acc_txt} das vezes. "
        txt += (f"Com notícias de fontes que o sistema nunca viu, o acerto médio foi de apenas cerca de {shift_acc * 100:.0f}%."
                if shift_acc is not None else "Em notícias de outras fontes ou assuntos, o acerto pode ser menor.")
    return {"level": lv["name"], "text": txt, "empirical": acc}


def _orig(term, text):
    m = re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text or "", flags=re.I)
    return m.group(0) if m else term


def highlights(exp, stats, text=""):
    """Agrupa os termos que mais influenciaram em: palavras/estilo (com frequências reais), nomes, termos de veículo e termos raros."""
    T = stats["terms"] if stats else {}; nF, nT = (stats["n_fake"], stats["n_true"]) if stats else (1, 1)
    items = {"falsa": [], "verdadeira": []}; names, fonte, raros = [], [], []
    for side, direction in (("FAKE", "falsa"), ("TRUE", "verdadeira")):
        for t in exp.get(side, []):
            term, st = t["term"], T.get(t["term"])
            if st is None:
                raros.append(term); continue
            dfF, dfT, conc, top, proper = st
            if proper:
                names.append(_orig(term, text)); continue
            if dfF + dfT < 8:
                raros.append(term); continue
            if conc >= 0.9 and dfF + dfT >= 8 and not _is_style(term):
                fonte.append((term, top)); continue
            rF, rT = dfF / nF, dfT / nT
            consistent = (rF > rT) if direction == "falsa" else (rT > rF)
            txt = f"{_label_term(term).capitalize() if term[0] in '!?' else _label_term(term)} aparece em {pct(rF)} das notícias falsas e em {pct(rT)} das verdadeiras do treinamento."
            if not consistent:
                txt += " Neste texto, o efeito vem da combinação com outras características."
            items[direction].append({"kind": "estilo" if _is_style(term) else "palavra", "term": term, "text": txt})
    for d in items: items[d] = items[d][:3]
    notes = []
    if names:
        ex = ", ".join(dict.fromkeys(names[:4]))
        notes.append({"kind": "nomes", "text": f"Nomes e siglas como {ex} aparecem no texto e influenciaram o cálculo, mas isso NÃO indica que a notícia seja falsa ou verdadeira: eles apenas refletem os assuntos mais frequentes em cada grupo de notícias do treinamento."})
    if fonte:
        ex = ", ".join(f"“{t}”" for t, _ in fonte[:3])
        notes.append({"kind": "veiculo", "text": f"Expressões como {ex} aparecem quase só em notícias de um mesmo veículo no treinamento. Podem refletir o estilo desse veículo, não a veracidade."})
    if raros:
        ex = ", ".join(f"“{t}”" for t in dict.fromkeys(raros[:3]))
        notes.append({"kind": "raro", "text": f"Algumas expressões ({ex}) influenciaram matematicamente o resultado, mas aparecem em poucos textos do treinamento. Não há interpretação confiável para elas e não representam evidência de falsidade ou veracidade."})
    return items, notes


def build_plain(label, q_fake, reasons, exp, text, stats, levels, n_words, shift_acc=None):
    items, notes = highlights(exp, stats, text)
    pro = items["falsa"] if label == "FAKE" else items["verdadeira"]
    ex = ", ".join(f"{_label_term(i['term'])}" for i in pro[:3])
    if label == "INCONCLUSIVE":
        body = " ".join(REASONS[r] for r in reasons if r in REASONS) or REASONS["ambiguo"]
        body += " Isso não significa que a notícia seja verdadeira nem falsa: o sistema apenas não encontrou sinais suficientes."
    else:
        lado = "falsas" if label == "FAKE" else "verdadeiras"
        body = f"O texto reúne características que, no treinamento, apareceram com mais frequência em notícias classificadas como {lado}"
        body += f" (por exemplo: {ex})." if ex else "."
        body += f" Isso não confirma que as informações sejam {'falsas' if label == 'FAKE' else 'verdadeiras'}: é necessário verificar as fontes e os fatos apresentados."
    cps = checkpoints_messages(extract_checkpoints(text), n_words)
    ents = extract_checkpoints(text)["entidades"]
    return {"headline": HEAD[label], "tone": {"FAKE": "fake", "TRUE": "true", "INCONCLUSIVE": "inc"}[label], "sentence": SENT[label],
            "confidence": confidence(label, q_fake, levels, shift_acc), "explanation": body,
            "highlights": {"falsa": items["falsa"], "verdadeira": items["verdadeira"], "notas": notes},
            "checkpoints": cps, "entities": ents,
            "external": {"performed": False, "message": EXTERNAL}, "limits": LIMITS}

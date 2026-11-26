"""Pontos que merecem verificação: extração por regras (sem IA externa, sem inventar nada) de elementos presentes no texto.
Nada aqui verifica fatos; apenas aponta o que o leitor pode conferir."""
import re

_MESES = "janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro"
_DATA = re.compile(rf"\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b|\b\d{{1,2}}\s+de\s+(?:{_MESES})(?:\s+de\s+\d{{4}})?|\b(?:{_MESES})\s+de\s+\d{{4}}|\b(?:19|20)\d{{2}}\b", re.I)
_NUM = re.compile(r"R\$\s?\d[\d.,]*(?:\s(?:milhões|milhão|bilhões|bilhão|mil))?|\b\d+(?:[.,]\d+)?\s?%|\b\d[\d.,]*\s(?:milhões|milhão|bilhões|bilhão|mil|pessoas|mortos|votos|casos)\b", re.I)
_ASPAS = re.compile(r"[“\"]([^”\"]{20,220})[”\"]")
_ATRIB = re.compile(r"\b(?i:segundo|de acordo com|conforme)\s+(?:o\s+|a\s+|os\s+|as\s+)?(?:(?:deputad[oa]|senador[a]?|ministr[oa]|presidente|governador[a]?|prefeit[oa]|ju[ií]z[a]?|delegad[oa]|promotor[a]?|professor[a]?|doutor[a]?|especialista|pesquisador[a]?)\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^,.;:\n]{2,60})", re.U)
_VERBO = re.compile(r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+){0,3})\s+(?:afirmou|afirmam|disse|declarou|informou|anunciou|revelou|garantiu|admitiu)\b", re.U)
_FONTE = re.compile(r"\b(?:segundo|de acordo com|conforme|fonte:|em nota|em entrevista|divulgado[s]? (?:por|pelo|pela)|informou)\b", re.I)
_NOME = re.compile(r"(?<![.!?:]\s)(?<!^)\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+){0,3})\b", re.U)
_IGNORAR = {"O", "A", "Os", "As", "Um", "Uma", "Em", "No", "Na", "Para", "Por", "Com", "Mas", "Se", "Ele", "Ela", "Isso", "Este", "Esta", "Segundo"}


def _uniq(items, k):
    seen, out = set(), []
    for x in items:
        x = re.sub(r"\s+", " ", x).strip(" ,.;:")
        if x and x.lower() not in seen:
            seen.add(x.lower()); out.append(x)
        if len(out) >= k:
            break
    return out


def extract_checkpoints(text, k=4):
    """Retorna dict com listas (datas, numeros, citacoes, atribuicoes, entidades) e flags objetivas do texto."""
    t = text or ""
    ents = [e for e in (m.group(1) for m in _NOME.finditer(t)) if e not in _IGNORAR and len(e) > 2]
    return {
        "datas": _uniq((m.group(0) for m in _DATA.finditer(t)), k),
        "numeros": _uniq((m.group(0) for m in _NUM.finditer(t)), k),
        "citacoes": _uniq(_ASPAS.findall(t), 3),
        "atribuicoes": _uniq([m.group(1) for m in _ATRIB.finditer(t)] + [m.group(1) for m in _VERBO.finditer(t)], k),
        "entidades": _uniq(ents, 6),
        "cita_fonte": bool(_FONTE.search(t)),
        "exclamacoes": t.count("!"),
        "palavras_em_caixa_alta": len([w for w in re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{4,}\b", t)]),
    }


def checkpoints_messages(c, n_words):
    """Mensagens em linguagem simples; cada uma só aparece se o elemento realmente existe (ou falta) no texto."""
    out = []
    if c["numeros"] or c["datas"]:
        itens = c["numeros"][:3] + c["datas"][:2]
        out.append({"id": "numeros", "title": "Números e datas citados", "items": itens, "text": "Confirme esses valores e datas em fontes oficiais ou em veículos de referência."})
    if c["citacoes"] or c["atribuicoes"]:
        out.append({"id": "declaracoes", "title": "Declarações atribuídas a pessoas ou instituições", "items": (c["atribuicoes"] + c["citacoes"])[:4],
                    "text": "Veja se a declaração foi realmente feita, por quem e em que contexto, procurando a fonte original."})
    if n_words >= 40 and not c["cita_fonte"]:
        out.append({"id": "sem_fonte", "title": "O texto não indica de onde vêm as informações", "items": [], "text": "Não encontramos expressões como “segundo” ou “de acordo com”. Procure a fonte original da informação."})
    if c["exclamacoes"] >= 3 or c["palavras_em_caixa_alta"] >= 3:
        out.append({"id": "enfase", "title": "Linguagem enfática", "items": [], "text": f"O texto usa {c['exclamacoes']} exclamação(ões) e {c['palavras_em_caixa_alta']} palavra(s) em caixa alta. Isso é um traço de estilo, não prova de falsidade, mas vale ler com atenção."})
    return out

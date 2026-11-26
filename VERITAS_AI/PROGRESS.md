# PROGRESS — VERITAS AI (branch `evolucao-v3`)
_Leia este arquivo primeiro ao retomar._

## Etapas do pedido v3 — status
1. Auditoria: feita (`scripts/audit_v3.py`, `model/audit_v3.json`, `RELATORIO_V3.md` §2–3). Site Vercel/GitHub inacessíveis nesta sessão (sem rede).
2. Resultado único (sem respostas concorrentes): feito e testado (navegador 40/40).
3. Explicações em linguagem simples (`veritas/plain.py`, `veritas/claims.py`, `model/term_stats.json`): feito.
4. Auditoria/evolução do modelo: feita (15 configurações; remoção de nomes próprios adotada; ganho pequeno).
5. Inconclusivo/confiabilidade: política por precisão na validação + regras de domínio: feita.
6. Verificação factual externa: **NÃO implementada** (sem integração). Gancho `veritas/evidence.py` + `docs/FACTCHECK_FUTURO.md`.
7. Testes: Python 14+7+12+12 e navegador 40/40 aprovados. **Deploy no Vercel não testado.**

## Pendências
Mais fontes (FAKE e TRUE) com licença verificada; integração de verificação factual; testar deploy Vercel; atualizar artigo/pitch/planilha (descrevem a v1); poucos exemplos de ciência/tecnologia, economia e religião.

## Arquivos-chave
`RELATORIO_V3.md`, `TECHNICAL_NOTES.md`, `veritas/{plain,claims,inference,data,preprocess}.py`, `scripts/{experiments_v2,analyze_v2,train_v2,build_term_stats,audit_v3}.py`, `app/static/js/app.js` (renderResult).

## Mensagem de continuidade
"Leia PROGRESS.md e RELATORIO_V3.md. Próximo passo: (a) incorporar novas fontes com licença e reexecutar os scripts na ordem do relatório §7, ou (b) integrar um EvidenceProvider real em veritas/evidence.py e exibi-lo em 'Verificação em fontes externas'."

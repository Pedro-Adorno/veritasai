# PROGRESS — VERITAS AI 2.0
_Leia este arquivo primeiro ao retomar._

## Estado: escopo da 2.0 CONCLUÍDO (branch `evolucao-v2`)
Fases 1–6 feitas: auditoria; exemplos dinâmicos; experimentos LOSO + controle de comprimento; calibração + abstenção; UX (inconclusivo, avisos, dashboard v2, página Tecnologia); testes e documentação. Resultado completo e honesto em `RELATORIO_V2.md`.

## Testes (todos executados e aprovados)
`tests/test_veritas.py` 14 · `tests/test_explicabilidade.py` 7 · `tests/test_v2.py` 12 · navegador desktop+celular: 36/36, 28/28, 20/20.

## Pendências / próximos passos
1. **Mais fontes de FAKE** (maior limitador de generalização) — exige base com licença verificável; sem internet nesta sessão.
2. Revisar a banda de abstenção e a calibração quando houver mais fontes (hoje a banda é estreita; meta de 80% de acurácia seletiva entre fontes NÃO atingida).
3. Confirmar licença do Fake.br antes de publicar `app/examples/examples.json`.
4. Artigo (DOCX/PDF), planilha de IA, roteiro e pitch ainda descrevem a **v1** (95,05%, 14 testes, "2016–2018"): atualizar se forem entregues com a 2.0.
5. Notebook v1 não foi reescrito; a v2 roda por `scripts/`.

## Arquivos para continuar
`RELATORIO_V2.md`, `TECHNICAL_NOTES.md`, `scripts/`, `veritas/{data,inference,preprocess}.py`, `model/experiments_v2.json`.

## Mensagem de continuidade
"Leia PROGRESS.md e TECHNICAL_NOTES.md. A 2.0 está concluída; a próxima tarefa é (1) incorporar novas fontes FAKE com licença verificada e reexecutar scripts/experiments_v2.py → analyze_v2.py → train_v2.py, ou (4) atualizar artigo/pitch para a v2."

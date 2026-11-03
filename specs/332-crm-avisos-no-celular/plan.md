<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 332 — Avisos das Conversas no celular

**Branch**: `332-crm-avisos-no-celular` (sobre a `330-crm-instagram-direct`) | **Data**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

## Resumo

A Plataforma vira um app instalável, com manifesto e service worker, que recebe Web Push. Cada pessoa ativa os avisos
em cada aparelho, e o registro vai para a tabela `push_assinaturas`. Depois do commit, três fatos mandam aviso:
- a mensagem nova da cliente, no WhatsApp ou no Instagram;
- o alerta de 15 min;
- a transferência.

O envio usa a cifra própria (RFC 8291) com VAPID, fica travado no ambiente local e nasce desligado sem as chaves.

## Contexto técnico

- **Linguagem**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite).
- **Dependência nova**: nenhuma biblioteca de Web Push. A cifra e o VAPID usam o `cryptography` (fixado no
  `requirements.txt`, a mesma versão da 329) e o `requests` (R1), provados pelo vetor
  do RFC 8291.
- **Armazenamento**: 1 tabela ([data-model.md](data-model.md)).
- **Verificação**: `verify_332.py` com dublê do `webpush`; os verifies 325, 328 e 330 continuam verdes.
- **Restrições**:
  - o aviso sai sempre depois do commit e nunca derruba o processamento;
  - a trava local fica ativa;
  - a base é uma branch fora da `main`.

## Constitution Check

| Princípio | Como o plano cumpre |
|---|---|
| I. Reutilizar | Reusa os pontos de "depois do commit" do `processar_aviso`, `responsavel_ativo`, `membros_da_equipe`, `e_da_equipe`, `pode_conversas` e o `cryptography`/`requests` da casa. A cifra própria é provada pelo vetor oficial (R1). |
| II. Padrões | Type hints, docstrings, funções curtas e constantes em `app/push/constantes.py`. |
| III. Camadas | O núcleo puro fica em `app/push/push_ops.py` e o que é de Conversas em `app/conversas/celular_ops.py`. Os endpoints ficam em `app/api/push.py`, importado em `app/api/__init__.py`. |
| IV. Não quebrar | Só aditivo. Os processadores recebem o conjunto `chegadas`, e os verifies anteriores são regressão. |
| V. Feedback | Estados do painel com texto, botão com `loading` e permissão negada explicada. |
| VI/VIII | Esteira completa; verify com 3 cenários que devem falhar. |
| X/XI | Painel conferido em 375×812, com alvos de 44 px e motion do `Dialog` existente. |
| XIII | `pode_conversas` em todo endpoint novo; linha em `docs/01` §4.3. |
| XIV | Chaves VAPID vazias = desligado, com aviso na subida. `_suppress_push()` trava o local. O contato tem default real. |
| XV | Textos internos com o glossário ("Ativar avisos", "Desativar", "Avisos no celular"). |
| Stack | Migration à mão, aditiva, sobre `a330c4e8f1b2`. `cryptography==46.0.7` fixado (o mesmo da 329). |

**Resultado**: ✅ sem violação.

## Estrutura

```text
app/models.py                                   # PushAssinatura
migrations/versions/b332d5f7a9c1_push_assinaturas.py
app/config.py, app/__init__.py, render.yaml     # WEB_PUSH_* (vazios), _suppress_push, log [push]
app/cli.py                                      # flask webpush-chaves
app/push/__init__.py, constantes.py, push_ops.py  # registrar, remover, enviar, chave
app/push/webpush.py                             # cifra RFC 8291 + VAPID RFC 8292 (sem Flask)
app/conversas/celular_ops.py                    # avisar_mensagens (destino e corpo do aviso da mensagem)
app/conversas/aviso_ops.py, instagram_ops.py    # juntam em `chegadas` as conversas com mensagem nova
app/conversas/equipe_ops.py                     # avisa depois do commit (alerta, transferência)
app/api/push.py                                 # GET chave, POST/DELETE aparelhos
frontend/apps/internal/public/{manifest.webmanifest,sw.js,icone-192.png,icone-512.png,apple-touch-icon.png}
frontend/apps/internal/index.html               # manifest, apple-touch-icon, theme-color
frontend/apps/internal/src/lib/avisos.ts        # estado, ativar, desativar
frontend/apps/internal/src/components/conversas/AvisosNoCelular.tsx + ListaDeConversas.tsx
```

**Reavaliação pós-design**: ✅.

# Feature Specification: Teto autorizado — valor do superadmin vira o limite do papel

**Feature Branch**: `238-teto-autorizado` · **Created**: 2026-08-14 · **Status**: hotfix com esteira compacta

## Contexto (caso real, urgente)

Baile do Addan (evento 1235, amanhã à noite): o dono (superadmin) subiu os cachês dos papéis e
salvou — acima do teto do orçamento, com o aviso normal e registro em log. Em seguida o casting
(Diogo) foi escalar as pessoas e não conseguiu salvar mantendo aqueles valores: para
não-superadmin, o sistema rebaixa qualquer cachê ao `cache_cap` original do orçamento, mesmo
quando o valor vigente foi um superadmin que colocou.

## Regra definida pelo dono (14/08/2026)

Se um superadmin salvou um valor ACIMA do teto num papel, **esse valor passa a ser o teto
efetivo do papel**: o casting pode salvar qualquer cachê até ele (inclusive mantê-lo ao
escalar), continuando impedido de ULTRAPASSÁ-LO.

## Functional Requirements

- **FR-001**: O teto efetivo de um papel para não-superadmin DEVE ser o MAIOR entre o teto do
  orçamento (`cache_cap`) e o cachê atualmente salvo no papel. (Só um superadmin consegue ter
  salvo algo acima do cap — o próprio rebaixamento garante o invariante.)
- **FR-002**: Não-superadmin que salvar valor ≤ teto efetivo NÃO sofre rebaixamento (em
  particular, escalar alguém mantendo o valor vigente sempre funciona); acima do teto efetivo,
  o rebaixamento continua — para o teto efetivo, não para o cap antigo.
- **FR-003**: O aviso da tela de casting DEVE usar o teto efetivo (não acusar "acima do
  limite" quem está exatamente no valor autorizado pelo superadmin).
- **FR-004**: Superadmin continua livre (com a nota de log de sempre); papéis sem `cache_cap`
  continuam sem teto; nada muda nos demais fluxos.

## Success Criteria

- **SC-001**: Num papel com cap X e valor salvo Y > X (por superadmin): não-superadmin salva Y
  (mantém), salva qualquer valor ≤ Y, e um valor > Y rebaixa para Y — verificado em
  `verify_238.py` contra o `manto_local`.
- **SC-002**: A tela não mostra aviso para valor ≤ teto efetivo e mostra o aviso atual acima
  dele.
- **SC-003**: Papéis com valor ≤ cap seguem com o comportamento de sempre (regressão).

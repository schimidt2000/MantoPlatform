# Feature Specification: Review de segurança e hardening do site

**Feature Branch**: `074-security-hardening`

**Created**: 2026-06-22

**Status**: Draft

**Input**: "Faça um review completo de segurança do site e faça as mudanças necessárias. Pode fazer
tudo que precisar para o bem da segurança do site."

## Contexto

Review de segurança defensivo do sistema (app Flask próprio, autorizado pelo dono). O objetivo é
**eliminar vulnerabilidades de alto impacto sem quebrar o site em produção**. Mudanças priorizam
risco x impacto: aplicam-se correções seguras e verificáveis; itens de maior risco de quebra ficam
documentados como recomendação.

### Achados (resumo)

| # | Severidade | Achado |
|---|-----------|--------|
| C1 | Crítico | Senha do super admin **hardcoded** no `seed.py` (em código e histórico git). |
| H1 | Alto | `SECRET_KEY` com **default fraco** conhecido; sem ele em produção, sessões podem ser forjadas. |
| H2 | Alto | **Sem cabeçalhos de segurança** (clickjacking, MIME-sniffing, etc.). |
| H3 | Alto | **Sem token CSRF**; mitigado por cookie SameSite, mas dependia de `FLASK_ENV`. |
| M1 | Médio | Segurança dependia de `FLASK_ENV=production` (cookies seguros). |
| M2 | Médio | **Open redirect** via `next` e `referrer` em algumas rotas. |
| M3 | Médio | Possível **XSS armazenado** via `\| safe` em JSON gerado (`</script>`). |
| M4 | Médio | Sem **limite global de upload** (DoS por arquivo gigante). |
| OK | — | bcrypt, ORM (sem SQLi), SQL bruto parametrizado, login com rate-limit, sessão limpa no login, sem eval/exec/subprocess, uploads com `secure_filename`+limite+download autenticado. |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sessões e cookies seguros sempre (Priority: P1) 🎯 MVP

Como dono do sistema, quero que cookies de sessão e proteções básicas estejam ativos
**independentemente** de variáveis de ambiente, para que a sessão do usuário não possa ser
roubada/forjada.

**Acceptance Scenarios**:

1. **Given** o app em produção, **When** uma resposta é enviada, **Then** os cookies de sessão são
   `HttpOnly`, `SameSite=Lax` e `Secure` (em HTTPS).
2. **Given** produção sem `SECRET_KEY` definido, **When** o app inicia, **Then** ele **não** usa a
   chave fraca conhecida (gera/usa uma chave forte), sem derrubar o site.

### User Story 2 - Cabeçalhos de segurança (Priority: P1)

Como dono, quero cabeçalhos de segurança em todas as respostas, para mitigar clickjacking, sniffing
e injeções.

**Acceptance Scenarios**:

1. **Given** qualquer página, **When** carregada, **Then** as respostas trazem `X-Content-Type-Options`,
   `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` e uma `Content-Security-Policy` que
   **não quebra** scripts/estilos/integrações existentes; HSTS em HTTPS.

### User Story 3 - Sem segredos no código e sem redirecionamento aberto (Priority: P1)

Como dono, quero que não haja senha fixa no código e que redirecionamentos sigam apenas para
páginas internas.

**Acceptance Scenarios**:

1. **Given** o `seed.py`, **When** cria o super admin inicial, **Then** a senha vem de variável de
   ambiente (ou é aleatória) e exige troca no primeiro acesso — **sem** senha fixa no código.
2. **Given** uma rota que aceita `next`, **When** `next` aponta para um site externo, **Then** o
   redirecionamento é **ignorado** e cai num destino interno seguro.

### Edge Cases

- Funcionalidades atuais (formulários, uploads, integrações Google, impressão) **continuam
  funcionando** após o hardening.
- Super admin **já existente** em produção não é afetado pela mudança do seed (só afeta banco vazio).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Remover qualquer **senha/segredo hardcoded** do código; senha inicial do super admin
  vem de env (ou aleatória) e exige **troca no primeiro acesso**.
- **FR-002**: `SECRET_KEY` MUST nunca ser a chave fraca conhecida em produção; se ausente, usar uma
  chave forte persistente, sem derrubar a aplicação.
- **FR-003**: Cookies de sessão MUST ser `HttpOnly` + `SameSite=Lax` sempre, e `Secure` em HTTPS,
  independentemente de `FLASK_ENV`.
- **FR-004**: Todas as respostas MUST incluir cabeçalhos de segurança (nosniff, frame-options,
  referrer-policy, permissions-policy, CSP mínima, HSTS em HTTPS) **sem quebrar** o site.
- **FR-005**: Redirecionamentos baseados em `next`/`referrer` MUST validar destino **interno**
  (sem open redirect).
- **FR-006**: Dados injetados como JSON em `<script>` MUST ser escapados para impedir quebra de
  contexto (`</script>`) — sem XSS armazenado.
- **FR-007**: MUST existir um **limite global de tamanho** de requisição/upload.
- **FR-008**: As proteções já existentes (rate-limit no login, hash bcrypt, ORM, etc.) MUST ser
  preservadas; nenhuma regressão funcional.

### Key Entities

- N/A (mudança de configuração/infra de segurança; sem novas entidades).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nenhuma senha/segredo fixo permanece no código-fonte da aplicação.
- **SC-002**: Respostas trazem os cabeçalhos de segurança e cookies endurecidos (verificado).
- **SC-003**: `next`/`referrer` externos são ignorados (redireciona para destino interno).
- **SC-004**: JSON em `<script>` não permite quebra de contexto.
- **SC-005**: App inicia e funcionalidades-chave seguem operando (login, páginas, uploads) — sem
  regressão; sem novos erros de lint.

## Assumptions

- Review e mudanças **defensivas**, autorizadas pelo dono do sistema.
- CSRF por token é **defesa-em-profundidade recomendada** (rollout em todos os formulários) — não
  aplicado agora por alto risco de quebra; mitigado por `SameSite=Lax` + `form-action 'self'`.
- O super admin de produção já existe; trocar a senha viva é ação operacional do dono (recomendada,
  pois a antiga estava no histórico git).
- CSP é mínima (sem `default-src`/`script-src` restritivos) para não quebrar scripts inline e
  integrações; endurecer CSP é evolução futura.

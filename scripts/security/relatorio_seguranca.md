# Relatório de Auditoria de Segurança — Plataforma Manto

**Gerado em:** 28/07/2026 03:15  
**Banco:** `localhost:5432/manto_local`  
**Resultado:** 76/76 verificações passaram — **tudo OK**

Gerado por `scripts/security/overnight_security_audit.py` (feature 191).


## 1. Cookies de sessão (HttpOnly / SameSite / Secure)

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Portal: login do talento responde 200 | — |
| ✅ | Portal (Talento): login emite cookie de sessão | — |
| ✅ | Portal (Talento): cookie tem HttpOnly (bloqueia leitura por XSS) | Expires=Fri, 28 Aug 2026 06:15:13 GMT; HttpOnly; Path=/; SameSite=Lax |
| ✅ | Portal (Talento): cookie tem SameSite=Lax ou Strict (bloqueia CSRF cross-site) | SameSite=lax |
| ✅ | Portal (Talento): flag Secure coerente com o ambiente | Secure=ausente (esperado: False) |
| ✅ | App interno: login de staff responde 200 | — |
| ✅ | App interno (Staff): login emite cookie de sessão | — |
| ✅ | App interno (Staff): cookie tem HttpOnly (bloqueia leitura por XSS) | HttpOnly; Path=/; SameSite=Lax |
| ✅ | App interno (Staff): cookie tem SameSite=Lax ou Strict (bloqueia CSRF cross-site) | SameSite=lax |
| ✅ | App interno (Staff): flag Secure coerente com o ambiente | Secure=ausente (esperado: False) |
| ✅ | ProductionConfig: SESSION_COOKIE_SECURE = True | — |
| ✅ | ProductionConfig: SESSION_COOKIE_HTTPONLY = True | — |
| ✅ | ProductionConfig: SESSION_COOKIE_SAMESITE em {Lax, Strict} | SameSite=Lax |

## 1b. Isolamento entre sessão de Staff e de Talento

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Cookie de Talento NÃO autentica na API de Staff (/api/auth/me) | HTTP 401 |
| ✅ | Cookie de Staff NÃO autentica na API do Portal (/api/portal/auth/me) | HTTP 401 |
| ✅ | Cookie de Staff NÃO alcança a Agenda do Portal | HTTP 401 |
| ✅ | Login de Talento encerra a sessão de Staff no mesmo cookie | HTTP 401 |
| ✅ | Login de Staff encerra a sessão de Talento no mesmo cookie | HTTP 401 |

## 2. RBAC — Talento tentando alcançar o App Interno

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Talento bloqueado em GET /api/auth/me | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/dashboard | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/financeiro/dashboard | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/financeiro/pagamentos | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/vendas/pipeline | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/admin/users | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/admin/settings | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/admin/logs | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/rh/dashboard | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/talents | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/talents/directory | HTTP 401 |
| ✅ | Talento bloqueado em GET /api/agenda | HTTP 401 |
| ✅ | GET /api/clientes | rota inexistente neste build — ignorada |

## 2b. RBAC — Anônimo (sem sessão)

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Anônimo bloqueado em GET /api/financeiro/dashboard | HTTP 401 |
| ✅ | Anônimo bloqueado em GET /api/admin/users | HTTP 401 |
| ✅ | Anônimo bloqueado em GET /api/portal/agenda | HTTP 401 |
| ✅ | Anônimo bloqueado em GET /api/portal/profile | HTTP 401 |
| ✅ | Anônimo bloqueado em GET /api/portal/historico | HTTP 401 |
| ✅ | Anônimo bloqueado em GET /api/portal/ratings/pending | HTTP 401 |

## 2c. RBAC — Acesso cruzado entre papéis de Staff (vendedor)

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Vendedor (COMERCIAL) autentica | — |
| ✅ | Vendedor bloqueado em painel de usuários (SUPERADMIN/FINANCEIRO) (GET /api/admin/users) | HTTP 403 |
| ✅ | Vendedor bloqueado em painel de RH / salários (GET /api/rh/dashboard) | HTTP 403 |
| ✅ | Vendedor bloqueado em planilha de pagamentos (GET /api/financeiro/pagamentos) | HTTP 403 |
| ✅ | Vendedor bloqueado em configurações do sistema (GET /api/admin/settings) | HTTP 403 |
| ✅ | Vendedor bloqueado em logs de auditoria (GET /api/admin/logs) | HTTP 403 |
| ✅ | Vendedor bloqueado em painel de desempenho (GET /api/admin/desempenho) | HTTP 403 |

## 2d. RBAC — Isolamento de dados entre talentos (IDOR)

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Talento não age sobre escalação alheia — POST /api/portal/invites/999999/accept | HTTP 404 |
| ✅ | Talento não age sobre escalação alheia — POST /api/portal/invites/999999/reject | HTTP 404 |
| ✅ | Talento não age sobre escalação alheia — POST /api/portal/roles/999999/ack-change | HTTP 404 |
| ✅ | Talento não apaga mídia alheia — DELETE /api/portal/profile/media/<id> | HTTP 404 |
| ✅ | Talento não lê figurino de evento em que não está escalado | HTTP 403 |
| ✅ | PATCH /api/portal/profile ignora `id` do cliente (usa o da sessão) | HTTP 200, nome='AUDIT191 Talento' |

## 3d. E-mails — mapa de disparadores

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Disparador mapeado: Reset de senha — Talento (`send_password_reset_email`) | /api/portal/auth/forgot-password |
| ✅ | Disparador mapeado: Primeiro acesso / boas-vindas — Talento (`send_welcome_email`) | /api/portal/auth/first-access |
| ✅ | Disparador mapeado: Envio de proposta/orçamento (`send_quote_email`) | /api/orcamento/* (orcamento_write) |
| ✅ | Disparador mapeado: Convite de elenco na página do evento (`send_invite_email`) | casting_ops.send_invite |
| ✅ | Disparador mapeado: Remoção do elenco (`send_removal_email`) | casting_ops.replace/remove |
| ✅ | Disparador mapeado: Alteração de horário/local do evento (`send_event_changed_email`) | event_ops/casting_ops |
| ✅ | Disparador mapeado: Comunicado do portal (`send_portal_announcement_email`) | /api/admin/config (announcement) |
| ✅ | Disparador mapeado: Alerta de ensaio (`send_ensaio_alert_email`) | cron de ensaio |
| ✅ | Reset de senha de Staff é manual (sem e-mail) — `user_ops.reset_password` | não há fluxo self-service por e-mail para staff; ver relatório |

## 3e. E-mails — todo caminho de envio é guardado

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Existe ao menos um caminho de envio mapeado | send_quote_email, _send |
| ✅ | `send_quote_email` envolve o envio em try/except (SMTP fora do ar não propaga) | — |
| ✅ | `send_quote_email` respeita SiteSetting.email_notifications_enabled | — |
| ✅ | `_send` envolve o envio em try/except (SMTP fora do ar não propaga) | — |
| ✅ | `_send` respeita SiteSetting.email_notifications_enabled | — |
| ✅ | `send_async` roda em thread com try/except (não derruba a request) | — |

## 3. E-mails — flag desligada (log silencioso, sem 500)

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Reset de senha do Talento não estoura com e-mail desligado | HTTP 200 |
| ✅ | Primeiro acesso do Talento não estoura com e-mail desligado | HTTP 400 |
| ✅ | email_service._send devolve False (não levanta) com a flag desligada | — |

## 3b. E-mails — flag ligada com SMTP quebrado (falha limpa, sem 500)

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | email_service._send devolve False (não propaga) quando o SMTP falha | — |
| ✅ | Reset de senha responde 200 mesmo com SMTP fora do ar | HTTP 200 |
| ✅ | Resposta traz mensagem amigável, não stack trace | Se os dados conferem, enviamos um link de redefinição para o seu e-mail. |
| ✅ | Primeiro acesso responde sem 500 com SMTP fora do ar | HTTP 400 |

## 3f. E-mails — proposta/orçamento (caminho com anexo PDF)

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Orçamento não é enviado com a flag desligada (devolve False) | — |
| ✅ | Orçamento devolve False (não propaga) com SMTP fora do ar | — |

## 3c. E-mails — reset de senha não revela existência de conta

| Resultado | Verificação | Detalhe |
| --- | --- | --- |
| ✅ | Mesmo status HTTP para conta existente e inexistente | real=200, falsa=200 |
| ✅ | Mesmo corpo de resposta para conta existente e inexistente | — |

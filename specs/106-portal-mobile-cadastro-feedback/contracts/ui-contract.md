# Contrato de UI — Feature 106

Nenhuma rota muda. Dois contratos de comportamento de interface:

## 1. Validação do formulário `/cadastro` (form.html)

### Estados

| Estado | Aparência |
|---|---|
| Campo válido | visual atual (borda `--line`, foco `--accent`) |
| Campo inválido pós-tentativa | container `.field` com classe `.field-invalid`: input com borda `var(--danger)` + shake 400ms; mensagem `.field-errmsg` (12.5px, `var(--danger)`) abaixo do campo |
| Grupo obrigatório inválido | mesmo tratamento no container do grupo, mensagem = texto do atributo `data-required-group` |
| Campo corrigido | destaque e mensagem removidos no evento `input`/`change` |

### Comportamento no submit

1. `<form novalidate>`; handler coleta, na ordem do DOM:
   - campos `:invalid` que estejam habilitados e visíveis (`!disabled`, `offsetParent != null`);
   - grupos `[data-required-group]` com zero checkboxes marcados.
2. Se houver inválidos: `preventDefault()`; marcar TODOS; rolar até o primeiro
   (`scrollIntoView({behavior:'smooth', block:'center'})`) e focar
   (`focus({preventScroll:true})`); botão de envio permanece habilitado e com texto normal.
3. Se não houver: comportamento atual (botão desabilita + "Enviando…", submit segue).
4. Nunca usar `alert()`; nunca limpar valores preenchidos.

### Mensagens padrão (pt-BR)

| Situação | Mensagem |
|---|---|
| Campo vazio (`valueMissing`) | "Preencha este campo." |
| E-mail inválido (`typeMismatch`) | "Informe um e-mail válido." |
| Arquivo obrigatório sem anexo | "Anexe o arquivo." |
| Grupo sem seleção | texto do `data-required-group` (já existente) |

## 2. Regras responsivas novas do portal (style.css, bloco `@media (max-width:768px)`)

| Regra | Efeito |
|---|---|
| `.portal-wrap .btn { min-height: 44px; }` | alvos de toque confortáveis em todo o portal |
| `.grid-pair { grid-template-columns: 1fr !important; }` (≤480px) | pares de campos do perfil empilham |
| Ajustes pontuais por template | ver research.md achados B, C, F, G |

Invariantes: sem scroll horizontal em 320–430px; regras existentes (portal-header,
invite-actions, grid-medidas, telefone/DDI do cadastro) preservadas.

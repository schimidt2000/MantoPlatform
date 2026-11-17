# 354 — Política de privacidade do atendimento (`/privacidade`)

**Branch**: `354-politica-de-privacidade` · **Created**: 2026-11-17 · **Status**: em andamento ·
**Migration**: nenhuma

## O pedido

O dono, ligando o CRM no número de teste da Meta (17/11): "pode criar a página geral". O app Meta
**Manto Plataforma** (ID 1690356099369816) só recebe mensagem de verdade depois de publicado, e a Meta só
publica com a **URL da política de privacidade** preenchida. A única página que existia era o aviso da loja
de conversas (`/catalogo/v/privacidade`, feature 344), que fala da loja e não das conversas do WhatsApp e do
Instagram.

## O que muda

1. **`/privacidade` na raiz do domínio** (`app.mantoproducoes.com.br/privacidade`), servida pelo bundle da
   vitrine como superfície de raiz — o mesmo arranjo de `/cadastro` e `/nfc`:
   - `frontend/server.js`: `PRIVACIDADE_PREFIX` servido de `PUBLIC_DIST` sem reescrever a URL, antes do
     bloco do host do portal;
   - `apps/public/src/App.tsx`: `/privacidade` em `isRootSurface` e a rota antes do `/:slug`.
   - A URL fica gravada no cadastro do app na Meta: não renomear.
2. **`PrivacidadePage`** (`apps/public/src/pages/PrivacidadePage.tsx`), no tom do site público (Princípio
   XV), dizendo só o que o sistema faz hoje:
   - o que a conversa guarda (`Conversa`, mensagens e mídias, `ConversaAnuncio`, notas da equipe) e a
     ficha da cliente (`Client`: nome, telefone, e-mail, CPF/CNPJ, endereço);
   - quem vê (Comercial e Superadmin, `pode_conversas`);
   - com quem divide (Meta, Render nos EUA, Google Agenda, ClickSign, quem processa o pagamento);
   - retenção sem prazo automático, a mensagem apagada no Instagram que some do sistema
     (`instagram_ops._apagar`) e os direitos pelo WhatsApp;
   - link para o aviso próprio da loja.

## Verificação

Sem comportamento de backend: sem `verify`. `npm run typecheck`; a tela aberta em 390 px pelo
`/privacidade` (superfície de raiz) e pelo `/catalogo/privacidade`; o `server.js` local servindo
`/privacidade` com o bundle da vitrine (não o do ERP). Texto aprovado pelo dono antes de publicar.

## Fora de escopo

- Botão para excluir conversa ou ficha a pedido da cliente: hoje a exclusão a pedido é manual (dívida
  registrada no `docs/05`).
- Parecer jurídico do texto (o mesmo pendente da 350, dívida 218).
- Instagram ligado (`INSTAGRAM_*`), que segue desligado.

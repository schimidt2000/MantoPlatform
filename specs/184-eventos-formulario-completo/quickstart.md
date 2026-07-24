# Quickstart: Reconstrução do Formulário de Cadastro/Edição de Eventos

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1      # backend, apontando para manto_local
cd frontend; npm run dev:internal
```

Logar como COMERCIAL ou SUPERADMIN (`joao@mantoproducoes.com.br`) para acessar `/events/new` e
`/events/:id/edit`.

## Checklist de verificação manual

1. **Bloco 1**: buscar cliente existente, adicionar com uma relação; cadastrar cliente novo
   inline (nome+telefone) e ver aparecer selecionado; buscar e vincular uma resposta de
   pré-contrato.
2. **Bloco 2**: preencher data/início/fim/tipo/local/descrição; tipo SHOW mantém ensaio sempre
   marcado e travado, com o texto de ajuda.
3. **Bloco 3**: adicionar 2+ personagens, ver o dropdown de figurino e o pré-escalar talento;
   clicar "Gerar título automaticamente" e ver o título no padrão `(TIPO) NOME1 + NOME2`; editar o
   título manualmente e confirmar que ele para de ser sobrescrito.
4. **Bloco 4**: alternar cortesia/permuta e ver os campos de valor esmaecerem e deixarem de ser
   obrigatórios; digitar valor antes do desconto e valor de venda e ver o % calculado.
5. **Bloco 5**: escolher cada forma de pagamento e ver os campos condicionais (parcelas/
   vencimento); anexar 2 comprovantes com valores, remover um antes de salvar.
6. **Bloco 6**: anexar o contrato, marcar "já assinado".
7. **Bloco 7**: adicionar uma observação de cada tipo (texto, foto, link).
8. Submeter vazio → banner de erro no topo/rodapé + scroll suave até o primeiro campo inválido,
   com foco nele.
9. Salvar com sucesso → evento criado com todos os anexos; se um anexo falhar propositalmente
   (ex.: desconectar a rede no meio), confirmar que aparece o status por item com "Tentar
   novamente", sem perder o evento já criado.
10. Abrir `/events/:id/edit` de um evento com dados variados → todos os campos pré-preenchidos;
    alterar um campo de cada bloco, salvar, reabrir o evento e confirmar a persistência.
11. Remover na edição um personagem com convite aceito, sem ser SUPERADMIN → operação recusada
    com mensagem clara, nada é salvo.
12. Usuário sem papel COMERCIAL/SUPERADMIN acessando `/events/new` ou `/events/:id/edit` →
    bloqueado.

## Verificação funcional automatizada

Script `scripts/db/verify_184_eventos_formulario_completo.py` (test client Flask, requests fora
de `app_context`, contra `manto_local`) cobrindo: `PATCH /api/events/<id>` (200, 400 de validação,
409 de convite aceito, 403 RBAC), `POST /events/<id>/contracts` com `is_signed`.

## E2E (Playwright)

```powershell
cd frontend/apps/internal
npx playwright test e2e/event-form.spec.ts
```

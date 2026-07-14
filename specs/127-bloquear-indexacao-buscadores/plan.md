# Implementation Plan: Bloquear Indexação em Buscadores (127)

**Branch**: `127-bloquear-indexacao-buscadores` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

## Summary

Duas mudanças pequenas, cobrindo o site inteiro sem precisar tocar em nenhum template:

1. Cabeçalho HTTP `X-Robots-Tag: noindex, nofollow, noarchive` em toda resposta — via o
   hook `@app.after_request` que já existe (`_security_headers`, feature 074). Robusto
   por natureza: cobre toda página presente e futura, pública ou atrás de login, sem
   depender de lembrar de adicionar uma tag em cada template novo (satisfaz FR-003).
2. Rota `/robots.txt` nova, servindo `User-agent: *\nDisallow: /`.

## Technical Context

**Stack**: o existente (Flask). **Storage**: N/A.

**Arquivos**: `app/__init__.py` — adiciona uma linha em `_security_headers()` +
nova rota `robots_txt()`.

**Testing**: verificação funcional — algumas rotas de amostra (login, home, um formulário
público) respondem com o cabeçalho; `/robots.txt` responde `Disallow: /`.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Usa o hook `_security_headers` já existente (feature 074) em vez de criar um novo `after_request` — mesmo padrão, uma linha a mais. |
| IV. Não quebrar | ✅ `X-Robots-Tag` é só um cabeçalho HTTP informativo — não muda nenhum comportamento funcional da aplicação; `/robots.txt` é uma rota nova, sem conflito com nada existente. |
| VI. Planejar | ✅ Este plano. |

**Gate: PASS.**

## Decisões

1. **Cabeçalho HTTP em vez de `<meta name="robots">` por template**: uma linha no hook
   global cobre 100% das páginas (presentes e futuras) automaticamente — a alternativa
   (meta tag por template) exigiria tocar em cada `base.html`/`_public_base.html`/futuros
   templates e seria fácil esquecer um. `X-Robots-Tag` é reconhecido pelos mesmos
   buscadores que respeitam a meta tag, com a vantagem de não depender de HTML algum
   (cobre até respostas JSON de API).
2. **Remoção de conteúdo já indexado fica fora do código**: registrado no spec como
   Assumption — depende de ferramenta do Google que exige comprovar posse do domínio,
   não é algo que o código consiga fazer sozinho.

# Tasks — Feedback Visual em Todo Botão de Ação (124)

- [X] T001 Constituição já emendada antes desta spec (`.specify/memory/constitution.md`
      v1.3.0 → v1.4.0: Princípio V reforçado + item novo no portão de qualidade)
- [X] T002 `app/templates/base.html`: guard global de `submit` passa a adicionar a classe
      `is-loading` aos botões desabilitados (além do `disabled` já existente); adicionar
      listener `window.addEventListener('pageshow', ...)` que remove `disabled`/`is-loading`
      de todo botão quando `event.persisted` (restauração via bfcache)
- [X] T003 `app/static/style.css`: regra nova `.btn:disabled, .btn.is-loading` (opacidade
      reduzida, `cursor: progress`) + `::after` com reticências — sem cor hardcoded nova
- [X] T004 Verificação vs manto_local: `/gastos/` e demais telas internas (`/`, `/agenda`)
      renderizam normalmente com o guard novo (12/12); JS servido contém `is-loading`,
      `pageshow`/`e.persisted` e ainda respeita `defaultPrevented`; CSS servido contém as
      novas regras; `/f/pre-contrato` (formulário público) sem regressão, mantém "Enviando"
      próprio. Ruff comparado contra worktree do `main`: 93/93 erros, zero novo (mudança é
      JS/CSS/constituição, sem Python). **Verificação visual em navegador real não foi
      possível neste ambiente** (sem ferramenta de automação de browser disponível) — a
      lógica foi conferida por leitura cuidadosa (fase de bubble, `defaultPrevented`
      preservado, `pageshow`/`persisted` é API padrão) e por HTTP, não por captura de tela.
- [X] T005 Commit, merge em main, push

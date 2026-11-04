# Quickstart — 333 Orçamento e formulário pela conversa

## 1. Verificação automática

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs/333-crm-orcamento-na-conversa/verify_333.py
```

O resultado esperado é tudo `OK`, com zero escapes. `verify_325`, `verify_328`, `verify_330` e `verify_332` continuam
verdes.

## 2. Tela

Backend e Vite sobem pela worktree, em portas próprias, com variáveis falsas do WhatsApp só nessa instância (o envio
fica travado pelo banco local). Conferir:
- "Enviar orçamento" e "Enviar formulário" na conversa;
- "Ligar à ficha" e o menu da ficha no cabeçalho;
- "Enviar na conversa" e os envios na tela do orçamento;
- o selo no histórico;
- o evento pré-preenchido com a cliente.

Em desktop e 375×812. Com a trava, o envio responde "O envio pelo WhatsApp está travado neste ambiente.": conferir o
texto e o diálogo.

## 3. De verdade (pelo dono, no número de teste, depois do deploy)

1. Gerar um orçamento na calculadora e, na tela dele, "Enviar na conversa" para o número de teste.
2. Conferir que chegam a mensagem e o PDF, que a ficha nasce e que o histórico mostra "Enviado na conversa".
3. "Criar evento" no orçamento e conferir a cliente já escolhida.

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button } from "@manto/ui";
import { mensagemDoErro, useDefinirResponsavel, type ConversaResumo } from "../../lib/conversas";
import { TransferirDialog } from "./TransferirDialog";

/**
 * Quem atende a conversa (feature 328, FR-001 a FR-004): a faixa sob o cabeçalho.
 *
 * - Sem responsável, ou com um responsável que perdeu o acesso: "Assumir".
 * - Com responsável: "Transferir…" e "Devolver à fila", para qualquer pessoa da equipe.
 *
 * Botões diretos em vez de menu: cada ação é um toque só. No celular, cada botão tem 44 px
 * (FR-017) e o nome de quem atende ganha uma linha própria (em 320 px ele seria cortado). A
 * corrida do "Assumir" volta 409 com o nome de quem ganhou — o texto do servidor aparece aqui, e
 * a conversa recarrega mostrando o novo responsável.
 */

interface ResponsavelDaConversaProps {
  conversa: ConversaResumo;
  usuarioId: number | null;
}

function rotuloDoResponsavel(conversa: ConversaResumo, usuarioId: number | null): string {
  const responsavel = conversa.responsavel;
  if (!responsavel) return "Sem responsável";
  if (responsavel.id === usuarioId) return "Você atende esta conversa";
  return conversa.responsavel_ativo === false
    ? `Responsável: ${responsavel.nome} (sem acesso)`
    : `Responsável: ${responsavel.nome}`;
}

export function ResponsavelDaConversa({ conversa, usuarioId }: ResponsavelDaConversaProps) {
  const reduzir = useReducedMotion();
  const definir = useDefinirResponsavel(conversa.id);
  const [transferindo, setTransferindo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const responsavel = conversa.responsavel ?? null;
  const podeAssumir = !responsavel || (conversa.responsavel_ativo === false && responsavel.id !== usuarioId);

  const executar = (acao: "assumir" | "devolver") => {
    setErro(null);
    definir.mutate(
      { acao },
      { onError: (falha) => setErro(mensagemDoErro(falha, "Não foi possível alterar o responsável. Tente novamente.")) },
    );
  };

  return (
    <div className="border-b border-line bg-panel px-3 py-1.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.p
            key={rotuloDoResponsavel(conversa, usuarioId)}
            className="min-w-0 basis-full truncate text-xs text-muted md:basis-0 md:flex-1"
            initial={reduzir ? false : { opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduzir ? undefined : { opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            {rotuloDoResponsavel(conversa, usuarioId)}
          </motion.p>
        </AnimatePresence>
        {podeAssumir ? (
          <Button
            type="button"
            size="sm"
            className="h-11 md:h-8"
            loading={definir.isPending && definir.variables?.acao === "assumir"}
            onClick={() => executar("assumir")}
          >
            Assumir
          </Button>
        ) : null}
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-11 md:h-8"
          onClick={() => setTransferindo(true)}
          disabled={definir.isPending}
        >
          Transferir…
        </Button>
        {responsavel ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-11 md:h-8"
            loading={definir.isPending && definir.variables?.acao === "devolver"}
            onClick={() => executar("devolver")}
          >
            Devolver à fila
          </Button>
        ) : null}
      </div>
      {erro ? (
        <p role="alert" className="pb-1 text-xs text-red">
          {erro}
        </p>
      ) : null}
      <TransferirDialog
        conversaId={conversa.id}
        nomeDoContato={conversa.nome}
        responsavelAtual={responsavel?.id ?? null}
        open={transferindo}
        onOpenChange={setTransferindo}
      />
    </div>
  );
}

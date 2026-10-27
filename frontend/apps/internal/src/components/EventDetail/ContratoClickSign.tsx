import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Badge,
  Button,
  ConfirmDialog,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  formatShortDate,
} from "@manto/ui";
import type { EventoDetalhe } from "../../lib/agenda";
import {
  prazoCurto,
  useContratosAConferir,
  useDesligarContrato,
  useLigarContrato,
  type ContratoAConferir,
  type ContratoDaVenda,
  type DocumentoClickSign,
} from "../../lib/contratos";
import { mensagemDaApi } from "../../lib/formulariosAdmin";
import { Empty, Panel, formatDateTime } from "./parts";

const TOM_DA_COR = { verde: "green", vermelho: "red", amarelo: "gold", cinza: "neutral" } as const;
const CANAL = { whatsapp: "pelo WhatsApp", email: "por e-mail", sms: "por SMS" } as Record<string, string>;
const STATUS = {
  running: "em processo",
  closed: "assinado",
  canceled: "cancelado na ClickSign",
  draft: "rascunho",
} as Record<string, string>;

/** "fulano" + canal + prazo de um documento, numa linha. */
function DetalheDoDocumento({ documento }: { documento: DocumentoClickSign }) {
  const partes = [
    STATUS[documento.status] ?? documento.status,
    documento.canal ? `enviado ${CANAL[documento.canal] ?? documento.canal}` : null,
    documento.status === "running" && documento.prazo ? `prazo até ${prazoCurto(documento.prazo)}` : null,
    documento.assinado_em ? `assinado em ${formatDateTime(documento.assinado_em)}` : null,
    documento.vinculo_origem === "manual" ? "ligado à mão" : "ligado automaticamente",
  ].filter(Boolean);
  return <p className="text-xs text-muted">{partes.join(" · ")}</p>;
}

/** "Achamos um contrato que parece desta venda" — ligar à venda deste evento. */
function FaixaAConferir({ item, eventId }: { item: ContratoAConferir; eventId: number }) {
  const reduceMotion = useReducedMotion();
  const ligar = useLigarContrato(eventId);
  return (
    <motion.li
      initial={reduceMotion ? false : { opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="overflow-hidden"
    >
      <div className="mt-2 flex flex-wrap items-center gap-2 rounded-md bg-accent-soft px-3 py-2 text-sm">
        <span className="min-w-0 flex-1 text-ink">
          Achamos um contrato que parece desta venda: <strong>{item.nome}</strong>
          {item.motivo_texto && <span className="block text-xs text-muted">{item.motivo_texto}</span>}
        </span>
        <Button
          type="button"
          size="sm"
          loading={ligar.isPending}
          onClick={() => ligar.mutate({ documentoId: item.documento_id, eventId })}
        >
          É desta venda
        </Button>
      </div>
      {ligar.isError && (
        <p role="alert" className="mt-1 text-xs text-red">
          {mensagemDaApi(ligar.error, "Não foi possível ligar. Tente novamente.")}
        </p>
      )}
    </motion.li>
  );
}

/** Diálogo "Ligar contrato da ClickSign": escolhe um dos contratos a conferir. */
function LigarContratoDialog({
  eventId,
  open,
  onOpenChange,
}: {
  eventId: number;
  open: boolean;
  onOpenChange: (aberto: boolean) => void;
}) {
  const lista = useContratosAConferir(open);
  const ligar = useLigarContrato(eventId);
  const [filtro, setFiltro] = useState("");
  const itens = (lista.data?.itens ?? []).filter((item) =>
    item.nome.toLowerCase().includes(filtro.trim().toLowerCase()),
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Ligar contrato da ClickSign</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted">
          Contratos que o sistema não conseguiu ligar sozinho. Escolha o desta venda.
        </p>
        <input
          type="search"
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          placeholder="Filtrar pelo nome (data, telefone, tema)"
          aria-label="Filtrar contratos"
          className="h-11 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink"
        />
        {lista.isLoading && <p className="text-sm text-muted">Carregando…</p>}
        {lista.isError && <p className="text-sm text-red">Não foi possível carregar os contratos.</p>}
        {lista.isSuccess && itens.length === 0 && <Empty>Nenhum contrato a conferir.</Empty>}
        <ul className="max-h-80 divide-y divide-line overflow-y-auto">
          {itens.map((item) => (
            <li key={item.documento_id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
              <span className="min-w-0 flex-1">
                <span className="block text-ink">{item.nome}</span>
                <span className="block text-xs text-muted">
                  {item.data_lida ? `Evento em ${formatShortDate(item.data_lida)}` : "Data ilegível"}
                  {item.motivo_texto ? ` · ${item.motivo_texto}` : ""}
                </span>
              </span>
              <Button
                size="sm"
                loading={ligar.isPending && ligar.variables?.documentoId === item.documento_id}
                onClick={() =>
                  ligar.mutate(
                    { documentoId: item.documento_id, eventId },
                    { onSuccess: () => onOpenChange(false) },
                  )
                }
              >
                Ligar
              </Button>
            </li>
          ))}
        </ul>
        {ligar.isError && (
          <p role="alert" className="text-sm text-red">
            {mensagemDaApi(ligar.error, "Não foi possível ligar. Tente novamente.")}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * "Situação do contrato" (feature 317): o contrato da ClickSign julgado pela venda — assinado,
 * aguardando (com prazo), vencido, recusado ou sem contrato — e a conferência do que o sistema não
 * ligou sozinho. Fica na aba Comercial, acima dos anexos.
 */
export function ContratoClickSign({ data }: { data: EventoDetalhe }) {
  const contrato: ContratoDaVenda | null | undefined = data.contrato;
  const eventId = data.event.id;
  const desligar = useDesligarContrato(eventId);
  const [desligando, setDesligando] = useState(false);
  const [ligarAberto, setLigarAberto] = useState(false);

  if (contrato === undefined) return null;
  if (contrato === null) {
    return (
      <Panel title="Situação do contrato">
        <p className="text-sm text-red">Não foi possível carregar a situação do contrato agora.</p>
      </Panel>
    );
  }
  if (!contrato.integracao_ligada) {
    return data.flags.is_superadmin ? (
      <Panel title="Situação do contrato">
        <p className="text-sm text-muted">Integração com a ClickSign desligada.</p>
      </Panel>
    ) : null;
  }

  const documento = contrato.documento;
  const podeLigar =
    contrato.pode_conferir && ["sem_contrato", "vencido", "recusado"].includes(contrato.situacao);

  return (
    <Panel
      title="Situação do contrato"
      actions={<Badge tone={TOM_DA_COR[contrato.cor]}>{contrato.rotulo}</Badge>}
    >
      {documento ? (
        <div className="space-y-1 text-sm">
          <p className="text-ink">{documento.nome}</p>
          <DetalheDoDocumento documento={documento} />
          {contrato.ultima_cobranca && (
            <p className="text-xs text-muted">
              Cobrado por {contrato.ultima_cobranca.por} em {formatDateTime(contrato.ultima_cobranca.em)}
            </p>
          )}
          {contrato.pode_conferir && (
            <Button variant="ghost" size="sm" onClick={() => setDesligando(true)}>
              Não é desta venda — desligar
            </Button>
          )}
        </div>
      ) : (
        <Empty>
          {contrato.situacao === "assinado_manual"
            ? "Assinado fora da ClickSign (marcado à mão)."
            : "Nenhum contrato da ClickSign ligado a esta venda."}
        </Empty>
      )}

      {contrato.outros_documentos.length > 0 && (
        <details className="mt-2 text-xs text-muted">
          <summary className="cursor-pointer">Outros contratos desta venda ({contrato.outros_documentos.length})</summary>
          <ul className="mt-1 space-y-1">
            {contrato.outros_documentos.map((outro) => (
              <li key={outro.id}>
                {outro.nome} — {STATUS[outro.status] ?? outro.status}
              </li>
            ))}
          </ul>
        </details>
      )}

      <ul>
        <AnimatePresence initial={false}>
          {contrato.a_conferir.map((item) => (
            <FaixaAConferir key={item.documento_id} item={item} eventId={eventId} />
          ))}
        </AnimatePresence>
      </ul>

      {podeLigar && (
        <div className="mt-3 border-t border-line pt-3">
          <Button variant="outline" size="sm" onClick={() => setLigarAberto(true)}>
            Ligar contrato da ClickSign
          </Button>
        </div>
      )}

      {desligar.isError && (
        <p role="alert" className="mt-1 text-sm text-red">
          {mensagemDaApi(desligar.error, "Não foi possível desligar.")}
        </p>
      )}
      <ConfirmDialog
        open={desligando}
        title="Desligar este contrato da venda?"
        description="O contrato volta para a lista A conferir e o sistema não o liga de novo sozinho a esta venda."
        confirmLabel="Desligar"
        pending={desligar.isPending}
        error={desligar.isError ? mensagemDaApi(desligar.error, "Não foi possível desligar.") : null}
        onConfirm={() =>
          documento && desligar.mutate(documento.id, { onSuccess: () => setDesligando(false) })
        }
        onOpenChange={(aberto) => {
          if (!aberto) {
            setDesligando(false);
            desligar.reset();
          }
        }}
      />
      <LigarContratoDialog eventId={eventId} open={ligarAberto} onOpenChange={setLigarAberto} />
    </Panel>
  );
}

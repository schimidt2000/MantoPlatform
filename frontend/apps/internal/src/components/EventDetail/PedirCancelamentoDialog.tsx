import { useState } from "react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
} from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { formatBRL, MoneyInput } from "@manto/money";
import type { EventoDetalhe, ModoDevolucao } from "../../lib/agenda";
import {
  type AlcanceCancelamento,
  type PedidoCancelamentoInput,
  usePedirCancelamento,
} from "../../lib/eventOps";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";

const MODOS: { modo: ModoDevolucao; rotulo: string; ajuda: string }[] = [
  { modo: "tudo", rotulo: "Devolver tudo", ajuda: "A cliente recebe de volta o que pagou." },
  { modo: "parte", rotulo: "Devolver parte", ajuda: "Você informa quanto volta." },
  { modo: "nada", rotulo: "Não devolver", ajuda: "A Manto retém o que recebeu." },
];

/** `dd/mm` a partir de um ISO, sem passar por `Date` (horário de parede de São Paulo). */
function ddMm(iso: string | null | undefined): string {
  if (!iso) return "sem data";
  const [, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes ? `${dia}/${mes}` : iso;
}

function Erro({ texto }: { texto?: string }) {
  if (!texto) return null;
  return (
    <p className="mt-1 text-xs text-red" role="alert">
      {texto}
    </p>
  );
}

export interface PedirCancelamentoDialogProps {
  data: EventoDetalhe;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEnviado: () => void;
}

/**
 * "Solicitar cancelamento" do Comercial (feature 315). Quem vende pede, com o motivo, o alcance numa
 * venda de vários dias e a devolução combinada com a cliente; só o Superadmin fecha o pedido
 * (cancelando, excluindo o vazio ou recusando). O diálogo não confere dinheiro: o máximo e o mínimo
 * da devolução são do cancelar, na hora de cancelar. O número de dias e o dia que receberia a venda
 * vêm prontos do servidor (`escolha_do_alcance`) — a tela não calcula.
 */
export function PedirCancelamentoDialog({ data, open, onOpenChange, onEnviado }: PedirCancelamentoDialogProps) {
  const event = data.event;
  const pedir = usePedirCancelamento(event.id);
  const [motivo, setMotivo] = useState("");
  const [alcance, setAlcance] = useState<AlcanceCancelamento | null>(null);
  const [modo, setModo] = useState<ModoDevolucao | null>(null);
  const [valor, setValor] = useState(0);
  const [nome, setNome] = useState("");
  const [pix, setPix] = useState("");
  const [vendaNova, setVendaNova] = useState(0);
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erro, setErro] = useState("");

  const virtual = event.event_type === "VIRTUAL";
  const satelite = event.is_satellite;
  const escolha = event.escolha_do_alcance ?? null;
  const umDiaSo = satelite || alcance === "so_este_dia";
  const modos = umDiaSo ? MODOS.filter((m) => m.modo !== "tudo") : MODOS;
  const recebe = modo === "tudo" || modo === "parte";
  const venda = data.cobranca?.valor ?? data.venda?.sale_value ?? null;
  const recebido = data.cobranca?.recebido ?? null;

  const completo =
    motivo.trim() !== "" &&
    (!escolha || alcance !== null) &&
    (virtual ||
      (modo !== null &&
        (modo !== "parte" || valor > 0) &&
        (!recebe || (nome.trim() !== "" && pix.trim() !== "")) &&
        (!umDiaSo || vendaNova > 0)));

  function limpar() {
    setMotivo("");
    setAlcance(null);
    setModo(null);
    setValor(0);
    setNome("");
    setPix("");
    setVendaNova(0);
    setErros({});
    setErro("");
  }

  function fechar(aberto: boolean) {
    if (!aberto) limpar();
    onOpenChange(aberto);
  }

  function enviar() {
    setErros({});
    setErro("");
    const corpo: PedidoCancelamentoInput = { motivo: motivo.trim() };
    if (escolha && alcance) corpo.alcance = alcance;
    if (!virtual && modo) {
      corpo.devolucao = { modo };
      if (modo === "parte") corpo.devolucao.valor = valor;
      if (recebe) {
        corpo.devolucao.nome = nome.trim();
        corpo.devolucao.pix = pix.trim();
      }
      if (umDiaSo) corpo.venda_nova = vendaNova;
    }
    pedir.mutate(corpo, {
      onSuccess: () => {
        fechar(false);
        onEnviado();
      },
      onError: (e) => {
        if (e instanceof ApiRequestError && e.fields) setErros(e.fields);
        setErro(e.message);
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={fechar}>
      <DialogContent open={open} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Solicitar cancelamento</DialogTitle>
        </DialogHeader>
        <div className="max-h-[65vh] space-y-3 overflow-y-auto pr-1">
          <p className="text-sm text-ink">“{event.title}”</p>

          <div>
            <label className={LABEL} htmlFor="pedido-motivo">
              Motivo
            </label>
            <textarea
              id="pedido-motivo"
              rows={3}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="O que a cliente pediu e o que foi combinado com ela"
              aria-invalid={Boolean(erros.motivo)}
              className="w-full rounded-md border border-line bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue"
            />
            <Erro texto={erros.motivo} />
          </div>

          {escolha && (
            <fieldset className="rounded-md border border-line p-3">
              <legend className="px-1 text-xs font-semibold uppercase text-muted">O que cancelar</legend>
              <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="O que cancelar">
                {(
                  [
                    ["todos", `Todos os ${escolha.dias} dias`, "A venda inteira."],
                    [
                      "so_este_dia",
                      "Só este dia",
                      escolha.proximo
                        ? `A venda passa para o dia ${ddMm(escolha.proximo.start_at)}.`
                        : "A venda segue nos outros dias.",
                    ],
                  ] as const
                ).map(([valorAlcance, rotulo, ajuda]) => (
                  <label
                    key={valorAlcance}
                    className={`flex min-h-11 cursor-pointer items-start gap-2 rounded-md border p-2 text-sm ${
                      alcance === valorAlcance ? "border-blue bg-blue-soft" : "border-line"
                    }`}
                  >
                    <input
                      type="radio"
                      name="pedido-alcance"
                      className="mt-1"
                      checked={alcance === valorAlcance}
                      onChange={() => {
                        setAlcance(valorAlcance);
                        // "Tudo" não vale num dia só.
                        if (valorAlcance === "so_este_dia" && modo === "tudo") setModo(null);
                      }}
                    />
                    <span>
                      <span className="block font-semibold text-ink">{rotulo}</span>
                      <span className="block text-xs text-muted">{ajuda}</span>
                    </span>
                  </label>
                ))}
              </div>
              <Erro texto={erros.alcance} />
            </fieldset>
          )}
          {satelite && (
            <p className="text-sm text-muted">Este é um dos dias da venda: o pedido vale só para ele.</p>
          )}

          {virtual ? (
            <p className="text-sm text-muted">Venda virtual: basta o motivo.</p>
          ) : (
            <fieldset className="rounded-md border border-line p-3">
              <legend className="px-1 text-xs font-semibold uppercase text-muted">
                Devolução combinada com a cliente
              </legend>
              <div
                className={`grid gap-2 ${umDiaSo ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}
                role="radiogroup"
                aria-label="Quanto devolver"
              >
                {modos.map((m) => (
                  <label
                    key={m.modo}
                    className={`flex min-h-11 cursor-pointer items-start gap-2 rounded-md border p-2 text-sm ${
                      modo === m.modo ? "border-blue bg-blue-soft" : "border-line"
                    }`}
                  >
                    <input
                      type="radio"
                      name="pedido-modo"
                      className="mt-1"
                      checked={modo === m.modo}
                      onChange={() => setModo(m.modo)}
                    />
                    <span>
                      <span className="block font-semibold text-ink">{m.rotulo}</span>
                      <span className="block text-xs text-muted">{m.ajuda}</span>
                    </span>
                  </label>
                ))}
              </div>
              <Erro texto={erros.devolucao_modo} />

              {recebe && (
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  {modo === "parte" && (
                    <div>
                      <label className={LABEL} htmlFor="pedido-valor">
                        Valor a devolver
                      </label>
                      <MoneyInput
                        id="pedido-valor"
                        className={FIELD}
                        value={valor}
                        onValueChange={setValor}
                        aria-invalid={Boolean(erros.devolucao_valor)}
                      />
                      <Erro texto={erros.devolucao_valor} />
                    </div>
                  )}
                  <div>
                    <label className={LABEL} htmlFor="pedido-nome">
                      Quem recebe
                    </label>
                    <Input
                      id="pedido-nome"
                      value={nome}
                      maxLength={200}
                      onChange={(e) => setNome(e.target.value)}
                      aria-invalid={Boolean(erros.devolucao_nome)}
                    />
                    <Erro texto={erros.devolucao_nome} />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor="pedido-pix">
                      PIX
                    </label>
                    <Input
                      id="pedido-pix"
                      value={pix}
                      maxLength={120}
                      onChange={(e) => setPix(e.target.value)}
                      aria-invalid={Boolean(erros.devolucao_pix)}
                    />
                    <Erro texto={erros.devolucao_pix} />
                  </div>
                </div>
              )}

              {umDiaSo && (
                <div className="mt-3 sm:w-1/2">
                  <label className={LABEL} htmlFor="pedido-venda-nova">
                    Novo valor da venda
                  </label>
                  <MoneyInput
                    id="pedido-venda-nova"
                    className={FIELD}
                    value={vendaNova}
                    onValueChange={setVendaNova}
                    aria-invalid={Boolean(erros.venda_nova)}
                  />
                  <p className="mt-1 text-xs text-muted">O que a venda passa a valer sem este dia.</p>
                  <Erro texto={erros.venda_nova} />
                </div>
              )}
            </fieldset>
          )}

          <div className="rounded-md border border-line bg-surface-2 p-3 text-sm text-ink">
            <p className="font-semibold">O que está em jogo</p>
            {(venda !== null || recebido !== null) && (
              <p className="mt-1">
                {venda !== null && <>Venda R$ {formatBRL(venda)}</>}
                {venda !== null && recebido !== null && " · "}
                {recebido !== null && <>recebido R$ {formatBRL(recebido)}</>}
              </p>
            )}
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-muted">
              <li>Quem estiver escalado recebe o aviso do cancelamento por e-mail.</li>
              <li>A multa ao elenco, se houver, é decidida pelo Superadmin.</li>
              <li>O Casting tira da escala e avisa cada artista.</li>
              <li>O ensaio do evento é cancelado junto.</li>
            </ul>
          </div>
          <p className="text-sm text-muted">Depois de enviado, só o Superadmin fecha o pedido.</p>

          {erro && (
            <p className="text-sm text-red" role="alert">
              {erro}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => fechar(false)}>
            Voltar
          </Button>
          <Button size="sm" loading={pedir.isPending} disabled={!completo} onClick={enviar}>
            Enviar pedido
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

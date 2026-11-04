import { useDeferredValue, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { ApiRequestError } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Skeleton,
} from "@manto/ui";
import {
  mensagemDoErro,
  novaChaveDeEnvio,
  precisaEscolherFicha,
  useConversas,
  useEnviarOrcamento,
  type ConversaResumo,
  type EnvioDoOrcamentoResposta,
  type EscolhaDaFicha,
} from "../../lib/conversas";
import { useOrcamentoHistorico, type OrcamentoHistoricoEntry } from "../../lib/orcamento";
import { EscolhaDeFicha, erroDaFicha, type ErroDaFicha } from "./EscolhaDeFicha";
import { IconeDoCanal } from "./IconeDoCanal";

/**
 * O orçamento pela conversa (feature 333): a mensagem pronta e, em seguida, o PDF, pelo envio da conversa.
 * Duas portas (decisão do dono): dentro da conversa ("Enviar orçamento", escolhendo entre os recentes) e na
 * tela do orçamento ("Enviar na conversa", escolhendo a conversa). As duas terminam no `EnvioDoOrcamento`.
 *
 * A chave de envio é da tentativa (nasce quando o envio abre): o clique repetido refaz o mesmo pedido e o
 * servidor não manda nada de novo.
 */

/** Os orçamentos recentes: os últimos 30 dias do time, no máximo 50 (spec, premissas). */
const DIAS_DOS_RECENTES = 30;
const LIMITE_DOS_RECENTES = 50;

export interface OrcamentoParaEnvio {
  id: number;
  cliente: string;
  /** Já no formato da tela (dd/mm/aaaa). */
  data: string;
  local: string;
  totais: { rotulo: string; valor: number }[];
  /** A ficha a que o orçamento já foi ligado (num envio anterior), ou `null`. */
  ficha: { id: number; nome: string } | null;
}

function dataDaTela(iso: string): string {
  const [ano, mes, dia] = (iso || "").slice(0, 10).split("-");
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : "";
}

export function orcamentoDoHistorico(e: OrcamentoHistoricoEntry): OrcamentoParaEnvio {
  return {
    id: e.id,
    cliente: e.client_name,
    data: dataDaTela(e.event_date),
    local: e.event_location,
    totais: [
      { rotulo: "1 h", valor: e.total_1h },
      { rotulo: "2 h", valor: e.total_2h },
      { rotulo: "3 h", valor: e.total_3h },
      { rotulo: "4 h", valor: e.total_4h },
    ].filter((t) => t.valor > 0),
    ficha: e.cliente ?? null,
  };
}

function ResumoDoOrcamento({ orcamento }: { orcamento: OrcamentoParaEnvio }) {
  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 rounded-md border border-line p-3 text-sm">
      <dt className="text-muted">Cliente</dt>
      <dd className="truncate">{orcamento.cliente || "—"}</dd>
      <dt className="text-muted">Data</dt>
      <dd>{orcamento.data || "—"}</dd>
      <dt className="text-muted">Local</dt>
      <dd className="break-words">{orcamento.local || "—"}</dd>
      <dt className="text-muted">Valores</dt>
      <dd>{orcamento.totais.map((t) => `${t.rotulo} R$ ${formatBRL(t.valor)}`).join(" · ") || "—"}</dd>
    </dl>
  );
}

function contatoDaConversa(conversa: ConversaResumo): string {
  if (conversa.canal === "instagram") return conversa.usuario ? `@${conversa.usuario}` : "Instagram";
  return conversa.telefone_legivel ?? conversa.telefone ?? "";
}

interface EnvioDoOrcamentoProps {
  conversa: ConversaResumo;
  orcamento: OrcamentoParaEnvio;
  onEnviado: () => void;
  onVoltar?: () => void;
}

/** A conferência e o envio: para quem, o resumo, a ficha (quando falta) e "Enviar orçamento". */
export function EnvioDoOrcamento({ conversa, orcamento, onEnviado, onVoltar }: EnvioDoOrcamentoProps) {
  const enviar = useEnviarOrcamento();
  const [chave] = useState(novaChaveDeEnvio);
  const [chaveDoPdf, setChaveDoPdf] = useState(novaChaveDeEnvio);
  const [escolha, setEscolha] = useState<EscolhaDaFicha | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [erroFicha, setErroFicha] = useState<ErroDaFicha | null>(null);
  const [naoEntregue, setNaoEntregue] = useState<string | null>(null);
  const escolherFicha = precisaEscolherFicha(conversa);
  // O orçamento que já é de outra ficha continua com ela (FR-006) e não batiza a ficha desta conversa.
  const deOutraFicha = Boolean(orcamento.ficha && orcamento.ficha.id !== conversa.cliente?.id);

  /** A confirmação só diz "enviado" se tudo saiu (XV); a parte recusada pela Meta vira aviso. */
  const conferirResposta = (resposta: EnvioDoOrcamentoResposta) => {
    const recusadas = resposta.mensagens.filter((m) => m.situacao === "falhou");
    if (recusadas.length === 0) {
      onEnviado();
      return;
    }
    const pdf = recusadas.find((m) => m.tipo === "documento");
    setNaoEntregue(
      pdf
        ? `O PDF não foi entregue${pdf.erro?.motivo ? ` (${pdf.erro.motivo.replace(/\.$/, "")})` : ""}. Use "Enviar só o PDF" para tentar novamente.`
        : "Parte da mensagem não foi entregue. Use \"Tentar novamente\" na conversa.",
    );
  };

  /**
   * O envio inteiro, ou só o PDF (o reenvio do que a Meta recusou). Os dois levam a ficha escolhida: sem
   * ela, o servidor recusa na conversa que não tem ficha. "Só o PDF" é um pedido novo a cada tentativa.
   */
  const pedir = (somentePdf: boolean) => {
    if (escolherFicha && !escolha) {
      setErroFicha({ campo: "cliente", mensagem: "Selecione a ficha da cliente ou informe nome e telefone." });
      return;
    }
    setErro(null);
    setErroFicha(null);
    setNaoEntregue(null);
    enviar.mutate(
      {
        conversaId: conversa.id,
        orcamento_id: orcamento.id,
        chave_envio: somentePdf ? chaveDoPdf : chave,
        cliente: escolherFicha && escolha ? escolha : undefined,
        somente_pdf: somentePdf || undefined,
      },
      {
        onSuccess: conferirResposta,
        onError: mostrarErro,
        onSettled: () => {
          if (somentePdf) setChaveDoPdf(novaChaveDeEnvio());
        },
      },
    );
  };

  function mostrarErro(falha: unknown) {
    const fields = falha instanceof ApiRequestError ? falha.fields : undefined;
    const daFicha = erroDaFicha(fields);
    // Sem a escolha na tela (a conversa mudou nesse meio-tempo), o erro da ficha vai para o aviso geral.
    if (daFicha && escolherFicha) setErroFicha(daFicha);
    else setErro(daFicha?.mensagem ?? fields?.orcamento ?? mensagemDoErro(falha, "Não foi possível enviar o orçamento. Tente novamente."));
  }

  return (
    <div className="space-y-3">
      <p className="flex min-w-0 items-center gap-1.5 text-sm">
        <span className="text-muted">Para:</span>
        <IconeDoCanal canal={conversa.canal} />
        <strong className="truncate">{conversa.nome}</strong>
        <span className="truncate text-muted">{contatoDaConversa(conversa)}</span>
      </p>
      <ResumoDoOrcamento orcamento={orcamento} />
      <p className="text-sm text-muted">Saem a mensagem pronta do orçamento e, em seguida, o PDF.</p>
      {deOutraFicha && orcamento.ficha ? (
        <p className="text-sm">
          Este orçamento já é da ficha de <strong>{orcamento.ficha.nome}</strong>: o envio fica registrado e ele
          continua com essa ficha.
        </p>
      ) : conversa.cliente ? (
        <p className="text-sm">
          O orçamento fica ligado à ficha de <strong>{conversa.cliente.nome}</strong>.
        </p>
      ) : null}
      {conversa.cliente ? null : escolherFicha ? (
        <EscolhaDeFicha
          id={`envio-ficha-${conversa.id}`}
          valor={escolha}
          onMudar={(v) => {
            setEscolha(v);
            setErroFicha(null);
          }}
          telefoneInicial={conversa.canal === "instagram" ? null : (conversa.telefone_legivel ?? conversa.telefone)}
          nomeInicial={orcamento.ficha ? conversa.nome_perfil : orcamento.cliente || conversa.nome_perfil}
          erro={erroFicha}
        />
      ) : (
        <p className="text-sm text-muted">
          Esta conversa ainda não tem ficha: ela é ligada à ficha deste telefone ou ganha uma nova.
        </p>
      )}
      {naoEntregue ? (
        <p role="alert" className="rounded-md bg-gold-50 px-3 py-2 text-sm text-gold-ink">
          {naoEntregue}
        </p>
      ) : null}
      {erro ? (
        <p role="alert" className="text-sm text-red">
          {erro}
        </p>
      ) : null}
      <DialogFooter className="flex-wrap gap-2">
        {onVoltar ? (
          <Button type="button" variant="outline" onClick={onVoltar} disabled={enviar.isPending}>
            Voltar
          </Button>
        ) : null}
        <Button type="button" variant="outline" onClick={() => pedir(true)} disabled={enviar.isPending}>
          Enviar só o PDF
        </Button>
        <Button type="button" onClick={() => pedir(false)} loading={enviar.isPending}>
          {enviar.isPending ? "Enviando…" : "Enviar orçamento"}
        </Button>
      </DialogFooter>
    </div>
  );
}

function BuscaDaLista({
  id,
  valor,
  onMudar,
  placeholder,
}: {
  id: string;
  valor: string;
  onMudar: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="relative">
      <label htmlFor={id} className="sr-only">
        {placeholder}
      </label>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
      <Input id={id} value={valor} onChange={(e) => onMudar(e.target.value)} placeholder={placeholder} className="pl-9" />
    </div>
  );
}

function trintaDiasAtras(): string {
  const d = new Date(Date.now() - DIAS_DOS_RECENTES * 24 * 60 * 60 * 1000);
  return d.toISOString().slice(0, 10);
}

function OrcamentosRecentes({ onEscolher }: { onEscolher: (o: OrcamentoParaEnvio) => void }) {
  const [busca, setBusca] = useState("");
  const termo = useDeferredValue(busca.trim());
  const historico = useOrcamentoHistorico({ q: termo, date_from: trintaDiasAtras() });
  const itens = (historico.data?.entries ?? []).slice(0, LIMITE_DOS_RECENTES);
  return (
    <div className="space-y-2">
      <BuscaDaLista
        id="busca-orcamento"
        valor={busca}
        onMudar={setBusca}
        placeholder="Buscar pelo nome da cliente ou pelo local"
      />
      {historico.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : historico.isError ? (
        <div className="space-y-2">
          <p role="alert" className="text-sm text-red">
            Não foi possível carregar os orçamentos. Tente novamente.
          </p>
          <Button type="button" variant="outline" loading={historico.isFetching} onClick={() => void historico.refetch()}>
            Tentar novamente
          </Button>
        </div>
      ) : itens.length === 0 ? (
        <p className="text-sm text-muted">Nenhum orçamento encontrado nos últimos 30 dias.</p>
      ) : (
        <ul className="max-h-72 divide-y divide-line overflow-y-auto rounded-md border border-line">
          {itens.map((e) => (
            <li key={e.id}>
              <button
                type="button"
                className="flex min-h-11 w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-none"
                onClick={() => onEscolher(orcamentoDoHistorico(e))}
              >
                <span className="text-sm font-medium">{e.client_name || "Sem nome"}</span>
                <span className="text-xs text-muted">
                  {[dataDaTela(e.event_date), e.event_location, e.user_name].filter(Boolean).join(" · ")}
                </span>
                {e.enviado_em ? <span className="text-xs text-muted">Enviado na conversa</span> : null}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted">Orçamento mais antigo: abra pelo histórico e use "Enviar na conversa".</p>
    </div>
  );
}

/** Dentro da conversa: escolher um dos orçamentos recentes e enviar. */
export function EnviarOrcamentoDialog({
  conversa,
  open,
  onOpenChange,
}: {
  conversa: ConversaResumo;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [escolhido, setEscolhido] = useState<OrcamentoParaEnvio | null>(null);
  useEffect(() => {
    if (!open) setEscolhido(null);
  }, [open]);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Enviar orçamento</DialogTitle>
          <DialogDescription>
            {escolhido ? "Confira o orçamento antes de enviar." : "Escolha um dos orçamentos recentes do time."}
          </DialogDescription>
        </DialogHeader>
        {!open ? null : escolhido ? (
          <EnvioDoOrcamento
            key={escolhido.id}
            conversa={conversa}
            orcamento={escolhido}
            onEnviado={() => onOpenChange(false)}
            onVoltar={() => setEscolhido(null)}
          />
        ) : (
          <OrcamentosRecentes onEscolher={setEscolhido} />
        )}
      </DialogContent>
    </Dialog>
  );
}

function ConversasParaEscolher({ onEscolher }: { onEscolher: (c: ConversaResumo) => void }) {
  const [busca, setBusca] = useState("");
  const termo = useDeferredValue(busca.trim());
  const lista = useConversas(termo);
  const conversas = lista.data?.conversas ?? [];
  return (
    <div className="space-y-2">
      <BuscaDaLista
        id="busca-conversa"
        valor={busca}
        onMudar={setBusca}
        placeholder="Buscar pelo nome, telefone ou @usuário"
      />
      {lista.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : lista.isError ? (
        <div className="space-y-2">
          <p role="alert" className="text-sm text-red">
            Não foi possível carregar as conversas. Tente novamente.
          </p>
          <Button type="button" variant="outline" loading={lista.isFetching} onClick={() => void lista.refetch()}>
            Tentar novamente
          </Button>
        </div>
      ) : conversas.length === 0 ? (
        <p className="text-sm text-muted">Nenhuma conversa encontrada.</p>
      ) : (
        <ul className="max-h-72 divide-y divide-line overflow-y-auto rounded-md border border-line">
          {conversas.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className="flex min-h-11 w-full items-center gap-2 px-3 py-2 text-left hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-none"
                onClick={() => onEscolher(c)}
              >
                <IconeDoCanal canal={c.canal} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{c.nome}</span>
                  <span className="block truncate text-xs text-muted">{contatoDaConversa(c)}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Na tela do orçamento: escolher a conversa e enviar. Depois, "Abrir conversa". */
export function EnviarNaConversaDialog({
  orcamento,
  open,
  onOpenChange,
}: {
  orcamento: OrcamentoParaEnvio;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [escolhida, setEscolhida] = useState<ConversaResumo | null>(null);
  const [enviadaPara, setEnviadaPara] = useState<ConversaResumo | null>(null);
  useEffect(() => {
    if (!open) {
      setEscolhida(null);
      setEnviadaPara(null);
    }
  }, [open]);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Enviar na conversa</DialogTitle>
          <DialogDescription>
            {enviadaPara
              ? `Orçamento enviado para ${enviadaPara.nome}.`
              : escolhida
                ? "Confira antes de enviar."
                : "Escolha a conversa da cliente."}
          </DialogDescription>
        </DialogHeader>
        {!open ? null : enviadaPara ? (
          <DialogFooter className="flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Fechar
            </Button>
            <Button asChild>
              <Link to={`/conversas?c=${enviadaPara.id}`}>Abrir conversa</Link>
            </Button>
          </DialogFooter>
        ) : escolhida ? (
          <EnvioDoOrcamento
            key={escolhida.id}
            conversa={escolhida}
            orcamento={orcamento}
            onEnviado={() => setEnviadaPara(escolhida)}
            onVoltar={() => setEscolhida(null)}
          />
        ) : (
          <ConversasParaEscolher onEscolher={setEscolhida} />
        )}
      </DialogContent>
    </Dialog>
  );
}

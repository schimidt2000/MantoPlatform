import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { CalendarPlus } from "lucide-react";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Skeleton,
} from "@manto/ui";
import {
  duracaoCurta,
  mensagemDoErro,
  quandoDoLembrete,
  useCancelarLembrete,
  useDecidirQualificacao,
  useLembrarAmanha,
  useReabrirConversa,
  useVendaDaConversa,
  type ConversaResumo,
  type Venda,
} from "../../lib/conversas";
import { KebabMenu } from "../KebabMenu";
import { PerdidaDialog } from "./PerdidaDialog";

/**
 * A venda na conversa aberta (feature 349): a faixa sob o responsável.
 *
 * Mostra a etapa (régua do funil), a qualificação (decisão da vendedora ou pontuação por regras, com os sinais), a
 * perda com o motivo, o tempo da primeira resposta — a resposta pelo celular aparece "sem autor", nunca escondida —,
 * o orçamento parado e o lembrete. Ações: "Criar evento" (com o orçamento, a ficha e quem atende) e o menu com
 * "Lembrar amanhã", "Qualificação…" e "Marcar como perdida"/"Reabrir conversa". Se o painel falha, a conversa
 * continua lendo e respondendo.
 */

interface PainelDaVendaProps {
  conversa: ConversaResumo;
  usuarioId: number | null;
  /** Sem ficha, "Criar evento" abre o "Ligar à ficha" primeiro. */
  onPedirFicha: () => void;
}

function textoDaPrimeiraResposta(venda: Venda): string | null {
  const pr = venda.primeira_resposta;
  if (pr.minutos === null) return pr.recebida_em ? "Sem resposta ainda" : null;
  const tempo = `1ª resposta em ${duracaoCurta(pr.minutos)}`;
  if (pr.origem === "celular") return `${tempo}, pelo celular (sem autor)`;
  if (pr.origem === "outro") return `${tempo}, por outro app (sem autor)`;
  return pr.autor ? `${tempo}, por ${pr.autor.nome}` : tempo;
}

function linhaDeBaixo(venda: Venda, usuarioId: number | null): string {
  const partes: string[] = [];
  // A frase da perda (obrigatória no "Outro") fica visível: no celular não existe o `title` do selo.
  if (venda.perda?.frase) partes.push(`“${venda.perda.frase}”`);
  const resposta = textoDaPrimeiraResposta(venda);
  if (resposta) partes.push(resposta);
  if (venda.parado) {
    partes.push(`Orçamento sem retorno há ${venda.parado.dias} ${venda.parado.dias === 1 ? "dia" : "dias"}`);
  }
  if (venda.lembrete?.em) {
    const para = venda.lembrete.para && venda.lembrete.para.id !== usuarioId ? ` para ${venda.lembrete.para.nome}` : "";
    partes.push(`Lembrete ${quandoDoLembrete(venda.lembrete.em)}${para}`);
  }
  return partes.join(" · ");
}

function QualificacaoDialog({
  conversaId,
  venda,
  open,
  onOpenChange,
}: {
  conversaId: number;
  venda: Venda;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const decidir = useDecidirQualificacao(conversaId);
  const [erro, setErro] = useState<string | null>(null);
  const q = venda.qualificacao;
  const escolher = (decisao: "qualificada" | "nao_qualificada" | null) => {
    setErro(null);
    decidir.mutate(
      { decisao },
      {
        onSuccess: () => onOpenChange(false),
        onError: (falha) => setErro(mensagemDoErro(falha, "Não foi possível salvar a qualificação. Tente novamente.")),
      },
    );
  };
  const situacao =
    q.pela === "decisao"
      ? `Decisão de ${q.decidida_por?.nome ?? "alguém da equipe"}: ${q.qualificada ? "qualificada" : "não qualificada"}. A regra fica de lado até usar a regra de novo.`
      : `Pela regra: ${q.qualificada ? "qualificada" : "não qualificada"}. A decisão da equipe vale sobre a regra.`;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-md">
        <DialogHeader>
          <DialogTitle>Qualificação</DialogTitle>
          <DialogDescription>{situacao}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <p className="text-sm font-medium text-ink">
            Pontuação: {q.pontos} {q.pontos === 1 ? "ponto" : "pontos"} (qualifica com {q.corte})
          </p>
          {q.sinais.length ? (
            <ul className="space-y-1 text-sm">
              {q.sinais.map((s) => (
                <li key={s.chave} className="flex justify-between gap-3">
                  <span>{s.rotulo}</span>
                  <span className="shrink-0 tabular-nums text-muted">+{s.pontos}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">Nenhum sinal ainda: sem orçamento, data, formulário nem evento anterior.</p>
          )}
          {erro ? (
            <p role="alert" className="text-sm text-red">
              {erro}
            </p>
          ) : null}
        </div>
        <DialogFooter className="flex-wrap gap-2">
          {q.decisao ? (
            <Button type="button" variant="ghost" disabled={decidir.isPending} onClick={() => escolher(null)}>
              Usar a regra
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            disabled={decidir.isPending || q.decisao === "nao_qualificada"}
            onClick={() => escolher("nao_qualificada")}
          >
            Não qualificada
          </Button>
          <Button
            type="button"
            loading={decidir.isPending && decidir.variables?.decisao === "qualificada"}
            disabled={q.decisao === "qualificada"}
            onClick={() => escolher("qualificada")}
          >
            Qualificada
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PainelDaVenda({ conversa, usuarioId, onPedirFicha }: PainelDaVendaProps) {
  const reduzir = useReducedMotion();
  const navigate = useNavigate();
  const consulta = useVendaDaConversa(conversa.id);
  const lembrar = useLembrarAmanha(conversa.id);
  const cancelar = useCancelarLembrete(conversa.id);
  const reabrir = useReabrirConversa(conversa.id);
  const [perdaAberta, setPerdaAberta] = useState(false);
  const [qualificacaoAberta, setQualificacaoAberta] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const venda = consulta.data;

  if (consulta.isLoading) {
    return (
      <div className="border-b border-line bg-panel px-3 py-2">
        <Skeleton className="h-6 w-2/3" />
      </div>
    );
  }
  if (consulta.isError || !venda) {
    return (
      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-panel px-3 py-1.5 text-xs">
        <p role="alert" className="text-red">
          Não foi possível carregar a venda. Tente novamente.
        </p>
        <Button type="button" size="sm" variant="outline" className="h-11 md:h-8" loading={consulta.isFetching} onClick={() => void consulta.refetch()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  const falhou = (texto: string) => (falha: unknown) => setErro(mensagemDoErro(falha, texto));
  const criarEvento = () => {
    if (!conversa.cliente) {
      onPedirFicha();
      return;
    }
    const params = new URLSearchParams({ conversa: String(conversa.id) });
    if (venda.fechamento.orcamento_id) params.set("orcamento_id", String(venda.fechamento.orcamento_id));
    navigate(`/events/new?${params.toString()}`);
  };
  const itens = [
    venda.lembrete?.em
      ? {
          label: "Cancelar lembrete",
          onClick: () => cancelar.mutate(undefined, { onError: falhou("Não foi possível cancelar o lembrete. Tente novamente.") }),
        }
      : {
          label: "Lembrar amanhã",
          onClick: () => lembrar.mutate(undefined, { onError: falhou("Não foi possível marcar o lembrete. Tente novamente.") }),
          disabled: Boolean(venda.perda),
          title: venda.perda ? "Reabra a conversa para marcar um lembrete." : undefined,
        },
    { label: "Qualificação…", onClick: () => setQualificacaoAberta(true) },
    venda.perda
      ? {
          label: "Reabrir conversa",
          onClick: () => reabrir.mutate(undefined, { onError: falhou("Não foi possível reabrir a conversa. Tente novamente.") }),
        }
      : { label: "Marcar como perdida", onClick: () => setPerdaAberta(true), destructive: true },
  ];
  const q = venda.qualificacao;
  const detalhe = linhaDeBaixo(venda, usuarioId);

  return (
    <motion.div
      className="border-b border-line bg-panel px-3 py-1.5"
      initial={reduzir ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.18 }}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
          <Badge tone={venda.etapa.chave === "chegou" ? "neutral" : "accent"}>{venda.etapa.rotulo}</Badge>
          {venda.anuncio ? <Badge tone="blue">Anúncio</Badge> : null}
          {venda.perda ? (
            <Badge tone="red">
              <span title={venda.perda.frase ?? undefined}>Perdida: {venda.perda.rotulo}</span>
            </Badge>
          ) : (
            <button
              type="button"
              onClick={() => setQualificacaoAberta(true)}
              className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`Qualificação: ${q.qualificada ? "qualificada" : "não qualificada"}, ${q.pontos} pontos. Ver detalhes`}
            >
              <Badge tone={q.qualificada ? "gold" : "neutral"}>
                {q.qualificada ? "Qualificada" : "Não qualificada"} · {q.pontos} pts
              </Badge>
            </button>
          )}
        </div>
        <Button type="button" size="sm" className="h-11 md:h-8" onClick={criarEvento}>
          <CalendarPlus className="h-4 w-4" aria-hidden />
          Criar evento
        </Button>
        <KebabMenu items={itens} label="Mais ações da venda" grande />
      </div>
      {detalhe ? <p className="mt-1 text-xs text-muted">{detalhe}</p> : null}
      {erro ? (
        <p role="alert" className="mt-1 text-xs text-red">
          {erro}
        </p>
      ) : null}
      <PerdidaDialog
        conversaId={conversa.id}
        nome={conversa.nome}
        motivos={venda.motivos_de_perda}
        open={perdaAberta}
        onClose={() => setPerdaAberta(false)}
      />
      <QualificacaoDialog
        conversaId={conversa.id}
        venda={venda}
        open={qualificacaoAberta}
        onOpenChange={setQualificacaoAberta}
      />
    </motion.div>
  );
}

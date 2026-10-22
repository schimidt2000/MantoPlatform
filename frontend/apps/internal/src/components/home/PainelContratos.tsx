import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, ConfirmDialog, MetricBadge, formatShortDate } from "@manto/ui";
import { copyToClipboard } from "../../lib/clipboard";
import {
  prazoCurto,
  useCobrarContrato,
  useDescartarContrato,
  useLigarContrato,
  type ContratoAConferir,
  type ContratosResumo,
  type LinhaContrato,
} from "../../lib/contratos";
import { buildCobrancaContratoMsg } from "../../lib/eventDetail";
import { mensagemDaApi } from "../../lib/formulariosAdmin";
import { SEVERIDADE_TOM, distanciaDaData } from "../../lib/homeListas";
import { formatDateTime } from "../EventDetail/parts";
import { AvisoDeFalha, GrupoDeLinhas } from "./GrupoDeLinhas";
import { LinhaDaHome } from "./LinhaDaHome";

const CANAL = { whatsapp: "WhatsApp", email: "e-mail", sms: "SMS" } as Record<string, string>;

/** Uma venda com contrato a cobrar, vencido, sem contrato ou já passada. */
function LinhaDoContrato({ linha, podeCobrar }: { linha: LinhaContrato; podeCobrar: boolean }) {
  const cobrar = useCobrarContrato(linha.event_id);
  const [aviso, setAviso] = useState("");
  const cobravel = podeCobrar && linha.situacao === "aguardando" && linha.documento_id && linha.mensagem;

  const aoCobrar = async () => {
    if (!linha.mensagem || !linha.documento_id) return;
    const copiou = await copyToClipboard(
      buildCobrancaContratoMsg(linha.mensagem, linha.canal, prazoCurto(linha.prazo)),
    );
    if (!copiou) {
      setAviso("Não foi possível copiar.");
      return;
    }
    cobrar.mutate(linha.documento_id, {
      onSuccess: () => setAviso("Mensagem copiada. Cobrança registrada."),
      onError: () => setAviso("Mensagem copiada, mas a cobrança não foi registrada."),
    });
  };

  return (
    <LinhaDaHome
      severidade={linha.severidade}
      cabecalho={
        <>
          <span className="min-w-0 break-words">{linha.cliente ?? linha.titulo}</span>
          <span className="font-normal text-muted tabular-nums">evento {formatShortDate(linha.data_evento)}</span>
          <MetricBadge tone={SEVERIDADE_TOM[linha.severidade]} size="xs">
            {linha.selo}
          </MetricBadge>
        </>
      }
      detalhe={
        <>
          <span className="block">
            {linha.rotulo}
            {linha.canal && linha.situacao === "aguardando" && ` · enviado por ${CANAL[linha.canal] ?? linha.canal}`}
            {linha.dias_ate_o_evento >= 0 &&
              ` · ${distanciaDaData(linha.dias_ate_o_evento, { passado: "aconteceu" })}`}
          </span>
          {linha.ultima_cobranca && (
            <span className="block">
              Cobrado por {linha.ultima_cobranca.por} em {formatDateTime(linha.ultima_cobranca.em)}
            </span>
          )}
          {aviso && (
            <span aria-live="polite" className="block text-green">
              {aviso}
            </span>
          )}
        </>
      }
      acoes={
        <div className="flex flex-wrap gap-1.5">
          {cobravel && (
            <Button type="button" size="sm" loading={cobrar.isPending} onClick={aoCobrar}>
              Cobrar contrato
            </Button>
          )}
          <Button asChild variant="outline" size="sm">
            <Link to={`/events/${linha.event_id}?aba=comercial`}>Abrir evento</Link>
          </Button>
        </div>
      }
    />
  );
}

/** Um contrato que o sistema não ligou sozinho: ligar à sugestão ou descartar. */
function LinhaAConferir({ item, podeConferir }: { item: ContratoAConferir; podeConferir: boolean }) {
  const ligar = useLigarContrato();
  const descartar = useDescartarContrato();
  const [descartando, setDescartando] = useState(false);
  const erro = ligar.isError
    ? mensagemDaApi(ligar.error, "Não foi possível ligar.")
    : null;

  return (
    <LinhaDaHome
      severidade="amarelo"
      cabecalho={
        <>
          <span className="min-w-0 break-words">{item.nome}</span>
          {item.data_lida && (
            <span className="font-normal text-muted tabular-nums">evento {formatShortDate(item.data_lida)}</span>
          )}
        </>
      }
      detalhe={
        <>
          {item.motivo_texto && <span className="block">{item.motivo_texto}</span>}
          {item.sugestoes.length === 0 && <span className="block">Nenhuma venda parecida na agenda.</span>}
          {erro && (
            <span role="alert" className="block text-red">
              {erro}
            </span>
          )}
        </>
      }
      acoes={
        podeConferir ? (
          <div className="flex flex-wrap gap-1.5">
            {item.sugestoes.slice(0, 2).map((sugestao) => (
              <Button
                key={sugestao.event_id}
                type="button"
                size="sm"
                variant={sugestao.mesmo_telefone ? "default" : "outline"}
                loading={ligar.isPending && ligar.variables?.eventId === sugestao.event_id}
                onClick={() => ligar.mutate({ documentoId: item.documento_id, eventId: sugestao.event_id })}
                title={sugestao.titulo}
              >
                É de {sugestao.cliente ?? "evento"}
                {sugestao.data_evento ? ` (${formatShortDate(sugestao.data_evento)})` : ""}
              </Button>
            ))}
            <Button type="button" size="sm" variant="ghost" onClick={() => setDescartando(true)}>
              Não é de nenhuma venda
            </Button>
            <ConfirmDialog
              open={descartando}
              title="Este contrato não é de nenhuma venda?"
              description="Ele sai da lista para sempre. Se for engano, é possível ligar pela página do evento."
              confirmLabel="Não é de nenhuma venda"
              pending={descartar.isPending}
              error={descartar.isError ? mensagemDaApi(descartar.error, "Não foi possível descartar.") : null}
              onConfirm={() => descartar.mutate(item.documento_id, { onSuccess: () => setDescartando(false) })}
              onOpenChange={(aberto) => {
                if (!aberto) {
                  setDescartando(false);
                  descartar.reset();
                }
              }}
            />
          </div>
        ) : null
      }
    />
  );
}

/**
 * Corpo do painel "Contratos" da Home (feature 317): quem precisa ser cobrado, o que venceu, as
 * vendas sem contrato nos próximos 30 dias, os contratos a conferir e, recolhidas, as festas que já
 * aconteceram sem contrato assinado. Ordem e cores vêm prontas do servidor.
 *
 * `contratos === null` é o bloco que falhou (aviso, nunca o "✓").
 */
export function PainelContratos({
  contratos,
  onTentarDeNovo,
  tentando,
}: {
  contratos: ContratosResumo | null;
  onTentarDeNovo: () => void;
  tentando: boolean;
}) {
  if (contratos === null) {
    return (
      <AvisoDeFalha
        texto="Não foi possível carregar os contratos."
        onTentarDeNovo={onTentarDeNovo}
        tentando={tentando}
      />
    );
  }
  if (!contratos.integracao_ligada) {
    return <p className="py-2 text-sm text-muted">Integração com a ClickSign desligada.</p>;
  }
  const { para_cobrar, vencidos, sem_contrato, a_conferir, ja_aconteceu, pode_cobrar } = contratos;
  const vazio = para_cobrar.length + vencidos.length + sem_contrato.length + a_conferir.length === 0;
  return (
    <div className="space-y-2">
      {vazio && <p className="py-2 text-sm text-muted">Nenhum contrato pendente ✓</p>}
      {para_cobrar.length > 0 && (
        <GrupoDeLinhas titulo="Para cobrar" itens={para_cobrar} chave={(l) => l.event_id}>
          {(linha) => <LinhaDoContrato linha={linha} podeCobrar={pode_cobrar} />}
        </GrupoDeLinhas>
      )}
      {vencidos.length > 0 && (
        <GrupoDeLinhas titulo="Venceu ou foi recusado" itens={vencidos} chave={(l) => l.event_id}>
          {(linha) => <LinhaDoContrato linha={linha} podeCobrar={false} />}
        </GrupoDeLinhas>
      )}
      {sem_contrato.length > 0 && (
        <GrupoDeLinhas titulo="Venda sem contrato" itens={sem_contrato} chave={(l) => l.event_id}>
          {(linha) => <LinhaDoContrato linha={linha} podeCobrar={false} />}
        </GrupoDeLinhas>
      )}
      {a_conferir.length > 0 && (
        <GrupoDeLinhas titulo="A conferir" itens={a_conferir} chave={(c) => c.documento_id}>
          {(item) => <LinhaAConferir item={item} podeConferir={pode_cobrar} />}
        </GrupoDeLinhas>
      )}
      {ja_aconteceu.length > 0 && (
        <details className="pt-2 text-sm">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-muted">
            Já aconteceu sem contrato assinado ({ja_aconteceu.length})
          </summary>
          <GrupoDeLinhas itens={ja_aconteceu} chave={(l) => l.event_id}>
            {(linha) => <LinhaDoContrato linha={linha} podeCobrar={false} />}
          </GrupoDeLinhas>
        </details>
      )}
    </div>
  );
}

import { Link } from "react-router-dom";
import { Button, MetricBadge, formatShortDate } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { CobrancasResumo, PendingPayment } from "../../lib/types";
import { SEVERIDADE_TOM, diaMes, distanciaDaData } from "../../lib/homeListas";
import { AvisoDeFalha, GrupoDeLinhas } from "./GrupoDeLinhas";
import { LinhaDaHome } from "./LinhaDaHome";

/**
 * Uma cobrança (feature 299): a cliente, a data do evento, o selo do servidor, o vencimento e
 * "Recebido X de Y — falta Z". O grupo é uma venda só: a linha é a do principal.
 *
 * Com o servidor antigo (sem `severidade`/`selo`, na janela de deploy) a linha fica cinza, sem
 * selo, e o resto continua lendo as chaves de sempre.
 */
function LinhaCobranca({ linha }: { linha: PendingPayment }) {
  const severidade = linha.severidade ?? "cinza";
  const vence = diaMes(linha.vencimento ?? linha.due_date);
  const atrasada = (linha.dias_ate_vencimento ?? 0) < 0;

  return (
    <LinhaDaHome
      severidade={severidade}
      cabecalho={
        <>
          <span className="min-w-0 break-words">{linha.cliente ?? linha.titulo ?? linha.event_title}</span>
          {linha.grupo_comercial && (
            <MetricBadge tone="neutral" size="xs">
              grupo de {linha.grupo_comercial.eventos} eventos
            </MetricBadge>
          )}
          {linha.data_evento && (
            <span className="font-normal text-muted tabular-nums">
              evento {formatShortDate(linha.data_evento)}
            </span>
          )}
          {linha.selo && (
            <MetricBadge tone={SEVERIDADE_TOM[severidade]} size="xs">
              {linha.selo}
            </MetricBadge>
          )}
          {linha.nota && <span className="text-xs font-normal text-red">{linha.nota}</span>}
        </>
      }
      detalhe={
        <>
          {vence && (
            <span className="block">
              vence {vence}
              {linha.vencimento_origem === "data_combinada" && " (data combinada)"}
              {atrasada && ` · ${distanciaDaData(linha.dias_ate_vencimento, { passado: "venceu" })}`}
            </span>
          )}
          <span className="block tabular-nums">
            Recebido R$ {formatBRL(linha.received)} de R$ {formatBRL(linha.sale)} — falta R${" "}
            {formatBRL(linha.saldo)}
          </span>
        </>
      }
      acoes={
        <Button asChild variant="outline" size="sm">
          <Link to={`/events/${linha.event_id}?aba=comercial`}>Abrir cobrança</Link>
        </Button>
      }
    />
  );
}

/**
 * Corpo do painel "Cobranças" (feature 299): toda venda com saldo, em ordem de cor e, dentro da
 * cor, pelo vencimento — a ordem vem pronta do servidor.
 *
 * `resumo === null` é a lista que falhou (aviso, nunca o "✓"); `undefined` é o servidor antigo, e
 * aí a lista aparece sem estado de erro.
 */
export function PainelCobrancas({
  linhas,
  resumo,
  onTentarDeNovo,
  tentando,
}: {
  linhas: PendingPayment[];
  resumo: CobrancasResumo | null | undefined;
  onTentarDeNovo: () => void;
  tentando: boolean;
}) {
  if (resumo === null) {
    return (
      <AvisoDeFalha
        texto="Não foi possível carregar as cobranças."
        onTentarDeNovo={onTentarDeNovo}
        tentando={tentando}
      />
    );
  }
  if (linhas.length === 0) {
    return <p className="py-2 text-sm text-muted">Nenhuma cobrança em aberto ✓</p>;
  }
  return (
    <GrupoDeLinhas itens={linhas} chave={(l) => l.event_id}>
      {(linha) => <LinhaCobranca linha={linha} />}
    </GrupoDeLinhas>
  );
}

import { Link } from "react-router-dom";
import { Button, MetricBadge, formatShortDate } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { LinhaSemValor, SemValorSummary } from "../../lib/types";
import { SEVERIDADE_TOM, diaMes, distanciaDaData } from "../../lib/homeListas";
import { AvisoDeFalha, GrupoDeLinhas } from "./GrupoDeLinhas";
import { LinhaDaHome } from "./LinhaDaHome";

/**
 * Uma venda sem valor (feature 299): quem, quando e "Pôr o valor".
 *
 * O valor fica no detalhe, fora do `MetricBadge` (que não quebra linha e estouraria no celular).
 * "Pôr o valor" abre a aba Comercial já em edição (2 cliques, SC-007); quem não edita a venda
 * (FINANCEIRO) vê "Abrir", só para leitura.
 */
function LinhaSemValorRow({ linha, podeEditarVenda }: { linha: LinhaSemValor; podeEditarVenda: boolean }) {
  const distancia = distanciaDaData(linha.dias_ate_o_evento, { passado: "aconteceu" });
  const valor = linha.valor_simbolico
    ? `R$ ${formatBRL(linha.valor ?? 0)} (valor simbólico)`
    : "a definir";
  const recebido = linha.recebido > 0 ? `já recebeu R$ ${formatBRL(linha.recebido)}` : null;
  const destino = podeEditarVenda
    ? `/events/${linha.event_id}?aba=comercial&editar=venda`
    : `/events/${linha.event_id}?aba=comercial`;

  return (
    <LinhaDaHome
      severidade={linha.severidade}
      cabecalho={
        <>
          <span className="min-w-0 break-words">{linha.cliente ?? linha.titulo}</span>
          {linha.data_evento && <span className="tabular-nums">{formatShortDate(linha.data_evento)}</span>}
          {distancia && (
            <MetricBadge tone={SEVERIDADE_TOM[linha.severidade]} size="xs">
              {distancia}
            </MetricBadge>
          )}
          {linha.grupo_comercial && (
            <MetricBadge tone="neutral" size="xs">
              grupo de {linha.grupo_comercial.eventos} eventos
            </MetricBadge>
          )}
        </>
      }
      detalhe={[valor, recebido].filter(Boolean).join(" · ")}
      acoes={
        <Button asChild variant={podeEditarVenda ? "default" : "outline"} size="sm">
          <Link to={destino}>{podeEditarVenda ? "Pôr o valor" : "Abrir"}</Link>
        </Button>
      }
    />
  );
}

/**
 * Corpo do painel "Sem valor" (feature 299): as vendas desde a data de início sem valor de venda,
 * em dois grupos — "ainda vai acontecer" (hoje incluído, o mais próximo primeiro) e "já aconteceu"
 * (o mais recente primeiro). A ordem vem pronta do servidor.
 *
 * `resumo === null` é a lista que falhou: aviso com "Tentar de novo", nunca o "✓".
 */
export function PainelSemValor({
  resumo,
  corte,
  podeEditarVenda,
  onTentarDeNovo,
  tentando,
}: {
  resumo: SemValorSummary | null;
  corte?: string | null;
  podeEditarVenda: boolean;
  onTentarDeNovo: () => void;
  tentando: boolean;
}) {
  if (resumo === null) {
    return (
      <AvisoDeFalha
        texto="Não foi possível carregar os eventos sem valor."
        onTentarDeNovo={onTentarDeNovo}
        tentando={tentando}
      />
    );
  }
  const desde = diaMes(corte);
  const vazio = resumo.a_acontecer.length === 0 && resumo.ja_aconteceu.length === 0;
  const linha = (item: LinhaSemValor) => <LinhaSemValorRow linha={item} podeEditarVenda={podeEditarVenda} />;

  return (
    <>
      {vazio ? (
        <p className="py-2 text-sm text-muted">Todos os eventos têm valor de venda ✓</p>
      ) : (
        <div className="space-y-3">
          {resumo.a_acontecer.length > 0 && (
            <GrupoDeLinhas titulo="Ainda vai acontecer" itens={resumo.a_acontecer} chave={(l) => l.event_id}>
              {linha}
            </GrupoDeLinhas>
          )}
          {resumo.ja_aconteceu.length > 0 && (
            <GrupoDeLinhas titulo="Já aconteceu" itens={resumo.ja_aconteceu} chave={(l) => l.event_id}>
              {linha}
            </GrupoDeLinhas>
          )}
        </div>
      )}
      {desde && <p className="mt-3 text-xs text-muted">Eventos desde {desde}, fora cortesia e compromisso interno.</p>}
    </>
  );
}

import { formatBRL } from "@manto/money";
import type { AcrescimosDoOrcamento } from "../../lib/eventCreate";

const LABEL = "mb-1 block text-[11px] font-bold uppercase tracking-wider text-muted";
const FIELD = "h-11 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink";
const FIELD_ERRO = "h-11 w-full rounded-md border border-red bg-panel px-3 text-sm text-ink";

export interface BvDoOrcamentoBlockProps {
  acrescimos: AcrescimosDoOrcamento | undefined;
  /** "1".."4" ou as horas da duração extra. */
  duracao: string;
  /** A duração extra gravada no orçamento (o prefill traz `custom` só para ela). */
  duracaoCustom: number | null | undefined;
  /** O total que a tela mostrou para a duração — só para COMPARAR com a venda, nunca para contar. */
  totalDaDuracao: number | null;
  venda: number | null;
  cortesia: boolean;
  aDefinir: boolean;
  recebedor: string;
  pix: string;
  onRecebedor: (v: string) => void;
  onPix: (v: string) => void;
  erros: { bv_recipient?: string; bv_pix?: string };
}

/** O BV do orçamento vai nascer com esta criação? (o servidor decide de verdade; isto é a tela) */
export function bvVaiNascerNaTela(props: Pick<BvDoOrcamentoBlockProps, "acrescimos" | "cortesia" | "aDefinir" | "venda">): boolean {
  const temBv = Boolean(props.acrescimos?.linhas.some((l) => l.is_bv));
  return temBv && !props.acrescimos?.personalizado && !props.cortesia && !props.aDefinir && (props.venda ?? 0) >= 1;
}

/**
 * Quadro do BV do orçamento no Novo evento (feature 305, F1).
 *
 * Mostra o BV CHEIO que o orçamento somou ao preço na duração escolhida (valor do servidor) e, quando
 * ele vai nascer, os dois campos obrigatórios — o dono: "é de extrema importância que, ao colocar na
 * agenda um evento com BV, seja obrigatório colocar o PIX de quem receberá o BV". Venda diferente do
 * total: o BV acompanha na mesma proporção, "calculado ao salvar" — nenhuma conta de dinheiro aqui.
 */
export function BvDoOrcamentoBlock(props: BvDoOrcamentoBlockProps) {
  const { acrescimos, duracao, duracaoCustom } = props;
  if (!acrescimos) return null;
  const bv = acrescimos.linhas.find((l) => l.is_bv);
  if (acrescimos.personalizado) {
    return (
      <p className="rounded-md border border-line p-3 text-sm text-muted">
        Orçamento personalizado: o BV não foi somado ao preço. Se houver repasse, lance em Acréscimos
        na aba Comercial, com quem recebe e o PIX.
      </p>
    );
  }
  if (!bv) return null;

  const chave = ["1", "2", "3", "4"].includes(duracao) ? (duracao as "1" | "2" | "3" | "4") : null;
  const cheio = chave
    ? bv.valores_brl[chave]
    : duracaoCustom != null && String(duracaoCustom) === duracao
      ? bv.valores_brl.custom
      : null;
  const semVenda = props.cortesia || props.aDefinir || (props.venda ?? 0) < 1;
  const proporcional =
    !semVenda && props.totalDaDuracao != null && props.venda != null && Math.abs(props.venda - props.totalDaDuracao) > 0.01;
  const rotulo = bv.percentual != null ? `${bv.percentual}%` : "em reais";

  return (
    <div className="space-y-3 rounded-md border border-line p-3">
      <p className="text-sm text-ink">
        <strong>BV · {rotulo}</strong>
        {cheio != null ? <> → R$ {formatBRL(cheio)}</> : <> → calculado ao salvar</>}
        {props.totalDaDuracao != null && <> no total de R$ {formatBRL(props.totalDaDuracao)} ({duracao}h)</>}
        {" "}— repasse a quem indicou; não entra na comissão.
      </p>
      {proporcional && (
        <p className="text-sm text-ink">
          O valor de venda é diferente do total do orçamento: o BV acompanha na mesma proporção
          (calculado ao salvar). Confira o BV e o valor total com BV.
        </p>
      )}
      {semVenda ? (
        <p className="text-sm text-muted">
          Sem valor de venda, o BV não entra agora: quando o valor for digitado, a aba Comercial vai
          pedir que o BV seja lançado em Acréscimos.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL} htmlFor="bv_recipient">
              Quem recebe o BV *
            </label>
            <input
              id="bv_recipient"
              className={props.erros.bv_recipient ? FIELD_ERRO : FIELD}
              maxLength={200}
              value={props.recebedor}
              aria-invalid={Boolean(props.erros.bv_recipient)}
              onChange={(e) => props.onRecebedor(e.target.value)}
            />
            {props.erros.bv_recipient && <p className="mt-1 text-xs text-red">{props.erros.bv_recipient}</p>}
          </div>
          <div>
            <label className={LABEL} htmlFor="bv_pix">
              PIX de quem recebe *
            </label>
            <input
              id="bv_pix"
              className={props.erros.bv_pix ? FIELD_ERRO : FIELD}
              maxLength={140}
              value={props.pix}
              aria-invalid={Boolean(props.erros.bv_pix)}
              onChange={(e) => props.onPix(e.target.value)}
            />
            {props.erros.bv_pix && <p className="mt-1 text-xs text-red">{props.erros.bv_pix}</p>}
          </div>
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Button, Card, CardContent, CardHeader, CardTitle, ConfirmDialog } from "@manto/ui";
import { MoneyInput } from "@manto/money";
import {
  diaParaTela,
  type FaixaEspecial,
  type ProdutoDeTabela,
  type ProdutosEstimativa,
  type VagaDoProduto,
} from "../../lib/orcamento";
import { INPUT_PRECOS } from "./PriceTable";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const ROTULO_MAX = 60;
const DESCRICAO_MAX = 120;
const VAGAS_MAX = 10;
const CHAVE_RE = /^[a-z0-9_]{1,30}$/;

const TIPOS: { tipo: VagaDoProduto["tipo"]; rotulo: string }[] = [
  { tipo: "especial", rotulo: "Especial" },
  { tipo: "ator", rotulo: "Ator" },
  { tipo: "coordenador", rotulo: "Coordenador" },
  { tipo: "maquiador", rotulo: "Maquiador" },
];
/** O servidor força estes labels (o 273 e o coordenador automático casam por nome). */
const LABEL_FIXO: Partial<Record<VagaDoProduto["tipo"], string>> = {
  coordenador: "Coordenador",
  maquiador: "Maquiador",
};

function produtoNovo(): ProdutoDeTabela {
  return {
    rotulo: "",
    descricao: "",
    ativo: true,
    preco: 0,
    por_faixa: {},
    vagas: [{ label: "Coordenador", tipo: "coordenador", cache: null, needs_makeup: false }],
    inclui_noturno: true,
  };
}

/** Rótulo legível de um campo (`preco`, `vagas.2.label`, `por_faixa.natal.preco`) na lista de erros. */
function rotuloDoCampo(campo: string, faixas: Record<string, FaixaEspecial>): string {
  if (campo === "preco") return "Preço";
  if (campo === "produto") return "Produto";
  if (campo === "rotulo") return "Rótulo";
  if (campo === "descricao") return "Descrição";
  if (campo === "vagas") return "Vagas";
  const vaga = /^vagas\.(\d+)\.(\w+)$/.exec(campo);
  if (vaga) return `Vaga ${Number(vaga[1]) + 1} — ${vaga[2] === "cache" ? "cachê" : vaga[2]}`;
  const faixa = /^por_faixa\.([^.]+)/.exec(campo);
  if (faixa) return `Preço em ${faixas[faixa[1]]?.rotulo ?? faixa[1]}`;
  return campo;
}

/**
 * Feature 309 — card "Produtos de tabela" da Configuração de Preços (molde do `DatasEspeciaisCard`):
 * o superadmin cadastra o pacote fechado — rótulo, descrição ao cliente, preço fixo por visita, preço
 * em cada data especial (vazio = estimativa marcada na data), a composição de vagas (cachê "pela
 * tabela" ou fixo, maquiagem) e se o noturno já está no preço. `erros` são os `fields` do 400
 * (`produtos.<chave>.<campo>`): o campo errado ganha destaque e o foco (Princípio V); `avisos` são o
 * que o servidor descartou sem recusar (faixa órfã). Remover produto ou vaga passa por
 * `ConfirmDialog`, nunca `window.confirm`.
 */
export function ProdutosConfigCard({
  produtos,
  estimativa,
  faixas,
  especiais,
  erros,
  avisos,
  onChange,
  onEstimativaChange,
}: {
  produtos: Record<string, ProdutoDeTabela>;
  estimativa: ProdutosEstimativa;
  faixas: Record<string, FaixaEspecial>;
  especiais: string[];
  erros: Record<string, string>;
  avisos: string[];
  onChange: (produtos: Record<string, ProdutoDeTabela>) => void;
  onEstimativaChange: (estimativa: ProdutosEstimativa) => void;
}) {
  const raiz = useRef<HTMLDivElement>(null);
  const [novaChave, setNovaChave] = useState("");
  const [erroChaveLocal, setErroChaveLocal] = useState<string | null>(null);
  const [remocao, setRemocao] = useState<{ chave: string; vaga?: number } | null>(null);

  // O primeiro campo inválido recebe o foco quando o servidor recusa (não basta mostrar texto).
  useEffect(() => {
    raiz.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
  }, [erros]);

  const setProduto = (chave: string, patch: Partial<ProdutoDeTabela>) =>
    onChange({ ...produtos, [chave]: { ...produtos[chave], ...patch } });
  const setVaga = (chave: string, i: number, patch: Partial<VagaDoProduto>) =>
    setProduto(chave, {
      vagas: produtos[chave].vagas.map((v, idx) => (idx === i ? { ...v, ...patch } : v)),
    });

  const adicionarProduto = () => {
    const chave = novaChave.trim().toLowerCase();
    if (!CHAVE_RE.test(chave)) {
      setErroChaveLocal("chave inválida — só letras minúsculas, números e _ (até 30)");
      return;
    }
    if (chave in produtos) {
      setErroChaveLocal(`"${chave}" já existe`);
      return;
    }
    setErroChaveLocal(null);
    onChange({ ...produtos, [chave]: produtoNovo() });
    setNovaChave("");
  };

  const confirmarRemocao = () => {
    if (!remocao) return;
    if (remocao.vaga == null) {
      const { [remocao.chave]: _removido, ...rest } = produtos;
      onChange(rest);
    } else {
      setProduto(remocao.chave, {
        vagas: produtos[remocao.chave].vagas.filter((_, i) => i !== remocao.vaga),
      });
    }
    setRemocao(null);
  };

  const erroEstimativa = (campo: keyof ProdutosEstimativa) => erros[`produtos_estimativa.${campo}`];
  const classeDe = (invalido: boolean) => `${INPUT_PRECOS}${invalido ? " border-red ring-1 ring-red" : ""}`;

  return (
    <Card ref={raiz} className="xl:col-span-2">
      <CardHeader>
        <CardTitle>Produtos de tabela</CardTitle>
        <p className="text-xs text-muted">
          Pacote fechado vendido pelo preço da tabela (fixo por visita, fora do markup). Os cachês das
          vagas são os da tabela de preços na data do evento — é o que vira o teto das vagas quando o
          orçamento vira evento. Produto inativo some da calculadora, mas orçamentos antigos continuam
          recalculando.
        </p>
      </CardHeader>
      <CardContent className="space-y-4 p-3">
        {avisos.length > 0 && (
          <ul className="rounded-md border border-gold/40 bg-gold-soft p-3 text-xs text-ink" role="status">
            {avisos.map((a) => (
              <li key={a}>⚠️ {a}</li>
            ))}
          </ul>
        )}
        {erros.produtos && (
          <p className="text-xs text-red" role="alert">
            {erros.produtos}
          </p>
        )}

        {Object.entries(produtos).map(([chave, produto]) => {
          const erro = (campo: string) => erros[`produtos.${chave}.${campo}`];
          // Inclui a chave exata `produtos.<chave>` ("produto inválido"), além dos campos.
          const errosDoProduto = Object.entries(erros)
            .filter(([k]) => k === `produtos.${chave}` || k.startsWith(`produtos.${chave}.`))
            .map(([k, msg]) => [k === `produtos.${chave}` ? "produto" : k.replace(`produtos.${chave}.`, ""), msg] as const);
          return (
            <div key={chave} className="space-y-3 rounded-md border border-line p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex-1">
                  <label className={LABEL}>
                    Rótulo <span className="font-normal">(chave: {chave})</span>
                  </label>
                  <input
                    className={classeDe(!!erro("rotulo"))}
                    aria-invalid={erro("rotulo") ? true : undefined}
                    maxLength={ROTULO_MAX}
                    value={produto.rotulo}
                    onChange={(e) => setProduto(chave, { rotulo: e.target.value })}
                  />
                </div>
                <div className="flex items-center gap-3 pt-5">
                  <label className="flex items-center gap-1.5 text-xs text-ink">
                    <input
                      type="checkbox"
                      checked={produto.ativo}
                      onChange={(e) => setProduto(chave, { ativo: e.target.checked })}
                    />
                    Ativo
                  </label>
                  <Button size="sm" variant="ghost" onClick={() => setRemocao({ chave })}>
                    Remover produto
                  </Button>
                </div>
              </div>

              <div>
                <label className={LABEL}>Descrição ao cliente (vai na mensagem e no PDF, até {DESCRICAO_MAX})</label>
                <input
                  className={classeDe(!!erro("descricao"))}
                  aria-invalid={erro("descricao") ? true : undefined}
                  maxLength={DESCRICAO_MAX}
                  value={produto.descricao}
                  onChange={(e) => setProduto(chave, { descricao: e.target.value })}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label className={LABEL}>Preço por visita</label>
                  <MoneyInput
                    className={classeDe(!!erro("preco"))}
                    aria-invalid={erro("preco") ? true : undefined}
                    value={produto.preco}
                    onValueChange={(v) => setProduto(chave, { preco: v })}
                  />
                </div>
                {Object.entries(faixas).map(([faixaChave, faixa]) => {
                  const campo = `por_faixa.${faixaChave}.preco`;
                  const preco = produto.por_faixa[faixaChave]?.preco ?? 0;
                  return (
                    <div key={faixaChave}>
                      <label className={LABEL}>
                        Preço em {faixa.rotulo} ({faixa.dias.map(diaParaTela).join(", ")})
                      </label>
                      <MoneyInput
                        className={classeDe(!!erro(campo))}
                        aria-invalid={erro(campo) ? true : undefined}
                        value={preco}
                        onValueChange={(v) => {
                          // Zero = sem preço na faixa: a calculadora ESTIMA e marca o orçamento.
                          const { [faixaChave]: _semUso, ...rest } = produto.por_faixa;
                          setProduto(chave, {
                            por_faixa: v > 0 ? { ...produto.por_faixa, [faixaChave]: { preco: v } } : rest,
                          });
                        }}
                      />
                      {preco <= 0 && (
                        <p className="mt-1 text-xs text-muted">vazio = estimativa na data (cachês × fator × markup)</p>
                      )}
                    </div>
                  );
                })}
              </div>

              <div>
                <label className={LABEL}>Vagas (composição) — o cachê "pela tabela" é resolvido na data do evento</label>
                <div className="space-y-2">
                  {produto.vagas.map((vaga, i) => {
                    const fixo = LABEL_FIXO[vaga.tipo];
                    const semTabela =
                      vaga.tipo === "especial" && vaga.label.trim() && !especiais.includes(vaga.label.trim());
                    return (
                      <div
                        key={i}
                        className="flex flex-wrap items-center gap-2 rounded-md bg-surface-2 p-2 text-xs"
                      >
                        <div className="flex gap-1">
                          {TIPOS.map((t) => (
                            <Button
                              key={t.tipo}
                              size="sm"
                              variant={vaga.tipo === t.tipo ? "default" : "outline"}
                              onClick={() =>
                                setVaga(chave, i, {
                                  tipo: t.tipo,
                                  label: LABEL_FIXO[t.tipo] ?? (fixo ? "" : vaga.label),
                                  needs_makeup: t.tipo === "especial" || t.tipo === "ator" ? vaga.needs_makeup : false,
                                })
                              }
                            >
                              {t.rotulo}
                            </Button>
                          ))}
                        </div>
                        <input
                          className={`${classeDe(!!erro(`vagas.${i}.label`))} w-44`}
                          aria-invalid={erro(`vagas.${i}.label`) ? true : undefined}
                          aria-label={`Personagem da vaga ${i + 1}`}
                          placeholder={vaga.tipo === "especial" ? "Nome do especial" : "Nome do personagem"}
                          value={vaga.label}
                          disabled={!!fixo}
                          onChange={(e) => setVaga(chave, i, { label: e.target.value })}
                        />
                        <label className="flex items-center gap-1 text-ink">
                          <input
                            type="checkbox"
                            checked={vaga.cache == null}
                            onChange={(e) => setVaga(chave, i, { cache: e.target.checked ? null : 0 })}
                          />
                          cachê pela tabela
                        </label>
                        {vaga.cache != null && (
                          <MoneyInput
                            className={`${classeDe(!!erro(`vagas.${i}.cache`))} w-28`}
                            aria-invalid={erro(`vagas.${i}.cache`) ? true : undefined}
                            aria-label={`Cachê fixo da vaga ${i + 1}`}
                            value={vaga.cache}
                            onValueChange={(v) => setVaga(chave, i, { cache: v })}
                          />
                        )}
                        {(vaga.tipo === "especial" || vaga.tipo === "ator") && (
                          <label className="flex items-center gap-1 text-ink">
                            <input
                              type="checkbox"
                              checked={vaga.needs_makeup}
                              onChange={(e) => setVaga(chave, i, { needs_makeup: e.target.checked })}
                            />
                            maquiagem
                          </label>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Remover vaga ${i + 1}`}
                          onClick={() => setRemocao({ chave, vaga: i })}
                        >
                          ×
                        </Button>
                        {semTabela && (
                          <p className="w-full text-gold-ink">
                            ⚠️ "{vaga.label.trim()}" não está na tabela de especiais — a vaga nasce sem teto.
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="mt-2"
                  disabled={produto.vagas.length >= VAGAS_MAX}
                  onClick={() =>
                    setProduto(chave, {
                      vagas: [...produto.vagas, { label: "", tipo: "especial", cache: null, needs_makeup: false }],
                    })
                  }
                >
                  + Vaga
                </Button>
              </div>

              <label className="flex items-center gap-2 text-xs text-ink">
                <input
                  type="checkbox"
                  checked={produto.inclui_noturno}
                  onChange={(e) => setProduto(chave, { inclui_noturno: e.target.checked })}
                />
                Noturno embutido no preço (não soma R$ 50 por pessoa do produto a partir das 19h)
              </label>

              {errosDoProduto.length > 0 && (
                <ul className="text-xs text-red" role="alert">
                  {errosDoProduto.map(([campo, msg]) => (
                    <li key={campo}>
                      {rotuloDoCampo(campo, faixas)}: {msg}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}

        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className={LABEL}>Novo produto (chave interna, ex.: visita_magica_duende)</label>
            <input
              className={`${INPUT_PRECOS} w-64${erroChaveLocal ? " border-red ring-1 ring-red" : ""}`}
              aria-invalid={erroChaveLocal ? true : undefined}
              placeholder="chave_do_produto"
              value={novaChave}
              onChange={(e) => {
                setNovaChave(e.target.value);
                setErroChaveLocal(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") adicionarProduto();
              }}
            />
            {erroChaveLocal && <p className="mt-1 text-xs text-red">{erroChaveLocal}</p>}
          </div>
          <Button size="sm" variant="outline" onClick={adicionarProduto}>
            Adicionar produto
          </Button>
        </div>

        <div className="rounded-md border border-line p-3">
          <p className="mb-2 text-xs font-semibold text-ink">Estimativa (produto sem preço numa data especial)</p>
          {erros.produtos_estimativa && (
            <p className="mb-2 text-xs text-red" role="alert">
              {erros.produtos_estimativa}
            </p>
          )}
          <p className="mb-2 text-xs text-muted">
            Preço estimado = Σ cachês das vagas na data × fator × markup. O orçamento sai marcado
            "estimativa" para a vendedora conferir.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className={LABEL}>Fator sobre os cachês</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                className={classeDe(!!erroEstimativa("fator_cache"))}
                aria-invalid={erroEstimativa("fator_cache") ? true : undefined}
                value={estimativa.fator_cache}
                onChange={(e) => onEstimativaChange({ ...estimativa, fator_cache: Number(e.target.value) })}
              />
              {erroEstimativa("fator_cache") && (
                <p className="mt-1 text-xs text-red">{erroEstimativa("fator_cache")}</p>
              )}
            </div>
            <div>
              <label className={LABEL}>Markup (coeficiente, entre 1 e 6)</label>
              <input
                type="number"
                step="0.01"
                min="1"
                max="6"
                className={classeDe(!!erroEstimativa("markup"))}
                aria-invalid={erroEstimativa("markup") ? true : undefined}
                value={estimativa.markup}
                onChange={(e) => onEstimativaChange({ ...estimativa, markup: Number(e.target.value) })}
              />
              {erroEstimativa("markup") && <p className="mt-1 text-xs text-red">{erroEstimativa("markup")}</p>}
            </div>
          </div>
        </div>
      </CardContent>

      <ConfirmDialog
        open={remocao != null}
        title={remocao?.vaga == null ? "Remover produto" : "Remover vaga"}
        description={
          remocao?.vaga == null
            ? `Remover "${remocao ? (produtos[remocao.chave]?.rotulo || remocao.chave) : ""}" da tabela? Orçamentos já salvos com ele continuam, mas um evento criado depois nasce com as vagas sem teto. Vale ao clicar em "Salvar configurações".`
            : `Remover a vaga ${remocao ? remocao.vaga + 1 : ""} (${
                remocao ? produtos[remocao.chave]?.vagas[remocao.vaga]?.label || "sem nome" : ""
              }) deste produto? Vale ao clicar em "Salvar configurações".`
        }
        confirmLabel="Remover"
        destructive
        pending={false}
        onConfirm={confirmarRemocao}
        onOpenChange={(aberto) => {
          if (!aberto) setRemocao(null);
        }}
      />
    </Card>
  );
}

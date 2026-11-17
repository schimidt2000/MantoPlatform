import { useEffect, useState } from "react";
import {
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Input,
  type ComboboxOption,
} from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { MoneyInput, formatBRL } from "@manto/money";
import {
  useFrentesConfig,
  useMarketingOptions,
  useSalvarFrentes,
  type MarketingAssigneeRef,
} from "../../lib/marketing";

function usuarioOptions(usuarios: MarketingAssigneeRef[]): ComboboxOption[] {
  return usuarios.map((u) => ({
    value: String(u.id),
    label: u.name,
    imageUrl: assetUrl(u.photo_url) ?? null,
    imageShape: "circle" as const,
  }));
}

const CAMPO_DINHEIRO =
  "h-10 w-full rounded-md border border-line bg-panel px-2 text-right text-sm text-ink tabular-nums";

/** Valores editados por frente: `null` = vazio (teto volta ao padrão; meta e verba ficam sem número). */
type PorFrente = Record<string, number | null>;

function dinheiro(valores: PorFrente): Record<string, string | null> {
  return Object.fromEntries(Object.entries(valores).map(([slug, v]) => [slug, v == null ? null : v.toFixed(2)]));
}

/**
 * Teto, meta e verba de cada frente e quem recebe os pedidos de criativo (features 345 e 351).
 *
 * Só o Superadmin salva (o servidor recusa os outros). Teto em branco = volta ao padrão calculado, que
 * aparece embaixo com a base do cálculo. Meta e verba são o padrão do mês: o calendário do ano vence mês a
 * mês. Em 390 px os três campos de cada frente ficam numa linha, com o rótulo em cima.
 */
export function FrentesConfigDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const config = useFrentesConfig(open);
  const opcoes = useMarketingOptions(open);
  const salvar = useSalvarFrentes();
  const [tetos, setTetos] = useState<PorFrente>({});
  const [metas, setMetas] = useState<PorFrente>({});
  const [verbas, setVerbas] = useState<PorFrente>({});
  const [foto, setFoto] = useState<string | null>(null);
  const [video, setVideo] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);

  useEffect(() => {
    if (!config.data) return;
    const frentes = config.data.frentes;
    setTetos(Object.fromEntries(frentes.map((f) => [f.slug, f.teto_editado && f.teto ? Number(f.teto) : null])));
    setMetas(Object.fromEntries(frentes.map((f) => [f.slug, f.meta_vendas_mes ?? null])));
    setVerbas(Object.fromEntries(frentes.map((f) => [f.slug, f.verba_mes ? Number(f.verba_mes) : null])));
    setFoto(config.data.responsaveis.foto ? String(config.data.responsaveis.foto.id) : null);
    setVideo(config.data.responsaveis.video ? String(config.data.responsaveis.video.id) : null);
  }, [config.data]);

  const campos = salvar.error instanceof ApiRequestError ? salvar.error.fields ?? {} : {};
  const erro = salvar.error instanceof ApiRequestError ? salvar.error.message : salvar.error ? "Não foi possível salvar. Tente novamente." : null;

  function enviar() {
    setSalvo(false);
    salvar.mutate(
      {
        tetos: dinheiro(tetos),
        metas,
        verbas: dinheiro(verbas),
        resp_foto_id: foto ? Number(foto) : null,
        resp_video_id: video ? Number(video) : null,
      },
      { onSuccess: () => setSalvo(true) },
    );
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Metas, verba e tetos</DialogTitle>
          <DialogDescription>
            Meta e verba valem para todo mês; o calendário do ano muda mês a mês. O teto é o máximo que vale pagar em
            anúncio por venda fechada — em branco, 25% da margem mediana do último ano.
          </DialogDescription>
        </DialogHeader>

        {config.isLoading && <p className="text-sm text-muted">Carregando…</p>}
        {config.isError && (
          <p className="text-sm text-red" role="alert">
            Não foi possível carregar as frentes. Tente novamente.
          </p>
        )}

        {config.data && (
          <div className="space-y-4">
            <div className="divide-y divide-line">
              {config.data.frentes.map((f) => (
                <fieldset key={f.slug} className="space-y-1.5 py-3 first:pt-0">
                  <legend className="text-sm font-semibold text-ink">{f.nome}</legend>
                  <div className="grid grid-cols-3 gap-2">
                    <label className="block text-[11px] font-medium text-muted">
                      Meta/mês
                      <Input
                        type="number"
                        inputMode="numeric"
                        min={0}
                        placeholder="vendas"
                        aria-label={`Meta de vendas por mês — ${f.nome}`}
                        className="mt-0.5 h-10 text-right tabular-nums"
                        value={metas[f.slug] ?? ""}
                        aria-invalid={Boolean(campos[`metas.${f.slug}`])}
                        onChange={(e) =>
                          setMetas((m) => ({ ...m, [f.slug]: e.target.value === "" ? null : Number(e.target.value) }))
                        }
                      />
                    </label>
                    <label className="block text-[11px] font-medium text-muted">
                      Verba/mês (R$)
                      <MoneyInput
                        className={`mt-0.5 ${CAMPO_DINHEIRO}`}
                        value={verbas[f.slug] ?? 0}
                        onValueChange={(v) => setVerbas((t) => ({ ...t, [f.slug]: v > 0 ? v : null }))}
                      />
                    </label>
                    <label className="block text-[11px] font-medium text-muted">
                      Teto/venda (R$)
                      <MoneyInput
                        className={`mt-0.5 ${CAMPO_DINHEIRO}`}
                        value={tetos[f.slug] ?? 0}
                        onValueChange={(v) => setTetos((t) => ({ ...t, [f.slug]: v > 0 ? v : null }))}
                      />
                    </label>
                  </div>
                  {[`metas.${f.slug}`, `verbas.${f.slug}`, `tetos.${f.slug}`].map(
                    (chave) =>
                      campos[chave] && (
                        <p key={chave} className="text-xs text-red" role="alert">
                          {campos[chave]}
                        </p>
                      ),
                  )}
                  <p className="text-[11px] text-muted">
                    Teto padrão: {f.teto_padrao ? `R$ ${formatBRL(Number(f.teto_padrao))}` : "—"} · {f.base_teto}
                  </p>
                </fieldset>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <span className="mb-1 block text-sm font-medium text-ink">Pedidos de foto e arte</span>
                <Combobox
                  aria-label="Responsável por foto e arte"
                  placeholder="Escolher pessoa…"
                  options={usuarioOptions(opcoes.data?.usuarios ?? [])}
                  loading={opcoes.isLoading}
                  value={foto}
                  clearable
                  onChange={(next) => setFoto(next)}
                />
              </div>
              <div>
                <span className="mb-1 block text-sm font-medium text-ink">Pedidos de vídeo</span>
                <Combobox
                  aria-label="Responsável por vídeo"
                  placeholder="Escolher pessoa…"
                  options={usuarioOptions(opcoes.data?.usuarios ?? [])}
                  loading={opcoes.isLoading}
                  value={video}
                  clearable
                  onChange={(next) => setVideo(next)}
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
              {erro && (
                <span className="mr-auto text-sm text-red" role="alert">
                  {erro}
                </span>
              )}
              {salvo && !erro && <span className="mr-auto text-sm text-green">Metas, verba e tetos salvos.</span>}
              {!config.data.pode_editar && (
                <span className="mr-auto text-sm text-muted">Só o Superadmin altera metas, verba, tetos e responsáveis.</span>
              )}
              <Button type="button" variant="outline" onClick={onClose}>
                Fechar
              </Button>
              {config.data.pode_editar && (
                <Button type="button" onClick={enviar} disabled={salvar.isPending}>
                  {salvar.isPending ? "Salvando…" : "Salvar"}
                </Button>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

import { useEffect, useState } from "react";
import {
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
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

/**
 * Tetos de custo por venda de cada frente e quem recebe os pedidos de criativo (feature 345).
 *
 * Só o Superadmin abre (o servidor recusa os outros). Teto em branco = volta ao padrão calculado,
 * que aparece embaixo de cada campo com a base do cálculo — o dono vê de onde veio o número.
 */
export function FrentesConfigDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const config = useFrentesConfig(open);
  const opcoes = useMarketingOptions(open);
  const salvar = useSalvarFrentes();
  // `null` = "usar o padrão"; número = teto editado.
  const [tetos, setTetos] = useState<Record<string, number | null>>({});
  const [foto, setFoto] = useState<string | null>(null);
  const [video, setVideo] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);

  useEffect(() => {
    if (!config.data) return;
    setTetos(
      Object.fromEntries(
        config.data.frentes.map((f) => [f.slug, f.teto_editado && f.teto ? Number(f.teto) : null]),
      ),
    );
    setFoto(config.data.responsaveis.foto ? String(config.data.responsaveis.foto.id) : null);
    setVideo(config.data.responsaveis.video ? String(config.data.responsaveis.video.id) : null);
  }, [config.data]);

  const erro = salvar.error instanceof ApiRequestError ? salvar.error.message : salvar.error ? "Não foi possível salvar." : null;

  function enviar() {
    setSalvo(false);
    salvar.mutate(
      {
        tetos: Object.fromEntries(
          Object.entries(tetos).map(([slug, valor]) => [slug, valor == null ? null : valor.toFixed(2)]),
        ),
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
          <DialogTitle>Tetos e responsáveis</DialogTitle>
          <DialogDescription>
            O teto é o máximo que vale pagar em anúncio por venda fechada de cada frente. Em branco, o sistema usa 25% da
            margem mediana do último ano.
          </DialogDescription>
        </DialogHeader>

        {config.isLoading && <p className="text-sm text-muted">Carregando…</p>}

        {config.data && (
          <div className="space-y-4">
            <div className="space-y-3">
              {config.data.frentes.map((f) => (
                <div key={f.slug} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-0.5">
                  <label htmlFor={`teto-${f.slug}`} className="text-sm font-medium text-ink">
                    {f.nome}
                  </label>
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm text-muted">R$</span>
                    <MoneyInput
                      id={`teto-${f.slug}`}
                      className="h-10 w-32 rounded-md border border-line bg-panel px-2 text-right text-sm text-ink tabular-nums"
                      value={tetos[f.slug] ?? 0}
                      onValueChange={(v) => setTetos((t) => ({ ...t, [f.slug]: v > 0 ? v : null }))}
                    />
                  </div>
                  <p className="col-span-2 text-[11px] text-muted">
                    Padrão: {f.teto_padrao ? `R$ ${formatBRL(Number(f.teto_padrao))}` : "—"} · {f.base_teto}
                  </p>
                </div>
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
              {salvo && !erro && <span className="mr-auto text-sm text-green">Salvo.</span>}
              {!config.data.pode_editar && (
                <span className="mr-auto text-sm text-muted">Só o Superadmin altera tetos e responsáveis.</span>
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

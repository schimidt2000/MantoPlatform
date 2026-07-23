import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { API_BASE, ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import {
  useCalcularPacote,
  useDistanciaEducaManto,
  useEducaMantoPackages,
  type PacoteItemRow,
} from "../lib/educamanto";

const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";
const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";

function brl(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `R$ ${formatBRL(v)}`;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiRequestError ? err.message : fallback;
}

function DetailTable({ rows }: { rows: PacoteItemRow[] }) {
  if (rows.length === 0) return null;
  const isMulti = rows.some((r) => r.sell_item !== undefined);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
            <th className="px-3 py-2">Item</th>
            <th className="px-3 py-2 text-right">Qtd</th>
            <th className="px-3 py-2 text-right">Custo total</th>
            <th className="px-3 py-2 text-right">Preço venda</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name} className="border-b border-line last:border-0">
              <td className="px-3 py-2 text-ink">{row.name}</td>
              <td className="px-3 py-2 text-right tabular-nums text-ink">{row.qty}</td>
              <td className="px-3 py-2 text-right tabular-nums text-ink">
                {brl(isMulti ? row.raw_item : row.raw)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums font-medium text-ink">
                {brl(isMulti ? row.sell_item : row.sell)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EducaMantoCalculadoraPage() {
  const reduceMotion = useReducedMotion();
  const packagesQuery = useEducaMantoPackages();
  const distancia = useDistanciaEducaManto();
  const calcular = useCalcularPacote();

  const [packageId, setPackageId] = useState<number | null>(null);
  const [d1, setD1] = useState(0);
  const [d2, setD2] = useState(0);
  const [ensemble, setEnsemble] = useState(0);
  const [acrescimo, setAcrescimo] = useState(0);
  const [endereco, setEndereco] = useState("");
  const [enderecoMsg, setEnderecoMsg] = useState<{ text: string; error: boolean } | null>(null);
  const [kmIda, setKmIda] = useState<number | null>(null);

  const packages = packagesQuery.data?.packages ?? [];

  useEffect(() => {
    if (packageId === null && packages.length > 0) {
      setPackageId(packages[0].id);
    }
  }, [packages, packageId]);

  const totalDias = d1 + d2;

  // Recalcula com debounce a cada mudança relevante — evita um POST por tecla digitada.
  useEffect(() => {
    if (!packageId || totalDias <= 0) return undefined;
    const timer = setTimeout(() => {
      calcular.mutate({
        package_id: packageId,
        d1,
        d2,
        ensemble,
        acrescimo,
        transporte: kmIda && kmIda > 0 ? { km_ida: kmIda } : undefined,
      });
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [packageId, d1, d2, ensemble, acrescimo, kmIda]);

  function handleCalcularDistancia() {
    if (!endereco.trim()) {
      setEnderecoMsg({ text: "Informe o endereço primeiro.", error: true });
      return;
    }
    setEnderecoMsg({ text: "Calculando…", error: false });
    distancia.mutate(endereco, {
      onSuccess: (data) => {
        setKmIda(data.km_ida);
        setEnderecoMsg({
          text: `Distância: ${data.km_ida} km (ida) · ${data.km_ida * 2} km ida e volta`,
          error: false,
        });
      },
      onError: (err) => {
        setEnderecoMsg({
          text: errorMessage(err, "Não foi possível calcular a distância."),
          error: true,
        });
      },
    });
  }

  function handleLimparTransporte() {
    setEndereco("");
    setKmIda(null);
    setEnderecoMsg(null);
  }

  const resultado = calcular.data;
  const transporte = resultado?.transporte;

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link to="/">‹ Início</Link>
        </Button>
        <a
          href={`${API_BASE}/educamanto/`}
          className="text-sm text-blue hover:underline"
        >
          Gerar PDF, ver histórico ou gerenciar pacotes ›
        </a>
      </div>

      <h1 className="text-2xl font-semibold text-ink">EducaManto — Calculadora</h1>

      {packagesQuery.isLoading && <Skeleton className="h-40 w-full" />}

      {packagesQuery.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os pacotes. Confira se você tem permissão para usar o
          EducaManto.
        </div>
      )}

      {packages.length > 0 && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-4"
        >
          <div className="flex flex-wrap gap-2">
            {packages.map((pkg) => (
              <button
                key={pkg.id}
                type="button"
                onClick={() => setPackageId(pkg.id)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  pkg.id === packageId
                    ? "bg-blue text-white"
                    : "border border-line text-ink hover:bg-surface-2"
                }`}
              >
                {pkg.name}
              </button>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Dias e ensemble</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className={LABEL} htmlFor="d1">
                  Dias — 1 sessão
                </label>
                <input
                  id="d1"
                  type="number"
                  min={0}
                  className={FIELD}
                  value={d1}
                  onChange={(e) => setD1(Math.max(0, Number(e.target.value) || 0))}
                />
              </div>
              <div>
                <label className={LABEL} htmlFor="d2">
                  Dias — 2 sessões
                </label>
                <input
                  id="d2"
                  type="number"
                  min={0}
                  className={FIELD}
                  value={d2}
                  onChange={(e) => setD2(Math.max(0, Number(e.target.value) || 0))}
                />
              </div>
              <div>
                <label className={LABEL} htmlFor="ensemble">
                  Ensemble
                </label>
                <input
                  id="ensemble"
                  type="number"
                  min={0}
                  className={FIELD}
                  value={ensemble}
                  onChange={(e) => setEnsemble(Math.max(0, Number(e.target.value) || 0))}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Transporte (apenas se for fora da cidade de São Paulo)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className={LABEL} htmlFor="endereco">
                  Endereço do evento
                </label>
                <div className="flex gap-2">
                  <input
                    id="endereco"
                    type="text"
                    placeholder="Rua, número, cidade…"
                    className={FIELD}
                    value={endereco}
                    onChange={(e) => setEndereco(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleCalcularDistancia();
                      }
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    loading={distancia.isPending}
                    onClick={handleCalcularDistancia}
                  >
                    Calcular
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={handleLimparTransporte}>
                    Limpar
                  </Button>
                </div>
                {enderecoMsg && (
                  <p className={`mt-1 text-xs ${enderecoMsg.error ? "text-red" : "text-muted"}`}>
                    {enderecoMsg.text}
                  </p>
                )}
              </div>

              {transporte && transporte.total > 0 && (
                <div className="rounded-md bg-surface-2 px-3 py-2 text-sm text-ink">
                  🚐{" "}
                  <strong>
                    Transporte:{" "}
                    {transporte.dias > 1
                      ? `${brl(transporte.valor_viagem)} por viagem × ${transporte.dias} dias = ${brl(transporte.total)}`
                      : `${brl(transporte.total)} (1 viagem)`}
                  </strong>{" "}
                  <span className="text-muted">
                    — {transporte.km_total} km (ida e volta) · {transporte.label} · adicional{" "}
                    {transporte.pessoas} pessoa(s). Já somado ao valor final.
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Acréscimo do vendedor</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-2 text-xs text-muted">
                Valor acrescentado ao orçamento — esta é a sua comissão.
              </p>
              <MoneyInput
                className={`${FIELD} w-40 text-right`}
                value={acrescimo}
                onValueChange={setAcrescimo}
                aria-label="Acréscimo do vendedor"
              />
            </CardContent>
          </Card>

          {totalDias <= 0 && (
            <p className="text-sm text-muted">Preencha os dias para calcular.</p>
          )}

          {calcular.isError && (
            <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
              {errorMessage(calcular.error, "Não foi possível calcular o pacote.")}
            </div>
          )}

          {calcular.isPending && totalDias > 0 && <Skeleton className="h-24 w-full" />}

          {resultado && totalDias > 0 && (
            <>
              <Card>
                <CardContent className="space-y-2 p-4">
                  <p className="text-xs uppercase text-muted">{resultado.scenario}</p>
                  {resultado.desconto_aplicado && (
                    <p className="text-xs text-green">
                      Desconto aplicado (−{brl(resultado.desconto)})
                    </p>
                  )}
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs uppercase text-muted">Valor sem nota</p>
                      <p className="text-xl font-semibold text-ink">
                        {brl(resultado.valor_final_sem_nota)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase text-muted">Valor com nota</p>
                      <p className="text-xl font-semibold text-ink">
                        {brl(resultado.valor_final_com_nota)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Detalhamento</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <DetailTable rows={resultado.item_rows} />
                </CardContent>
              </Card>
            </>
          )}
        </motion.div>
      )}
    </div>
  );
}

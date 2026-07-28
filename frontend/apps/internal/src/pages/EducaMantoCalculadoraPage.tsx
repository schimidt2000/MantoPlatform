import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ApiRequestError } from "@manto/api-client";
import {
  AccordionRow,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { GoogleAddressInput } from "../components/GoogleAddressInput";
import {
  useCalcularPacote,
  useDistanciaEducaManto,
  useEducaMantoPackages,
  useEducaMantoQuoteDetalhe,
  useGerarOrcamento,
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
    <Table>
      <thead>
        <TableRow head>
          <TableCell as="th">Item</TableCell>
          <TableCell as="th" align="right">
            Qtd
          </TableCell>
          <TableCell as="th" align="right">
            Custo total
          </TableCell>
          <TableCell as="th" align="right">
            Preço venda
          </TableCell>
        </TableRow>
      </thead>
      <tbody>
        {rows.map((row) => (
          <TableRow key={row.name}>
            <TableCell className="text-ink">{row.name}</TableCell>
            <TableCell align="right">{row.qty}</TableCell>
            <TableCell align="right">{brl(isMulti ? row.raw_item : row.raw)}</TableCell>
            <TableCell align="right" className="font-medium">
              {brl(isMulti ? row.sell_item : row.sell)}
            </TableCell>
          </TableRow>
        ))}
      </tbody>
    </Table>
  );
}

export function EducaMantoCalculadoraPage() {
  const reduceMotion = useReducedMotion();
  const [searchParams] = useSearchParams();
  const recalcularId = searchParams.get("recalcular_id");
  const recalcularIdNum = recalcularId ? Number(recalcularId) : null;
  const packageIdParam = searchParams.get("package_id");

  const packagesQuery = useEducaMantoPackages();
  const distancia = useDistanciaEducaManto();
  const calcular = useCalcularPacote();
  const gerarOrcamento = useGerarOrcamento();
  const quoteDetalhe = useEducaMantoQuoteDetalhe(recalcularIdNum);

  const [packageId, setPackageId] = useState<number | null>(null);
  const [d1, setD1] = useState(0);
  const [d2, setD2] = useState(0);
  const [ensemble, setEnsemble] = useState(0);
  const [acrescimo, setAcrescimo] = useState(0);
  const [endereco, setEndereco] = useState("");
  const [enderecoMsg, setEnderecoMsg] = useState<{ text: string; error: boolean } | null>(null);
  const [kmIda, setKmIda] = useState<number | null>(null);
  const [clientName, setClientName] = useState("");
  const [gerarMsg, setGerarMsg] = useState<{ text: string; error: boolean } | null>(null);

  const packages = packagesQuery.data?.packages ?? [];

  useEffect(() => {
    if (packageId !== null) return;
    if (packageIdParam && packages.some((p) => p.id === Number(packageIdParam))) {
      setPackageId(Number(packageIdParam));
    } else if (packages.length > 0) {
      setPackageId(packages[0].id);
    }
  }, [packages, packageId, packageIdParam]);

  // "Recalcular" — repopula o formulário a partir do snapshot de um orçamento salvo.
  useEffect(() => {
    const snap = quoteDetalhe.data;
    if (!snap) return;
    setD1(snap.d1);
    setD2(snap.d2);
    setEnsemble(snap.ensemble);
    setAcrescimo(snap.acrescimo);
    setClientName(snap.client_name ?? "");
    setKmIda(snap.transporte?.kmT ?? null);
    setEnderecoMsg(
      snap.transporte?.kmT
        ? { text: `Distância recuperada do orçamento salvo: ${snap.transporte.label}`, error: false }
        : null,
    );
    if (snap.packages[0]) setPackageId(snap.packages[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quoteDetalhe.data]);

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

  /**
   * Calcula o KM pela Distance Matrix. `override` chega quando o usuário escolhe uma sugestão do
   * Google (feature 195): o estado `endereco` ainda não refletiu o novo valor nesse tick, então
   * usamos o texto normalizado direto — sem ele, a primeira consulta iria com o endereço antigo.
   */
  function handleCalcularDistancia(override?: string) {
    const alvo = (override ?? endereco).trim();
    if (!alvo) {
      setEnderecoMsg({ text: "Informe o endereço primeiro.", error: true });
      return;
    }
    setEnderecoMsg({ text: "Calculando…", error: false });
    distancia.mutate(alvo, {
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

  function handleGerarOrcamento() {
    if (!resultado || !selectedPackage) return;
    setGerarMsg({ text: "Gerando…", error: false });
    gerarOrcamento.mutate(
      {
        packages: [
          {
            id: selectedPackage.id,
            name: selectedPackage.name,
            sem_nota: resultado.valor_final_sem_nota,
            com_nota: resultado.valor_final_com_nota,
          },
        ],
        d1,
        d2,
        ensemble,
        acrescimo,
        transporte: transporte
          ? { total: transporte.total, label: transporte.label, kmT: transporte.km_total, pessoas: transporte.pessoas }
          : undefined,
        client_name: clientName,
      },
      {
        onSuccess: () => setGerarMsg({ text: "Orçamento gerado e baixado com sucesso.", error: false }),
        onError: (err) =>
          setGerarMsg({
            text: errorMessage(err, "Não foi possível gerar o orçamento."),
            error: true,
          }),
      },
    );
  }

  const resultado = calcular.data;
  const transporte = resultado?.transporte;
  const selectedPackage = packages.find((p) => p.id === packageId);

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="EducaManto — Calculadora"
        className="mb-0"
        actions={
          <div className="flex flex-wrap gap-3 text-sm">
            {resultado && selectedPackage && (
              <Button size="sm" loading={gerarOrcamento.isPending} onClick={handleGerarOrcamento}>
                Gerar orçamento
              </Button>
            )}
            <Button asChild variant="ghost" size="sm">
              <Link to="/educamanto/historico">Histórico</Link>
            </Button>
            {packageId && (
              <Button asChild variant="ghost" size="sm">
                <Link to={`/educamanto/pacotes/${packageId}/editar`}>Editar pacote</Link>
              </Button>
            )}
            <Button asChild variant="ghost" size="sm">
              <Link to="/educamanto/pacotes/novo">+ Novo pacote</Link>
            </Button>
          </div>
        }
      />

      {quoteDetalhe.isFetching && (
        <p className="text-xs text-muted">Carregando orçamento para recalcular…</p>
      )}

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
          <div>
            <label className={LABEL} htmlFor="package">
              Pacote
            </label>
            <select
              id="package"
              className={`${FIELD} max-w-md`}
              value={packageId ?? ""}
              onChange={(e) => setPackageId(Number(e.target.value))}
            >
              {packages.map((pkg) => (
                <option key={pkg.id} value={pkg.id}>
                  {pkg.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Dias e ensemble</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-3">
                  <div>
                    <label className={LABEL} htmlFor="d1">
                      Dias — 1 sessão
                    </label>
                    <Input
                      id="d1"
                      type="number"
                      min={0}
                      value={d1}
                      onChange={(e) => setD1(Math.max(0, Number(e.target.value) || 0))}
                    />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor="d2">
                      Dias — 2 sessões
                    </label>
                    <Input
                      id="d2"
                      type="number"
                      min={0}
                      value={d2}
                      onChange={(e) => setD2(Math.max(0, Number(e.target.value) || 0))}
                    />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor="ensemble">
                      Ensemble
                    </label>
                    <Input
                      id="ensemble"
                      type="number"
                      min={0}
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
                      {/* Autocomplete do Google Places (feature 195, Princípio X.3) — endereço
                          normalizado é o que faz a Distance Matrix acertar o KM. */}
                      <GoogleAddressInput
                        id="endereco"
                        aria-label="Endereço do evento"
                        className="flex-1"
                        placeholder="Rua, número, cidade…"
                        value={endereco}
                        onChange={setEndereco}
                        onSelectSuggestion={(description) =>
                          handleCalcularDistancia(description)
                        }
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        loading={distancia.isPending}
                        onClick={() => handleCalcularDistancia()}
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
                <CardContent className="space-y-3">
                  <p className="text-xs text-muted">
                    Valor acrescentado ao orçamento — esta é a sua comissão.
                  </p>
                  <MoneyInput
                    className={`${FIELD} w-40 text-right`}
                    value={acrescimo}
                    onValueChange={setAcrescimo}
                    aria-label="Acréscimo do vendedor"
                  />
                  <div>
                    <label className={LABEL} htmlFor="client_name">
                      Nome do cliente (opcional)
                    </label>
                    <Input
                      id="client_name"
                      type="text"
                      value={clientName}
                      onChange={(e) => setClientName(e.target.value)}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              {totalDias <= 0 && (
                <p className="text-sm text-muted">Preencha os dias para calcular.</p>
              )}

              {calcular.isError && (
                <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
                  {errorMessage(calcular.error, "Não foi possível calcular o pacote.")}
                </div>
              )}

              {calcular.isPending && totalDias > 0 && <Skeleton className="h-40 w-full" />}

              {resultado && totalDias > 0 && (
                <>
                  <p className="text-xs uppercase text-muted">{resultado.scenario}</p>
                  {resultado.desconto_aplicado && (
                    <p className="text-xs text-green">
                      Desconto aplicado (−{brl(resultado.desconto)})
                    </p>
                  )}
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-lg border border-green bg-green-soft p-4">
                      <p className="text-xs font-semibold uppercase text-green">Sem Nota Fiscal</p>
                      <p className="text-2xl font-semibold text-ink">
                        {brl(resultado.valor_final_sem_nota)}
                      </p>
                      <div className="mt-2 space-y-0.5 text-xs text-ink/80">
                        <p>Custo base: {brl(resultado.raw_cost)}</p>
                        <p>Comissão do vendedor: {brl(acrescimo)}</p>
                      </div>
                    </div>
                    <div className="rounded-lg border border-blue bg-blue-soft p-4">
                      <p className="text-xs font-semibold uppercase text-blue">Com Nota Fiscal</p>
                      <p className="text-2xl font-semibold text-ink">
                        {brl(resultado.valor_final_com_nota)}
                      </p>
                      <div className="mt-2 space-y-0.5 text-xs text-ink/80">
                        <p>Custo base: {brl(resultado.raw_cost)}</p>
                        <p>Comissão do vendedor: {brl(acrescimo)}</p>
                      </div>
                    </div>
                  </div>

                  <Card>
                    <CardContent className="p-0">
                      <AccordionRow summary={<span className="p-3 font-medium text-ink">Ver detalhes de custos</span>}>
                        <DetailTable rows={resultado.item_rows} />
                      </AccordionRow>
                    </CardContent>
                  </Card>

                  {gerarMsg && (
                    <p className={`text-xs ${gerarMsg.error ? "text-red" : "text-muted"}`}>
                      {gerarMsg.text}
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { MoneyInput } from "@manto/money";
import {
  useAddEspecial,
  useOrcamentoSettings,
  useRemoveEspecial,
  useSaveOrcamentoSettings,
  type PricingSettings,
} from "../lib/orcamento";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-9 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
const DUR_LABELS = ["1h", "2h", "3h", "4h"];

function PriceTable({
  rows,
}: {
  rows: { label: string; values: number[]; onChange: (values: number[]) => void }[];
}) {
  return (
    <Table>
      <thead>
        <TableRow head>
          <TableCell as="th">Item</TableCell>
          {DUR_LABELS.map((d) => (
            <TableCell as="th" align="right" key={d}>
              {d}
            </TableCell>
          ))}
        </TableRow>
      </thead>
      <tbody>
        {rows.map((row) => (
          <TableRow key={row.label}>
            <TableCell className="font-medium text-ink">{row.label}</TableCell>
            {DUR_LABELS.map((d, i) => (
              <TableCell key={d} align="right">
                <MoneyInput
                  className={`${INPUT} text-right`}
                  value={row.values[i] ?? 0}
                  onValueChange={(v) => row.onChange(row.values.map((x, idx) => (idx === i ? v : x)))}
                />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </tbody>
    </Table>
  );
}

export function OrcamentoConfigPrecosPage() {
  const query = useOrcamentoSettings();
  const save = useSaveOrcamentoSettings();
  const addEspecial = useAddEspecial();
  const removeEspecial = useRemoveEspecial();

  const [settings, setSettings] = useState<PricingSettings | null>(null);
  const [novoEspecialNome, setNovoEspecialNome] = useState("");
  const [novoAcrescimo, setNovoAcrescimo] = useState("");

  useEffect(() => {
    if (query.data && !settings) setSettings(query.data.settings);
  }, [query.data, settings]);

  if (query.isLoading || !settings) {
    return (
      <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
        <PageHeader title="Configuração de Preços" className="mb-0" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="mx-auto max-w-[1400px] p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar a configuração de preços.
        </div>
      </div>
    );
  }

  const handleSave = () => {
    save.mutate(settings, { onSuccess: (data) => setSettings(data.settings) });
  };

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Configuração de Preços"
        subtitle="Valores de referência da Calculadora de Orçamento"
        className="mb-0"
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/orcamento">‹ Voltar à calculadora</Link>
          </Button>
        }
      />

      {/* Oito tabelas de preço independentes: em duas colunas dá para conferir markup e cachês
          sem rolar oito telas. `items-start` porque as tabelas têm alturas bem diferentes. */}
      {/* `[&>*]:min-w-0`: item de grid nasce com `min-width:auto`, o que impede o
          `overflow-x-auto` da tabela de agir e estoura a página no celular. */}
      <div className="grid items-start gap-4 [&>*]:min-w-0 xl:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Markup (Coeficiente de Venda)</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <PriceTable
            rows={[
              {
                label: "Receptivo / Interativo",
                values: settings.markup.receptivo,
                onChange: (v) => setSettings({ ...settings, markup: { ...settings.markup, receptivo: v } }),
              },
              {
                label: "Show",
                values: settings.markup.show,
                onChange: (v) => setSettings({ ...settings, markup: { ...settings.markup, show: v } }),
              },
            ]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cachê — Atores</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <PriceTable
            rows={Object.entries(settings.ator).map(([key, values]) => ({
              label: key,
              values,
              onChange: (v: number[]) => setSettings({ ...settings, ator: { ...settings.ator, [key]: v } }),
            }))}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cachê — Cantores</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <PriceTable
            rows={[
              {
                label: "Base",
                values: settings.cantor.base,
                onChange: (v) => setSettings({ ...settings, cantor: { ...settings.cantor, base: v } }),
              },
              {
                label: "Adicional por show",
                values: settings.cantor.show_extra,
                onChange: (v) => setSettings({ ...settings, cantor: { ...settings.cantor, show_extra: v } }),
              },
              {
                label: "Adicional por maquiagem",
                values: settings.cantor.make_extra,
                onChange: (v) => setSettings({ ...settings, cantor: { ...settings.cantor, make_extra: v } }),
              },
            ]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Técnico de Som e Coordenadores</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <PriceTable
            rows={[
              {
                label: "Técnico de som",
                values: settings.tecnico_som,
                onChange: (v) => setSettings({ ...settings, tecnico_som: v }),
              },
              {
                label: "Coordenador (sem show)",
                values: settings.coordenador.false,
                onChange: (v) => setSettings({ ...settings, coordenador: { ...settings.coordenador, false: v } }),
              },
              {
                label: "Coordenador (com show)",
                values: settings.coordenador.true,
                onChange: (v) => setSettings({ ...settings, coordenador: { ...settings.coordenador, true: v } }),
              },
            ]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Itens Especiais (Customizados)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 p-0">
          <Table>
            <thead>
              <TableRow head>
                <TableCell as="th">Personagem / Variante</TableCell>
                {DUR_LABELS.map((d) => (
                  <TableCell as="th" align="right" key={d}>
                    {d}
                  </TableCell>
                ))}
                <TableCell as="th" align="right">
                  Ações
                </TableCell>
              </TableRow>
            </thead>
            <tbody>
              {Object.entries(settings.especiais).flatMap(([nome, val]) => {
                const remover = (
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={removeEspecial.isPending}
                    onClick={() => {
                      if (!window.confirm(`Remover "${nome}" da tabela de preços?`)) return;
                      removeEspecial.mutate(nome);
                      const { [nome]: _removed, ...rest } = settings.especiais;
                      setSettings({ ...settings, especiais: rest });
                    }}
                  >
                    Remover
                  </Button>
                );
                if (Array.isArray(val)) {
                  return (
                    <TableRow key={nome}>
                      <TableCell className="font-medium text-ink">{nome}</TableCell>
                      {DUR_LABELS.map((d, i) => (
                        <TableCell key={d} align="right">
                          <MoneyInput
                            className={`${INPUT} text-right`}
                            value={val[i] ?? 0}
                            onValueChange={(v) =>
                              setSettings({
                                ...settings,
                                especiais: {
                                  ...settings.especiais,
                                  [nome]: val.map((x, idx) => (idx === i ? v : x)),
                                },
                              })
                            }
                          />
                        </TableCell>
                      ))}
                      <TableCell align="right">{remover}</TableCell>
                    </TableRow>
                  );
                }
                return Object.entries(val).map(([variant, values]) => (
                  <TableRow key={`${nome}-${variant}`}>
                    <TableCell className="text-ink">
                      {nome} <span className="text-muted">— {variant}</span>
                    </TableCell>
                    {DUR_LABELS.map((d, i) => (
                      <TableCell key={d} align="right">
                        <MoneyInput
                          className={`${INPUT} text-right`}
                          value={values[i] ?? 0}
                          onValueChange={(v) =>
                            setSettings({
                              ...settings,
                              especiais: {
                                ...settings.especiais,
                                [nome]: { ...val, [variant]: values.map((x, idx) => (idx === i ? v : x)) },
                              },
                            })
                          }
                        />
                      </TableCell>
                    ))}
                    <TableCell align="right">{remover}</TableCell>
                  </TableRow>
                ));
              })}
            </tbody>
          </Table>
          <div className="flex gap-2 p-3">
            <input
              className={INPUT}
              placeholder="Nome do novo item especial"
              value={novoEspecialNome}
              onChange={(e) => setNovoEspecialNome(e.target.value)}
            />
            <Button
              size="sm"
              loading={addEspecial.isPending}
              onClick={() => {
                if (!novoEspecialNome.trim()) return;
                addEspecial.mutate(
                  { nome: novoEspecialNome.trim(), prices: [0, 0, 0, 0] },
                  { onSuccess: (data) => setSettings(data.settings) },
                );
                setNovoEspecialNome("");
              }}
            >
              Adicionar
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Maquiador e brinde</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>1ª maquiagem</label>
            <MoneyInput
              className={INPUT}
              value={settings.maquiador.make_1}
              onValueChange={(v) => setSettings({ ...settings, maquiador: { ...settings.maquiador, make_1: v } })}
            />
          </div>
          <div>
            <label className={LABEL}>2ª maquiagem (adicional)</label>
            <MoneyInput
              className={INPUT}
              value={settings.maquiador.make_2_adicional}
              onValueChange={(v) =>
                setSettings({ ...settings, maquiador: { ...settings.maquiador, make_2_adicional: v } })
              }
            />
          </div>
          <div>
            <label className={LABEL}>Maquiagem extra (a partir da 3ª)</label>
            <MoneyInput
              className={INPUT}
              value={settings.maquiador.make_extra_adicional}
              onValueChange={(v) =>
                setSettings({ ...settings, maquiador: { ...settings.maquiador, make_extra_adicional: v } })
              }
            />
          </div>
          <div>
            <label className={LABEL}>Maquiagem especial</label>
            <MoneyInput
              className={INPUT}
              value={settings.maquiador.make_especial}
              onValueChange={(v) =>
                setSettings({ ...settings, maquiador: { ...settings.maquiador, make_especial: v } })
              }
            />
          </div>
          <div>
            <label className={LABEL}>Brinde de show</label>
            <MoneyInput
              className={INPUT}
              value={settings.brinde_show}
              onValueChange={(v) => setSettings({ ...settings, brinde_show: v })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Transporte</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {(Object.keys(settings.transporte) as (keyof PricingSettings["transporte"])[]).map((key) => (
            <div key={key}>
              <label className={LABEL}>{key}</label>
              <input
                type="number"
                step="0.1"
                className={INPUT}
                value={settings.transporte[key]}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    transporte: { ...settings.transporte, [key]: Number(e.target.value) },
                  })
                }
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Tipos de acréscimo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-2">
            {settings.acrescimo_tipos.map((t) => (
              <span key={t} className="flex items-center gap-1 rounded-md bg-surface-2 px-2 py-1 text-xs text-ink">
                {t}
                <button
                  type="button"
                  className="text-muted hover:text-red"
                  onClick={() =>
                    setSettings({
                      ...settings,
                      acrescimo_tipos: settings.acrescimo_tipos.filter((x) => x !== t),
                    })
                  }
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              className={INPUT}
              placeholder="Novo tipo de acréscimo"
              value={novoAcrescimo}
              onChange={(e) => setNovoAcrescimo(e.target.value)}
            />
            <Button
              size="sm"
              onClick={() => {
                if (!novoAcrescimo.trim()) return;
                setSettings({
                  ...settings,
                  acrescimo_tipos: [...settings.acrescimo_tipos, novoAcrescimo.trim()],
                });
                setNovoAcrescimo("");
              }}
            >
              Adicionar
            </Button>
          </div>
        </CardContent>
      </Card>
      </div>

      <Button loading={save.isPending} onClick={handleSave}>
        Salvar configurações
      </Button>
      {save.isSuccess && <p className="text-sm text-green">Configurações salvas com sucesso!</p>}
      {save.isError && <p className="text-sm text-red">Não foi possível salvar as configurações.</p>}
    </div>
  );
}

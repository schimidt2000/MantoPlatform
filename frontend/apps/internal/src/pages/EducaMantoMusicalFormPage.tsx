import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { MoneyInput } from "@manto/money";
import {
  useCreateMusical,
  useMusicalDetalhe,
  useUpdateMusical,
  type EducaMantoMusical,
  type MusicalInput,
} from "../lib/educamanto";

const INPUT =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";
const INPUT_ERROR = "border-red ring-1 ring-red";
const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const MIN_ENSAIOS = 2;

/** Item editável do formulário (sem id — a lista inteira é substituída no salvar). */
interface ItemForm {
  name: string;
  qty: number;
  cost_1s: number;
  cost_2s: number;
  cost_1s_days: number;
  cost_2s_days: number;
  ensemble_add: number;
}

const ITEM_VAZIO: ItemForm = {
  name: "",
  qty: 1,
  cost_1s: 0,
  cost_2s: 0,
  cost_1s_days: 0,
  cost_2s_days: 0,
  ensemble_add: 0,
};

interface FormState {
  name: string;
  num_personagens: number;
  num_producao: number;
  num_ensaios: number;
  margin_1s: number;
  margin_2s: number;
  margin_1s_days: number;
  margin_2s_days: number;
  discount_days: number;
  /** Em % (0-100) na tela; convertido para fração no envio. */
  discount_pct: number;
  ensemble_1s: number;
  ensemble_2s: number;
  ensemble_1s_days: number;
  ensemble_2s_days: number;
  custo_som: [number, number, number, number];
  custo_iluminacao: [number, number, number, number];
  custo_cenario: [number, number, number, number];
  custo_alimentacao_1s: number;
  custo_alimentacao_2s: number;
  custo_catering_ensaio_pp: number;
  custo_ajuda_ensaio_pp: number;
  items: ItemForm[];
}

const FORM_INICIAL: FormState = {
  name: "",
  num_personagens: 0,
  num_producao: 2,
  num_ensaios: MIN_ENSAIOS,
  margin_1s: 1.41,
  margin_2s: 1.7,
  margin_1s_days: 1.5,
  margin_2s_days: 1.8,
  discount_days: 3,
  discount_pct: 5,
  ensemble_1s: 350,
  ensemble_2s: 600,
  ensemble_1s_days: 300,
  ensemble_2s_days: 550,
  custo_som: [0, 0, 0, 0],
  custo_iluminacao: [0, 0, 0, 0],
  custo_cenario: [0, 0, 0, 0],
  custo_alimentacao_1s: 55,
  custo_alimentacao_2s: 73,
  custo_catering_ensaio_pp: 28,
  custo_ajuda_ensaio_pp: 50,
  items: [{ ...ITEM_VAZIO }],
};

function musicalParaForm(m: EducaMantoMusical): FormState {
  return {
    name: m.name,
    num_personagens: m.num_personagens,
    num_producao: m.num_producao,
    num_ensaios: m.num_ensaios,
    margin_1s: m.margin_1s,
    margin_2s: m.margin_2s,
    margin_1s_days: m.margin_1s_days,
    margin_2s_days: m.margin_2s_days,
    discount_days: m.discount_days,
    discount_pct: Math.round(m.discount_pct * 100 * 100) / 100,
    ensemble_1s: m.ensemble_1s,
    ensemble_2s: m.ensemble_2s,
    ensemble_1s_days: m.ensemble_1s_days,
    ensemble_2s_days: m.ensemble_2s_days,
    custo_som: [m.custo_som_1s, m.custo_som_2s, m.custo_som_1s_days, m.custo_som_2s_days],
    custo_iluminacao: [
      m.custo_iluminacao_1s,
      m.custo_iluminacao_2s,
      m.custo_iluminacao_1s_days,
      m.custo_iluminacao_2s_days,
    ],
    custo_cenario: [
      m.custo_cenario_1s,
      m.custo_cenario_2s,
      m.custo_cenario_1s_days,
      m.custo_cenario_2s_days,
    ],
    custo_alimentacao_1s: m.custo_alimentacao_1s,
    custo_alimentacao_2s: m.custo_alimentacao_2s,
    custo_catering_ensaio_pp: m.custo_catering_ensaio_pp,
    custo_ajuda_ensaio_pp: m.custo_ajuda_ensaio_pp,
    items:
      m.items.length > 0
        ? m.items.map(({ id: _id, ...resto }) => ({ ...resto }))
        : [{ ...ITEM_VAZIO }],
  };
}

function formParaInput(form: FormState): MusicalInput {
  return {
    name: form.name.trim(),
    num_personagens: form.num_personagens,
    num_producao: form.num_producao,
    num_ensaios: form.num_ensaios,
    margin_1s: form.margin_1s,
    margin_2s: form.margin_2s,
    margin_1s_days: form.margin_1s_days,
    margin_2s_days: form.margin_2s_days,
    discount_days: form.discount_days,
    discount_pct: form.discount_pct / 100,
    ensemble_1s: form.ensemble_1s,
    ensemble_2s: form.ensemble_2s,
    ensemble_1s_days: form.ensemble_1s_days,
    ensemble_2s_days: form.ensemble_2s_days,
    custo_som_1s: form.custo_som[0],
    custo_som_2s: form.custo_som[1],
    custo_som_1s_days: form.custo_som[2],
    custo_som_2s_days: form.custo_som[3],
    custo_iluminacao_1s: form.custo_iluminacao[0],
    custo_iluminacao_2s: form.custo_iluminacao[1],
    custo_iluminacao_1s_days: form.custo_iluminacao[2],
    custo_iluminacao_2s_days: form.custo_iluminacao[3],
    custo_cenario_1s: form.custo_cenario[0],
    custo_cenario_2s: form.custo_cenario[1],
    custo_cenario_1s_days: form.custo_cenario[2],
    custo_cenario_2s_days: form.custo_cenario[3],
    custo_alimentacao_1s: form.custo_alimentacao_1s,
    custo_alimentacao_2s: form.custo_alimentacao_2s,
    custo_catering_ensaio_pp: form.custo_catering_ensaio_pp,
    custo_ajuda_ensaio_pp: form.custo_ajuda_ensaio_pp,
    items: form.items.filter((item) => item.name.trim() !== ""),
  };
}

const CENARIO_LABELS = ["1 sessão", "2 sessões", "1S/dia (multi)", "2S/dia (multi)"];

/** Linha de 4 MoneyInputs — custo por cenário de um bloco (som/iluminação/cenário). */
function CustoCenarioRow({
  valores,
  onChange,
}: {
  valores: [number, number, number, number];
  onChange: (novos: [number, number, number, number]) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-4">
      {CENARIO_LABELS.map((rotulo, i) => (
        <div key={rotulo}>
          <label className={LABEL}>{rotulo}</label>
          <MoneyInput
            className={`${INPUT} text-right`}
            value={valores[i]}
            onValueChange={(v) => {
              const novos = [...valores] as [number, number, number, number];
              novos[i] = v;
              onChange(novos);
            }}
            aria-label={rotulo}
          />
        </div>
      ))}
    </div>
  );
}

export function EducaMantoMusicalFormPage() {
  const { id } = useParams();
  const musicalId = id ? Number(id) : null;
  const navigate = useNavigate();

  const detalhe = useMusicalDetalhe(musicalId);
  const criar = useCreateMusical();
  const atualizar = useUpdateMusical(musicalId ?? 0);

  const [form, setForm] = useState<FormState>(FORM_INICIAL);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);

  useEffect(() => {
    if (detalhe.data) setForm(musicalParaForm(detalhe.data));
  }, [detalhe.data]);

  function set<K extends keyof FormState>(campo: K, valor: FormState[K]) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function setItem(idx: number, mudancas: Partial<ItemForm>) {
    setForm((prev) => ({
      ...prev,
      items: prev.items.map((item, i) => (i === idx ? { ...item, ...mudancas } : item)),
    }));
  }

  const salvando = criar.isPending || atualizar.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldErrors({});
    setErroGeral(null);
    if (!form.name.trim()) {
      setFieldErrors({ name: "Informe o nome do musical." });
      return;
    }
    if (form.num_ensaios < MIN_ENSAIOS) {
      setFieldErrors({ num_ensaios: `O mínimo são ${MIN_ENSAIOS} ensaios.` });
      return;
    }
    const input = formParaInput(form);
    const acao = musicalId ? atualizar : criar;
    acao.mutate(input, {
      onSuccess: (salvo) => navigate(`/educamanto/musicais/${salvo.id}/editar`),
      onError: (err) => {
        if (err instanceof ApiRequestError && err.fields) {
          setFieldErrors(err.fields);
        }
        setErroGeral(
          err instanceof ApiRequestError ? err.message : "Não foi possível salvar o musical.",
        );
      },
    });
  }

  if (musicalId && detalhe.isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (musicalId && detalhe.isError) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
        <PageHeader title="EducaManto — Musical" className="mb-0" />
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o musical — a edição é exclusiva do superadmin.
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title={musicalId ? `Editar musical — ${form.name || "…"}` : "Novo musical"}
        className="mb-0"
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/educamanto/musicais">‹ Musicais</Link>
          </Button>
        }
      />

      <form onSubmit={handleSubmit} className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Dados do musical</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            <div className="sm:col-span-3">
              <label className={LABEL} htmlFor="name">
                Nome
              </label>
              <input
                id="name"
                type="text"
                className={`${INPUT} ${fieldErrors.name ? INPUT_ERROR : ""}`}
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
              />
              {fieldErrors.name && <p className="mt-1 text-xs text-red">{fieldErrors.name}</p>}
            </div>
            <div>
              <label className={LABEL} htmlFor="num_personagens">
                Personagens
              </label>
              <Input
                id="num_personagens"
                type="number"
                min={0}
                value={form.num_personagens}
                onChange={(e) => set("num_personagens", Math.max(0, Number(e.target.value) || 0))}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="num_producao">
                Produção
              </label>
              <Input
                id="num_producao"
                type="number"
                min={0}
                value={form.num_producao}
                onChange={(e) => set("num_producao", Math.max(0, Number(e.target.value) || 0))}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="num_ensaios">
                Nº de ensaios (mín. {MIN_ENSAIOS})
              </label>
              <Input
                id="num_ensaios"
                type="number"
                min={MIN_ENSAIOS}
                className={fieldErrors.num_ensaios ? INPUT_ERROR : ""}
                value={form.num_ensaios}
                onChange={(e) => set("num_ensaios", Math.max(0, Number(e.target.value) || 0))}
              />
              {fieldErrors.num_ensaios && (
                <p className="mt-1 text-xs text-red">{fieldErrors.num_ensaios}</p>
              )}
            </div>
            <div>
              <label className={LABEL} htmlFor="margin_1s">
                Margem — 1 sessão
              </label>
              <Input
                id="margin_1s"
                type="number"
                step={0.01}
                min={0}
                value={form.margin_1s}
                onChange={(e) => set("margin_1s", Number(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="margin_2s">
                Margem — 2 sessões
              </label>
              <Input
                id="margin_2s"
                type="number"
                step={0.01}
                min={0}
                value={form.margin_2s}
                onChange={(e) => set("margin_2s", Number(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="margin_1s_days">
                Margem — 1S/dia (multi)
              </label>
              <Input
                id="margin_1s_days"
                type="number"
                step={0.01}
                min={0}
                value={form.margin_1s_days}
                onChange={(e) => set("margin_1s_days", Number(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="margin_2s_days">
                Margem — 2S/dia (multi)
              </label>
              <Input
                id="margin_2s_days"
                type="number"
                step={0.01}
                min={0}
                value={form.margin_2s_days}
                onChange={(e) => set("margin_2s_days", Number(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="discount_days">
                Desconto a partir de (dias)
              </label>
              <Input
                id="discount_days"
                type="number"
                min={0}
                value={form.discount_days}
                onChange={(e) => set("discount_days", Math.max(0, Number(e.target.value) || 0))}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="discount_pct">
                Desconto (%)
              </label>
              <Input
                id="discount_pct"
                type="number"
                step={0.5}
                min={0}
                value={form.discount_pct}
                onChange={(e) => set("discount_pct", Math.max(0, Number(e.target.value) || 0))}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Som completo (responsabilidade: sonorização)</CardTitle>
          </CardHeader>
          <CardContent>
            <CustoCenarioRow valores={form.custo_som} onChange={(v) => set("custo_som", v)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Iluminação completa (responsabilidade: iluminação)</CardTitle>
          </CardHeader>
          <CardContent>
            <CustoCenarioRow
              valores={form.custo_iluminacao}
              onChange={(v) => set("custo_iluminacao", v)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cenário / ambientação (responsabilidade: cenário)</CardTitle>
          </CardHeader>
          <CardContent>
            <CustoCenarioRow
              valores={form.custo_cenario}
              onChange={(v) => set("custo_cenario", v)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Alimentação e ensaios (por pessoa)</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-4">
            <div>
              <label className={LABEL}>Alimentação — 1 sessão</label>
              <MoneyInput
                className={`${INPUT} text-right`}
                value={form.custo_alimentacao_1s}
                onValueChange={(v) => set("custo_alimentacao_1s", v)}
                aria-label="Alimentação 1 sessão"
              />
            </div>
            <div>
              <label className={LABEL}>Alimentação — 2 sessões</label>
              <MoneyInput
                className={`${INPUT} text-right`}
                value={form.custo_alimentacao_2s}
                onValueChange={(v) => set("custo_alimentacao_2s", v)}
                aria-label="Alimentação 2 sessões"
              />
            </div>
            <div>
              <label className={LABEL}>Catering por ensaio</label>
              <MoneyInput
                className={`${INPUT} text-right`}
                value={form.custo_catering_ensaio_pp}
                onValueChange={(v) => set("custo_catering_ensaio_pp", v)}
                aria-label="Catering por ensaio"
              />
            </div>
            <div>
              <label className={LABEL}>Ajuda de custo por ensaio</label>
              <MoneyInput
                className={`${INPUT} text-right`}
                value={form.custo_ajuda_ensaio_pp}
                onValueChange={(v) => set("custo_ajuda_ensaio_pp", v)}
                aria-label="Ajuda de custo por ensaio"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cachê do ensemble (figurante extra)</CardTitle>
          </CardHeader>
          <CardContent>
            <CustoCenarioRow
              valores={[
                form.ensemble_1s,
                form.ensemble_2s,
                form.ensemble_1s_days,
                form.ensemble_2s_days,
              ]}
              onChange={([a, b, c, d]) => {
                set("ensemble_1s", a);
                set("ensemble_2s", b);
                set("ensemble_1s_days", c);
                set("ensemble_2s_days", d);
              }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Itens sempre inclusos (elenco, produção, gráfica…)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {form.items.map((item, idx) => (
              <div key={idx} className="rounded-md border border-line p-3">
                <div className="grid gap-3 sm:grid-cols-6">
                  <div className="sm:col-span-2">
                    <label className={LABEL}>Nome do item</label>
                    <input
                      type="text"
                      className={INPUT}
                      value={item.name}
                      onChange={(e) => setItem(idx, { name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className={LABEL}>Qtd</label>
                    <Input
                      type="number"
                      min={0}
                      value={item.qty}
                      onChange={(e) => setItem(idx, { qty: Math.max(0, Number(e.target.value) || 0) })}
                    />
                  </div>
                  {(["cost_1s", "cost_2s", "cost_1s_days", "cost_2s_days"] as const).map(
                    (campo, i) => (
                      <div key={campo}>
                        <label className={LABEL}>{CENARIO_LABELS[i]}</label>
                        <MoneyInput
                          className={`${INPUT} text-right`}
                          value={item[campo]}
                          onValueChange={(v) => setItem(idx, { [campo]: v })}
                          aria-label={`${item.name || "item"} — ${CENARIO_LABELS[i]}`}
                        />
                      </div>
                    ),
                  )}
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <label className="flex items-center gap-2 text-xs text-ink">
                    <input
                      type="checkbox"
                      checked={item.ensemble_add > 0}
                      onChange={(e) => setItem(idx, { ensemble_add: e.target.checked ? 1 : 0 })}
                    />
                    Cresce com o ensemble
                  </label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={form.items.length <= 1}
                    onClick={() =>
                      setForm((prev) => ({
                        ...prev,
                        items: prev.items.filter((_, i) => i !== idx),
                      }))
                    }
                  >
                    Remover
                  </Button>
                </div>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                setForm((prev) => ({ ...prev, items: [...prev.items, { ...ITEM_VAZIO }] }))
              }
            >
              + Adicionar item
            </Button>
          </CardContent>
        </Card>

        {erroGeral && (
          <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
            {erroGeral}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button asChild variant="ghost">
            <Link to="/educamanto/musicais">Cancelar</Link>
          </Button>
          <Button type="submit" loading={salvando}>
            {musicalId ? "Salvar musical" : "Criar musical"}
          </Button>
        </div>
      </form>
    </div>
  );
}

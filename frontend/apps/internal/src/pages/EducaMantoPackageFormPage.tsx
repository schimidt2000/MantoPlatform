import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { MoneyInput } from "@manto/money";
import {
  useCreatePackage,
  useEducaMantoPackages,
  useUpdatePackage,
  type EducaMantoItem,
  type PackageInput,
} from "../lib/educamanto";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
const INPUT_ERROR = "border-red focus:ring-red";

type ItemForm = Omit<EducaMantoItem, "id">;

const EMPTY_ITEM: ItemForm = {
  name: "",
  qty: 1,
  cost_1s: 0,
  cost_2s: 0,
  cost_1s_days: 0,
  cost_2s_days: 0,
  ensemble_add: 0,
};

export function EducaMantoPackageFormPage() {
  const params = useParams<{ id?: string }>();
  const pkgId = params.id ? Number(params.id) : undefined;
  const isEdit = pkgId !== undefined;
  const navigate = useNavigate();

  const packagesQuery = useEducaMantoPackages();
  const createPackage = useCreatePackage();
  const updatePackage = useUpdatePackage(pkgId ?? 0);

  const existing = packagesQuery.data?.packages.find((p) => p.id === pkgId);

  const [name, setName] = useState("");
  const [marginNormal, setMarginNormal] = useState({ margin_1s: 0, margin_2s: 0 });
  const [marginDays, setMarginDays] = useState({ margin_1s_days: 0, margin_2s_days: 0 });
  const [discountDays, setDiscountDays] = useState(2);
  const [discountPct, setDiscountPct] = useState(0);
  const [commissionRate, setCommissionRate] = useState(0);
  const [ensemble, setEnsemble] = useState({
    ensemble_1s: 350,
    ensemble_2s: 600,
    ensemble_1s_days: 300,
    ensemble_2s_days: 550,
  });
  const [items, setItems] = useState<ItemForm[]>([{ ...EMPTY_ITEM }]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (existing) {
      setName(existing.name);
      setMarginNormal({ margin_1s: existing.margin_1s, margin_2s: existing.margin_2s });
      setMarginDays({
        margin_1s_days: existing.margin_1s_days,
        margin_2s_days: existing.margin_2s_days,
      });
      setDiscountDays(existing.discount_days);
      setDiscountPct(existing.discount_pct * 100);
      setCommissionRate(existing.commission_rate * 100);
      setEnsemble({
        ensemble_1s: existing.ensemble_1s,
        ensemble_2s: existing.ensemble_2s,
        ensemble_1s_days: existing.ensemble_1s_days,
        ensemble_2s_days: existing.ensemble_2s_days,
      });
      setItems(existing.items.length > 0 ? existing.items : [{ ...EMPTY_ITEM }]);
    }
  }, [existing]);

  function updateItem(index: number, patch: Partial<ItemForm>) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)));
  }

  function addItem() {
    setItems((prev) => [...prev, { ...EMPTY_ITEM }]);
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldErrors({});
    setFormError(null);

    if (!name.trim()) {
      setFieldErrors({ name: "Informe o nome do pacote." });
      return;
    }

    const input: PackageInput = {
      name: name.trim(),
      margin_1s: marginNormal.margin_1s,
      margin_2s: marginNormal.margin_2s,
      margin_1s_days: marginDays.margin_1s_days,
      margin_2s_days: marginDays.margin_2s_days,
      discount_days: discountDays,
      discount_pct: discountPct / 100,
      commission_rate: commissionRate / 100,
      ensemble_1s: ensemble.ensemble_1s,
      ensemble_2s: ensemble.ensemble_2s,
      ensemble_1s_days: ensemble.ensemble_1s_days,
      ensemble_2s_days: ensemble.ensemble_2s_days,
      items: items.filter((it) => it.name.trim().length > 0),
    };

    const mutation = isEdit ? updatePackage : createPackage;
    mutation.mutate(input, {
      onSuccess: (pkg) => {
        navigate(`/educamanto/pacotes/${pkg.id}/editar`, { replace: true });
      },
      onError: (err) => {
        if (err instanceof ApiRequestError && err.fields) {
          setFieldErrors(err.fields);
        } else {
          setFormError(
            err instanceof ApiRequestError ? err.message : "Não foi possível salvar o pacote.",
          );
        }
      },
    });
  }

  if (isEdit && packagesQuery.isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  const saving = createPackage.isPending || updatePackage.isPending;

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader title={isEdit ? "Editar pacote" : "Novo pacote"} className="mb-0" />

      {formError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          {formError}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Dados do pacote</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className={LABEL} htmlFor="name">
              Nome
            </label>
            <input
              id="name"
              className={`${INPUT} ${fieldErrors.name ? INPUT_ERROR : ""}`}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            {fieldErrors.name && <p className="mt-1 text-xs text-red">{fieldErrors.name}</p>}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className={LABEL} htmlFor="margin_1s">
                Margem — 1 sessão (multiplicador)
              </label>
              <input
                id="margin_1s"
                type="number"
                step="0.01"
                className={INPUT}
                value={marginNormal.margin_1s}
                onChange={(e) =>
                  setMarginNormal((prev) => ({ ...prev, margin_1s: Number(e.target.value) || 0 }))
                }
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="margin_2s">
                Margem — 2 sessões (multiplicador)
              </label>
              <input
                id="margin_2s"
                type="number"
                step="0.01"
                className={INPUT}
                value={marginNormal.margin_2s}
                onChange={(e) =>
                  setMarginNormal((prev) => ({ ...prev, margin_2s: Number(e.target.value) || 0 }))
                }
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="margin_1s_days">
                Margem — 1 sessão/dia (multi-dia)
              </label>
              <input
                id="margin_1s_days"
                type="number"
                step="0.01"
                className={INPUT}
                value={marginDays.margin_1s_days}
                onChange={(e) =>
                  setMarginDays((prev) => ({
                    ...prev,
                    margin_1s_days: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="margin_2s_days">
                Margem — 2 sessões/dia (multi-dia)
              </label>
              <input
                id="margin_2s_days"
                type="number"
                step="0.01"
                className={INPUT}
                value={marginDays.margin_2s_days}
                onChange={(e) =>
                  setMarginDays((prev) => ({
                    ...prev,
                    margin_2s_days: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className={LABEL} htmlFor="discount_days">
                Desconto a partir de (dias)
              </label>
              <input
                id="discount_days"
                type="number"
                min={0}
                className={INPUT}
                value={discountDays}
                onChange={(e) => setDiscountDays(Number(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="discount_pct">
                Desconto (%)
              </label>
              <input
                id="discount_pct"
                type="number"
                step="0.1"
                className={INPUT}
                value={discountPct}
                onChange={(e) => setDiscountPct(Number(e.target.value) || 0)}
              />
            </div>
            <div>
              <label className={LABEL} htmlFor="commission_rate">
                Comissão (%)
              </label>
              <input
                id="commission_rate"
                type="number"
                step="0.1"
                className={INPUT}
                value={commissionRate}
                onChange={(e) => setCommissionRate(Number(e.target.value) || 0)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cachê do ensemble (figurante extra)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-4">
          <div>
            <label className={LABEL}>1 sessão</label>
            <MoneyInput
              className={INPUT}
              value={ensemble.ensemble_1s}
              onValueChange={(v) => setEnsemble((prev) => ({ ...prev, ensemble_1s: v }))}
            />
          </div>
          <div>
            <label className={LABEL}>2 sessões</label>
            <MoneyInput
              className={INPUT}
              value={ensemble.ensemble_2s}
              onValueChange={(v) => setEnsemble((prev) => ({ ...prev, ensemble_2s: v }))}
            />
          </div>
          <div>
            <label className={LABEL}>1 sessão/dia</label>
            <MoneyInput
              className={INPUT}
              value={ensemble.ensemble_1s_days}
              onValueChange={(v) => setEnsemble((prev) => ({ ...prev, ensemble_1s_days: v }))}
            />
          </div>
          <div>
            <label className={LABEL}>2 sessões/dia</label>
            <MoneyInput
              className={INPUT}
              value={ensemble.ensemble_2s_days}
              onValueChange={(v) => setEnsemble((prev) => ({ ...prev, ensemble_2s_days: v }))}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Itens do pacote</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {items.map((item, index) => (
            <div key={index} className="rounded-md border border-line p-3">
              <div className="mb-2 flex items-center gap-2">
                <input
                  className={`${INPUT} flex-1`}
                  placeholder="Nome do item"
                  value={item.name}
                  onChange={(e) => updateItem(index, { name: e.target.value })}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeItem(index)}
                  disabled={items.length === 1}
                >
                  Remover
                </Button>
              </div>
              <div className="grid gap-2 sm:grid-cols-5">
                <div>
                  <label className={LABEL}>Qtd</label>
                  <input
                    type="number"
                    min={0}
                    className={INPUT}
                    value={item.qty}
                    onChange={(e) => updateItem(index, { qty: Number(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <label className={LABEL}>Custo 1S</label>
                  <MoneyInput
                    className={INPUT}
                    value={item.cost_1s}
                    onValueChange={(v) => updateItem(index, { cost_1s: v })}
                  />
                </div>
                <div>
                  <label className={LABEL}>Custo 2S</label>
                  <MoneyInput
                    className={INPUT}
                    value={item.cost_2s}
                    onValueChange={(v) => updateItem(index, { cost_2s: v })}
                  />
                </div>
                <div>
                  <label className={LABEL}>Custo 1S/dia</label>
                  <MoneyInput
                    className={INPUT}
                    value={item.cost_1s_days}
                    onValueChange={(v) => updateItem(index, { cost_1s_days: v })}
                  />
                </div>
                <div>
                  <label className={LABEL}>Custo 2S/dia</label>
                  <MoneyInput
                    className={INPUT}
                    value={item.cost_2s_days}
                    onValueChange={(v) => updateItem(index, { cost_2s_days: v })}
                  />
                </div>
              </div>
              <label className="mt-2 flex items-center gap-2 text-xs text-muted">
                <input
                  type="checkbox"
                  checked={item.ensemble_add === 1}
                  onChange={(e) => updateItem(index, { ensemble_add: e.target.checked ? 1 : 0 })}
                />
                Cresce com o ensemble
              </label>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={addItem}>
            + Adicionar item
          </Button>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button type="submit" loading={saving}>
          {isEdit ? "Salvar alterações" : "Criar pacote"}
        </Button>
      </div>
    </form>
  );
}

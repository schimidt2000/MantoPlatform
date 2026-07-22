import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { Button, Card, CardContent } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { useCurrentUser } from "../lib/useAuth";
import { useTalent, useUpdateTalent, type TalentUpdateInput } from "../lib/talents";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

function Field({
  label,
  value,
  onChange,
  disabled,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  type?: string;
}) {
  return (
    <div>
      <label className={LABEL}>{label}</label>
      <input
        type={type}
        className={INPUT}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export function TalentEditPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const navigate = useNavigate();
  const query = useTalent(id);
  const { data: user } = useCurrentUser();
  const update = useUpdateTalent(id);

  const [form, setForm] = useState<TalentUpdateInput | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (query.data && !form) {
      const { id: _id, status: _status, notes: _notes, warning_level: _wl, ...editable } =
        query.data.talent;
      setForm(editable);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.data]);

  if (query.isLoading || !form) {
    return <div className="mx-auto max-w-2xl p-6 text-sm text-muted">Carregando…</div>;
  }
  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-sm text-red">Não foi possível carregar o talento.</div>
    );
  }

  const set = <K extends keyof TalentUpdateInput>(key: K, value: TalentUpdateInput[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  const submit = () => {
    setFieldErrors({});
    update.mutate(form, {
      onSuccess: () => navigate(`/talents/${id}`),
      onError: (err) => {
        if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
      },
    });
  };

  const s = (v: string | null | undefined) => v ?? "";

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 pb-24 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to={`/talents/${id}`}>‹ Perfil</Link>
      </Button>
      <h1 className="text-2xl font-semibold text-ink">Editar talento</h1>

      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nome completo" value={s(form.full_name)} onChange={(v) => set("full_name", v)} />
            <Field
              label="Nome artístico"
              value={s(form.artistic_name)}
              onChange={(v) => set("artistic_name", v)}
            />
            <Field label="Telefone" value={s(form.phone)} onChange={(v) => set("phone", v)} />
            <Field
              label="E-mail"
              value={s(form.email_contact)}
              onChange={(v) => set("email_contact", v)}
            />
            <Field
              label="Data de nascimento"
              type="date"
              value={s(form.birth_date)}
              onChange={(v) => set("birth_date", v)}
            />
            <Field label="Gênero" value={s(form.gender)} onChange={(v) => set("gender", v)} />
            <Field label="Raça" value={s(form.race)} onChange={(v) => set("race", v)} />
            <Field label="Idiomas" value={s(form.languages)} onChange={(v) => set("languages", v)} />
          </div>
          <Field label="Habilidades" value={s(form.skills)} onChange={(v) => set("skills", v)} />
          <Field label="Tags" value={s(form.tags)} onChange={(v) => set("tags", v)} />

          <div className="grid grid-cols-3 gap-3">
            <Field
              label="Altura (cm)"
              type="number"
              value={form.height_cm != null ? String(form.height_cm) : ""}
              onChange={(v) => set("height_cm", v ? Number(v) : null)}
            />
            <Field
              label="Tamanho superior"
              value={s(form.clothing_size_top)}
              onChange={(v) => set("clothing_size_top", v)}
            />
            <Field
              label="Tamanho inferior"
              value={s(form.clothing_size_bottom)}
              onChange={(v) => set("clothing_size_bottom", v)}
            />
            <Field label="Calçado" value={s(form.shoe_size)} onChange={(v) => set("shoe_size", v)} />
            <div>
              <label className={LABEL}>Passaporte/Visto</label>
              <select
                className={INPUT}
                value={s(form.passport_status)}
                onChange={(e) => set("passport_status", e.target.value)}
              >
                <option value="">Não informado</option>
                <option value="visa">Passaporte + visto</option>
                <option value="passport">Passaporte sem visto</option>
                <option value="none">Sem passaporte</option>
              </select>
            </div>
            <div>
              <label className={LABEL}>Já trabalhou com a Manto</label>
              <select
                className={INPUT}
                value={form.worked_before == null ? "" : form.worked_before ? "1" : "0"}
                onChange={(e) =>
                  set("worked_before", e.target.value === "" ? null : e.target.value === "1")
                }
              >
                <option value="">Não informado</option>
                <option value="1">Sim</option>
                <option value="0">Não</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Field label="RG" value={s(form.rg)} onChange={(v) => set("rg", v)} />
            </div>
            <div>
              <label className={LABEL}>
                CPF {!user?.is_superadmin && "(só superadmin edita)"}
              </label>
              <input
                className={INPUT}
                value={s(form.cpf)}
                disabled={!user?.is_superadmin}
                onChange={(e) => set("cpf", e.target.value)}
              />
              {fieldErrors.cpf && <p className="mt-1 text-xs text-red">{fieldErrors.cpf}</p>}
            </div>
            <Field label="Chave PIX" value={s(form.pix_key)} onChange={(v) => set("pix_key", v)} />
            <Field
              label="Chave PIX (2ª)"
              value={s(form.pix_key_secondary)}
              onChange={(v) => set("pix_key_secondary", v)}
            />
            <Field
              label="Tipo de chave PIX"
              value={s(form.pix_key_type)}
              onChange={(v) => set("pix_key_type", v)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Marca do carro" value={s(form.car_brand)} onChange={(v) => set("car_brand", v)} />
            <Field label="Modelo do carro" value={s(form.car_model)} onChange={(v) => set("car_model", v)} />
            <Field label="Ano do carro" value={s(form.car_year)} onChange={(v) => set("car_year", v)} />
            <Field label="Placa" value={s(form.car_plate)} onChange={(v) => set("car_plate", v)} />
            <Field
              label="CNH válida até"
              type="date"
              value={s(form.cnh_expiration)}
              onChange={(v) => set("cnh_expiration", v)}
            />
          </div>

          <Field
            label="Como conheceu a Manto"
            value={s(form.how_found_us)}
            onChange={(v) => set("how_found_us", v)}
          />

          {update.isError && !Object.keys(fieldErrors).length && (
            <p className="text-sm text-red">Não foi possível salvar. Tente novamente.</p>
          )}

          <div className="flex gap-2 border-t border-line pt-4">
            <Button loading={update.isPending} onClick={submit}>
              Salvar
            </Button>
            <Button asChild variant="outline">
              <Link to={`/talents/${id}`}>Cancelar</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

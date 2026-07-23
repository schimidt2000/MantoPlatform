import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { useAdminSettings, useUpdateAdminSettings } from "../lib/adminConfig";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

export function AdminSettingsPage() {
  const query = useAdminSettings();
  const update = useUpdateAdminSettings();

  const [commission, setCommission] = useState("");
  const [taxRate, setTaxRate] = useState("");
  const [fatorR, setFatorR] = useState("");
  const [address, setAddress] = useState("");
  const [margin, setMargin] = useState("");
  const [mapsKey, setMapsKey] = useState("");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [releaseDate, setReleaseDate] = useState("");

  useEffect(() => {
    if (query.data) {
      setCommission(String(query.data.default_commission_rate ?? ""));
      setTaxRate(String(query.data.tax_rate ?? ""));
      setFatorR(String(query.data.fator_r_threshold ?? ""));
      setAddress(query.data.manto_address);
      setMargin(String(query.data.departure_margin_minutes ?? ""));
      setMapsKey(query.data.google_maps_api_key);
      setEmailNotifications(query.data.email_notifications_enabled);
      setWhatsappNumber(query.data.whatsapp_form_number);
      setReleaseDate(query.data.release_date ?? "");
    }
  }, [query.data]);

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
<PageHeader title="Configurações" className="mb-0" />

      <div className="flex flex-wrap gap-2">
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/logs">Logs</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/desempenho">Desempenho</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/sync">Sync da agenda</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/anuncio-portal">Anúncio do portal</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/migrar-arquivos">Migrar arquivos</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/importar-catalogo">Importar catálogo</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/catalogo">Gerenciar catálogo</Link>
        </Button>
      </div>

      {query.isLoading && <Skeleton className="h-64 w-full" />}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as configurações.
        </div>
      )}

      {query.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Financeiro</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL}>Comissão padrão (%)</label>
                <input
                  className={INPUT}
                  value={commission}
                  onChange={(e) => setCommission(e.target.value)}
                />
              </div>
              <div>
                <label className={LABEL}>Imposto (%)</label>
                <input
                  className={INPUT}
                  value={taxRate}
                  onChange={(e) => setTaxRate(e.target.value)}
                />
              </div>
              <div>
                <label className={LABEL}>Fator R — limite (%)</label>
                <input
                  className={INPUT}
                  value={fatorR}
                  onChange={(e) => setFatorR(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Logística</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className={LABEL}>Endereço base (Manto)</label>
                <input
                  className={INPUT}
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
              </div>
              <div>
                <label className={LABEL}>Margem de saída (minutos)</label>
                <input
                  className={INPUT}
                  value={margin}
                  onChange={(e) => setMargin(e.target.value)}
                />
              </div>
              <div>
                <label className={LABEL}>Chave da API do Google Maps</label>
                <input
                  className={INPUT}
                  value={mapsKey}
                  onChange={(e) => setMapsKey(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notificações e formulários</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <label className="flex items-center gap-2 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                />
                Notificações por email ativadas
              </label>
              <div>
                <label className={LABEL}>WhatsApp dos formulários de pré-contrato</label>
                <input
                  className={INPUT}
                  value={whatsappNumber}
                  onChange={(e) => setWhatsappNumber(e.target.value)}
                />
              </div>
              <div>
                <label className={LABEL}>Data de início do sistema</label>
                <input
                  type="date"
                  className={INPUT}
                  value={releaseDate}
                  onChange={(e) => setReleaseDate(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Logo</CardTitle>
            </CardHeader>
            <CardContent>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/svg+xml"
                className="text-sm text-ink"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) update.mutate({ logo: file });
                }}
              />
            </CardContent>
          </Card>

          <Button
            loading={update.isPending}
            onClick={() =>
              update.mutate({
                default_commission_rate: commission ? Number(commission) : undefined,
                tax_rate: taxRate ? Number(taxRate) : undefined,
                fator_r_threshold: fatorR ? Number(fatorR) : undefined,
                manto_address: address,
                departure_margin_minutes: margin ? Number(margin) : undefined,
                google_maps_api_key: mapsKey,
                email_notifications_enabled: emailNotifications,
                whatsapp_form_number: whatsappNumber,
                release_date: releaseDate || undefined,
              })
            }
          >
            Salvar configurações
          </Button>
          {update.isError && <p className="text-sm text-red">Não foi possível salvar.</p>}
        </>
      )}
    </div>
  );
}

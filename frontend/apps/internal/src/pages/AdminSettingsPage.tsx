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
  const [educamantoCommission, setEducamantoCommission] = useState("");
  const [infinitepayHandle, setInfinitepayHandle] = useState("");
  const [regenerarToken, setRegenerarToken] = useState(false);
  const [address, setAddress] = useState("");
  const [margin, setMargin] = useState("");
  const [mapsKey, setMapsKey] = useState("");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [googleReviewUrl, setGoogleReviewUrl] = useState("");
  const [releaseDate, setReleaseDate] = useState("");

  useEffect(() => {
    if (query.data) {
      setCommission(String(query.data.default_commission_rate ?? ""));
      setTaxRate(String(query.data.tax_rate ?? ""));
      setFatorR(String(query.data.fator_r_threshold ?? ""));
      setEducamantoCommission(String(query.data.educamanto_commission_rate ?? ""));
      setInfinitepayHandle(query.data.infinitepay_handle ?? "");
      setAddress(query.data.manto_address);
      setMargin(String(query.data.departure_margin_minutes ?? ""));
      setMapsKey(query.data.google_maps_api_key);
      setEmailNotifications(query.data.email_notifications_enabled);
      setWhatsappNumber(query.data.whatsapp_form_number);
      setGoogleReviewUrl(query.data.google_review_url);
      setReleaseDate(query.data.release_date ?? "");
    }
  }, [query.data]);

  return (
    <div className="mx-auto max-w-[1200px] space-y-4 p-4 sm:p-6">
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
          {/* Blocos de configuração são independentes entre si — em duas colunas a página inteira
              cabe na tela, em vez de virar uma coluna estreita de 2xl com muita rolagem. */}
          <div className="grid items-start gap-4 [&>*]:min-w-0 lg:grid-cols-2">
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
              <div>
                <label className={LABEL}>Comissão EducaManto (%)</label>
                <input
                  className={INPUT}
                  value={educamantoCommission}
                  onChange={(e) => setEducamantoCommission(e.target.value)}
                />
                <p className="mt-1 text-xs text-muted">
                  Do responsável EducaManto, sobre o <strong>lucro</strong> do evento (venda −
                  BV − cachês). Vazio = 5%.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Sem estes dois campos a Loja de Interações Virtuais não vende: toda reserva morre
              em "O meio de pagamento ainda não está configurado". As colunas existiam desde a
              205, mas nenhuma tela as escrevia. */}
          <Card>
            <CardHeader>
              <CardTitle>Pagamento da Loja de Interações Virtuais</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className={LABEL}>InfiniteTag (conta que recebe)</label>
                <input
                  className={INPUT}
                  value={infinitepayHandle}
                  placeholder="mantoproducoes"
                  onChange={(e) => setInfinitepayHandle(e.target.value)}
                />
                <p className="mt-1 text-xs text-muted">
                  É o seu usuário na InfinitePay — o mesmo que aparece no link de cobrança. Pode
                  colar com <code>$</code> na frente, que ele é removido.
                </p>
              </div>
              <div>
                <label className={LABEL}>Aviso de pagamento (webhook)</label>
                <p className="text-sm text-ink">
                  {query.data.infinitepay_webhook_configured ? (
                    <span className="text-green">✓ Configurado</span>
                  ) : (
                    <span className="text-red">Ainda não configurado</span>
                  )}
                </p>
                <label className="mt-2 flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    checked={regenerarToken}
                    onChange={(e) => setRegenerarToken(e.target.checked)}
                  />
                  Gerar um segredo novo ao salvar
                </label>
                <p className="mt-1 text-xs text-muted">
                  É o segredo que autentica o aviso de pagamento da operadora — o sistema gera e
                  guarda sozinho, você não precisa copiar nada. Gerar de novo{" "}
                  <strong>invalida o anterior</strong>: só faça isso se suspeitar que vazou.
                </p>
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
                <label className={LABEL}>Link de avaliação no Google (feedback 5 estrelas)</label>
                <input
                  className={INPUT}
                  placeholder="https://g.page/r/…/review — vazio usa o padrão"
                  value={googleReviewUrl}
                  onChange={(e) => setGoogleReviewUrl(e.target.value)}
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
                accept="image/png,image/jpeg,image/webp"
                className="text-sm text-ink"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) update.mutate({ logo: file });
                }}
              />
            </CardContent>
          </Card>
          </div>

          <Button
            loading={update.isPending}
            onClick={() =>
              update.mutate({
                default_commission_rate: commission ? Number(commission) : undefined,
                tax_rate: taxRate ? Number(taxRate) : undefined,
                fator_r_threshold: fatorR ? Number(fatorR) : undefined,
                educamanto_commission_rate: educamantoCommission
                  ? Number(educamantoCommission)
                  : undefined,
                infinitepay_handle: infinitepayHandle || undefined,
                infinitepay_regenerate_token: regenerarToken || undefined,
                manto_address: address,
                departure_margin_minutes: margin ? Number(margin) : undefined,
                google_maps_api_key: mapsKey,
                email_notifications_enabled: emailNotifications,
                whatsapp_form_number: whatsappNumber,
                google_review_url: googleReviewUrl,
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

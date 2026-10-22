import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader } from "@manto/ui";
import { usePortalAnnouncement } from "../lib/adminConfig";

export function AdminPortalAnnouncementPage() {
  const announce = usePortalAnnouncement();

  return (
    <div className="mx-auto max-w-lg space-y-4 p-4 sm:p-6">
<PageHeader title="Anúncio do portal" className="mb-0" />

      <Card>
        <CardHeader>
          <CardTitle>Enviar anúncio por e-mail</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted">
            Envia um e-mail a todos os talentos com e-mail cadastrado, anunciando o portal.
          </p>
          <Button
            loading={announce.isPending}
            onClick={() => {
              if (window.confirm("Enviar o anúncio do portal para todos os talentos com e-mail?")) {
                announce.mutate();
              }
            }}
          >
            Enviar anúncio
          </Button>
          {announce.data && (
            <p className="text-sm text-ink">
              Enviados: {announce.data.sent} · Falhas: {announce.data.failed}
            </p>
          )}
          {announce.isError && (
            <p className="text-sm text-red">Não foi possível enviar o anúncio.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

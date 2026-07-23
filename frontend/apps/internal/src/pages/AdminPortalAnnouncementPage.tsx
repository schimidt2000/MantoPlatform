import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader } from "@manto/ui";
import { usePortalAnnouncement } from "../lib/adminConfig";

export function AdminPortalAnnouncementPage() {
  const announce = usePortalAnnouncement();

  return (
    <div className="mx-auto max-w-lg space-y-4 p-4 sm:p-6">
<PageHeader title="Anúncio do portal" className="mb-0" />

      <Card>
        <CardHeader>
          <CardTitle>Enviar anúncio por email</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted">
            Envia um email a todas as talentos com email cadastrado, anunciando o portal.
          </p>
          <Button
            loading={announce.isPending}
            onClick={() => {
              if (window.confirm("Enviar o anúncio do portal para todas as talentos com email?")) {
                announce.mutate();
              }
            }}
          >
            Enviar anúncio
          </Button>
          {announce.data && (
            <p className="text-sm text-ink">
              Enviado: {announce.data.sent} · Falhas: {announce.data.failed}
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

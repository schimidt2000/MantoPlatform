import { useParams, Link } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { useFigurino } from "../lib/portalFigurino";

export function PortalFigurinoPage() {
  const params = useParams<{ eventId: string }>();
  const eventId = params.eventId ? Number(params.eventId) : undefined;
  const query = useFigurino(eventId);

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Ficha de Figurino"
        className="mb-0"
        actions={
          <Link to="/agenda" className="text-sm text-accent hover:underline">
            ‹ Agenda
          </Link>
        }
      />

      {query.isLoading && <Skeleton className="h-64 w-full" />}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Você não está escalado neste evento.
        </div>
      )}

      {query.data && query.data.sheets.length === 0 && (
        <p className="text-sm text-muted">Ainda não há ficha de figurino para este evento.</p>
      )}

      {query.data &&
        query.data.sheets.map((sheet) => (
          <Card key={sheet.character_name}>
            <CardContent className="space-y-3 p-4">
              <p className="font-medium text-ink">{sheet.character_name}</p>
              {sheet.photo_url && (
                <img
                  src={assetUrl(sheet.photo_url)}
                  alt={`Referência de ${sheet.character_name}`}
                  className="w-full rounded-md object-cover"
                />
              )}
              {sheet.pieces.length > 0 && (
                <ul className="list-inside list-disc text-sm text-ink">
                  {sheet.pieces.map((piece) => (
                    <li key={piece.name}>
                      {piece.name}
                      {piece.qty > 1 ? ` (×${piece.qty})` : ""}
                    </li>
                  ))}
                </ul>
              )}
              {sheet.notes && <p className="text-sm text-muted">{sheet.notes}</p>}
            </CardContent>
          </Card>
        ))}
    </div>
  );
}

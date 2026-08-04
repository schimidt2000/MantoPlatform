import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Plus, Video } from "lucide-react";
import {
  AvatarThumb,
  Badge,
  Button,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import {
  useVirtualCampaigns,
  VIRTUAL_CAMPAIGN_STATUS_LABELS,
  VIRTUAL_CAMPAIGN_STATUS_TONES,
  apiMoneyToNumber,
  type VirtualCampaign,
} from "../lib/virtuais";

/**
 * Listagem das campanhas da Loja de Interações Virtuais (feature 205, US1).
 *
 * Mostra de relance o que a equipe comercial pergunta ao abrir a tela: em que pé está a campanha,
 * quanto já vendeu e quanto estoque sobrou. Todo valor passa por `formatBRL` do `@manto/money` —
 * nenhuma máscara própria aqui (Princípio IX).
 */

function CampaignRow({ campaign }: { campaign: VirtualCampaign }) {
  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2">
          <AvatarThumb
            src={assetUrl(campaign.character?.photo_url ?? campaign.cover_url)}
            name={campaign.character?.name ?? campaign.title}
            shape="square"
            size="md"
            fallbackIcon="🎭"
          />
          <div className="min-w-0">
            <Link
              to={`/virtuais/campanhas/${campaign.id}`}
              className="font-medium text-ink hover:underline"
            >
              {campaign.title}
            </Link>
            {campaign.character && (
              <div className="truncate text-[11px] text-muted">{campaign.character.name}</div>
            )}
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge tone={VIRTUAL_CAMPAIGN_STATUS_TONES[campaign.status]}>
          {VIRTUAL_CAMPAIGN_STATUS_LABELS[campaign.status]}
        </Badge>
      </TableCell>
      <TableCell align="right">R$ {formatBRL(apiMoneyToNumber(campaign.price_live))}</TableCell>
      <TableCell align="right">R$ {formatBRL(apiMoneyToNumber(campaign.price_recorded))}</TableCell>
      <TableCell align="right">{campaign.sold_count}</TableCell>
      <TableCell align="right">R$ {formatBRL(apiMoneyToNumber(campaign.revenue))}</TableCell>
      <TableCell align="right">
        <span className="text-ink">{campaign.slots_available}</span>
        <span className="text-muted"> / {campaign.slots_total}</span>
      </TableCell>
      <TableCell align="right">
        <span className="text-ink">{campaign.recorded_used}</span>
        <span className="text-muted"> / {campaign.recorded_capacity_total}</span>
      </TableCell>
    </TableRow>
  );
}

export function VirtuaisCampanhasPage() {
  const reduceMotion = useReducedMotion();
  const { data, isLoading, isError, error } = useVirtualCampaigns();
  const campaigns = data?.campaigns ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Interações Virtuais"
        subtitle="Campanhas de venda de chamadas ao vivo e vídeos gravados com personagens do catálogo."
        actions={
          <Button asChild>
            <Link to="/virtuais/campanhas/nova">
              <Plus className="size-4" />
              Nova campanha
            </Link>
          </Button>
        }
      />

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
          Não foi possível carregar as campanhas
          {error instanceof Error ? `: ${error.message}` : "."}
        </div>
      )}

      {!isLoading && !isError && campaigns.length === 0 && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-line p-10 text-center">
          <Video className="size-8 text-muted" />
          <p className="text-sm text-muted">
            Nenhuma campanha ainda. Crie a primeira para começar a vender interações.
          </p>
        </div>
      )}

      {!isLoading && !isError && campaigns.length > 0 && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <Table>
            <thead>
              <TableRow head>
                <TableCell as="th">Campanha</TableCell>
                <TableCell as="th">Situação</TableCell>
                <TableCell as="th" align="right">
                  Chamada
                </TableCell>
                <TableCell as="th" align="right">
                  Gravado
                </TableCell>
                <TableCell as="th" align="right">
                  Vendidos
                </TableCell>
                <TableCell as="th" align="right">
                  Faturado
                </TableCell>
                <TableCell as="th" align="right">
                  Horários
                </TableCell>
                <TableCell as="th" align="right">
                  Vídeos
                </TableCell>
              </TableRow>
            </thead>
            <tbody>
              {campaigns.map((campaign) => (
                <CampaignRow key={campaign.id} campaign={campaign} />
              ))}
            </tbody>
          </Table>
        </motion.div>
      )}
    </div>
  );
}

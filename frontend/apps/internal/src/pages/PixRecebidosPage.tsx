import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Card, CardContent, PageHeader, Skeleton, Tabs, TabsList, TabsTrigger } from "@manto/ui";
import { CartaoPixLigado, CartaoPixParaConferir } from "../components/pix/CartaoPix";
import { ConfigPixPainel, ResumoPorConta, SaudeDaLeitura } from "../components/pix/PainelPix";
import { usePixLista, type AbaPix } from "../lib/pix";

/**
 * "PIX recebidos" (feature 318): o que o sistema leu dos avisos do Inter e não conseguiu ligar
 * sozinho ("É esta?"), o que ligou nos últimos 30 dias e — para Financeiro/Superadmin — o recebido
 * por conta. O Superadmin configura a leitura aqui mesmo.
 */
export function PixRecebidosPage() {
  const [aba, setAba] = useState<AbaPix>("conferir");
  const lista = usePixLista(aba);
  const flags = lista.data?.flags;

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
      <PageHeader
        title="PIX recebidos"
        subtitle="O PIX que entra no Inter se liga sozinho à venda; quando há dúvida, ele espera aqui"
        className="mb-0"
      />
      <SaudeDaLeitura />

      <Tabs value={aba} onValueChange={(v) => setAba(v as AbaPix)}>
        <TabsList>
          <TabsTrigger value="conferir">
            Para conferir{lista.data ? ` (${lista.data.contagem_conferir})` : ""}
          </TabsTrigger>
          <TabsTrigger value="ligados">Ligados (30 dias)</TabsTrigger>
        </TabsList>
      </Tabs>

      {lista.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : lista.isError ? (
        <p role="alert" className="text-sm text-red">
          Não foi possível carregar os PIX.
        </p>
      ) : aba === "conferir" ? (
        lista.data?.itens.length ? (
          <ul className="space-y-3">
            <AnimatePresence initial={false}>
              {lista.data.itens.map((pix) => (
                <CartaoPixParaConferir key={pix.id} pix={pix} />
              ))}
            </AnimatePresence>
          </ul>
        ) : (
          <p className="rounded-md border border-line bg-panel px-4 py-6 text-center text-sm text-muted">
            Nenhum PIX esperando conferência.
          </p>
        )
      ) : lista.data?.itens.length ? (
        <ul className="divide-y divide-line rounded-md border border-line bg-panel px-4">
          {lista.data.itens.map((pix) => (
            <CartaoPixLigado key={pix.id} pix={pix} podeDesfazer={Boolean(flags?.pode_desfazer)} />
          ))}
        </ul>
      ) : (
        <p className="rounded-md border border-line bg-panel px-4 py-6 text-center text-sm text-muted">
          Nenhum PIX ligado nos últimos 30 dias.
        </p>
      )}

      {flags?.pode_resumo && (
        <Card>
          <CardContent className="space-y-2 p-4">
            <h2 className="text-base font-semibold text-ink">Recebido por conta</h2>
            <ResumoPorConta />
          </CardContent>
        </Card>
      )}

      {flags?.pode_configurar && (
        <Card>
          <CardContent className="space-y-2 p-4">
            <h2 className="text-base font-semibold text-ink">Configuração da leitura</h2>
            <ConfigPixPainel />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

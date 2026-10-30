import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, UserRound } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Skeleton } from "@manto/ui";
import {
  diaDaMensagem,
  horaNaLista,
  rotuloDoDia,
  useConversa,
  useMarcarLida,
  useMensagensAnteriores,
  type Mensagem as MensagemTipo,
} from "../../lib/conversas";
import { CaixaDeEnvio } from "./CaixaDeEnvio";
import { EnviarModeloDialog } from "./EnviarModeloDialog";
import { Mensagem } from "./Mensagem";

/**
 * A conversa aberta (feature 325, FR-014): cabeçalho com a ficha, mensagens separadas por dia,
 * "Carregar anteriores" e a caixa de envio. Rola para a última mensagem quando chega uma nova.
 *
 * Ao abrir — e quando chega mensagem nova com a conversa aberta — chama o "lida": zera a contagem
 * da equipe e dá o tique azul para a cliente. Só quando há não lidas, para o polling não ficar
 * marcando lida a cada 4 s.
 */

interface ConversaAbertaProps {
  conversaId: number;
  intervaloMs: number;
  onVoltar: () => void;
}

export function ConversaAberta({ conversaId, intervaloMs, onVoltar }: ConversaAbertaProps) {
  const dados = useConversa(conversaId, intervaloMs);
  const marcarLida = useMarcarLida();
  const queryClient = useQueryClient();
  const [modeloAberto, setModeloAberto] = useState(false);
  const [verAnteriores, setVerAnteriores] = useState(false);
  const fim = useRef<HTMLDivElement>(null);
  const mensagens = dados.data?.mensagens;
  const ultimaId = mensagens?.at(-1)?.id ?? null;
  const anteriores = useMensagensAnteriores(conversaId, mensagens?.[0]?.id ?? null, verAnteriores);

  useEffect(() => {
    setVerAnteriores(false);
  }, [conversaId]);

  const naoLidas = dados.data?.conversa.nao_lidas ?? 0;
  useEffect(() => {
    if (naoLidas > 0 && !marcarLida.isPending) marcarLida.mutate(conversaId);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só quando muda a conversa ou a contagem
  }, [conversaId, naoLidas]);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [ultimaId]);

  const todas = useMemo<MensagemTipo[]>(() => {
    const antigas = (anteriores.data?.pages ?? []).slice().reverse().flatMap((p) => p.mensagens);
    return [...antigas, ...(mensagens ?? [])];
  }, [anteriores.data, mensagens]);

  if (dados.isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-16 w-2/3" />
        <Skeleton className="ml-auto h-16 w-2/3" />
      </div>
    );
  }
  if (dados.isError || !dados.data) {
    return (
      <div className="space-y-3 p-4">
        <p role="alert" className="text-sm text-red">
          Não foi possível carregar a conversa. Tente novamente.
        </p>
        <Button type="button" variant="outline" onClick={() => void dados.refetch()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  const { conversa, tem_mais } = dados.data;
  const temMaisAntigas = verAnteriores ? anteriores.hasNextPage : tem_mais;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-2 border-b border-line bg-panel px-3 py-2">
        <Button type="button" variant="ghost" size="sm" className="md:hidden" onClick={onVoltar} aria-label="Voltar">
          <ArrowLeft className="h-5 w-5" aria-hidden />
        </Button>
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{conversa.nome}</p>
          <p className="truncate text-xs text-muted">
            {conversa.telefone_legivel ?? "Sem telefone"}
            {conversa.janela_aberta ? "" : " · janela de 24 h fechada"}
          </p>
        </div>
        {conversa.cliente ? (
          <Button asChild variant="outline" size="sm">
            <Link to={`/clientes/${conversa.cliente.id}`}>
              <UserRound className="h-4 w-4" aria-hidden />
              Ver ficha
            </Link>
          </Button>
        ) : null}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto bg-surface px-3 py-3">
        {temMaisAntigas ? (
          <div className="mb-3 text-center">
            <Button
              type="button"
              variant="outline"
              size="sm"
              loading={anteriores.isFetching}
              onClick={() => (verAnteriores ? void anteriores.fetchNextPage() : setVerAnteriores(true))}
            >
              Carregar anteriores
            </Button>
          </div>
        ) : null}
        {todas.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">Nenhuma mensagem nesta conversa ainda.</p>
        ) : (
          <ul className="space-y-2">
            {todas.map((mensagem, indice) => {
              const novoDia = indice === 0 || diaDaMensagem(todas[indice - 1]?.momento ?? null) !== diaDaMensagem(mensagem.momento);
              return (
                <Fragment key={mensagem.id}>
                  {novoDia ? (
                    <li className="py-1 text-center text-xs font-medium text-muted" aria-hidden>
                      {rotuloDoDia(mensagem.momento)}
                    </li>
                  ) : null}
                  <Mensagem mensagem={mensagem} />
                </Fragment>
              );
            })}
          </ul>
        )}
        <div ref={fim} />
      </div>

      <CaixaDeEnvio
        conversa={conversa}
        onEnviarModelo={() => setModeloAberto(true)}
        onJanelaFechou={() => void queryClient.invalidateQueries({ queryKey: ["conversas", "aberta", conversaId] })}
      />
      <EnviarModeloDialog
        conversaId={conversa.id}
        nomeDoContato={conversa.nome}
        open={modeloAberto}
        onOpenChange={setModeloAberto}
      />
      <span className="sr-only" aria-live="polite">
        {conversa.ultima_mensagem_em ? `Última mensagem às ${horaNaLista(conversa.ultima_mensagem_em)}` : ""}
      </span>
    </div>
  );
}

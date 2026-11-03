import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, UserRound } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Skeleton } from "@manto/ui";
import {
  diaDaMensagem,
  horaNaLista,
  novaChaveDeEnvio,
  rotuloDoDia,
  useConversa,
  useEnviarTexto,
  useMarcarLida,
  useMensagensAnteriores,
  type Mensagem as MensagemTipo,
  type Nota,
} from "../../lib/conversas";
import { useCurrentUser } from "../../lib/useAuth";
import { CaixaDeEnvio } from "./CaixaDeEnvio";
import { EnviarModeloDialog } from "./EnviarModeloDialog";
import { Mensagem } from "./Mensagem";
import { NotaInterna } from "./NotaInterna";
import { ResponsavelDaConversa } from "./ResponsavelDaConversa";

/**
 * A conversa aberta (feature 325, FR-014): cabeçalho com a ficha, mensagens separadas por dia,
 * "Carregar anteriores" e a caixa de envio. Rola para a última mensagem quando chega uma nova.
 *
 * Ao abrir — e quando chega mensagem nova com a conversa aberta — chama o "lida": zera a contagem
 * da equipe e dá o tique azul para a cliente. Só quando há não lidas, para o polling não ficar
 * marcando lida a cada 4 s.
 *
 * Feature 328: a faixa do responsável sob o cabeçalho, e as notas internas intercaladas às
 * mensagens pelo horário. A nota mais antiga que a primeira mensagem carregada só aparece quando
 * não há mais mensagens antigas a carregar — senão ela ficaria fora de ordem no topo.
 */

type ItemDaLinha =
  | { tipo: "mensagem"; chave: string; momento: string | null; mensagem: MensagemTipo }
  | { tipo: "nota"; chave: string; momento: string | null; nota: Nota };

function instante(iso: string | null): number {
  return iso ? Date.parse(iso) : 0;
}

/** Mensagens e notas numa linha do tempo só, por horário (o sort é estável: empate mantém a ordem). */
function linhaDoTempo(mensagens: MensagemTipo[], notas: Nota[], haMaisAntigas: boolean): ItemDaLinha[] {
  const inicio = mensagens[0]?.momento ?? null;
  const visiveis = notas.filter((n) => !haMaisAntigas || !inicio || instante(n.momento) >= instante(inicio));
  return [
    ...mensagens.map((m): ItemDaLinha => ({ tipo: "mensagem", chave: `m${m.id}`, momento: m.momento, mensagem: m })),
    ...visiveis.map((n): ItemDaLinha => ({ tipo: "nota", chave: `n${n.id}`, momento: n.momento, nota: n })),
  ].sort((a, b) => instante(a.momento) - instante(b.momento));
}

interface ConversaAbertaProps {
  conversaId: number;
  intervaloMs: number;
  onVoltar: () => void;
}

/** Junta as páginas antigas e a atual sem repetir mensagem (a mesma pode estar nas duas). */
function semRepetir(listas: MensagemTipo[][]): MensagemTipo[] {
  const vistas = new Set<number>();
  return listas.flat().filter((m) => (vistas.has(m.id) ? false : (vistas.add(m.id), true)));
}

export function ConversaAberta({ conversaId, intervaloMs, onVoltar }: ConversaAbertaProps) {
  const dados = useConversa(conversaId, intervaloMs);
  const usuario = useCurrentUser();
  const marcarLida = useMarcarLida();
  const reenviar = useEnviarTexto(conversaId);
  const queryClient = useQueryClient();
  const [modeloAberto, setModeloAberto] = useState(false);
  const [cursorDasAnteriores, setCursorDasAnteriores] = useState<number | null>(null);
  const [reenviandoId, setReenviandoId] = useState<number | null>(null);
  const fim = useRef<HTMLDivElement>(null);
  const mensagens = dados.data?.mensagens;
  const ultimaId = mensagens?.at(-1)?.id ?? null;
  const ultimaNotaId = dados.data?.notas?.at(-1)?.id ?? null;
  const anteriores = useMensagensAnteriores(conversaId, cursorDasAnteriores);

  const naoLidas = dados.data?.conversa.nao_lidas ?? 0;
  useEffect(() => {
    if (naoLidas > 0 && !marcarLida.isPending) marcarLida.mutate(conversaId);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só quando muda a conversa ou a contagem
  }, [conversaId, naoLidas]);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [ultimaId, ultimaNotaId]);

  const todas = useMemo<MensagemTipo[]>(() => {
    const antigas = (anteriores.data?.pages ?? []).slice().reverse().map((p) => p.mensagens);
    return semRepetir([...antigas, mensagens ?? []]);
  }, [anteriores.data, mensagens]);

  const haMaisAntigas = cursorDasAnteriores === null ? Boolean(dados.data?.tem_mais) : Boolean(anteriores.hasNextPage);
  const notas = dados.data?.notas;
  const itens = useMemo(() => linhaDoTempo(todas, notas ?? [], haMaisAntigas), [todas, notas, haMaisAntigas]);

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
        <Button type="button" variant="outline" loading={dados.isFetching} onClick={() => void dados.refetch()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  const { conversa } = dados.data;
  const temMaisAntigas = haMaisAntigas;

  const carregarAnteriores = () => {
    if (cursorDasAnteriores === null) setCursorDasAnteriores(todas[0]?.id ?? null);
    else void anteriores.fetchNextPage();
  };

  const tentarDeNovo = (mensagem: MensagemTipo) => {
    if (!mensagem.texto) return;
    setReenviandoId(mensagem.id);
    reenviar.mutate(
      { texto: mensagem.texto, chave_envio: novaChaveDeEnvio() },
      { onSettled: () => setReenviandoId(null) },
    );
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-2 border-b border-line bg-panel px-3 py-2">
        <Button
          type="button"
          variant="ghost"
          className="h-11 w-11 px-0 md:hidden"
          onClick={onVoltar}
          aria-label="Voltar"
        >
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
      <ResponsavelDaConversa conversa={conversa} usuarioId={usuario.data?.id ?? null} />

      <div className="min-h-0 flex-1 overflow-y-auto bg-surface px-3 py-3">
        {temMaisAntigas ? (
          <div className="mb-3 text-center">
            <Button
              type="button"
              variant="outline"
              size="sm"
              loading={anteriores.isFetching}
              onClick={carregarAnteriores}
            >
              Carregar anteriores
            </Button>
          </div>
        ) : null}
        {itens.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">Nenhuma mensagem nesta conversa ainda.</p>
        ) : (
          <ul className="space-y-2">
            {itens.map((item, indice) => {
              const novoDia =
                indice === 0 || diaDaMensagem(itens[indice - 1]?.momento ?? null) !== diaDaMensagem(item.momento);
              return (
                <Fragment key={item.chave}>
                  {novoDia ? (
                    <li className="py-1 text-center text-xs font-medium text-muted" aria-hidden>
                      {rotuloDoDia(item.momento)}
                    </li>
                  ) : null}
                  {item.tipo === "nota" ? (
                    <NotaInterna nota={item.nota} />
                  ) : (
                    <Mensagem
                      mensagem={item.mensagem}
                      onTentarDeNovo={conversa.janela_aberta ? tentarDeNovo : undefined}
                      reenviando={reenviandoId === item.mensagem.id}
                    />
                  )}
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

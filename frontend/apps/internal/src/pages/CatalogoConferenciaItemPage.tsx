import type { ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { Badge, Button, Skeleton } from "@manto/ui";
import { useAbrirArquivo } from "../components/ArquivoViewer";
import { AcrescentarPersonagem } from "../components/conferencia/AcrescentarPersonagem";
import { DecisaoDoItem } from "../components/conferencia/DecisaoDoItem";
import { GaleriaDoItem } from "../components/conferencia/GaleriaDoItem";
import { PersonagemPropostoCard } from "../components/conferencia/PersonagemPropostoCard";
import { RodapeDaConferencia } from "../components/conferencia/RodapeDaConferencia";
import {
  ROTULO_DA_SITUACAO,
  ROTULO_DO_TIPO,
  TIPOS_COM_ELENCO,
  useItemDaConferencia,
  type DetalheDaConferencia,
  type SituacaoDoItem,
} from "../lib/catalogoConferencia";
import { LinkVoltarParaLista } from "../lib/navegacao";

const COR_DA_SITUACAO: Record<SituacaoDoItem, "neutral" | "green" | "gold"> = {
  a_conferir: "neutral",
  conferido: "green",
  sem_leitura: "gold",
};

function resumoDoElenco(detalhe: DetalheDaConferencia): string {
  const personagens = detalhe.conferencia?.personagens ?? [];
  const aCriar = personagens.filter((p) => p.decisao === "criar");
  const semFoto = aCriar.filter((p) => p.sem_foto).length;
  const partes = [`${personagens.length} ${personagens.length === 1 ? "personagem" : "personagens"}`];
  partes.push(`${aCriar.length} a criar`);
  if (semFoto) partes.push(`${semFoto} sem foto`);
  return partes.join(" · ");
}

function Aviso({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-line bg-surface-2 p-3 text-sm text-ink">{children}</p>;
}

/**
 * Conferência de UM item do catálogo (feature 360): as fotos da galeria, o que a leitura propôs e
 * o que quem confere decide. Uma tela por item, com "Conferir" preso ao rodapé — no celular são
 * 352 itens, e uma página só com todos eles deixaria a ação principal fora do alcance.
 */
export function CatalogoConferenciaItemPage() {
  const params = useParams();
  const itemId = Number(params.itemId);
  const location = useLocation();
  const navigate = useNavigate();
  const reduzirMovimento = useReducedMotion();
  const abrirArquivo = useAbrirArquivo();
  const busca = new URLSearchParams(location.search);
  const query = useItemDaConferencia(Number.isInteger(itemId) ? itemId : undefined, {
    tipo: busca.get("tipo") ?? undefined,
    q: busca.get("q") ?? undefined,
  });
  const fila = `/admin/catalogo/conferencia${location.search}`;

  // `replace`: a pilha do histórico fica sempre [fila, item]. Depois de vinte itens, "voltar"
  // ainda cai na fila, no ponto em que ela estava — e não no item anterior.
  function irPara(id: number) {
    navigate(
      { pathname: `/admin/catalogo/conferencia/${id}`, search: location.search },
      { replace: true, state: location.state },
    );
  }

  function abrirFoto(url: string, nome: string) {
    abrirArquivo({ url: assetUrl(url) ?? url, nome });
  }

  const voltar = (
    <LinkVoltarParaLista to={fila} className="inline-flex min-h-11 items-center text-sm text-muted hover:text-accent">
      ‹ Fila da conferência
    </LinkVoltarParaLista>
  );

  if (!Number.isInteger(itemId)) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
        {voltar}
        <Aviso>Item não encontrado.</Aviso>
      </div>
    );
  }

  if (query.isPending) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
        {voltar}
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    const naoExiste = query.error instanceof ApiRequestError && query.error.status === 404;
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
        {voltar}
        <Aviso>{naoExiste ? "Item não encontrado." : "Não foi possível carregar o item. Tente novamente."}</Aviso>
        {!naoExiste && (
          <Button variant="outline" onClick={() => query.refetch()}>
            Tentar novamente
          </Button>
        )}
      </div>
    );
  }

  const detalhe = query.data;
  const { item, conferencia, situacao } = detalhe;
  const travado = situacao === "conferido";
  const temElenco = conferencia !== null && TIPOS_COM_ELENCO.includes(conferencia.tipo);

  return (
    <div className="mx-auto max-w-5xl px-4 pt-4 sm:px-6 sm:pt-6">
      <motion.div
        // Remonta a cada item: estados de "salvando" e erros de um item não vazam para o seguinte.
        // Prefixo na chave: o rodapé é irmão e também remonta por item — duas chaves iguais entre
        // irmãos fazem o React manter o conteúdo antigo na tela ao trocar de item.
        key={`conteudo-${item.id}`}
        initial={reduzirMovimento ? false : { opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: reduzirMovimento ? 0 : 0.2, ease: "easeOut" }}
        className="space-y-4 pb-6"
      >
        <header className="space-y-2">
          {voltar}
          <h1 className="text-2xl font-semibold leading-tight text-ink">{item.nome}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge tone={COR_DA_SITUACAO[situacao]}>{ROTULO_DA_SITUACAO[situacao]}</Badge>
            {conferencia && <Badge tone="accent">{ROTULO_DO_TIPO[conferencia.tipo]}</Badge>}
            {item.categorias.length > 0 && <span className="text-muted">{item.categorias.join(", ")}</span>}
            <Link
              to={`/admin/catalogo/${item.id}/editar`}
              className="inline-flex min-h-11 items-center font-medium text-accent underline"
            >
              Ver no catálogo
            </Link>
          </div>
        </header>

        <GaleriaDoItem nome={item.nome} fotos={item.fotos} onAbrir={abrirFoto} />

        {!detalhe.na_fila && <Aviso>Este item saiu da fila: já tem elenco ou ficha no catálogo.</Aviso>}

        {conferencia === null ? (
          <Aviso>Este item ainda não tem leitura das fotos. Cadastre o elenco no catálogo.</Aviso>
        ) : (
          <>
            {(conferencia.nota || conferencia.acao || conferencia.grupo) && (
              <section className="space-y-1 rounded-lg border border-line bg-panel p-3 text-sm" aria-label="Leitura das fotos">
                <h2 className="font-semibold text-ink">O que a leitura das fotos propôs</h2>
                {conferencia.nota && <p className="text-ink">{conferencia.nota}</p>}
                {conferencia.acao && <p className="text-ink">{conferencia.acao}</p>}
                {conferencia.grupo && <p className="text-muted">Grupo possível: {conferencia.grupo}</p>}
              </section>
            )}

            <DecisaoDoItem itemId={item.id} nomeDoItem={item.nome} conferencia={conferencia} travado={travado} />

            {temElenco ? (
              <section className="space-y-3" aria-label="Elenco proposto">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-sm font-semibold text-ink">Elenco proposto</h2>
                  <p className="text-xs text-muted">{resumoDoElenco(detalhe)}</p>
                </div>
                {conferencia.personagens.length === 0 && (
                  <p className="text-sm text-muted">Nenhum personagem proposto para este item.</p>
                )}
                {/* `grid-cols-1` + `min-w-0`: sem coluna explícita a trilha vira `auto`, cresce com o
                    conteúdo do cartão e estoura os 390 px do celular. */}
                <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2 [&>*]:min-w-0">
                  {conferencia.personagens.map((personagem) => (
                    <PersonagemPropostoCard
                      key={personagem.id}
                      itemId={item.id}
                      personagem={personagem}
                      travado={travado}
                      onAbrirFoto={abrirFoto}
                    />
                  ))}
                </ul>
                {!travado && <AcrescentarPersonagem itemId={item.id} />}
              </section>
            ) : (
              conferencia.personagens.length > 0 && (
                <p className="text-sm text-muted">
                  O elenco proposto ({conferencia.personagens.length}) fica guardado e volta a valer se o tipo voltar a
                  ser tema ou dupla.
                </p>
              )
            )}
          </>
        )}
      </motion.div>

      <RodapeDaConferencia
        key={`rodape-${item.id}`}
        itemId={item.id}
        situacao={situacao}
        conferencia={conferencia}
        anteriorId={detalhe.anterior_id}
        proximoId={detalhe.proximo_id}
        fila={fila}
        onIrPara={irPara}
      />
    </div>
  );
}

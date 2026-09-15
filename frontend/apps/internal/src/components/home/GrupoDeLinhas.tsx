import { useState, type Key, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button } from "@manto/ui";

/** Quantas linhas cada lista (ou cada grupo) mostra antes do "Mostrar todas". */
export const LIMITE_LINHAS_PAINEL = 6;

/** Sub-lista com título dentro de um painel (Ensaio, Casting, Formulários, Sem valor). */
export function PanelGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-1 pt-2 first:pt-0">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      {children}
    </div>
  );
}

/** O "Mostrar todas as N" das listas da Home — uma peça só (antes eram duas cópias). */
export function BotaoMostrarTodas({
  expandida,
  total,
  onClick,
}: {
  expandida: boolean;
  total: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="-mx-4 block w-[calc(100%+2rem)] cursor-pointer px-4 py-2 text-center text-xs font-medium text-accent hover:bg-surface-2"
    >
      {expandida ? "Mostrar menos" : `Mostrar todas as ${total}`}
    </button>
  );
}

/**
 * Aviso de lista que não carregou (feature 299, FR-032): nunca o "✓" de lista vazia, que diria
 * "em dia" justo quando ninguém sabe.
 */
export function AvisoDeFalha({
  texto,
  onTentarDeNovo,
  tentando,
}: {
  texto: string;
  onTentarDeNovo: () => void;
  tentando: boolean;
}) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-2 py-2 text-sm text-red">
      <span>{texto}</span>
      <Button type="button" variant="outline" size="sm" loading={tentando} onClick={onTentarDeNovo}>
        Tentar de novo
      </Button>
    </div>
  );
}

/**
 * Um grupo de linhas com as 6 primeiras à mostra e o resto atrás de "Mostrar todas" (298).
 *
 * Não é a `ListaTruncada` porque a linha resolvida precisa SAIR com animação, e o
 * `AnimatePresence` só acompanha filhos diretos com `key`. Com movimento reduzido a linha some
 * sem transição. Com `titulo`, o grupo ganha o cabeçalho com a contagem.
 */
export function GrupoDeLinhas<T>({
  titulo,
  itens,
  chave,
  children,
}: {
  titulo?: string;
  itens: T[];
  chave: (item: T) => Key;
  children: (item: T) => ReactNode;
}) {
  const [expandida, setExpandida] = useState(false);
  const reduceMotion = useReducedMotion();
  const visiveis = expandida ? itens : itens.slice(0, LIMITE_LINHAS_PAINEL);

  const lista = (
    <>
      <AnimatePresence initial={false}>
        {visiveis.map((item) => (
          <motion.div
            key={chave(item)}
            initial={reduceMotion ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={reduceMotion ? { opacity: 0, transition: { duration: 0 } } : { opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="-mx-4 overflow-hidden border-b border-line last:border-b-0"
          >
            {children(item)}
          </motion.div>
        ))}
      </AnimatePresence>
      {itens.length > LIMITE_LINHAS_PAINEL && (
        <BotaoMostrarTodas
          expandida={expandida}
          total={itens.length}
          onClick={() => setExpandida((v) => !v)}
        />
      )}
    </>
  );

  return titulo ? <PanelGroup title={`${titulo} (${itens.length})`}>{lista}</PanelGroup> : <div>{lista}</div>;
}

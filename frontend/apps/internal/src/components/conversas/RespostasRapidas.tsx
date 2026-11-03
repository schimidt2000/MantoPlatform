import { useEffect, useRef, type KeyboardEvent } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Search, Settings2 } from "lucide-react";
import { Button, Skeleton, cn } from "@manto/ui";
import type { RespostaRapida } from "../../lib/conversas";

/**
 * A lista de respostas rápidas sobre a caixa de envio (feature 328, FR-010/FR-011).
 *
 * Abre de dois jeitos: pelo botão (com campo de busca próprio) ou digitando "/" no começo da
 * mensagem (a busca é o que vem depois da barra, e as setas e o Enter funcionam no próprio campo).
 * Escolher uma INSERE o texto no campo — nada é enviado. No celular, o painel ocupa a largura da
 * caixa de envio, que é a da tela (FR-017).
 */

const DIACRITICOS = new RegExp("[\\u0300-\\u036f]", "g");

function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(DIACRITICOS, "").toLowerCase();
}

/** Filtra pelo título ou pelo atalho, ignorando acentos e caixa. */
export function filtrarRespostas(respostas: RespostaRapida[] | undefined, consulta: string): RespostaRapida[] {
  const termo = normalizar(consulta.trim());
  if (!respostas) return [];
  if (!termo) return respostas;
  return respostas.filter(
    (r) => normalizar(r.titulo).includes(termo) || (r.atalho ? normalizar(r.atalho).includes(termo) : false),
  );
}

export interface ControleDaLista {
  total: number;
  ativo: number;
  onAtivo: (indice: number) => void;
  onEscolherAtivo: () => void;
  onFechar: () => void;
}

/** ↑ ↓ Enter Esc na lista. Devolve true quando a tecla foi da lista (quem chama não a trata). */
export function teclaNaLista(evento: KeyboardEvent, controle: ControleDaLista): boolean {
  const { total, ativo, onAtivo, onEscolherAtivo, onFechar } = controle;
  if (evento.key === "Escape") {
    evento.preventDefault();
    onFechar();
    return true;
  }
  if (total === 0) return false;
  if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
    evento.preventDefault();
    const passo = evento.key === "ArrowDown" ? 1 : -1;
    onAtivo((ativo + passo + total) % total);
    return true;
  }
  if (evento.key === "Enter" && !evento.shiftKey) {
    evento.preventDefault();
    onEscolherAtivo();
    return true;
  }
  return false;
}

interface RespostasRapidasProps {
  idDaLista: string;
  respostas: RespostaRapida[];
  carregando: boolean;
  falhou: boolean;
  onTentarDeNovo: () => void;
  tentandoDeNovo: boolean;
  /** Com busca própria (aberta pelo botão); sem ela, a busca é o texto depois da "/". */
  busca: { valor: string; onMudar: (valor: string) => void } | null;
  controle: ControleDaLista;
  onEscolher: (resposta: RespostaRapida) => void;
  onGerenciar: () => void;
}

export function RespostasRapidas({
  idDaLista,
  respostas,
  carregando,
  falhou,
  onTentarDeNovo,
  tentandoDeNovo,
  busca,
  controle,
  onEscolher,
  onGerenciar,
}: RespostasRapidasProps) {
  const reduzir = useReducedMotion();
  const ativoRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    ativoRef.current?.scrollIntoView({ block: "nearest" });
  }, [controle.ativo]);

  return (
    <motion.div
      className="absolute inset-x-0 bottom-full z-30 mb-1 rounded-md border border-line bg-panel shadow-md"
      initial={reduzir ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
    >
      {busca ? (
        <div className="relative border-b border-line p-2">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input
            autoFocus
            value={busca.valor}
            onChange={(e) => busca.onMudar(e.target.value)}
            onKeyDown={(e) => void teclaNaLista(e, controle)}
            placeholder="Buscar resposta rápida"
            aria-label="Buscar resposta rápida"
            aria-controls={idDaLista}
            className="h-11 w-full rounded-md border border-line-strong bg-panel pl-8 pr-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-9"
          />
        </div>
      ) : null}
      <div className="max-h-64 overflow-y-auto">
        {carregando ? (
          <div className="space-y-2 p-2">
            <Skeleton className="h-11 w-full" />
            <Skeleton className="h-11 w-full" />
          </div>
        ) : falhou ? (
          <div className="space-y-2 p-3">
            <p role="alert" className="text-sm text-red">
              Não foi possível carregar as respostas rápidas. Tente novamente.
            </p>
            <Button type="button" variant="outline" size="sm" loading={tentandoDeNovo} onClick={onTentarDeNovo}>
              Tentar novamente
            </Button>
          </div>
        ) : respostas.length === 0 ? (
          <p className="p-3 text-sm text-muted">Nenhuma resposta rápida encontrada.</p>
        ) : (
          <ul id={idDaLista} role="listbox" aria-label="Respostas rápidas">
            {respostas.map((resposta, indice) => (
              <li
                key={resposta.id}
                ref={indice === controle.ativo ? ativoRef : undefined}
                role="option"
                aria-selected={indice === controle.ativo}
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => controle.onAtivo(indice)}
                onClick={() => onEscolher(resposta)}
                className={cn(
                  "min-h-11 cursor-pointer border-b border-line px-3 py-2 last:border-b-0",
                  indice === controle.ativo && "bg-surface-2",
                )}
              >
                <span className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-sm font-medium">{resposta.titulo}</span>
                  {resposta.atalho ? <span className="shrink-0 text-xs text-muted">/{resposta.atalho}</span> : null}
                </span>
                <span className="line-clamp-2 text-xs text-muted">{resposta.texto}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="border-t border-line p-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-11 w-full justify-start md:h-9"
          onMouseDown={(e) => e.preventDefault()}
          onClick={onGerenciar}
        >
          <Settings2 className="h-4 w-4" aria-hidden />
          Gerenciar respostas rápidas
        </Button>
      </div>
    </motion.div>
  );
}

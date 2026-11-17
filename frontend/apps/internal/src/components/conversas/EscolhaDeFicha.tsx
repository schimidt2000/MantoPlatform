import { useState } from "react";
import { Search } from "lucide-react";
import { Button, Input, Skeleton, cn } from "@manto/ui";
import { useClientSearch } from "../../lib/clientes";
import type { EscolhaDaFicha } from "../../lib/conversas";

/**
 * A escolha da ficha da cliente na conversa (feature 333): buscar uma existente pelo nome ou telefone, ou
 * criar uma nova com nome e telefone. Não grava nada: devolve a escolha para quem chama (o diálogo da ficha
 * ou o envio do orçamento), que manda ao servidor. A ficha nova sai do servidor com a origem "Conversa".
 */

interface EscolhaDeFichaProps {
  id: string;
  valor: EscolhaDaFicha | null;
  onMudar: (valor: EscolhaDaFicha | null) => void;
  /** No WhatsApp, o telefone da conversa já entra no "Criar ficha". */
  telefoneInicial?: string | null;
  nomeInicial?: string | null;
  erro?: ErroDaFicha | null;
}

/** O erro da ficha e o campo que ele aponta (`cliente` = a busca; `nome`; `telefone`). */
export interface ErroDaFicha {
  campo: "cliente" | "nome" | "telefone";
  mensagem: string;
}

export function EscolhaDeFicha({ id, valor, onMudar, telefoneInicial, nomeInicial, erro }: EscolhaDeFichaProps) {
  const [modo, setModo] = useState<"buscar" | "criar">("buscar");
  const [busca, setBusca] = useState("");
  const [nome, setNome] = useState(nomeInicial ?? "");
  const [telefone, setTelefone] = useState(telefoneInicial ?? "");
  const resultados = useClientSearch(busca);

  const criar = (novoNome: string, novoTelefone: string) => {
    setNome(novoNome);
    setTelefone(novoTelefone);
    onMudar(novoNome.trim() || novoTelefone.trim() ? { nome: novoNome, telefone: novoTelefone } : null);
  };

  if (valor && "client_id" in valor) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-md border border-line px-3 py-2">
        <p className="min-w-0 truncate text-sm">
          Ficha: <strong>{valor.nome}</strong>
        </p>
        <Button type="button" variant="ghost" size="sm" onClick={() => onMudar(null)}>
          Trocar
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {modo === "buscar" ? (
        <>
          <label htmlFor={`${id}-busca`} className="text-sm font-medium">
            Ficha da cliente
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
            <Input
              id={`${id}-busca`}
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar pelo nome ou telefone"
              className={cn("pl-9", erro?.campo === "cliente" && "border-red ring-1 ring-red")}
              aria-invalid={erro?.campo === "cliente" ? true : undefined}
              aria-describedby={erro ? `${id}-erro` : undefined}
            />
          </div>
          {busca.trim().length >= 2 ? (
            resultados.isLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : resultados.isError ? (
              <p role="alert" className="text-sm text-red">
                Não foi possível buscar as fichas. Tente novamente.
              </p>
            ) : (resultados.data ?? []).length === 0 ? (
              <p className="text-sm text-muted">Nenhuma ficha encontrada.</p>
            ) : (
              <ul className="max-h-48 divide-y divide-line overflow-y-auto rounded-md border border-line">
                {(resultados.data ?? []).map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      className="flex min-h-11 w-full flex-col items-start px-3 py-2 text-left hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-none"
                      onClick={() => onMudar({ client_id: c.id, nome: c.name })}
                    >
                      <span className="text-sm font-medium">{c.name}</span>
                      <span className="text-xs text-muted">{c.phone_display}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )
          ) : null}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setModo("criar");
              criar(nome, telefone);
            }}
          >
            Criar ficha
          </Button>
        </>
      ) : (
        <>
          <div className="grid gap-2 sm:grid-cols-2 [&>*]:min-w-0">
            <div className="space-y-1">
              <label htmlFor={`${id}-nome`} className="text-sm font-medium">
                Nome da cliente
              </label>
              <Input
                id={`${id}-nome`}
                value={nome}
                onChange={(e) => criar(e.target.value, telefone)}
                aria-invalid={erro?.campo === "nome" ? true : undefined}
                aria-describedby={erro?.campo === "nome" ? `${id}-erro` : undefined}
                className={cn(erro?.campo === "nome" && "border-red ring-1 ring-red")}
              />
            </div>
            <div className="space-y-1">
              <label htmlFor={`${id}-telefone`} className="text-sm font-medium">
                Telefone
              </label>
              <Input
                id={`${id}-telefone`}
                value={telefone}
                inputMode="tel"
                placeholder="Ex.: (11) 91234-5678"
                onChange={(e) => criar(nome, e.target.value)}
                aria-invalid={erro?.campo === "telefone" ? true : undefined}
                aria-describedby={erro?.campo === "telefone" ? `${id}-erro` : undefined}
                className={cn(erro?.campo === "telefone" && "border-red ring-1 ring-red")}
              />
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setModo("buscar");
              onMudar(null);
            }}
          >
            Buscar ficha
          </Button>
        </>
      )}
      {erro ? (
        <p id={`${id}-erro`} role="alert" className="text-sm text-red">
          {erro.mensagem}
        </p>
      ) : null}
    </div>
  );
}

/** O erro do servidor que é da ficha (`cliente`, `nome`, `telefone`), para mostrar no campo certo. */
export function erroDaFicha(fields: Record<string, string> | undefined): ErroDaFicha | null {
  if (!fields) return null;
  for (const campo of ["cliente", "nome", "telefone"] as const) {
    if (fields[campo]) return { campo, mensagem: fields[campo] };
  }
  return null;
}

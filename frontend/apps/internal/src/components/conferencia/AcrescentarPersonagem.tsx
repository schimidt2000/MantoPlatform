import { useState, type FormEvent } from "react";
import { Button, cn } from "@manto/ui";
import { erroDoCampo, mensagemDoErro, useAcrescentarPersonagem } from "../../lib/catalogoConferencia";

/**
 * Acrescenta ao elenco proposto um personagem que a leitura não viu (FR-005). Entra só com o nome,
 * sem foto; a ficha se escolhe depois, no cartão dele.
 */
export function AcrescentarPersonagem({ itemId }: { itemId: number }) {
  const acrescentar = useAcrescentarPersonagem(itemId);
  const [nome, setNome] = useState("");
  const erroDoNome = erroDoCampo(acrescentar.error, "nome");
  const erroGeral = erroDoNome ? null : mensagemDoErro(acrescentar.error);

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    // O nome só sai do campo depois que o servidor confirma: erro não apaga o que foi digitado.
    acrescentar.mutate({ nome }, { onSuccess: () => setNome("") });
  }

  return (
    <form onSubmit={enviar} className="rounded-lg border border-dashed border-line p-3">
      <label className="mb-1 block text-sm font-medium text-ink" htmlFor={`novo-personagem-${itemId}`}>
        Acrescentar personagem
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id={`novo-personagem-${itemId}`}
          className={cn(
            // `flex-1` só na linha (sm+): na coluna do celular ele zeraria a base e venceria o `h-11`.
            "h-11 w-full min-w-0 shrink-0 rounded-md border border-line bg-panel px-3 text-sm text-ink sm:w-auto sm:flex-1",
            erroDoNome && "border-red",
          )}
          value={nome}
          maxLength={200}
          placeholder="Nome do personagem que faltou"
          aria-invalid={Boolean(erroDoNome)}
          onChange={(e) => setNome(e.target.value)}
        />
        <Button type="submit" variant="outline" loading={acrescentar.isPending}>
          Acrescentar
        </Button>
      </div>
      {(erroDoNome || erroGeral) && <p className="mt-1 text-xs text-red">{erroDoNome ?? erroGeral}</p>}
    </form>
  );
}

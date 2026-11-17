import { useEffect, useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
} from "@manto/ui";
import { useInserirCrianca, type TextoDeConsentimento } from "../../lib/baseAutorizada";

export interface CriancaDialogProps {
  clientId: number;
  texto: TextoDeConsentimento;
  origens: string[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConcluido: (mensagem: string) => void;
}

/**
 * Inserir o aniversário de uma criança (feature 350, LGPD art. 14).
 *
 * Primeiro nome e data, nada mais. A caixa de autorização nunca vem marcada: sem ela o servidor
 * recusa e o campo é apontado. Cada criança tem o próprio aceite (irmãos são aceites separados).
 */
export function CriancaDialog({
  clientId,
  texto,
  origens,
  open,
  onOpenChange,
  onConcluido,
}: CriancaDialogProps) {
  const [nome, setNome] = useState("");
  const [nascimento, setNascimento] = useState("");
  const [origem, setOrigem] = useState("");
  const [aceite, setAceite] = useState(false);
  const inserir = useInserirCrianca(clientId);

  useEffect(() => {
    if (open) {
      setNome("");
      setNascimento("");
      setOrigem("");
      setAceite(false);
      inserir.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const campos = inserir.error instanceof ApiRequestError ? (inserir.error.fields ?? {}) : {};
  const erroGeral =
    inserir.error && Object.keys(campos).length === 0
      ? "Não foi possível salvar. Tente novamente."
      : null;

  function salvar() {
    inserir.mutate(
      { primeiro_nome: nome, nascimento, aceite, origem },
      {
        onSuccess: () => {
          onOpenChange(false);
          onConcluido("Aniversário salvo na ficha.");
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={(aberto) => !inserir.isPending && onOpenChange(aberto)}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Inserir aniversário</DialogTitle>
          <DialogDescription>
            Só com a autorização da mãe, do pai ou do responsável.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-sm text-muted">Primeiro nome da criança</span>
            <Input
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              maxLength={60}
              aria-invalid={Boolean(campos.primeiro_nome)}
              placeholder="Ex.: Lia"
            />
            {campos.primeiro_nome && (
              <p className="mt-1 text-sm text-red" role="alert">
                {campos.primeiro_nome}
              </p>
            )}
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-muted">Data de aniversário</span>
            <Input
              type="date"
              value={nascimento}
              onChange={(e) => setNascimento(e.target.value)}
              aria-invalid={Boolean(campos.nascimento)}
            />
            {campos.nascimento && (
              <p className="mt-1 text-sm text-red" role="alert">
                {campos.nascimento}
              </p>
            )}
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-muted">Por onde a responsável autorizou</span>
            {/* Quatro opções fixas: `<select>` nativo é permitido abaixo de 10 itens (XII). */}
            <select
              value={origem}
              onChange={(e) => setOrigem(e.target.value)}
              className="h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
              aria-invalid={Boolean(campos.origem)}
            >
              <option value="">Selecione…</option>
              {origens.map((opcao) => (
                <option key={opcao} value={opcao}>
                  {opcao}
                </option>
              ))}
            </select>
            {campos.origem && (
              <p className="mt-1 text-sm text-red" role="alert">
                {campos.origem}
              </p>
            )}
          </label>
          <label
            className={`flex cursor-pointer gap-3 rounded-md border px-3 py-2 text-sm text-ink ${
              campos.aceite ? "border-red" : "border-line"
            }`}
          >
            <input
              type="checkbox"
              checked={aceite}
              onChange={(e) => setAceite(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 accent-accent"
            />
            <span>
              A responsável autorizou com este texto: “{texto.texto}”
              <span className="mt-1 block text-xs text-muted">Versão {texto.versao}</span>
            </span>
          </label>
          {campos.aceite && (
            <p className="text-sm text-red" role="alert">
              {campos.aceite}
            </p>
          )}
          {erroGeral && (
            <p className="text-sm text-red" role="alert">
              {erroGeral}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={inserir.isPending}>
            Cancelar
          </Button>
          <Button onClick={salvar} loading={inserir.isPending}>
            Salvar aniversário
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

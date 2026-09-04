import { useMemo, useState } from "react";
import {
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Input,
  type ComboboxOption,
} from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { useFigurinoSheets } from "../lib/figurino";
import { useSolicitarFicha } from "../lib/figurinoProducao";

/** Remove acentos e caixa — mesmo espírito do `strip_accents_lower` do backend. */
function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

export interface FigurinoPickerProps {
  value: number | null;
  onChange: (sheetId: number | null) => void;
  /**
   * Nome do personagem: as fichas cujo nome bate sobem para o topo da lista — mesmo
   * match por nome normalizado que a impressão de fichas usa.
   */
  characterName?: string;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
  placeholder?: string;
}

/**
 * Busca visual de ficha de figurino — **a única porta para escolher uma ficha** no app.
 *
 * Nasceu na feature 215 para substituir o `<datalist>` do card de figurino (que no Chrome não
 * renderiza imagem nenhuma e só vinculava no `blur`: digitar errado significava não vincular
 * nada, sem aviso). Em 225d absorveu o `FigurinoSheetPicker` da 209, que resolvia o mesmo
 * problema com uma lista própria — duas buscas de ficha com aparências diferentes era
 * exatamente o que o Princípio de consistência proíbe, e a do design system ganha porque o
 * `Combobox` já traz filtro sem acento, teto de resultados, limpar e navegação por teclado.
 *
 * São 616 fichas: escolher por nome numa lista alfabética é inviável, e a escolha é visual por
 * natureza — daí a miniatura quadrada em cada resultado (Princípio X.2).
 */
export function FigurinoPicker({
  value,
  onChange,
  characterName,
  disabled = false,
  ariaLabel,
  className,
  placeholder,
}: FigurinoPickerProps) {
  const query = useFigurinoSheets();
  const items = query.data?.items;

  // "Solicitar ficha" (feature 237): quando a busca não tem o personagem, o pedido nasce daqui
  // e cai na fila de Produção e Compras como tipo "Ficha". O texto digitado pré-preenche o nome.
  const solicitar = useSolicitarFicha();
  const [textoDigitado, setTextoDigitado] = useState("");
  const [dialogAberto, setDialogAberto] = useState(false);
  const [personagem, setPersonagem] = useState("");
  const [observacao, setObservacao] = useState("");
  const [solicitadoMsg, setSolicitadoMsg] = useState<string | null>(null);
  const [erroMsg, setErroMsg] = useState<string | null>(null);

  function abrirSolicitacao() {
    setPersonagem(textoDigitado.trim());
    setObservacao("");
    setErroMsg(null);
    setDialogAberto(true);
  }

  function enviarSolicitacao() {
    if (!personagem.trim()) {
      setErroMsg("Diga o nome do personagem da ficha.");
      return;
    }
    setErroMsg(null);
    solicitar.mutate(
      {
        personagem: personagem.trim(),
        observacao: observacao.trim() || undefined,
        origem: window.location.pathname,
      },
      {
        onSuccess: () => {
          setDialogAberto(false);
          setSolicitadoMsg(`Ficha de "${personagem.trim()}" solicitada ao figurino.`);
        },
        onError: (err) => {
          setErroMsg(
            err instanceof ApiRequestError
              ? err.message
              : "Não foi possível solicitar a ficha.",
          );
        },
      },
    );
  }

  const options = useMemo<ComboboxOption[]>(() => {
    const sheets = items ?? [];
    const charNorm = normalize((characterName ?? "").trim());
    // Sugestão primeiro: a ficha homônima do personagem é o caso esmagadoramente comum.
    const ordered = charNorm
      ? [...sheets].sort((a, b) => {
          const aHit = normalize(a.character_name).includes(charNorm) ? 0 : 1;
          const bHit = normalize(b.character_name).includes(charNorm) ? 0 : 1;
          return aHit !== bHit ? aHit - bHit : 0;
        })
      : sheets;
    return ordered.map((sheet) => ({
      value: String(sheet.id),
      label: sheet.character_name,
      imageUrl: sheet.photo_url ? assetUrl(sheet.photo_url, { largura: 128 }) : null,
      imageShape: "square" as const,
      fallbackIcon: "👗",
    }));
  }, [items, characterName]);

  return (
    <div className={className}>
      <Combobox
        aria-label={ariaLabel ?? "Buscar ficha de figurino"}
        placeholder={placeholder ?? "🔍 Buscar ficha de figurino…"}
        emptyMessage="Nenhuma ficha encontrada."
        options={options}
        loading={query.isLoading}
        disabled={disabled}
        value={value != null ? String(value) : null}
        onChange={(next) => onChange(next ? Number(next) : null)}
        onInputValueChange={setTextoDigitado}
      />
      {!disabled && (
        <div className="mt-1 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={abrirSolicitacao}
            className="text-xs text-accent hover:underline"
          >
            Não achou? Solicitar ficha
          </button>
          {solicitadoMsg && (
            <span className="text-xs text-green" role="status">
              {solicitadoMsg}
            </span>
          )}
        </div>
      )}

      <Dialog open={dialogAberto} onOpenChange={setDialogAberto}>
        <DialogContent open={dialogAberto} className="max-w-md">
          <DialogHeader>
            <DialogTitle>Solicitar ficha ao figurino</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <p className="text-xs text-muted">
              O pedido entra na fila de Produção e Compras do figurino como tipo
              &quot;Ficha&quot;, registrando você como solicitante.
            </p>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase text-muted" htmlFor="ficha-personagem">
                Nome do personagem
              </label>
              <Input
                id="ficha-personagem"
                value={personagem}
                onChange={(e) => setPersonagem(e.target.value)}
                placeholder="Ex.: Zeca Urubu"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase text-muted" htmlFor="ficha-observacao">
                Observação (opcional)
              </label>
              <textarea
                id="ficha-observacao"
                className="h-20 w-full resize-y rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink"
                value={observacao}
                onChange={(e) => setObservacao(e.target.value)}
                placeholder="Contexto pro figurino (evento, prazo, referências)…"
              />
            </div>
            {erroMsg && (
              <p className="text-xs text-red" role="alert">
                {erroMsg}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setDialogAberto(false)}>
                Cancelar
              </Button>
              <Button size="sm" loading={solicitar.isPending} onClick={enviarSolicitacao}>
                Solicitar ficha
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

import { useEffect, useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import { Pencil, Plus, Trash2 } from "lucide-react";
import {
  Button,
  ConfirmDialog,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Skeleton,
} from "@manto/ui";
import {
  mensagemDoErro,
  useExcluirResposta,
  useRespostasRapidas,
  useSalvarResposta,
  type RespostaRapida,
} from "../../lib/conversas";

/**
 * "Gerenciar respostas rápidas" (feature 328, FR-010): a lista da equipe, com criar, editar e
 * excluir. Qualquer pessoa do Comercial mexe (decisão do dono, 03/11). Excluir pede confirmação
 * (Princípio V); a recusa do servidor (título ou atalho repetido, atalho com espaço) aparece no
 * campo certo.
 */

type Campo = "titulo" | "atalho" | "texto";
type ErrosDosCampos = Partial<Record<Campo, string>>;

interface Rascunho {
  id: number | null;
  titulo: string;
  atalho: string;
  texto: string;
}

const VAZIO: Rascunho = { id: null, titulo: "", atalho: "", texto: "" };
const CLASSE_INVALIDO = "aria-[invalid=true]:border-red aria-[invalid=true]:ring-1 aria-[invalid=true]:ring-red";

function errosDaRecusa(falha: unknown): ErrosDosCampos {
  if (!(falha instanceof ApiRequestError) || !falha.fields) return {};
  const { titulo, atalho, texto } = falha.fields as Record<string, string | undefined>;
  return { titulo, atalho, texto };
}

function FormularioDaResposta({
  rascunho,
  onMudar,
  erros,
}: {
  rascunho: Rascunho;
  onMudar: (campo: Campo, valor: string) => void;
  erros: ErrosDosCampos;
}) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label htmlFor="resposta-titulo" className="text-sm font-medium">
          Título
        </label>
        <Input
          id="resposta-titulo"
          aria-describedby={erros.titulo ? "erro-resposta-titulo" : undefined}
          value={rascunho.titulo}
          maxLength={80}
          aria-invalid={erros.titulo ? true : undefined}
          className={CLASSE_INVALIDO}
          onChange={(e) => onMudar("titulo", e.target.value)}
        />
        {erros.titulo ? (
          <p id="erro-resposta-titulo" className="text-xs text-red">
            {erros.titulo}
          </p>
        ) : null}
      </div>
      <div className="space-y-1.5">
        <label htmlFor="resposta-atalho" className="text-sm font-medium">
          Atalho (opcional)
        </label>
        <Input
          id="resposta-atalho"
          aria-describedby={erros.atalho ? "erro-resposta-atalho" : undefined}
          value={rascunho.atalho}
          maxLength={31}
          placeholder="pagamento"
          aria-invalid={erros.atalho ? true : undefined}
          className={CLASSE_INVALIDO}
          onChange={(e) => onMudar("atalho", e.target.value)}
        />
        <p className="text-xs text-muted">Digite "/" e o atalho na mensagem para encontrar esta resposta.</p>
        {erros.atalho ? (
          <p id="erro-resposta-atalho" className="text-xs text-red">
            {erros.atalho}
          </p>
        ) : null}
      </div>
      <div className="space-y-1.5">
        <label htmlFor="resposta-texto" className="text-sm font-medium">
          Texto
        </label>
        <textarea
          id="resposta-texto"
          aria-describedby={erros.texto ? "erro-resposta-texto" : undefined}
          value={rascunho.texto}
          maxLength={4096}
          rows={5}
          aria-invalid={erros.texto ? true : undefined}
          onChange={(e) => onMudar("texto", e.target.value)}
          className={`w-full rounded-md border border-line-strong bg-panel px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${CLASSE_INVALIDO}`}
        />
        <p className="text-xs text-muted">Use {"{nome}"} para o primeiro nome do contato.</p>
        {erros.texto ? (
          <p id="erro-resposta-texto" className="text-xs text-red">
            {erros.texto}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function ListaDasRespostas({
  respostas,
  onEditar,
  onExcluir,
}: {
  respostas: RespostaRapida[];
  onEditar: (resposta: RespostaRapida) => void;
  onExcluir: (resposta: RespostaRapida) => void;
}) {
  if (respostas.length === 0) {
    return <p className="py-4 text-center text-sm text-muted">Nenhuma resposta rápida cadastrada ainda.</p>;
  }
  return (
    <ul className="max-h-[50vh] divide-y divide-line overflow-y-auto rounded-md border border-line">
      {respostas.map((resposta) => (
        <li key={resposta.id} className="flex items-start gap-2 px-3 py-2">
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">
              {resposta.titulo}
              {resposta.atalho ? <span className="ml-2 text-xs font-normal text-muted">/{resposta.atalho}</span> : null}
            </span>
            <span className="line-clamp-2 text-xs text-muted">{resposta.texto}</span>
          </span>
          <Button
            type="button"
            variant="ghost"
            className="h-11 w-11 shrink-0 px-0"
            aria-label={`Editar ${resposta.titulo}`}
            onClick={() => onEditar(resposta)}
          >
            <Pencil className="h-4 w-4" aria-hidden />
          </Button>
          <Button
            type="button"
            variant="ghost"
            className="h-11 w-11 shrink-0 px-0 text-red"
            aria-label={`Excluir ${resposta.titulo}`}
            onClick={() => onExcluir(resposta)}
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </Button>
        </li>
      ))}
    </ul>
  );
}

interface GerenciarRespostasDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GerenciarRespostasDialog({ open, onOpenChange }: GerenciarRespostasDialogProps) {
  const respostas = useRespostasRapidas(open);
  const salvar = useSalvarResposta();
  const excluir = useExcluirResposta();
  const [rascunho, setRascunho] = useState<Rascunho | null>(null);
  const [erros, setErros] = useState<ErrosDosCampos>({});
  const [erro, setErro] = useState<string | null>(null);
  const [aExcluir, setAExcluir] = useState<RespostaRapida | null>(null);

  useEffect(() => {
    if (!open) {
      setRascunho(null);
      setErros({});
      setErro(null);
    }
  }, [open]);

  const editar = (resposta: RespostaRapida | null) => {
    setErros({});
    setErro(null);
    setRascunho(resposta ? { ...resposta, atalho: resposta.atalho ?? "" } : VAZIO);
  };

  const mudar = (campo: Campo, valor: string) => {
    setRascunho((atual) => (atual ? { ...atual, [campo]: valor } : atual));
    setErros((atuais) => ({ ...atuais, [campo]: undefined }));
  };

  const gravar = () => {
    if (!rascunho) return;
    setErro(null);
    salvar.mutate(
      { id: rascunho.id, titulo: rascunho.titulo, atalho: rascunho.atalho || null, texto: rascunho.texto },
      {
        onSuccess: () => setRascunho(null),
        onError: (falha) => {
          const doCampo = errosDaRecusa(falha);
          setErros(doCampo);
          // O foco vai ao primeiro campo apontado (Princípio V).
          const primeiro = (["titulo", "atalho", "texto"] as const).find((c) => doCampo[c]);
          if (primeiro) document.getElementById(`resposta-${primeiro}`)?.focus();
          // Com o erro apontado no campo, não repete a mesma frase no rodapé.
          const noCampo = Object.values(doCampo).some(Boolean);
          setErro(noCampo ? null : mensagemDoErro(falha, "Não foi possível gravar a resposta. Tente novamente."));
        },
      },
    );
  };

  const confirmarExclusao = () => {
    if (!aExcluir) return;
    excluir.mutate(aExcluir.id, { onSuccess: () => setAExcluir(null) });
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent open={open} className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{rascunho ? (rascunho.id ? "Editar resposta rápida" : "Nova resposta rápida") : "Respostas rápidas"}</DialogTitle>
            <DialogDescription>
              Textos prontos da equipe. Escolher um na conversa coloca o texto no campo, sem enviar.
            </DialogDescription>
          </DialogHeader>
          {rascunho ? (
            <FormularioDaResposta rascunho={rascunho} onMudar={mudar} erros={erros} />
          ) : respostas.isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : respostas.isError ? (
            <div className="space-y-2">
              <p role="alert" className="text-sm text-red">
                Não foi possível carregar as respostas rápidas. Tente novamente.
              </p>
              <Button type="button" variant="outline" loading={respostas.isFetching} onClick={() => void respostas.refetch()}>
                Tentar novamente
              </Button>
            </div>
          ) : (
            <ListaDasRespostas respostas={respostas.data?.respostas ?? []} onEditar={editar} onExcluir={setAExcluir} />
          )}
          {erro ? (
            <p role="alert" className="text-sm text-red">
              {erro}
            </p>
          ) : null}
          <DialogFooter>
            {rascunho ? (
              <>
                <Button type="button" variant="outline" onClick={() => setRascunho(null)} disabled={salvar.isPending}>
                  Cancelar
                </Button>
                <Button type="button" onClick={gravar} loading={salvar.isPending}>
                  {salvar.isPending ? "Salvando…" : "Salvar"}
                </Button>
              </>
            ) : (
              <>
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                  Fechar
                </Button>
                <Button type="button" onClick={() => editar(null)}>
                  <Plus className="h-4 w-4" aria-hidden />
                  Nova resposta
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={aExcluir !== null}
        title="Excluir esta resposta?"
        description={aExcluir ? `"${aExcluir.titulo}" sai da lista da equipe inteira.` : ""}
        confirmLabel="Excluir"
        destructive
        pending={excluir.isPending}
        error={excluir.error ? mensagemDoErro(excluir.error, "Não foi possível excluir. Tente novamente.") : null}
        onConfirm={confirmarExclusao}
        onOpenChange={(aberto) => {
          if (!aberto) {
            setAExcluir(null);
            excluir.reset();
          }
        }}
      />
    </>
  );
}

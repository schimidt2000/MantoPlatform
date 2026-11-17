import { useEffect, useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Skeleton,
} from "@manto/ui";
import { copyToClipboard } from "../../lib/clipboard";
import {
  dataCurta,
  usePosEvento,
  useRegistrarPosEvento,
  type SituacaoDoPosEvento,
} from "../../lib/baseAutorizada";

const ESPERA_DAS_FOTOS_MS = 400;

const SITUACAO: Record<SituacaoDoPosEvento, string> = {
  pendente: "Pendente",
  copiado: "Copiado",
  conversa: "Enviado pela conversa",
};

export interface PosEventoDialogProps {
  /** `null` = fechado. */
  eventId: number | null;
  onClose: () => void;
  onAviso: (mensagem: string) => void;
}

/** O valor do campo, mas só depois de a pessoa parar de digitar (a prévia relê no servidor). */
function useDepoisDeDigitar(valor: string): string {
  const [estavel, setEstavel] = useState(valor);
  useEffect(() => {
    const espera = window.setTimeout(() => setEstavel(valor), ESPERA_DAS_FOTOS_MS);
    return () => window.clearTimeout(espera);
  }, [valor]);
  return estavel;
}

function erroDoCampo(erro: unknown, campo: string): string | undefined {
  return erro instanceof ApiRequestError ? erro.fields?.[campo] : undefined;
}

/**
 * O pós-evento único (feature 350): uma mensagem com fotos, avaliação, indicação e o convite para
 * receber novidades, montada no servidor (a mesma que vai pela conversa).
 *
 * "Copiar mensagem" copia a prévia já na tela, dentro do toque (o Safari recusa copiar depois de
 * uma espera), e só então registra. "Enviar pela conversa" só aparece ativo com o CRM ligado, a
 * conversa da contratante e a janela de 24 h aberta — o motivo aparece quando não dá.
 */
export function PosEventoDialog({ eventId, onClose, onAviso }: PosEventoDialogProps) {
  const [fotos, setFotos] = useState("");
  const fotosEstavel = useDepoisDeDigitar(fotos);
  const previa = usePosEvento(eventId, fotosEstavel);
  const registrar = useRegistrarPosEvento(eventId);
  const [falhaAoCopiar, setFalhaAoCopiar] = useState(false);
  const aberto = eventId !== null;

  useEffect(() => {
    if (aberto) {
      setFotos("");
      setFalhaAoCopiar(false);
      registrar.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId]);

  useEffect(() => {
    // O link já gravado volta para o campo na primeira leitura.
    if (previa.data?.fotos_url && fotos === "" && fotosEstavel === "") setFotos(previa.data.fotos_url);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previa.data?.fotos_url]);

  const dados = previa.data;
  const erroDasFotos = erroDoCampo(previa.error, "fotos_url") ?? erroDoCampo(registrar.error, "fotos_url");
  const erroGeral =
    previa.error && !erroDasFotos
      ? previa.error instanceof ApiRequestError
        ? previa.error.message
        : "Não foi possível montar a mensagem. Tente novamente."
      : registrar.error && !erroDasFotos
        ? registrar.error instanceof ApiRequestError
          ? registrar.error.message
          : "Não foi possível registrar. Tente novamente."
        : null;

  async function copiar() {
    if (!dados) return;
    setFalhaAoCopiar(false);
    const copiou = await copyToClipboard(dados.mensagem);
    if (!copiou) {
      // O aviso fica DENTRO do diálogo (o da página estaria atrás da sobreposição) e nada é
      // registrado: só conta como "copiado" o que de fato foi para a área de transferência.
      setFalhaAoCopiar(true);
      return;
    }
    registrar.mutate(
      { canal: "copiado", fotos_url: fotos },
      {
        onSuccess: () => {
          onAviso("Mensagem do pós-evento copiada.");
          onClose();
        },
      },
    );
  }

  function enviar() {
    registrar.mutate(
      { canal: "conversa", fotos_url: fotos },
      {
        onSuccess: () => {
          onAviso("Pós-evento enviado pela conversa.");
          onClose();
        },
      },
    );
  }

  return (
    <Dialog open={aberto} onOpenChange={(abrir) => !abrir && !registrar.isPending && onClose()}>
      <DialogContent open={aberto} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Pós-evento</DialogTitle>
          <DialogDescription>
            Uma mensagem só, no dia seguinte: agradecimento, fotos, avaliação, indicação e o convite
            para receber novidades.
          </DialogDescription>
        </DialogHeader>

        {dados && (
          <div className="flex flex-wrap gap-2">
            <Badge tone={dados.situacao === "pendente" ? "neutral" : "green"}>
              {SITUACAO[dados.situacao]}
              {dados.registrado_em ? ` em ${dataCurta(dados.registrado_em)}` : ""}
            </Badge>
            {dados.avaliacao_recebida && <Badge tone="blue">Avaliação recebida</Badge>}
          </div>
        )}

        <label className="block">
          <span className="mb-1 block text-sm text-muted">Link das fotos (opcional)</span>
          <Input
            type="url"
            inputMode="url"
            value={fotos}
            onChange={(e) => setFotos(e.target.value)}
            placeholder="https://…"
            aria-invalid={Boolean(erroDasFotos)}
          />
          {erroDasFotos && (
            <p className="mt-1 text-sm text-red" role="alert">
              {erroDasFotos}
            </p>
          )}
        </label>

        {previa.isLoading && !dados ? (
          <Skeleton className="h-48 w-full" />
        ) : dados ? (
          <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-line bg-surface-2 p-3 font-sans text-sm text-ink">
            {dados.mensagem}
          </pre>
        ) : null}

        {dados && !dados.conversa.pode_enviar && dados.conversa.motivo && (
          <p className="text-sm text-muted">{dados.conversa.motivo}</p>
        )}
        {erroGeral && (
          <p className="text-sm text-red" role="alert">
            {erroGeral}
          </p>
        )}
        {falhaAoCopiar && (
          <p className="text-sm text-red" role="alert">
            Não foi possível copiar. Selecione o texto da mensagem e copie à mão.
          </p>
        )}

        {/* Três botões não cabem numa linha em 390 px: quebram em vez de sair da tela. */}
        <DialogFooter className="flex-wrap">
          <Button variant="ghost" onClick={onClose} disabled={registrar.isPending}>
            Fechar
          </Button>
          <Button
            variant="outline"
            onClick={enviar}
            loading={registrar.isPending && registrar.variables?.canal === "conversa"}
            disabled={!dados?.conversa.pode_enviar || registrar.isPending || dados?.situacao === "conversa"}
          >
            Enviar pela conversa
          </Button>
          <Button
            onClick={copiar}
            loading={registrar.isPending && registrar.variables?.canal === "copiado"}
            // A prévia tem de estar com o link que está no campo (ele relê depois de digitar).
            disabled={!dados || registrar.isPending || previa.isFetching || fotos.trim() !== fotosEstavel.trim()}
          >
            Copiar mensagem
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

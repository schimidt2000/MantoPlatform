import { useEffect, useState } from "react";
import { Smartphone } from "lucide-react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Skeleton,
  cn,
} from "@manto/ui";
import {
  AvisosNegados,
  type EstadoDosAvisos,
  ativarAvisos,
  desativarAvisos,
  estadoDosAvisos,
  useChaveDosAvisos,
} from "../../lib/avisos";

/**
 * "Avisos no celular" (feature 332, FR-001/FR-002): ativar ou desativar os avisos das Conversas
 * neste aparelho. Cada aparelho é ativado à parte; quem tocar no aviso cai na conversa.
 */

const TEXTO_DO_ESTADO: Record<EstadoDosAvisos, string> = {
  desligado: "Os avisos no celular ainda não foram configurados.",
  sem_suporte: "Este navegador não recebe avisos.",
  iphone_fora_da_tela_de_inicio:
    "No iPhone, adicione a Plataforma à Tela de Início (Compartilhar → Adicionar à Tela de Início) e abra por lá para ativar.",
  negado: "O navegador bloqueou os avisos. Libere nas configurações do navegador e tente novamente.",
  inativo: "Os avisos estão desativados neste aparelho.",
  ativo: "Os avisos estão ativados neste aparelho.",
};

export function AvisosNoCelular() {
  const [aberto, setAberto] = useState(false);
  const chave = useChaveDosAvisos(true);
  const [estado, setEstado] = useState<EstadoDosAvisos | null>(null);
  const [falhouEstado, setFalhouEstado] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  const [ocupado, setOcupado] = useState<"ativar" | "desativar" | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const chavePublica = chave.data?.chave_publica ?? null;
  useEffect(() => {
    if (!chave.data) return;
    let vivo = true;
    setFalhouEstado(false);
    estadoDosAvisos(chavePublica).then(
      (novo) => {
        if (vivo) setEstado(novo);
      },
      () => {
        if (vivo) setFalhouEstado(true);
      },
    );
    return () => {
      vivo = false;
    };
  }, [chave.data, chavePublica, tentativa]);

  /** Relê o estado depois de uma falha; se até a leitura falhar, a tela oferece "Tentar novamente". */
  const releEstado = async () => {
    try {
      setEstado(await estadoDosAvisos(chavePublica));
    } catch {
      setFalhouEstado(true);
    }
  };

  useEffect(() => {
    if (!aberto) setErro(null);
  }, [aberto]);

  const ativar = async () => {
    if (!chavePublica) return;
    setErro(null);
    setOcupado("ativar");
    try {
      await ativarAvisos(chavePublica);
      setEstado("ativo");
    } catch (falha) {
      if (falha instanceof AvisosNegados) await releEstado();
      else setErro("Não foi possível ativar os avisos. Tente novamente.");
    } finally {
      setOcupado(null);
    }
  };

  const desativar = async () => {
    setErro(null);
    setOcupado("desativar");
    try {
      await desativarAvisos();
      setEstado("inativo");
    } catch {
      setErro("Não foi possível desativar os avisos. Tente novamente.");
      await releEstado();
    } finally {
      setOcupado(null);
    }
  };

  const ativo = estado === "ativo";
  return (
    <>
      <Button
        type="button"
        variant="outline"
        className={cn("h-11 w-11 shrink-0 px-0", ativo && "text-accent")}
        aria-label="Avisos no celular"
        title="Avisos no celular"
        onClick={() => setAberto(true)}
      >
        <Smartphone className="h-4 w-4" aria-hidden />
      </Button>
      <Dialog open={aberto} onOpenChange={setAberto}>
        <DialogContent open={aberto} className="max-w-md">
          <DialogHeader>
            <DialogTitle>Avisos no celular</DialogTitle>
            <DialogDescription>
              O aparelho avisa quando uma cliente escreve, quando alguém espera resposta há 15 minutos e quando uma
              conversa é transferida para você. Cada aparelho é ativado à parte.
            </DialogDescription>
          </DialogHeader>
          {chave.isError || falhouEstado ? (
            <div className="space-y-2">
              <p role="alert" className="text-sm text-red">
                Não foi possível carregar os avisos. Tente novamente.
              </p>
              <Button
                type="button"
                variant="outline"
                loading={chave.isFetching}
                onClick={() => (chave.isError ? void chave.refetch() : setTentativa((n) => n + 1))}
              >
                Tentar novamente
              </Button>
            </div>
          ) : estado === null ? (
            <Skeleton className="h-5 w-full" />
          ) : (
            <p className="text-sm" aria-live="polite">
              {TEXTO_DO_ESTADO[estado]}
            </p>
          )}
          {erro ? (
            <p role="alert" className="text-sm text-red">
              {erro}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setAberto(false)} disabled={ocupado !== null}>
              Fechar
            </Button>
            {estado === "inativo" ? (
              <Button type="button" onClick={() => void ativar()} loading={ocupado === "ativar"}>
                {ocupado === "ativar" ? "Ativando…" : "Ativar avisos"}
              </Button>
            ) : null}
            {estado === "ativo" ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => void desativar()}
                loading={ocupado === "desativar"}
              >
                {ocupado === "desativar" ? "Desativando…" : "Desativar avisos"}
              </Button>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

import { useState } from "react";
import { Badge, Button } from "@manto/ui";
import { useClientDetail } from "../../lib/clientes";
import type { ConversaResumo } from "../../lib/conversas";
import { AceiteDeNovidadesDialog } from "../clientes/AceiteDeNovidadesDialog";

/**
 * Feature 350: o aceite de novidades da ficha, logo abaixo do cabeçalho da conversa.
 *
 * Quando a cliente diz "quero receber" na conversa, a vendedora registra aqui mesmo — a origem já
 * vem "Conversa" e a referência da conversa vai para o histórico como prova. O "SAIR" da cliente
 * retira sozinho (servidor). Sem ficha ligada, nada aparece: não há onde gravar.
 */
export function AceiteNaConversa({ conversa }: { conversa: ConversaResumo }) {
  const [aberto, setAberto] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const cliente = conversa.cliente;
  // A ficha traz os textos e a lista de origens (uma fonte só); só é lida quando há ficha.
  const ficha = useClientDetail(cliente ? cliente.id : Number.NaN);
  if (!cliente || cliente.aceite_novidades === undefined) return null;
  const consentimentos = ficha.data?.consentimentos;
  const podeEditar = Boolean(ficha.data?.flags?.pode_editar_base);

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-line bg-panel px-3 py-1.5 text-xs">
      <span className="text-muted">Novidades:</span>
      {cliente.aceite_novidades ? <Badge tone="green">Autorizou</Badge> : <Badge>Sem aceite</Badge>}
      {aviso && (
        <span className="text-green" role="status">
          {aviso}
        </span>
      )}
      {consentimentos && podeEditar && (
        <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setAberto(true)}>
          {cliente.aceite_novidades ? "Retirar aceite" : "Registrar aceite"}
        </Button>
      )}
      {consentimentos && (
        <AceiteDeNovidadesDialog
          clientId={cliente.id}
          nome={cliente.nome}
          ativo={Boolean(cliente.aceite_novidades)}
          texto={consentimentos.textos.novidades}
          origens={consentimentos.origens}
          origemPadrao="Conversa"
          referencia={`conversa:${conversa.id}`}
          open={aberto}
          onOpenChange={setAberto}
          onConcluido={setAviso}
        />
      )}
    </div>
  );
}

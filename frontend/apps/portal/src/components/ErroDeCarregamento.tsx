import { Button } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";

interface ErroDeCarregamentoProps {
  /** O erro que a consulta devolveu. */
  erro: unknown;
  /** O que a tela tentava carregar, em minúsculas: "sua agenda", "seus convites". */
  oQue: string;
  /** Refaz a consulta. */
  aoTentarDeNovo: () => void;
  carregando?: boolean;
}

/**
 * O recado de falha do portal (feature 294) — um por causa, não um para todas.
 *
 * O portal imprimia "Não foi possível carregar sua agenda." para qualquer falha. Um artista que
 * lê isso não tem o que fazer, e quem recebe o relato não tem o que investigar: a mesma frase
 * cobria sessão expirada, servidor fora do ar e 4G que caiu no elevador. Foi assim que o caso do
 * portal ficou meses sem fechar.
 *
 * A sessão expirada não chega aqui: o `main.tsx` trata o 401 globalmente e o `RequireTalentAuth`
 * leva a pessoa ao login guardando para onde ela ia. O que sobra é falha de rede ou de servidor —
 * e essas têm conserto do lado de quem lê: tentar de novo.
 */
export function ErroDeCarregamento({
  erro,
  oQue,
  aoTentarDeNovo,
  carregando,
}: ErroDeCarregamentoProps) {
  const status = erro instanceof ApiRequestError ? erro.status : null;
  const semRede = status === null;

  return (
    <div className="p-4">
      <div className="space-y-3 rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
        <p>
          {semRede
            ? `Não conseguimos falar com o servidor para carregar ${oQue}. Verifique sua conexão.`
            : `Deu um erro do nosso lado ao carregar ${oQue}. Já estamos avisados.`}
        </p>
        <Button variant="outline" onClick={aoTentarDeNovo} loading={carregando}>
          Tentar de novo
        </Button>
        {status !== null && (
          // O código é o que transforma "o portal não abre" num relato investigável.
          <p className="text-xs opacity-70">Se precisar contar para a equipe: erro {status}.</p>
        )}
      </div>
    </div>
  );
}

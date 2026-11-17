import { useMemo } from "react";
import { Combobox, type ComboboxOption } from "@manto/ui";
import { normalizarNomeFornecedor, useFornecedores, type Fornecedor } from "../../lib/fornecedores";

export interface FornecedorCampoProps {
  id?: string;
  /** O nome no formulário (o escolhido ou o digitado). */
  nome: string;
  /** O fornecedor escolhido na sugestão; `null` quando a pessoa digitou. */
  fornecedorId: number | null;
  invalid?: boolean;
  /** Digitar desfaz a escolha: vale o texto (o servidor liga pelo nome ou cadastra). */
  onDigitar: (texto: string) => void;
  /** Escolher preenche o formulário com nome, PIX e categoria do cadastro. */
  onEscolher: (fornecedor: Fornecedor) => void;
}

function opcao(f: Fornecedor): ComboboxOption {
  return {
    value: String(f.id),
    label: f.nome,
    // PIX na segunda linha também entra na busca: dá para achar o fornecedor pelo CPF ou e-mail.
    description: [f.pix, f.categoria_padrao].filter(Boolean).join(" · ") || null,
    imageShape: "circle",
  };
}

/**
 * Campo do fornecedor no gasto extra (feature 352): `Combobox` em texto livre sobre o cadastro.
 *
 * A lista dos ativos vem uma vez e filtra no navegador, ignorando acento. Abaixo do campo, o aviso
 * do que vai acontecer ao salvar: nome novo vira fornecedor; nome já cadastrado em outra grafia
 * fica com a grafia do cadastro.
 */
export function FornecedorCampo({ id, nome, fornecedorId, invalid, onDigitar, onEscolher }: FornecedorCampoProps) {
  const query = useFornecedores();
  const ativos = useMemo(
    () => (query.data?.fornecedores ?? []).filter((f) => f.ativo),
    [query.data],
  );
  const opcoes = useMemo(() => ativos.map(opcao), [ativos]);

  // O aviso compara com a lista inteira do payload: o Financeiro recebe também os arquivados, e o
  // servidor liga o gasto a um arquivado de mesmo nome (não cria outro).
  const normalizado = normalizarNomeFornecedor(nome);
  const igual = normalizado
    ? (query.data?.fornecedores ?? []).find((f) => normalizarNomeFornecedor(f.nome) === normalizado)
    : undefined;

  let aviso: string | null = null;
  if (fornecedorId === null && normalizado && query.data) {
    if (!igual) aviso = "Fornecedor novo: ficará salvo para os próximos gastos.";
    else if (!igual.ativo) aviso = `Fornecedor arquivado: o gasto será ligado a “${igual.nome}”.`;
    else if (igual.nome !== nome.trim()) aviso = `Já cadastrado: o gasto será salvo como “${igual.nome}”.`;
  }

  return (
    <div>
      <Combobox
        id={id}
        freeSolo
        options={opcoes}
        value={nome}
        loading={query.isLoading}
        invalid={invalid}
        placeholder="Digite o nome do fornecedor"
        emptyMessage="Nenhum fornecedor encontrado."
        aria-label="Nome do fornecedor"
        onChange={(texto, escolhida) => {
          const fornecedor = escolhida ? ativos.find((f) => String(f.id) === escolhida.value) : undefined;
          if (fornecedor) onEscolher(fornecedor);
          else onDigitar(texto ?? "");
        }}
      />
      {aviso && <p className="mt-1 text-xs text-muted">{aviso}</p>}
    </div>
  );
}

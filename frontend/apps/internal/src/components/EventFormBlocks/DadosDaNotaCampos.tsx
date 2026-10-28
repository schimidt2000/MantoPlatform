import type { Ref } from "react";
import {
  OBSERVACOES_MAX,
  formatarDoc,
  type DadosDaNota,
  type ErrosDaNota,
} from "../../lib/notaFiscal";
import { FIELD, FIELD_ERROR, FieldError, HELP, LABEL } from "./shared";

export interface DadosDaNotaCamposProps {
  valor: DadosDaNota;
  onChange: (patch: Partial<DadosDaNota>) => void;
  erros?: ErrosDaNota;
  /** O documento do cadastro do cliente, mostrado como o que vale com o campo em branco. */
  docDoCliente?: string | null;
  /** Para o foco chegar ao campo do erro (Princípio V). */
  refDoc?: Ref<HTMLInputElement>;
  refMunicipio?: Ref<HTMLInputElement>;
  /** Prefixo dos ids — a tela do evento e o card Comercial podem coexistir. */
  idPrefixo?: string;
}

/**
 * Os dados da nota (feature 323), abertos quando a venda "precisa de nota fiscal". Componente
 * controlado: serve ao formulário do evento (react-hook-form) e ao card Comercial (`useState`).
 */
export function DadosDaNotaCampos({
  valor,
  onChange,
  erros,
  docDoCliente,
  refDoc,
  refMunicipio,
  idPrefixo = "nota",
}: DadosDaNotaCamposProps) {
  const id = (campo: string) => `${idPrefixo}_${campo}`;
  const docCadastro = docDoCliente ? formatarDoc(docDoCliente) : null;

  return (
    <fieldset className="space-y-3 rounded-lg border border-line bg-surface-2/40 p-3">
      <legend className="px-1 text-sm font-medium text-ink">Dados da nota</legend>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL} htmlFor={id("tomador_doc")}>
            CNPJ ou CPF do tomador
          </label>
          <input
            id={id("tomador_doc")}
            ref={refDoc}
            inputMode="numeric"
            className={erros?.nota_tomador_doc ? FIELD_ERROR : FIELD}
            value={valor.tomador_doc}
            placeholder={docCadastro ?? "00.000.000/0000-00"}
            onChange={(e) => onChange({ tomador_doc: e.target.value })}
            onBlur={(e) => onChange({ tomador_doc: formatarDoc(e.target.value) })}
          />
          <FieldError message={erros?.nota_tomador_doc} />
          {!erros?.nota_tomador_doc && (
            <p className={HELP}>
              {docCadastro
                ? `Em branco, vale o do cadastro do cliente: ${docCadastro}.`
                : "Em branco, vale o do cadastro do cliente."}
            </p>
          )}
        </div>
        <div>
          <label className={LABEL} htmlFor={id("referencia")}>
            Referência do cliente
          </label>
          <input
            id={id("referencia")}
            className={FIELD}
            value={valor.referencia}
            placeholder="Ex.: AF 618/2026"
            maxLength={120}
            onChange={(e) => onChange({ referencia: e.target.value })}
          />
          <p className={HELP}>Pedido de compra ou AF, se o cliente informou.</p>
        </div>
      </div>

      <label className="flex min-h-11 items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          className="h-5 w-5"
          checked={valor.iss_retido}
          onChange={(e) => onChange({ iss_retido: e.target.checked })}
        />
        ISS retido pelo tomador
      </label>

      {valor.iss_retido && (
        <div>
          <label className={LABEL} htmlFor={id("municipio")}>
            Município da prestação *
          </label>
          <input
            id={id("municipio")}
            ref={refMunicipio}
            className={erros?.nota_municipio ? FIELD_ERROR : FIELD}
            value={valor.municipio}
            placeholder="Ex.: Jundiaí - SP"
            maxLength={120}
            onChange={(e) => onChange({ municipio: e.target.value })}
          />
          <FieldError message={erros?.nota_municipio} />
        </div>
      )}

      <div>
        <label className={LABEL} htmlFor={id("observacoes")}>
          Observações para a nota
        </label>
        <textarea
          id={id("observacoes")}
          rows={3}
          maxLength={OBSERVACOES_MAX}
          className={`w-full rounded-md border bg-panel px-2 py-2 text-sm text-ink ${
            erros?.nota_observacoes ? "border-2 border-red" : "border-line"
          }`}
          value={valor.observacoes}
          placeholder="O que o cliente pediu para constar na nota"
          onChange={(e) => onChange({ observacoes: e.target.value })}
        />
        <FieldError message={erros?.nota_observacoes} />
      </div>
    </fieldset>
  );
}

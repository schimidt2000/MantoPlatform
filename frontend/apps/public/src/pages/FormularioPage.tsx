import { useFormSchema } from "../lib/formularios";
import { DynamicForm } from "../components/formularios/DynamicForm";
import type { FormType } from "../lib/formularios";

interface FormularioPageProps {
  formType: FormType;
}

/** Usada por `/f/pre-contrato` (formType="comum") e `/f/corporativo` (formType="corporativo"). */
export function FormularioPage({ formType }: FormularioPageProps) {
  const schema = useFormSchema(formType);

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <header className="mb-4">
        <h1 className="font-display text-2xl text-ink">
          {schema.data?.header ?? "Formulário"}
        </h1>
        <p className="text-sm text-muted">Manto Produções</p>
      </header>
      <DynamicForm formType={formType} />
    </div>
  );
}

import { CadastroForm } from "../components/cadastro/CadastroForm";

export function CadastroPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <header className="mb-4">
        <h1 className="font-display text-2xl text-ink">Banco de Talentos</h1>
        <p className="text-sm text-muted">Manto Produções</p>
      </header>
      <div className="mb-4 rounded-lg border border-line bg-accent-soft p-4 text-sm text-ink">
        Preencha este formulário para fazer parte do nosso banco de talentos. Os dados não serão
        compartilhados e serão utilizados pela empresa apenas para seleção em eventos e envio de
        documentos quando necessário (liberação em eventos específicos e/ou compra de passagens).
        Os campos com <span className="text-red">*</span> são obrigatórios — e você envia as
        fotos/documentos <strong>direto por aqui</strong>, sem precisar de espaço no Google Drive.
      </div>
      <CadastroForm />
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Camera, X } from "lucide-react";
import { Button } from "@manto/ui";

export interface FotosDoPedidoPickerProps {
  fotos: File[];
  onChange: (fotos: File[]) => void;
  disabled?: boolean;
  /** Texto de apoio — muda com o tipo do pedido ("mostre o defeito" vs "o que comprar"). */
  ajuda?: string;
}

/** Teto por foto ANTES de subir. Acima disto quase sempre é vídeo ou arquivo trocado. */
const MAX_BYTES = 25 * 1024 * 1024;

function formatarTamanho(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Fotos anexadas já na abertura do pedido (feature 225g) — opcionais, quantas quiser, nos três
 * tipos.
 *
 * Existe porque a foto é o enunciado do pedido, não um complemento dele: "tem uma peça solta
 * dentro do boneco" com a foto do defeito é um pedido que a oficina entende sem ligar de volta.
 * Antes só dava para anexar DEPOIS de criar, na tela de detalhe — e lá o anexo exige permissão de
 * execução, então quem abria o pedido muitas vezes não conseguia anexar nada.
 *
 * A compressão fica no servidor (`storage.save_file`: lado máximo 1200px, JPEG qualidade 85), a
 * mesma de todo upload do app. Aqui só se barra o arquivo absurdo, para não gastar a franquia de
 * quem está num salão de festa no 4G.
 */
export function FotosDoPedidoPicker({
  fotos,
  onChange,
  disabled = false,
  ajuda,
}: FotosDoPedidoPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  // Arquivo recusado por tamanho tem de DIZER que foi recusado: sumir da lista sem explicação é
  // a pessoa achar que anexou e o pedido chegar sem a foto do defeito.
  const [recusados, setRecusados] = useState<string[]>([]);
  // Uma URL de objeto por arquivo, revogada quando o arquivo sai da lista ou o diálogo fecha —
  // sem isto cada foto escolhida vaza um blob pela sessão inteira.
  const urls = useRef(new Map<File, string>());

  const urlDe = (file: File): string => {
    let url = urls.current.get(file);
    if (!url) {
      url = URL.createObjectURL(file);
      urls.current.set(file, url);
    }
    return url;
  };

  useEffect(() => {
    const mapa = urls.current;
    for (const [file, url] of mapa) {
      if (!fotos.includes(file)) {
        URL.revokeObjectURL(url);
        mapa.delete(file);
      }
    }
  }, [fotos]);

  useEffect(
    () => () => {
      const mapa = urls.current;
      for (const url of mapa.values()) URL.revokeObjectURL(url);
      mapa.clear();
    },
    [],
  );

  function acrescentar(escolhidos: FileList | null) {
    if (!escolhidos?.length) return;
    // Acrescenta em vez de substituir: dá para escolher em várias tandas (câmera, galeria…).
    // O par nome+tamanho evita duplicar a mesma foto quando a pessoa reabre o seletor.
    const jaTem = new Set(fotos.map((f) => `${f.name}:${f.size}`));
    const candidatos = Array.from(escolhidos).filter((f) => !jaTem.has(`${f.name}:${f.size}`));
    const grandesDemais = candidatos.filter((f) => f.size > MAX_BYTES);
    const novos = candidatos.filter((f) => f.size <= MAX_BYTES);
    setRecusados(grandesDemais.map((f) => f.name));
    if (novos.length) onChange([...fotos, ...novos]);
  }

  const grandes = fotos.filter((f) => f.size > 4 * 1024 * 1024);

  return (
    <div>
      <span className="text-xs text-muted">Fotos (opcional)</span>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => {
          acrescentar(e.target.files);
          // Zerar o valor deixa a MESMA foto ser escolhida de novo depois de removida.
          e.target.value = "";
        }}
      />

      {fotos.length > 0 && (
        <ul className="mb-2 mt-1 grid grid-cols-4 gap-2 sm:grid-cols-5">
          {fotos.map((foto) => (
            <li key={`${foto.name}:${foto.size}`} className="relative">
              <img
                src={urlDe(foto)}
                alt={foto.name}
                className="aspect-square w-full rounded-md border border-line object-cover"
              />
              <button
                type="button"
                disabled={disabled}
                aria-label={`Remover ${foto.name}`}
                onClick={() => onChange(fotos.filter((f) => f !== foto))}
                className="absolute -right-1.5 -top-1.5 flex h-6 w-6 items-center justify-center rounded-full border border-line bg-panel text-muted shadow-sm hover:text-red disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" />
              </button>
              <span className="mt-0.5 block truncate text-[10px] text-muted">
                {formatarTamanho(foto.size)}
              </span>
            </li>
          ))}
        </ul>
      )}

      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        className={fotos.length > 0 ? "" : "mt-1"}
        onClick={() => inputRef.current?.click()}
      >
        <Camera className="mr-1 h-4 w-4" />
        {fotos.length > 0 ? "Adicionar mais fotos" : "Adicionar fotos"}
      </Button>

      <p className="mt-1 text-xs text-muted">
        {fotos.length > 0
          ? `${fotos.length} foto${fotos.length > 1 ? "s" : ""} — as imagens são reduzidas no envio (máx. 1200px).`
          : (ajuda ?? "Uma foto poupa explicação. As imagens são reduzidas no envio.")}
      </p>
      {grandes.length > 0 && (
        <p className="mt-1 text-xs text-muted">
          {grandes.length === 1 ? "Uma foto é grande" : `${grandes.length} fotos são grandes`} e o
          envio pode demorar num 4G — elas chegam reduzidas do outro lado.
        </p>
      )}
      {recusados.length > 0 && (
        <p className="mt-1 text-xs text-red">
          Não anexei {recusados.join(", ")}: passa de {MAX_BYTES / (1024 * 1024)} MB, e esse
          tamanho quase sempre é vídeo ou arquivo trocado.
        </p>
      )}
    </div>
  );
}

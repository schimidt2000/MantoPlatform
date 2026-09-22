import type { PortalRole } from "../lib/portalAgenda";

/**
 * A linha que diz o que a pessoa faz no evento — fonte única para Agenda, Convites e Histórico.
 *
 * Existe porque as três telas repetiam a string `Personagem:` à mão, e **40% das escalações não
 * são personagem**: 289 das 731 com talento são Coordenador, Técnico de Som, Maquiador,
 * Foto/Vídeo ou Transporte. Quem coordena lia "Personagem: Coordenador".
 *
 * Quem decide a natureza da vaga é o servidor (`role_type`); aqui só se escolhe a palavra. Sem o
 * campo — na janela de bundle novo com servidor velho — a linha volta a dizer "Personagem", que é
 * o comportamento de hoje: nada quebra, nada melhora.
 */
export function RoleLine({ role, className }: { role: PortalRole; className?: string }) {
  const rotulo = role.role_type === "extra" ? "Função" : "Personagem";
  return (
    <p className={className ?? "text-sm text-muted"}>
      {rotulo}: {role.character_name}
    </p>
  );
}

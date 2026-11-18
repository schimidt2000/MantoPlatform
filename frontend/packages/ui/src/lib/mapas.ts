/**
 * Links para abrir um endereço nos apps de mapas (feature 347).
 *
 * São links universais HTTPS, não esquemas próprios (`comgooglemaps://`, `waze://`): com o app
 * instalado, o iOS e o Android entregam o link ao app; sem o app, o mesmo link abre o site do
 * serviço. Esquema próprio sem o app instalado vira "endereço inválido" no Safari, e o navegador
 * não deixa saber se o app existe.
 *
 * Os três mostram o LOCAL, não a rota já iniciada: a rota escolheria sozinha o primeiro resultado
 * de um texto como "Buffet Encantado", sem a pessoa ver o pino. Ela fica a um toque dentro do app.
 *
 * O Apple Mapas usa o formato `?q=` porque é o que todo iOS em uso entende; o `/search?query=`
 * novo só existe nos mais recentes.
 */

const GOOGLE_MAPS = "https://www.google.com/maps/search/?api=1&query=";
const APPLE_MAPAS = "https://maps.apple.com/?q=";
const WAZE = "https://waze.com/ul?q=";

export type AppDeMapa = "google" | "apple" | "waze";

export interface OpcaoDeMapa {
  app: AppDeMapa;
  rotulo: string;
  url: string;
}

/**
 * As três opções para o endereço, nesta ordem: Google Maps, Apple Mapas, Waze. Endereço vazio,
 * só com espaços ou ausente devolve lista vazia — a tela não desenha nada tocável.
 *
 * `encodeURIComponent` é obrigatório: um "&" ou "#" no nome do buffet cortaria a busca no meio.
 */
export function linksDeMapa(endereco: string | null | undefined): OpcaoDeMapa[] {
  const limpo = (endereco ?? "").trim();
  if (!limpo) return [];
  const q = encodeURIComponent(limpo);
  return [
    { app: "google", rotulo: "Google Maps", url: GOOGLE_MAPS + q },
    { app: "apple", rotulo: "Apple Mapas", url: APPLE_MAPAS + q },
    { app: "waze", rotulo: "Waze", url: WAZE + q },
  ];
}

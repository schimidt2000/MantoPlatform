/**
 * Destino interno pós-login, vindo de `?destino=` (feature 293).
 *
 * O e-mail que pede o reenvio das fotos precisa levar a pessoa até `/fotos-documentos` depois de
 * ela criar a senha — sem isso o link cai na agenda e quem veio consertar a foto não acha onde
 * fazer isso. Como o valor chega pela URL, ele é validado com a MESMA regra do `_safe_next` do
 * backend (`app/__init__.py`): só caminho interno, e `//` fora porque `//evil.example` é uma URL
 * absoluta disfarçada de caminho relativo.
 */
export const DESTINO_PARAM = "destino";

/** O caminho pedido, se for um destino interno seguro; senão `null`. */
export function destinoSeguro(valor: string | null | undefined): string | null {
  if (!valor) return null;
  if (!valor.startsWith("/") || valor.startsWith("//")) return null;
  return valor;
}

/** Acrescenta `?destino=` a uma rota do portal, quando há destino a preservar. */
export function comDestino(rota: string, destino: string | null): string {
  return destino ? `${rota}?${DESTINO_PARAM}=${encodeURIComponent(destino)}` : rota;
}

# Contrato de interface — `@manto/ui`

Sem endpoint novo. O contrato é o da peça compartilhada que as duas SPAs consomem.

## `linksDeMapa(endereco)` — `packages/ui/src/lib/mapas.ts`

```ts
type AppDeMapa = "google" | "apple" | "waze";
interface OpcaoDeMapa { app: AppDeMapa; rotulo: string; url: string }
function linksDeMapa(endereco: string | null | undefined): OpcaoDeMapa[];
```

- Entrada vazia, só espaços, `null` ou `undefined` → `[]`.
- Caso contrário → três opções, ordem Google Maps, Apple Mapas, Waze, com
  `encodeURIComponent(endereco.trim())` nas URLs de `research.md` R1.
- Pura: sem `window`, sem efeito.

## `<EnderecoNoMapa>` — `packages/ui/src/components/endereco-no-mapa.tsx`

```ts
interface EnderecoNoMapaProps {
  endereco: string | null | undefined;
  className?: string; // classes extras do gatilho (ex.: alvo de 44px no portal)
}
```

- `linksDeMapa(endereco)` vazio → devolve `null` (a tela não desenha nada).
- Gatilho: `<button type="button">` com ícone de local e o endereço como texto, cor de link,
  quebra de linha no endereço longo.
- Toque → `Dialog` "Abrir endereço", descrição = endereço inteiro, uma lista com os três links
  (`<a target="_blank" rel="noopener noreferrer">`, altura mínima de 44px). Toque num link fecha a
  escolha.
- Fecha sem abrir nada: toque fora, "Fechar", Esc (comportamento do `Dialog`).

## Exportação

`packages/ui/src/index.ts` exporta `EnderecoNoMapa`, `EnderecoNoMapaProps`, `linksDeMapa`,
`OpcaoDeMapa` e `AppDeMapa` (sem a linha, a peça "não existe" e nada acusa erro — `docs/00` §5).

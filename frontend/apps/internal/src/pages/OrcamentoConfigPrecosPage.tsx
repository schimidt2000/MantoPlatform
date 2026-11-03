import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useReducedMotion } from "framer-motion";
import { ApiRequestError } from "@manto/api-client";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { MoneyInput } from "@manto/money";
import { DatasEspeciaisCard } from "../components/orcamento/DatasEspeciaisCard";
import { INPUT_PRECOS, PriceTable, type PriceTableRow } from "../components/orcamento/PriceTable";
import { ProdutosConfigCard } from "../components/orcamento/ProdutosConfigCard";
import {
  useAddEspecial,
  useOrcamentoSettings,
  useRemoveEspecial,
  useSaveOrcamentoSettings,
  type PricingSettings,
} from "../lib/orcamento";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = INPUT_PRECOS;
const SEM_ERROS: Record<string, string> = {};

/** Índice da página: a tabela tem oito blocos e a pergunta é sempre "onde fica X?". */
const SECOES = [
  { id: "markup", titulo: "Markup" },
  { id: "caches", titulo: "Cachês do elenco" },
  { id: "servicos", titulo: "Técnico, maquiador e brinde" },
  { id: "transporte", titulo: "Transporte" },
  { id: "acrescimos", titulo: "Acréscimos" },
  { id: "datas-especiais", titulo: "Datas especiais" },
  { id: "produtos", titulo: "Produtos de tabela" },
  { id: "educamanto", titulo: "EducaManto" },
] as const;

/*
 * Feature 324: as chaves do ator são técnicas (`cara_limpa|true|false` = subtipo|show|maquiagem) e
 * a tela as mostrava cruas. A leitura é só de exibição — a chave salva não muda.
 */
const SUBTIPO_ATOR: Record<string, string> = { cara_limpa: "Ator (cara limpa)", boneco: "Boneco" };
const ORDEM_SUBTIPO = ["cara_limpa", "boneco"];

function linhasDoAtor(
  ator: PricingSettings["ator"],
  onChange: (chave: string, v: number[]) => void,
): PriceTableRow[] {
  return Object.entries(ator)
    .map(([chave, values]) => {
      const [subtipo, show, make] = chave.split("|");
      return { chave, subtipo, show, make, values };
    })
    .sort(
      (a, b) =>
        (ORDEM_SUBTIPO.indexOf(a.subtipo) + 1 || 99) - (ORDEM_SUBTIPO.indexOf(b.subtipo) + 1 || 99) ||
        a.chave.localeCompare(b.chave),
    )
    .map(({ chave, subtipo, show, make, values }) => ({
      key: chave,
      label: SUBTIPO_ATOR[subtipo] ?? subtipo,
      hint: `${show === "true" ? "Com show" : "Sem show"} · ${make === "true" ? "com maquiagem" : "sem maquiagem"}`,
      values,
      onChange: (v: number[]) => onChange(chave, v),
    }));
}

/** Variantes do personagem especial: o servidor usa `false/true` ou `none/show/cantor`. */
const VARIANTE: Record<string, string> = {
  false: "Sem show",
  none: "Sem show",
  true: "Com show",
  show: "Com show",
  cantor: "Cantando",
};
const ORDEM_VARIANTE = ["false", "none", "true", "show", "cantor"];

function Secao({
  id,
  titulo,
  descricao,
  children,
}: {
  id: string;
  titulo: string;
  descricao?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-titulo`} className="scroll-mt-4 space-y-3">
      <div>
        <h2 id={`${id}-titulo`} className="text-base font-semibold text-ink">
          {titulo}
        </h2>
        {descricao && <p className="mt-0.5 max-w-3xl text-sm text-muted">{descricao}</p>}
      </div>
      {children}
    </section>
  );
}

function CartaoTitulo({ titulo, descricao }: { titulo: string; descricao?: ReactNode }) {
  return (
    <CardHeader className="pb-3">
      <CardTitle className="text-base">{titulo}</CardTitle>
      {descricao && <p className="text-xs text-muted">{descricao}</p>}
    </CardHeader>
  );
}

function Campo({
  id,
  rotulo,
  ajuda,
  children,
}: {
  id: string;
  rotulo: string;
  ajuda?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className={LABEL}>
        {rotulo}
      </label>
      {children}
      {ajuda && <p className="mt-1 text-xs text-muted">{ajuda}</p>}
    </div>
  );
}

export function OrcamentoConfigPrecosPage() {
  const query = useOrcamentoSettings();
  const save = useSaveOrcamentoSettings();
  const addEspecial = useAddEspecial();
  const removeEspecial = useRemoveEspecial();
  const reduzir = useReducedMotion();

  const [settings, setSettings] = useState<PricingSettings | null>(null);
  const [novoEspecialNome, setNovoEspecialNome] = useState("");
  const [novoAcrescimo, setNovoAcrescimo] = useState("");
  const [remocaoEspecial, setRemocaoEspecial] = useState<string | null>(null);
  // Feature 307: os `fields` do 400 do servidor (`datas_especiais.<faixa>.<campo>`) vão aos cards.
  // Referência ESTÁVEL (useMemo): os cards levam o foco ao primeiro `aria-invalid` quando `erros`
  // muda — um `{}` novo a cada render roubava o foco a cada tecla depois de um erro local.
  const errosDeSalvar: Record<string, string> = useMemo(
    () => (save.error instanceof ApiRequestError && save.error.fields ? save.error.fields : SEM_ERROS),
    [save.error],
  );

  useEffect(() => {
    if (query.data && !settings) setSettings(query.data.settings);
  }, [query.data, settings]);

  if (query.isError) {
    return (
      <div className="mx-auto max-w-[1400px] p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar a configuração de preços. Tente novamente.
        </div>
      </div>
    );
  }

  if (query.isLoading || !settings) {
    return (
      <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
        <PageHeader title="Configuração de Preços" className="mb-0" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const handleSave = () => {
    save.mutate(settings, { onSuccess: (data) => setSettings(data.settings) });
  };

  const irPara = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: reduzir ? "auto" : "smooth", block: "start" });

  const adicionarEspecial = () => {
    const nome = novoEspecialNome.trim();
    if (!nome) return;
    addEspecial.mutate(
      { nome, prices: [0, 0, 0, 0] },
      {
        onSuccess: (data) => {
          setSettings(data.settings);
          setNovoEspecialNome("");
        },
      },
    );
  };

  const confirmarRemocaoEspecial = () => {
    const nome = remocaoEspecial;
    if (!nome) return;
    removeEspecial.mutate(nome, {
      onSuccess: () => {
        const { [nome]: _removed, ...rest } = settings.especiais;
        // Feature 307: a sobrescrita do especial sai das faixas junto — senão o
        // próximo "Salvar" mandaria um nome órfão e levaria 400.
        const faixas = Object.fromEntries(
          Object.entries(settings.datas_especiais ?? {}).map(([k, f]) => {
            const { [nome]: _semUso, ...cache } = f.cache;
            return [k, { ...f, cache }];
          }),
        );
        setSettings({ ...settings, especiais: rest, datas_especiais: faixas });
        setRemocaoEspecial(null);
      },
    });
  };

  const adicionarAcrescimo = () => {
    const tipo = novoAcrescimo.trim();
    if (!tipo || settings.acrescimo_tipos.includes(tipo)) return;
    setSettings({ ...settings, acrescimo_tipos: [...settings.acrescimo_tipos, tipo] });
    setNovoAcrescimo("");
  };

  const setTransporte = (chave: keyof PricingSettings["transporte"], v: number) =>
    setSettings({ ...settings, transporte: { ...settings.transporte, [chave]: v } });
  const setMaquiador = (chave: keyof PricingSettings["maquiador"], v: number) =>
    setSettings({ ...settings, maquiador: { ...settings.maquiador, [chave]: v } });

  // Uma linha por variante; o nome e o "Remover" só na primeira linha do personagem.
  const linhasEspeciais = Object.entries(settings.especiais).flatMap(([nome, val]) => {
    if (Array.isArray(val)) {
      return [
        {
          key: nome,
          nome,
          variante: null as string | null,
          primeira: true,
          values: val,
          onChange: (v: number[]) =>
            setSettings({ ...settings, especiais: { ...settings.especiais, [nome]: v } }),
        },
      ];
    }
    return Object.entries(val)
      .sort(([a], [b]) => ORDEM_VARIANTE.indexOf(a) - ORDEM_VARIANTE.indexOf(b))
      .map(([variante, values], i) => ({
        key: `${nome}-${variante}`,
        nome,
        variante: VARIANTE[variante] ?? variante,
        primeira: i === 0,
        values,
        onChange: (v: number[]) =>
          setSettings({
            ...settings,
            especiais: { ...settings.especiais, [nome]: { ...val, [variante]: v } },
          }),
      }));
  });

  const errosGerais = Object.entries(errosDeSalvar).filter(
    // Os erros das datas especiais e dos produtos aparecem no próprio card (campo destacado);
    // aqui só o resto. `produtos` cobre também `produtos_estimativa`.
    ([campo]) => !campo.startsWith("datas_especiais") && !campo.startsWith("produtos"),
  );

  return (
    <div className="mx-auto max-w-[1400px] space-y-8 p-4 sm:p-6">
      <div className="space-y-4">
        <PageHeader
          title="Configuração de Preços"
          subtitle="Valores que a Calculadora de Orçamento usa para montar o preço de cada evento"
          className="mb-0"
          actions={
            <Button asChild variant="ghost" size="sm">
              <Link to="/orcamento">‹ Voltar à calculadora</Link>
            </Button>
          }
        />

        <Card>
          <CartaoTitulo
            titulo="Como a calculadora monta o preço"
            descricao="Cada tabela tem uma coluna por duração do evento (1h, 2h, 3h e 4h). Os cachês são o que a Manto paga; o preço de venda sai do markup."
          />
          <CardContent>
            <ol className="grid gap-2 text-sm text-ink sm:grid-cols-2 xl:grid-cols-5">
              {[
                ["Cachês do elenco", "Atores, bonecos, cantores, personagens especiais e coordenadores somados."],
                ["× Markup", "Receptivo ou show. Numa data especial, vale o markup da data."],
                ["+ Produtos de tabela", "Preço fixo do pacote, sem markup."],
                ["+ Serviços", "Brinde do show, adicional noturno, técnico de som e maquiador."],
                ["+ Transporte e acréscimos", "Deslocamento, adicionais da equipe e acréscimos do orçamento."],
              ].map(([titulo, texto], i) => (
                <li key={titulo} className="flex gap-2 rounded-md bg-surface-2 p-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-panel text-xs font-semibold text-muted">
                    {i + 1}
                  </span>
                  <span>
                    <span className="block font-medium">{titulo}</span>
                    <span className="text-xs text-muted">{texto}</span>
                  </span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>

        <nav aria-label="Seções da configuração" className="flex flex-wrap gap-2">
          {SECOES.map((s) => (
            <Button key={s.id} size="sm" variant="outline" onClick={() => irPara(s.id)}>
              {s.titulo}
            </Button>
          ))}
        </nav>
      </div>

      <Secao
        id="markup"
        titulo="Markup"
        descricao="Multiplica a soma dos cachês para chegar ao preço de venda. Ex.: cachês somando R$ 1.000 com markup 2,60 viram R$ 2.600."
      >
        <Card className="2xl:max-w-[calc(50%-0.5rem)]">
          <CardContent className="p-0">
            <PriceTable
              itemLabel="Tipo de evento"
              rows={[
                {
                  label: "Receptivo / interativo",
                  hint: "Evento sem show",
                  values: settings.markup.receptivo,
                  onChange: (v) => setSettings({ ...settings, markup: { ...settings.markup, receptivo: v } }),
                },
                {
                  label: "Show",
                  hint: "Evento com show (cantor, DJ, ator ou especial em show)",
                  values: settings.markup.show,
                  onChange: (v) => setSettings({ ...settings, markup: { ...settings.markup, show: v } }),
                },
              ]}
            />
          </CardContent>
        </Card>
      </Secao>

      <Secao
        id="caches"
        titulo="Cachês do elenco"
        descricao="Quanto a Manto paga a cada pessoa do elenco, por duração. Todos estes valores passam pelo markup."
      >
        {/* `[&>*]:min-w-0`: item de grid nasce com `min-width:auto`, o que impede o
            `overflow-x-auto` da tabela de agir e estoura a página no celular. */}
        <div className="grid items-start gap-4 [&>*]:min-w-0 2xl:grid-cols-2">
          <Card>
            <CartaoTitulo titulo="Atores e bonecos" />
            <CardContent className="p-0">
              <PriceTable
                itemLabel="Personagem"
                rows={linhasDoAtor(settings.ator, (chave, v) =>
                  setSettings({ ...settings, ator: { ...settings.ator, [chave]: v } }),
                )}
              />
            </CardContent>
          </Card>

          <div className="grid gap-4 [&>*]:min-w-0">
            <Card>
              <CartaoTitulo
                titulo="Cantores"
                descricao="O cachê do cantor é o valor base mais os adicionais que se aplicam."
              />
              <CardContent className="p-0">
                <PriceTable
                  rows={[
                    {
                      label: "Cachê base",
                      values: settings.cantor.base,
                      onChange: (v) => setSettings({ ...settings, cantor: { ...settings.cantor, base: v } }),
                    },
                    {
                      label: "+ Adicional de show",
                      hint: "Soma ao base quando o cantor faz show",
                      values: settings.cantor.show_extra,
                      onChange: (v) => setSettings({ ...settings, cantor: { ...settings.cantor, show_extra: v } }),
                    },
                    {
                      label: "+ Adicional de maquiagem",
                      hint: "Soma ao base quando o cantor é maquiado",
                      values: settings.cantor.make_extra,
                      onChange: (v) => setSettings({ ...settings, cantor: { ...settings.cantor, make_extra: v } }),
                    },
                  ]}
                />
              </CardContent>
            </Card>

            <Card>
              <CartaoTitulo
                titulo="Coordenador"
                descricao="Cachê de cada coordenador do evento."
              />
              <CardContent className="p-0">
                <PriceTable
                  rows={[
                    {
                      label: "Evento sem show",
                      values: settings.coordenador.false,
                      onChange: (v) =>
                        setSettings({ ...settings, coordenador: { ...settings.coordenador, false: v } }),
                    },
                    {
                      label: "Evento com show",
                      values: settings.coordenador.true,
                      onChange: (v) =>
                        setSettings({ ...settings, coordenador: { ...settings.coordenador, true: v } }),
                    },
                  ]}
                />
              </CardContent>
            </Card>
          </div>

          <Card className="2xl:col-span-2">
            <CartaoTitulo
              titulo="Personagens especiais"
              descricao="Personagens com cachê próprio (Papai Noel, Sósia, Perna de Pau…). Os que têm variante mostram uma linha para cada uma."
            />
            <CardContent className="space-y-0 p-0">
              <PriceTable
                itemLabel="Personagem"
                rows={linhasEspeciais.map((l) => ({
                  key: l.key,
                  label: l.nome,
                  hint: l.variante ?? undefined,
                  values: l.values,
                  onChange: l.onChange,
                  // O "Remover" tira o personagem inteiro: só na primeira linha dele.
                  acao: l.primeira ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label={`Remover ${l.nome}`}
                      onClick={() => setRemocaoEspecial(l.nome)}
                    >
                      Remover
                    </Button>
                  ) : null,
                }))}
              />
              <div className="space-y-3 border-t border-line p-4">
                <div className="flex flex-wrap items-end gap-2">
                  <div className="w-full max-w-xs">
                    <label htmlFor="novo-especial" className={LABEL}>
                      Novo personagem especial
                    </label>
                    <input
                      id="novo-especial"
                      className={INPUT}
                      placeholder="Ex.: Mágico"
                      value={novoEspecialNome}
                      onChange={(e) => setNovoEspecialNome(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") adicionarEspecial();
                      }}
                    />
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    loading={addEspecial.isPending}
                    disabled={!novoEspecialNome.trim()}
                    onClick={adicionarEspecial}
                  >
                    Adicionar personagem
                  </Button>
                </div>
                <p className="text-xs text-muted">
                  Adicionar e remover personagem são gravados na hora, sem o botão Salvar. Adicionar
                  recarrega a tabela: salve antes as alterações pendentes. O personagem novo entra com
                  cachê zerado.
                </p>
                {addEspecial.isError && (
                  <p className="text-xs text-red" role="alert">
                    Não foi possível adicionar o personagem. Tente novamente.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </Secao>

      <Secao
        id="servicos"
        titulo="Técnico, maquiador e brinde"
        descricao="Entram depois do markup. Técnico de som e maquiador somam o custo × 1,5 (markup de serviço); o brinde entra pelo valor."
      >
        <div className="grid items-start gap-4 [&>*]:min-w-0 2xl:grid-cols-2">
          <Card>
            <CartaoTitulo
              titulo="Técnico de som"
              descricao="Custo por duração. Entra só em evento com show."
            />
            <CardContent className="p-0">
              <PriceTable
                rows={[
                  {
                    label: "Técnico de som",
                    values: settings.tecnico_som,
                    onChange: (v) => setSettings({ ...settings, tecnico_som: v }),
                  },
                ]}
              />
            </CardContent>
          </Card>

          <Card>
            <CartaoTitulo
              titulo="Maquiador e brinde"
              descricao="Valor por evento, igual para qualquer duração."
            />
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Campo id="make-1" rotulo="1ª maquiagem" ajuda="Custo da primeira maquiagem do evento.">
                <MoneyInput
                  id="make-1"
                  className={INPUT}
                  value={settings.maquiador.make_1}
                  onValueChange={(v) => setMaquiador("make_1", v)}
                />
              </Campo>
              <Campo id="make-2" rotulo="2ª maquiagem" ajuda="Soma à 1ª.">
                <MoneyInput
                  id="make-2"
                  className={INPUT}
                  value={settings.maquiador.make_2_adicional}
                  onValueChange={(v) => setMaquiador("make_2_adicional", v)}
                />
              </Campo>
              <Campo id="make-extra" rotulo="Da 3ª maquiagem em diante" ajuda="Valor de cada maquiagem a mais.">
                <MoneyInput
                  id="make-extra"
                  className={INPUT}
                  value={settings.maquiador.make_extra_adicional}
                  onValueChange={(v) => setMaquiador("make_extra_adicional", v)}
                />
              </Campo>
              <Campo id="make-especial" rotulo="Maquiagem especial" ajuda="Valor de cada maquiagem especial.">
                <MoneyInput
                  id="make-especial"
                  className={INPUT}
                  value={settings.maquiador.make_especial}
                  onValueChange={(v) => setMaquiador("make_especial", v)}
                />
              </Campo>
              <Campo
                id="brinde-show"
                rotulo="Brinde do show"
                ajuda="Somado uma vez ao preço quando o evento tem show."
              >
                <MoneyInput
                  id="brinde-show"
                  className={INPUT}
                  value={settings.brinde_show}
                  onValueChange={(v) => setSettings({ ...settings, brinde_show: v })}
                />
              </Campo>
            </CardContent>
          </Card>
        </div>
      </Secao>

      <Secao
        id="transporte"
        titulo="Transporte"
        descricao="Usado nos eventos fora de SP. A distância conta ida e volta (km rodados)."
      >
        <div className="grid items-start gap-4 [&>*]:min-w-0 xl:grid-cols-2">
          <Card>
            <CartaoTitulo titulo="Veículos" descricao="Valor por km rodado." />
            <CardContent className="grid gap-4 sm:grid-cols-3 xl:grid-cols-2">
              <Campo id="van-com" rotulo="Van com carretinha (R$/km)">
                <MoneyInput
                  id="van-com"
                  className={INPUT}
                  value={settings.transporte.van_com_carretinha}
                  onValueChange={(v) => setTransporte("van_com_carretinha", v)}
                />
              </Campo>
              <Campo id="van-sem" rotulo="Van sem carretinha (R$/km)">
                <MoneyInput
                  id="van-sem"
                  className={INPUT}
                  value={settings.transporte.van_sem_carretinha}
                  onValueChange={(v) => setTransporte("van_sem_carretinha", v)}
                />
              </Campo>
              <Campo id="carro-km" rotulo="Carro (R$/km, por carro)">
                <MoneyInput
                  id="carro-km"
                  className={INPUT}
                  value={settings.transporte.carro_por_km}
                  onValueChange={(v) => setTransporte("carro_por_km", v)}
                />
              </Campo>
            </CardContent>
          </Card>

          <Card>
            <CartaoTitulo
              titulo="Adicionais da equipe"
              descricao="Somados ao veículo. Continuam valendo quando a cliente cuida do deslocamento."
            />
            <CardContent className="grid gap-4 sm:grid-cols-3 xl:grid-cols-2">
              <Campo
                id="afsp"
                rotulo="Adicional fora de SP — divisor"
                ajuda="Por pessoa: km rodados ÷ este número. Com 3, uma viagem de 300 km rende R$ 100 por pessoa."
              >
                <input
                  id="afsp"
                  type="number"
                  step="0.1"
                  className={INPUT}
                  value={settings.transporte.afsp_divisor}
                  onChange={(e) => setTransporte("afsp_divisor", Number(e.target.value))}
                />
              </Campo>
              <Campo
                id="ashow"
                rotulo="Adicional de show — divisor"
                ajuda="Por evento com show: km rodados ÷ este número."
              >
                <input
                  id="ashow"
                  type="number"
                  step="0.1"
                  className={INPUT}
                  value={settings.transporte.ashow_divisor}
                  onChange={(e) => setTransporte("ashow_divisor", Number(e.target.value))}
                />
              </Campo>
              <Campo
                id="ashow-min"
                rotulo="Adicional de show — a partir de (km)"
                ajuda="O adicional de show só entra acima destes km rodados."
              >
                <input
                  id="ashow-min"
                  type="number"
                  step="10"
                  className={INPUT}
                  value={settings.transporte.ashow_min_km}
                  onChange={(e) => setTransporte("ashow_min_km", Number(e.target.value))}
                />
              </Campo>
            </CardContent>
          </Card>
        </div>
      </Secao>

      <Secao
        id="acrescimos"
        titulo="Acréscimos"
        descricao="Opções do campo Tipo nos acréscimos da calculadora. BV e Outro aparecem sempre e não precisam estar na lista."
      >
        <Card className="max-w-3xl">
          <CardContent className="space-y-4 pt-5">
            <ul className="flex flex-wrap gap-2" aria-label="Tipos de acréscimo">
              {settings.acrescimo_tipos.length === 0 && (
                <li className="text-xs text-muted">Nenhum tipo cadastrado.</li>
              )}
              {settings.acrescimo_tipos.map((t) => (
                <li
                  key={t}
                  className="flex items-center gap-1 rounded-md bg-surface-2 py-1 pl-2.5 pr-1 text-sm text-ink"
                >
                  {t}
                  <button
                    type="button"
                    className="flex h-6 w-6 items-center justify-center rounded text-muted hover:text-red"
                    aria-label={`Remover ${t}`}
                    onClick={() =>
                      setSettings({
                        ...settings,
                        acrescimo_tipos: settings.acrescimo_tipos.filter((x) => x !== t),
                      })
                    }
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-end gap-2">
              <div className="w-full max-w-xs">
                <label htmlFor="novo-acrescimo" className={LABEL}>
                  Novo tipo de acréscimo
                </label>
                <input
                  id="novo-acrescimo"
                  className={INPUT}
                  placeholder="Ex.: Taxa de montagem"
                  value={novoAcrescimo}
                  onChange={(e) => setNovoAcrescimo(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") adicionarAcrescimo();
                  }}
                />
              </div>
              <Button size="sm" variant="outline" disabled={!novoAcrescimo.trim()} onClick={adicionarAcrescimo}>
                Adicionar tipo
              </Button>
            </div>
          </CardContent>
        </Card>
      </Secao>

      <Secao
        id="datas-especiais"
        titulo="Datas especiais"
        descricao="Dias do ano com preço próprio, como a véspera e o dia de Natal. A calculadora reconhece pela data do evento."
      >
        {/* Feature 307: faixas de data especial (24 e 25/12) — a calculadora resolve pela data. */}
        {Object.entries(settings.datas_especiais ?? {}).map(([chave, faixa]) => (
          <DatasEspeciaisCard
            key={chave}
            chave={chave}
            faixa={faixa}
            especiais={Object.keys(settings.especiais)}
            erros={errosDeSalvar}
            onChange={(nova) =>
              setSettings({
                ...settings,
                datas_especiais: { ...settings.datas_especiais, [chave]: nova },
              })
            }
          />
        ))}
      </Secao>

      {/* Feature 309: produtos de tabela (a Visita Mágica). Sem o bloco (backend velho) o card não
          existe — e o "Salvar" não manda `produtos`, então o servidor novo mantém o que tem. */}
      {settings.produtos && (
        <Secao
          id="produtos"
          titulo="Produtos de tabela"
          descricao="Pacotes vendidos por preço fechado, como a Visita Mágica."
        >
          <ProdutosConfigCard
            produtos={settings.produtos}
            estimativa={settings.produtos_estimativa ?? { fator_cache: 2, markup: 3 }}
            faixas={settings.datas_especiais ?? {}}
            especiais={Object.keys(settings.especiais)}
            erros={errosDeSalvar}
            avisos={save.data?.avisos ?? []}
            onChange={(produtos) => setSettings({ ...settings, produtos })}
            onEstimativaChange={(produtos_estimativa) => setSettings({ ...settings, produtos_estimativa })}
          />
        </Secao>
      )}

      <Secao
        id="educamanto"
        titulo="EducaManto"
        descricao="Custos usados pela calculadora do EducaManto."
      >
        <div className="grid items-start gap-4 [&>*]:min-w-0 xl:grid-cols-2">
          <Card>
            <CartaoTitulo
              titulo="Som e iluminação"
              descricao="Custo por dia de evento, conforme quem fornece o equipamento. A equipe técnica já está no valor, e cada combinação tem preço próprio (não é a soma das partes)."
            />
            <CardContent className="grid gap-4 sm:grid-cols-2">
              {(
                [
                  ["som_luz", "Som e iluminação pela Manto"],
                  ["som", "Só som pela Manto"],
                  ["luz", "Só iluminação pela Manto"],
                  ["nenhum", "Tudo pela contratante (só o sonoplasta)"],
                ] as const
              ).map(([chave, rotulo]) => (
                <Campo key={chave} id={`edu-${chave}`} rotulo={rotulo}>
                  <MoneyInput
                    id={`edu-${chave}`}
                    className={INPUT}
                    value={settings.educamanto_som_luz[chave]}
                    onValueChange={(v) =>
                      setSettings({
                        ...settings,
                        educamanto_som_luz: { ...settings.educamanto_som_luz, [chave]: v },
                      })
                    }
                  />
                </Campo>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CartaoTitulo titulo="Cenografia" />
            <CardContent>
              <Campo
                id="caminhao-sp"
                rotulo="Caminhão de cenografia em SP"
                ajuda="Valor fixo por evento dentro de São Paulo. Fora de SP o caminhão sai e entram 2 vans, pelo valor por km do Transporte."
              >
                <MoneyInput
                  id="caminhao-sp"
                  className={INPUT}
                  value={settings.transporte.caminhao_sp}
                  onValueChange={(v) => setTransporte("caminhao_sp", v)}
                />
              </Campo>
            </CardContent>
          </Card>
        </div>
      </Secao>

      {/* Barra fixa: com oito seções, o "Salvar" no pé da página ficava a várias telas de distância. */}
      <div className="sticky bottom-0 z-10 -mx-4 border-t border-line bg-panel px-4 py-3 sm:-mx-6 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Button loading={save.isPending} onClick={handleSave}>
            Salvar configurações
          </Button>
          {save.isSuccess && !save.isPending && (
            <p className="text-sm text-green" role="status">
              Configurações salvas.
            </p>
          )}
          {save.isError && (
            <div className="space-y-1" role="alert">
              <p className="text-sm text-red">
                Não foi possível salvar as configurações. Confira os campos destacados e tente novamente.
              </p>
              {errosGerais.map(([campo, msg]) => (
                <p key={campo} className="text-xs text-red">
                  {campo}: {msg}
                </p>
              ))}
            </div>
          )}
          {!save.isSuccess && !save.isError && (
            <p className="text-xs text-muted">Os valores passam a valer nos próximos cálculos depois de salvar.</p>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={remocaoEspecial != null}
        title="Remover personagem especial"
        description={`Remover "${remocaoEspecial ?? ""}" da tabela de preços? A remoção é gravada na hora e o personagem deixa de aparecer na calculadora.`}
        confirmLabel="Remover"
        destructive
        pending={removeEspecial.isPending}
        error={removeEspecial.isError ? "Não foi possível remover o personagem. Tente novamente." : null}
        onConfirm={confirmarRemocaoEspecial}
        onOpenChange={(aberto) => {
          if (!aberto) {
            setRemocaoEspecial(null);
            removeEspecial.reset();
          }
        }}
      />
    </div>
  );
}

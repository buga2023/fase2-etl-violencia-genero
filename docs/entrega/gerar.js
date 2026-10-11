// Gera o documento da Entrega Técnica — Fase 2 em DOCX e HTML (o PDF sai do HTML).
// Números do banco vêm de docs/verificacao_banco.json (python -m scripts.verificar_banco).
// Uso: node docs/entrega/gerar.js <pasta_saida> [url_repositorio]
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, HeadingLevel,
  AlignmentType, WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber,
} = require("docx");

const RAIZ = path.resolve(__dirname, "..", "..");
const SAIDA = path.resolve(process.argv[2] || path.join(RAIZ, "docs", "entrega"));
const REPO = process.argv[3] || "";
const BASE = "Entrega_Fase2_Gustavo_Souza_Santos";
const ler = (...p) => fs.readFileSync(path.join(RAIZ, ...p), "utf8");
const db = JSON.parse(ler("docs", "verificacao_banco.json"));
const manifesto = JSON.parse(ler("data", "raw", "manifest.json"));
const csv = (nome) => { const [cab, ...ls] = ler("data", "processed", nome).trim().split(/\r?\n/); const c = cab.split(",");
  return ls.map((l) => Object.fromEntries(l.split(",").map((v, i) => [c[i], v]))); };

// rastro do tratamento: linhas "| etapa | valor |" do relatório gerado pelo pipeline
const rel = {};
ler("docs", "relatorio_tratamento.md").split(/\r?\n/).forEach((l) => {
  const m = l.match(/^\| (.+?) \| ([\d.]+) \|$/); if (m) rel[m[1].trim()] = Number(m[2].replace(/\./g, ""));
});
const R = (prefixo) => { const k = Object.keys(rel).find((x) => x.startsWith(prefixo)); if (!k) throw new Error("relatório sem: " + prefixo); return rel[k]; };

const n = (v) => Number(v).toLocaleString("pt-BR");
const pct = (v, d = 1) => Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }) + "%";
const mib = (b) => (b / 1048576).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " MiB";
const col = (bloco, nome) => bloco.colunas.indexOf(nome);
const cont = Object.fromEntries(db.contagem.linhas);
const tamanhoMiB = db.tamanho_bytes / 1048576;
if (!db.aiven) throw new Error("verificacao_banco.json não veio do Aiven: rode scripts/verificar_banco.py com o .env do Aiven");

// sanidade por ano, recalculada dos CSVs tratados
const evento = Object.fromEntries(csv("dim_evento.csv").map((e) => [e.id_evento, e.nome]));
const negra = Object.fromEntries(csv("dim_raca_cor.csv").map((r) => [r.id_raca_cor, r.negra === "True"]));
const anos = {};
const ano = (a) => (anos[a] = anos[a] || { fem: 0, femF: 0, sim: 0, neg: 0, ign: 0 });
csv("fato_vitimas_sinesp.csv").forEach((f) => { if (evento[f.id_evento] !== "Feminicídio") return;
  const a = ano(f.id_tempo.slice(0, 4)); a.fem += +f.qt_vitimas; if (f.id_sexo === "1") a.femF += +f.qt_vitimas; });
csv("fato_obitos_agressao_sim.csv").forEach((f) => { const a = ano(f.id_tempo.slice(0, 4)); a.sim += +f.qt_obitos;
  if (negra[f.id_raca_cor]) a.neg += +f.qt_obitos; if (f.id_raca_cor === "9") a.ign += +f.qt_obitos; });

// ---------------------------------------------------------------- conteúdo
// Blocos: h1, h2, p (texto com **negrito**), bullets, table {head, rows, widths}, img, note
const C = [];
const h1 = (t) => C.push({ h1: t });
const h2 = (t) => C.push({ h2: t });
const p = (t) => C.push({ p: t });
const ul = (...itens) => C.push({ bullets: itens });
const tab = (head, rows, widths) => C.push({ table: { head, rows, widths } });
const nota = (t) => C.push({ note: t });

C.push({ title: "Fase 2 — Unificação, Tratamento, Modelagem e Armazenamento dos Dados" });
C.push({ meta: [
  ["Disciplina", "Big Data e Analytics"],
  ["Tema", "Monitoramento de Segurança Pública e Feminicídio Interseccional (ODS 5 e ODS 18)"],
  ["Fontes", "SINESP-VDE (MJSP), SIM (DataSUS/OpenDataSUS) e IBGE Localidades"],
  ["Aluno", "Gustavo Souza Santos"],
  ["Repositório", REPO || "(link a inserir)"],
  ["Banco", `Aiven for PostgreSQL (plano Free), ${db.versao.split(" on ")[0]}, schema vde`],
] });

h1("1. Base de dados tratada");
p("A base tratada une duas fontes oficiais que se complementam: a **SINESP-VDE** registra vítimas de crimes violentos com quebra por **sexo**, mas não tem raça/cor; o **SIM** registra cada óbito com **raça/cor** e idade. Cruzar as duas pelas dimensões que compartilham (mês, município/UF e sexo) é o que permite a leitura interseccional gênero × raça pedida pelo projeto.");

h2("1.1 Origem dos dados");
tab(["Fonte", "Conteúdo", "Formato", "Onde foi obtida"], [
  ["SINESP-VDE (MJSP)", "Vítimas por UF, município, mês e evento, com quebra feminino/masculino/não informado; 31 indicadores", "XLSX, um arquivo por ano (~24 MB)", "gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/download/dnsp-base-de-dados/bancovde-<ano>.xlsx (o antigo dados.mj.gov.br saiu do ar)"],
  ["SIM (DataSUS)", "Uma linha por Declaração de Óbito, 86 a 88 colunas conforme o ano", "CSV ';' (2019–2020); CSV em ZIP (2021–2024), sem cabeçalho em 2022–2023", "OpenDataSUS: s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM/csv/ (2021–2024) e diaad.s3.sa-east-1.amazonaws.com/sim/ (2019–2020)"],
  ["IBGE Localidades", "Código e nome dos 5.571 municípios", "JSON (API REST)", "servicodados.ibge.gov.br/api/v1/localidades/municipios"],
], [1700, 2700, 1900, 3060]);
p("Classificação: SINESP e SIM são dados **estruturados** (tabelas); a API do IBGE entrega dados **semi-estruturados** (JSON). As três fontes são dados abertos governamentais, já anonimizados na origem.");

h2("1.2 Versão original utilizada");
p("Os arquivos oficiais não são alterados. O pipeline grava `data/raw/manifest.json` com nome, tamanho, data e **SHA-256** de cada arquivo, e a tabela `meta_carga` guarda a mesma linhagem dentro do banco. Quando o arquivo lido pelo ETL sai de um ZIP oficial (SIM 2021 a 2024: extraído em 2021 e 2024, padronizado em 2022 e 2023), a `meta_carga` registra também o ZIP de origem e o hash dele (`arquivo_origem`, `sha256_origem`).");
tab(["Fonte", "Arquivo", "Papel", "Tamanho", "SHA-256 (início)"],
  manifesto.map((m) => [m.fonte, m.arquivo,
    m.arquivo.endsWith(".zip") ? "oficial (ZIP)" : /Geral_202[23]\.csv$/.test(m.arquivo) ? "derivado do ZIP" : /Geral_202[14]\.csv$/.test(m.arquivo) ? "extraído do ZIP" : "oficial",
    mib(m.tamanho_bytes), m.sha256.slice(0, 16)]),
  [1300, 3500, 1600, 1300, 1660]);
nota("SIM 2022 e 2023: o OpenDataSUS publica esses anos em ZIP com CSV sem linha de cabeçalho e data DD-MM-AAAA. O ZIP oficial é a versão original; etl/padronizar_sim.py só nomeia as 6 colunas usadas, pela posição do layout oficial, e reescreve a data como DDMMAAAA, igual aos outros anos. Se alguma linha vier com menos colunas que o layout, o passo falha em vez de descartá-la.");

h2("1.3 Versão resultante após o tratamento");
p("A versão tratada existe em dois lugares com o mesmo conteúdo: os CSVs em `data/processed/` (uma tabela por arquivo, versionados no repositório) e as tabelas do schema `vde` no PostgreSQL.");
tab(["Fonte", "Linhas lidas", "Após filtros", "Linhas finais (grão agregado)", "Total conferido"], [
  ["SINESP-VDE (6 arquivos)", n(R("Linhas lidas")), `${n(R("Após filtro de"))} (8 eventos)`, n(cont.fato_vitimas_sinesp), `${n(R("Total de vítimas"))} vítimas`],
  ["SIM (6 anos)", n(R("Declarações de óbito lidas")), `${n(R("Após filtro CID"))} (X85–Y09, sexo feminino)`, n(cont.fato_obitos_agressao_sim), `${n(R("Total de óbitos"))} óbitos`],
  ["IBGE", "5.571 municípios", "5.571", n(cont.dim_municipio) + " (inclui 27 'NÃO INFORMADO', um por UF)", "—"],
], [2100, 1500, 2300, 2000, 1460]);

h2("1.4 Principais decisões e justificativas");
p("**SINESP-VDE**");
tab(["Problema na origem", "Decisão", "Justificativa"], [
  ["Nomes de coluna variam entre anos", "Normalização (minúsculas, sem acento) e validação das colunas obrigatórias", "O pipeline não quebra com mudança de layout e falha cedo se faltar campo essencial"],
  ["data_referencia como data, texto MM/AAAA ou ano/mês separados", "Conversão para DATE no dia 01", "Grão mensal único para as duas fontes"],
  ["31 indicadores, a maioria fora do tema (drogas, roubo de carga, bombeiros...)", "Mantidos 8 eventos de violência contra a pessoa", "Foco no tema e menos volume; comparação ignora acento e caixa"],
  ["Contagens como texto com milhar ('1.050')", "Conversão para INTEGER (inteiro_br)", "Equivale à conversão 'texto → número' pedida no guia"],
  ["Vítimas sem quebra por sexo", "Total atribuído a 'Não informado'", "Não perde vítimas e não inventa sexo"],
  ["Formato largo (feminino, masculino, não informado)", "Unpivot: uma linha por sexo", "Sexo vira dimensão, igual ao SIM, e as fontes ficam comparáveis"],
  ["DF informa uma linha por Região Administrativa, todas como 'BRASÍLIA'", "Linhas iguais no mesmo arquivo são mantidas e somadas; só a mesma linha repetida em outro arquivo é removida", "São registros distintos: removê-los apagava cerca de 60% das vítimas do DF (ver 4.1)"],
  ["Município identificado só pelo nome", "Junção com o IBGE por nome normalizado + tabela de aliases", "Gera o código IBGE, chave para cruzar com o SIM"],
  ["Nome sem correspondência ou 'Não informado'", "Vai para a linha 'NÃO INFORMADO' da UF", "Preserva o total estadual"],
  ["Colunas agente, arma, faixa_etaria, total_peso", "Descartadas", "Só são preenchidas em outros indicadores: 0 linhas do escopo as usam"],
], [2800, 3200, 3360]);
p("**SIM/DataSUS**");
tab(["Problema na origem", "Decisão", "Justificativa"], [
  ["~1,5 milhão de linhas/ano e 86–88 colunas", "Leitura de 6 colunas em blocos de 200 mil linhas, cada bloco agregado", "Memória constante; base final muito abaixo de 1 GB"],
  ["Todas as causas de morte", "Filtro CID-10 X85–Y09 (agressões, por expressão regular) e sexo feminino ('2' ou 'F')", "Recorte da Fase 1; a regex evita aceitar códigos truncados"],
  ["DTOBITO DDMMAAAA, às vezes sem zero à esquerda", "Lida como texto, completada com zeros e convertida para DATE", "Evita perder óbitos dos dias 1 a 9"],
  ["IDADE codificada (1º dígito = unidade: 0 min, 1 h, 2 dias, 3 meses, 4 anos, 5 = 100+)", "Decodificada em anos (unidades 0–3 = 0 anos; vazio e 999 = ignorada) e agrupada em 9 faixas", "Faixa etária é o terceiro eixo interseccional"],
  ["RACACOR vazio ou fora do domínio", "Mapeado para 9 = Ignorada; flag negra = preta + parda", "Critério IBGE/FBSP; ignorados ficam visíveis"],
  ["CAUSABAS com 4 caracteres", "Agrupada pelo meio da agressão (arma de fogo, cortante...)", "Dimensão analítica de baixa cardinalidade"],
  ["CODMUNOCOR com 6 dígitos", "Junção com cod_ibge // 10; sem correspondência → 'NÃO INFORMADO' da UF", "Município de ocorrência, comparável ao registro policial"],
], [2800, 3200, 3360]);
p("**LGPD:** as fontes já são públicas e anonimizadas (sem nome, CPF ou endereço). O ETL lê só as 6 colunas necessárias do SIM e carrega contagens por mês, município e perfil, nunca a declaração de óbito. Isso **reduz** o risco de reidentificação, mas não o elimina: como homicídios de mulheres são raros por município e mês, a maioria das células tem contagem 1. A camada de apresentação (Fase 3) deve agregar por UF ou suprimir células pequenas.");

h2("1.5 Ajustes e correções feitos na execução real");
ul(
  "**Correspondência de municípios:** 6 nomes da SINESP sem par no IBGE foram resolvidos com aliases inequívocos (um único candidato na UF): Barão de Monte Alto → Barão do Monte Alto (MG); Santo Antônio do Leverger → Santo Antônio de Leverger (MT); Arês → Arez e Açu → Assú (RN); São Luiz → São Luiz do Anauá (RR); Gracho Cardoso → Graccho Cardoso (SE). Resultado: de 6 para 0 nomes sem correspondência.",
  "**Eventos:** os 8 eventos configurados aparecem nos arquivos com a mesma grafia; nenhum ajuste foi necessário.",
  "**SIM 2021–2024:** o link antigo do S3 respondia 403; os links oficiais atuais do OpenDataSUS estão em etl/config.py (SIM_FONTES) e o download, a extração e a padronização são automáticos.",
  `**Revisão adversarial:** uma revisão independente recalculou os totais a partir dos arquivos brutos e encontrou dois erros, corrigidos com teste antes da carga final: (1) a remoção de "duplicatas" apagava Regiões Administrativas do DF (${n(R("Total de vítimas") - 965890)} vítimas recuperadas: o total passou de 965.890 para ${n(R("Total de vítimas"))}); (2) idades em minutos (recém-nascidos) eram classificadas como ignoradas.`,
);

h1("2. Processo de tratamento dos dados");
p("O processo é um ETL em **Python + pandas**, reproduzível e versionado no repositório. Cada camada fica num módulo:");
tab(["Etapa", "Módulo", "O que faz"], [
  ["Extração", "etl/extract.py", "Baixa IBGE, SINESP e SIM dos links oficiais, extrai os ZIPs e grava o manifesto SHA-256"],
  ["Padronização", "etl/padronizar_sim.py", "Dá cabeçalho e formato de data aos CSVs do SIM 2022/2023"],
  ["Dimensões", "etl/dimensoes.py", "Dimensões estáticas e municípios via API do IBGE"],
  ["Tratamento", "etl/transform_sinesp.py, etl/transform_sim.py", "Regras das tabelas da seção 1.4; cada etapa registra linhas de entrada e saída"],
  ["Carga", "etl/load.py", "Executa o DDL e carrega com COPY numa transação única (idempotente)"],
  ["Relatório", "run_pipeline.py", "Orquestra tudo e gera docs/relatorio_tratamento.md com os números reais"],
  ["Evidências", "scripts/verificar_banco.py", "Roda sql/03_verificacao.sql no banco e grava docs/verificacao_banco.md"],
], [1600, 3300, 4460]);
p("**Decisões técnicas:**");
ul(
  "**pandas com leitura em blocos (chunks):** cobre CSV, XLSX e JSON com a mesma API e processa 9,3 milhões de declarações de óbito com memória constante.",
  "**Agregar antes de carregar:** o tema pede contagens e taxas, não registros nominais. Isso mantém a base em poucos MiB e minimiza dados pessoais (LGPD).",
  "**Parâmetros centralizados em etl/config.py:** anos, links, eventos, CIDs e aliases mudam sem tocar na lógica.",
  "**Carga transacional com COPY:** método mais rápido do PostgreSQL; se algo falhar, o banco volta ao estado anterior.",
  "**Testes automatizados (pytest, 9 testes):** dados sintéticos com os defeitos reais das fontes: milhar em texto, linhas do DF por Região Administrativa, cópia da mesma linha em outro arquivo, data sem zero, sexo F/2, idade em minutos, bordas do CID, município inexistente, UF inválida e CSV sem cabeçalho.",
  "**Segurança:** a credencial do banco fica só no .env (fora do git); o repositório traz apenas o .env.example.",
);
p("**Como reproduzir:** `pip install -r requirements.txt` → copiar `.env.example` para `.env` e colar a Service URI do Aiven → `python run_pipeline.py` (baixa as três fontes, trata, carrega e gera o relatório; leva cerca de 30 minutos) → `python -m scripts.verificar_banco`.");

h1("3. Base armazenada em banco de dados");
h2("3.1 Estrutura criada: esquema estrela com duas tabelas fato");
C.push({ img: path.join(__dirname, "diagrama_estrela.png"), w: 620, h: 319 });
ul(
  "**Por que relacional (PostgreSQL):** os dados são estruturados, com chaves e relacionamentos estáveis, e o uso é analítico com somas e filtros; integridade (FK, CHECK) e SQL padrão pesam mais que a flexibilidade de esquema de um banco NoSQL.",
  "**Por que estrela:** a finalidade é analítica (KPIs e dashboard da Fase 3). Poucos joins, consultas simples e rápidas.",
  "**Por que duas tabelas fato:** as fontes têm grãos e medidas diferentes (SINESP: evento × sexo; SIM: raça × idade × meio). Uma tabela única criaria colunas vazias e somas erradas.",
  "**Dimensões conformadas** (tempo, município/UF, sexo) são compartilhadas e permitem cruzar as fontes sem misturá-las. A visão vw_comparativo_uf_ano coloca lado a lado, por UF e ano, as vítimas da SINESP e os óbitos do SIM.",
  "**Integridade no banco:** FKs em todos os relacionamentos, CHECK em mês, ano e quantidades (> 0) e no sexo do fato SIM (só feminino), e UNIQUE em códigos naturais.",
);

h2("3.2 Principais tabelas, campos e tipos");
const CHAVES = {
  dim_tempo: "PK id_tempo (AAAAMM)", dim_uf: "PK cod_uf", dim_municipio: "PK id_municipio (serial); UNIQUE cod_ibge; FK cod_uf",
  dim_sexo: "PK id_sexo", dim_raca_cor: "PK id_raca_cor", dim_faixa_etaria: "PK id_faixa", dim_evento: "PK id_evento",
  dim_meio_agressao: "PK id_meio", meta_carga: "PK id_carga (serial)",
  fato_vitimas_sinesp: "PK composta (id_tempo, id_municipio, id_evento, id_sexo); todas FK",
  fato_obitos_agressao_sim: "PK composta (id_tempo, id_municipio, id_sexo, id_raca_cor, id_faixa, id_meio); todas FK",
};
const porTabela = {};
db.colunas.linhas.forEach(([t, c, tipo, nulo]) => { (porTabela[t] = porTabela[t] || []).push(`${c} (${tipo}${nulo === "YES" ? ", nulo" : ""})`); });
tab(["Tabela", "Chave", "Campos (tipo)"], Object.entries(porTabela).map(([t, cs]) => [t, CHAVES[t] || "", cs.join("; ")]), [2200, 2600, 4560]);

h2("3.3 Relacionamentos");
tab(["Tabela", "Coluna (FK)", "Referência", "Coluna"], db.fks.linhas, [3000, 2000, 2600, 1760]);

h2("3.4 Quantidade de dados armazenados");
tab(["Tabela", "Registros"], db.contagem.linhas.map(([t, c]) => [t, n(c)]), [5000, 4360]);
p(`**Espaço ocupado pelo schema vde:** ${mib(db.tamanho_bytes)} de 1.024 MiB do plano Free (${pct(100 * tamanhoMiB / 1024)}), somando tabelas, índices e TOAST.`);

h2("3.5 Consulta interseccional (vw_comparativo_uf_ano)");
const cp = db.comparativo;
p(`As 10 UFs com mais óbitos de mulheres por agressão no SIM em ${cp.linhas[0][col(cp, "ano")]}. A coluna comparável ao SIM é a de **vítimas letais mulheres** da SINESP (feminicídio, homicídio, latrocínio e lesão seguida de morte com vítima do sexo feminino); feminicídio é um subconjunto dela.`);
tab(["UF", "Feminicídios mulheres (SINESP)", "Vítimas letais mulheres (SINESP)", "Óbitos mulheres por agressão (SIM)", "Óbitos mulheres negras (SIM)", "% negras"],
  cp.linhas.map((l) => [l[col(cp, "uf")], n(l[col(cp, "feminicidios_mulheres_sinesp")]), n(l[col(cp, "vitimas_letais_mulheres_sinesp")]),
    n(l[col(cp, "obitos_agressao_mulheres_sim")]), n(l[col(cp, "obitos_mulheres_negras_sim")]), pct(l[col(cp, "pct_mulheres_negras_sim")])]),
  [700, 1900, 1900, 2000, 1800, 1060]);

h2("3.6 Checagem de sanidade");
tab(["Ano", "Feminicídios (SINESP, todas as vítimas)", "Feminicídios com vítima mulher", "Óbitos de mulheres por agressão (SIM)", "% mulheres negras (SIM)"],
  Object.entries(anos).sort().map(([a, v]) => [a, n(v.fem), n(v.femF), n(v.sim), pct(100 * v.neg / v.sim)]),
  [900, 2300, 2100, 2300, 1760]);
p(`Comparação com publicações: o Anuário Brasileiro de Segurança Pública (FBSP) registra 1.492 feminicídios em 2024 na edição 2025, revisados para 1.504 na edição 2026 (aqui: ${n(anos["2024"].fem)}); o Atlas da Violência 2025 (Ipea/FBSP), que usa o mesmo SIM, aponta 3.903 mulheres assassinadas em 2023, 68,2% negras (aqui: ${n(anos["2023"].sim)} e ${pct(100 * anos["2023"].neg / anos["2023"].sim)}). A pequena diferença no SIM vem do recorte: o Atlas soma também as mortes por intervenção legal (CID Y35–Y36), que este projeto não inclui.`);

h1("4. Limitações e divergências");
ul(
  `**4.1 DF por Região Administrativa (corrigido).** O DF lança várias linhas por mês com o mesmo município (BRASÍLIA), uma por Região Administrativa, sem coluna que as diferencie. A versão anterior removia essas linhas como duplicatas e perdia cerca de 60% das vítimas do DF (ex.: 2019, feminicídios no DF: 32 no bruto, 13 após a remoção). Nos anos conferidos linha a linha (2019, 2023 e 2024), as linhas repetidas fora do DF tinham zero vítimas. A regra agora remove só a mesma linha repetida em arquivos diferentes; medição em docs/impacto_duplicatas.csv.`,
  "**4.2 Feminicídio com vítima não feminina:** a SINESP traz de 3 a 9 vítimas do sexo masculino por ano em 'Feminicídio' (mais 1 a 4 sem sexo informado), provável erro de registro na origem. A quebra por sexo foi mantida como veio; a view oferece as duas medidas (todas as vítimas e só mulheres).",
  "**4.3 Granularidade de estupro:** estupro e estupro de vulnerável só existem no nível estadual na SINESP: 100% dessas vítimas ficam na linha 'NÃO INFORMADO' da UF. Análises municipais desses eventos não são possíveis; mapas devem usar UF. O campo violencia_genero marca a tipificação legal por gênero (feminicídio), não a natureza do crime.",
  "**4.4 SIM 2024 preliminar:** publicado no OpenDataSUS como DO24OPEN, tem total cerca de 7% menor que 2023 em todos os meses; os números podem ser revisados pelo Ministério da Saúde.",
  `**4.5 Raça/cor ignorada:** ${pct(100 * Object.values(anos).reduce((s, v) => s + v.ign, 0) / Object.values(anos).reduce((s, v) => s + v.sim, 0))} dos óbitos do SIM no período têm raça/cor ignorada; eles ficam no denominador do percentual de mulheres negras, que por isso é ligeiramente conservador.`,
  "**4.6 Grão de comparação:** as fontes são cruzadas por UF × ano (e município × mês). Não há como ligar uma vítima da SINESP a um óbito do SIM, e isso é intencional (LGPD).",
);

h1("Anexo — evidências da base no Aiven");
p(`Saída de \`sql/03_verificacao.sql\` executado no serviço Aiven for PostgreSQL (host \`${db.host_mascarado || "*.aivencloud.com"}\`, ${db.versao.split(" on ")[0]}) em ${new Date(db.executado_em).toLocaleString("pt-BR")}. Campos e tipos (consulta 3), FKs (consulta 4) e amostra da view (consulta 6) estão nas seções 3.2, 3.3 e 3.5; a saída completa está em evidencias/verificacao_banco.md.`);
const mc = db.meta_carga;
tab(["Fonte", "Arquivo carregado", "SHA-256", "Arquivo oficial de origem", "SHA-256 origem", "Linhas lidas", "Após filtro"],
  mc.linhas.map((l) => [l[col(mc, "fonte")], l[col(mc, "arquivo")], l[col(mc, "sha256")], l[col(mc, "arquivo_origem")] || "—", l[col(mc, "sha256_origem")] || "—", n(l[col(mc, "linhas_lidas")]), n(l[col(mc, "linhas_apos_filtro")])]),
  [1000, 2000, 1250, 1900, 1250, 1050, 910]);


// ---------------------------------------------------------------- render DOCX
const AZUL = "1F3864";
const runs = (txt, base = {}) => txt.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((s) =>
  s.startsWith("**") ? new TextRun({ ...base, text: s.slice(2, -2), bold: true })
    : s.startsWith("`") ? new TextRun({ ...base, text: s.slice(1, -1), font: "Consolas", size: (base.size || 21) - 2 })
      : new TextRun({ ...base, text: s }));
const borda = { style: BorderStyle.SINGLE, size: 4, color: "9AAFD6" };
const bordas = { top: borda, bottom: borda, left: borda, right: borda };
const celula = (txt, w, cab, par) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders: bordas,
  shading: cab ? { fill: AZUL, type: ShadingType.CLEAR, color: "auto" } : par ? { fill: "EEF2FA", type: ShadingType.CLEAR, color: "auto" } : undefined,
  margins: { top: 60, bottom: 60, left: 100, right: 100 },
  children: [new Paragraph({ children: runs(String(txt), { size: 17, color: cab ? "FFFFFF" : "222222", bold: cab }) })],
});
const filhos = [];
for (const b of C) {
  if (b.title) filhos.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: b.title, bold: true, size: 34, color: AZUL })],
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: AZUL, space: 6 } }, spacing: { after: 200 } }));
  else if (b.meta) b.meta.forEach(([k, v]) => filhos.push(new Paragraph({ spacing: { after: 20 }, children: [new TextRun({ text: k + ": ", bold: true, size: 21 }), new TextRun({ text: v, size: 21 })] })));
  else if (b.h1) filhos.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 120 }, children: [new TextRun({ text: b.h1, bold: true, size: 28, color: AZUL })] }));
  else if (b.h2) filhos.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 80 }, children: [new TextRun({ text: b.h2, bold: true, size: 23, color: "2E5597" })] }));
  else if (b.p) filhos.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 }, children: runs(b.p, { size: 21 }) }));
  else if (b.note) filhos.push(new Paragraph({ spacing: { after: 120 }, shading: { fill: "FFF4E5", type: ShadingType.CLEAR, color: "auto" }, children: runs(b.note, { size: 19, italics: true }) }));
  else if (b.bullets) b.bullets.forEach((t) => filhos.push(new Paragraph({ numbering: { reference: "bul", level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { after: 60 }, children: runs(t, { size: 21 }) })));
  else if (b.img) filhos.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: fs.readFileSync(b.img), transformation: { width: b.w, height: b.h } })] }));
  else if (b.table) {
    const { head, rows, widths } = b.table;
    filhos.push(new Table({ width: { size: widths.reduce((a, x) => a + x, 0), type: WidthType.DXA }, columnWidths: widths,
      rows: [new TableRow({ tableHeader: true, children: head.map((h, i) => celula(h, widths[i], true)) }),
        ...rows.map((r, j) => new TableRow({ children: r.map((v, i) => celula(v, widths[i], false, j % 2 === 1)) }))] }));
    filhos.push(new Paragraph({ spacing: { after: 80 }, children: [] }));
  }
}
const doc = new Document({
  creator: "Gustavo Souza Santos", title: "Entrega Técnica Fase 2",
  styles: { default: { document: { run: { font: "Calibri", size: 21 } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
  sections: [{
    properties: { page: { margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ children: ["Fase 2 — Gustavo Souza Santos — página ", PageNumber.CURRENT], size: 16, color: "777777" })] })] }) },
    children: filhos,
  }],
});

// ---------------------------------------------------------------- render HTML (para o PDF)
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const inl = (s) => esc(s).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
let html = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Entrega Técnica Fase 2</title><style>
@page{size:A4;margin:18mm 18mm 16mm}body{font-family:Calibri,"Segoe UI",Arial,sans-serif;font-size:10.5pt;color:#222;line-height:1.38}
h1.t{font-size:17pt;color:#${AZUL};border-bottom:2px solid #${AZUL};padding-bottom:6px;margin:0 0 10px}
h1{font-size:14pt;color:#${AZUL};margin:18px 0 6px;page-break-after:avoid}h2{font-size:11.5pt;color:#2E5597;margin:12px 0 4px;page-break-after:avoid}
p{margin:0 0 7px;text-align:justify}.m{margin:0}ul{margin:0 0 8px;padding-left:18px}li{margin-bottom:3px;text-align:justify}
table{border-collapse:collapse;width:100%;margin:2px 0 10px;font-size:8.6pt;page-break-inside:auto}tr{page-break-inside:avoid}
th{background:#${AZUL};color:#fff;text-align:left;padding:4px 6px;border:1px solid #9AAFD6}td{padding:3px 6px;border:1px solid #9AAFD6;vertical-align:top}
tr:nth-child(even) td{background:#EEF2FA}code{font-family:Consolas,monospace;font-size:9pt}.n{background:#FFF4E5;padding:6px 8px;font-style:italic;font-size:9.5pt;margin:0 0 8px}
img{display:block;margin:4px auto 8px;max-width:100%}</style></head><body>`;
for (const b of C) {
  if (b.title) html += `<h1 class="t">${esc(b.title)}</h1>`;
  else if (b.meta) html += b.meta.map(([k, v]) => `<p class="m"><b>${esc(k)}:</b> ${esc(v)}</p>`).join("");
  else if (b.h1) html += `<h1>${esc(b.h1)}</h1>`;
  else if (b.h2) html += `<h2>${esc(b.h2)}</h2>`;
  else if (b.p) html += `<p>${inl(b.p)}</p>`;
  else if (b.note) html += `<p class="n">${inl(b.note)}</p>`;
  else if (b.bullets) html += `<ul>${b.bullets.map((t) => `<li>${inl(t)}</li>`).join("")}</ul>`;
  else if (b.img) html += `<img src="data:image/png;base64,${fs.readFileSync(b.img).toString("base64")}" width="${b.w}">`;
  else if (b.table) html += `<table><thead><tr>${b.table.head.map((h) => `<th>${inl(h)}</th>`).join("")}</tr></thead><tbody>${b.table.rows.map((r) => `<tr>${r.map((v) => `<td>${inl(v)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}
html += "</body></html>";

fs.mkdirSync(SAIDA, { recursive: true });
fs.writeFileSync(path.join(SAIDA, BASE + ".html"), html, "utf8");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(SAIDA, BASE + ".docx"), buf);
  console.log("Gerado:", path.join(SAIDA, BASE + ".docx"), "e .html");
});

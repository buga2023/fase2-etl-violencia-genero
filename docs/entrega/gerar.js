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
const db = JSON.parse(fs.readFileSync(path.join(RAIZ, "docs", "verificacao_banco.json"), "utf8"));
const manifesto = JSON.parse(fs.readFileSync(path.join(RAIZ, "data", "raw", "manifest.json"), "utf8"));
const impacto = fs.readFileSync(path.join(RAIZ, "docs", "impacto_duplicatas.csv"), "utf8")
  .trim().split(/\r?\n/).slice(1).map((l) => l.split(","));

const n = (v) => Number(v).toLocaleString("pt-BR");
const mb = (b) => (b / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " MB";
const cont = Object.fromEntries(db.contagem.linhas);
const tamanhoMB = db.tamanho_bytes / 1048576;
const ambiente = db.aiven
  ? "Aiven for PostgreSQL (Free Tier)"
  : "ensaio em PostgreSQL 16 local; a carga no Aiven usa o mesmo comando";

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
  ["Repositório", REPO || "(link a inserir após o push)"],
  ["Banco", `PostgreSQL, schema vde — ${ambiente}`],
] });

h1("1. Base de dados tratada");
p("A base tratada une duas fontes oficiais que se complementam: a **SINESP-VDE** registra vítimas de crimes violentos com quebra por **sexo**, mas não tem raça/cor; o **SIM** registra cada óbito com **raça/cor** e idade. Cruzar as duas pelas dimensões que elas compartilham (mês, município/UF e sexo) é o que permite a leitura interseccional gênero × raça pedida pelo projeto.");

h2("1.1 Origem dos dados");
tab(["Fonte", "Conteúdo", "Formato", "Onde foi obtida"], [
  ["SINESP-VDE (MJSP)", "Vítimas por UF, município, mês e evento, com quebra feminino/masculino/não informado", "XLSX, um arquivo por ano", "gov.br/mj — dnsp-base-de-dados/bancovde-<ano>.xlsx (o antigo dados.mj.gov.br saiu do ar)"],
  ["SIM (DataSUS)", "Uma linha por Declaração de Óbito, 80+ colunas", "CSV ';' (2019–2021, 2024) e CSV em ZIP sem cabeçalho (2022–2023)", "OpenDataSUS: S3 ckan.saude.gov.br/SIM e diaad.s3 (2019–2020)"],
  ["IBGE Localidades", "Código e nome dos 5.571 municípios", "JSON (API REST)", "servicodados.ibge.gov.br/api/v1/localidades/municipios"],
], [1800, 3000, 1900, 2660]);
p("Classificação: SINESP e SIM são dados **estruturados** (tabelas); a API do IBGE entrega dados **semi-estruturados** (JSON). As três fontes são dados abertos governamentais.");

h2("1.2 Versão original utilizada");
p("Os arquivos brutos não são alterados. O pipeline grava `data/raw/manifest.json` com nome, tamanho, data e **SHA-256** de cada arquivo, e a mesma linhagem fica dentro do banco na tabela `meta_carga`. Qualquer pessoa consegue conferir se está usando exatamente a mesma versão.");
tab(["Fonte", "Arquivo", "Tamanho", "SHA-256 (início)"],
  manifesto.map((m) => [m.fonte, m.arquivo, mb(m.tamanho_bytes), m.sha256.slice(0, 16)]),
  [1500, 4000, 1500, 2360]);
nota("SIM 2022 e 2023: o OpenDataSUS publica esses anos em ZIP com CSV sem linha de cabeçalho e data DD-MM-AAAA. O ZIP oficial é a versão original (hash acima); o script scripts/padronizar_sim.py só nomeia as 6 colunas usadas pela posição do layout oficial e reescreve a data como DDMMAAAA, igual aos outros anos.");

h2("1.3 Versão resultante após o tratamento");
p("A versão tratada existe em dois lugares com o mesmo conteúdo: os CSVs em `data/processed/` (uma tabela por arquivo, versionados no repositório) e as tabelas do schema `vde` no PostgreSQL.");
tab(["Fonte", "Linhas lidas", "Após filtros", "Linhas finais (grão agregado)", "Total conferido"], [
  ["SINESP-VDE (6 arquivos)", "4.588.376", "2.436.806 (8 eventos)", n(cont.fato_vitimas_sinesp), "965.890 vítimas"],
  ["SIM (6 anos)", "9.281.165", "22.691 (X85–Y09, sexo feminino)", n(cont.fato_obitos_agressao_sim), "22.691 óbitos"],
  ["IBGE", "5.571 municípios", "5.571", n(cont.dim_municipio) + " (inclui 27 'NÃO INFORMADO')", "—"],
], [2100, 1500, 2300, 2000, 1460]);

h2("1.4 Principais decisões e justificativas");
p("**SINESP-VDE**");
tab(["Problema na origem", "Decisão", "Justificativa"], [
  ["Nomes de coluna variam entre anos", "Normalização (minúsculas, sem acento) e validação das colunas obrigatórias", "O pipeline não quebra com mudança de layout e falha cedo se faltar campo essencial"],
  ["31 indicadores, a maioria fora do tema (drogas, roubo de carga, bombeiros...)", "Mantidos 8 eventos de violência contra a pessoa", "Foco no tema e menos volume; comparação ignora acento e caixa"],
  ["Contagens como texto com milhar ('1.050')", "Conversão para INTEGER (inteiro_br)", "Equivale à conversão 'texto → número' pedida no guia"],
  ["Formato largo (feminino, masculino, não informado)", "Unpivot: uma linha por sexo", "Sexo vira dimensão, igual ao SIM, e as fontes ficam comparáveis"],
  ["Município identificado só pelo nome", "Junção com o IBGE por nome normalizado + tabela de aliases", "Gera o código IBGE, chave para cruzar com o SIM"],
  ["Nome sem correspondência ou 'Não informado'", "Vai para a linha 'NÃO INFORMADO' da UF", "Preserva o total estadual"],
  ["Linhas duplicadas", "Removidas as duplicatas exatas", "Evita contar duas vezes (ver limitação 4.1 sobre o DF)"],
  ["Colunas agente, arma, faixa_etaria, total_peso", "Descartadas", "Só são preenchidas em outros indicadores: 0 linhas do escopo as usam"],
], [2800, 3200, 3360]);
p("**SIM/DataSUS**");
tab(["Problema na origem", "Decisão", "Justificativa"], [
  ["~1,5 milhão de linhas/ano e 87 colunas", "Leitura de 6 colunas em blocos de 200 mil linhas, cada bloco agregado", "Memória constante; base final muito abaixo de 1 GB"],
  ["Todas as causas de morte", "Filtro CID-10 X85–Y09 (agressões) e sexo feminino ('2' ou 'F')", "Recorte da Fase 1"],
  ["DTOBITO DDMMAAAA, às vezes sem zero à esquerda", "Lida como texto, completada com zeros e convertida para DATE", "Evita perder óbitos dos dias 1 a 9"],
  ["IDADE codificada (unidade + valor)", "Decodificada em anos e agrupada em 9 faixas", "Faixa etária é o terceiro eixo interseccional"],
  ["RACACOR vazio ou fora do domínio", "Mapeado para 9 = Ignorada; flag negra = preta + parda", "Critério IBGE/FBSP; ignorados ficam visíveis"],
  ["CAUSABAS com 4 caracteres", "Agrupada pelo meio da agressão (arma de fogo, cortante...)", "Dimensão analítica de baixa cardinalidade"],
  ["CODMUNOCOR com 6 dígitos", "Junção com cod_ibge // 10; sem correspondência → 'NÃO INFORMADO' da UF", "Município de ocorrência, comparável ao registro policial"],
], [2800, 3200, 3360]);
p("**LGPD:** o óbito individual nunca é carregado. O banco recebe só contagens agregadas por mês, município e perfil, o que reduz milhões de linhas a milhares e elimina o risco de reidentificação.");

h2("1.5 Ajustes feitos na execução real");
ul(
  "**Correspondência de municípios:** 6 nomes da SINESP sem par no IBGE foram resolvidos com aliases inequívocos (um único candidato na UF): Barão de Monte Alto → Barão do Monte Alto (MG); Santo Antônio do Leverger → Santo Antônio de Leverger (MT); Arês → Arez e Açu → Assú (RN); São Luiz → São Luiz do Anauá (RR); Gracho Cardoso → Graccho Cardoso (SE). Resultado: de 6 para 0 nomes sem correspondência.",
  "**Eventos:** os 8 eventos configurados aparecem nos arquivos com a mesma grafia; nenhum ajuste foi necessário.",
  "**SIM 2021–2024:** o link antigo do S3 respondia 403; os arquivos foram obtidos nos links oficiais atuais do OpenDataSUS e os de 2022 e 2023 passaram pela padronização descrita em 1.2.",
);

h1("2. Processo de tratamento dos dados");
p("O processo é um ETL em **Python + pandas**, reproduzível e versionado no repositório. Cada camada fica num módulo:");
tab(["Etapa", "Módulo", "O que faz"], [
  ["Extração", "etl/extract.py", "Baixa IBGE e SIM e grava o manifesto SHA-256 da versão original"],
  ["Padronização", "scripts/padronizar_sim.py", "Dá cabeçalho e formato de data aos CSVs do SIM 2022/2023"],
  ["Dimensões", "etl/dimensoes.py", "Dimensões estáticas e municípios via API do IBGE"],
  ["Tratamento", "etl/transform_sinesp.py, etl/transform_sim.py", "Regras das tabelas da seção 1.4; cada etapa registra linhas de entrada e saída"],
  ["Carga", "etl/load.py", "Executa o DDL e carrega com COPY numa transação única (idempotente)"],
  ["Relatório", "run_pipeline.py", "Gera docs/relatorio_tratamento.md com os números reais"],
  ["Evidências", "scripts/verificar_banco.py", "Roda sql/03_verificacao.sql e grava docs/verificacao_banco.md"],
], [1600, 3300, 4460]);
p("**Decisões técnicas:**");
ul(
  "**pandas com leitura em blocos (chunks):** cobre CSV, XLSX e JSON com a mesma API e processa 9,3 milhões de declarações de óbito com memória constante.",
  "**Agregar antes de carregar:** o tema pede contagens e taxas, não registros nominais. Isso mantém a base em poucos MB e atende à LGPD.",
  "**Parâmetros centralizados em etl/config.py:** anos, eventos, CIDs e aliases mudam sem tocar na lógica.",
  "**Carga transacional com COPY:** método mais rápido do PostgreSQL; se algo falhar, o banco volta ao estado anterior.",
  "**Testes automatizados (pytest, 7 testes):** dados sintéticos com os defeitos reais das fontes (milhar em texto, duplicata, data sem zero, sexo F/2, município inexistente, UF inválida, CSV sem cabeçalho).",
  "**Segurança:** a credencial do banco fica só no .env (fora do git); o repositório traz apenas o .env.example.",
);
p("**Como reproduzir:** `pip install -r requirements.txt` → colocar a Service URI do Aiven no `.env` → `python run_pipeline.py`. Os arquivos da SINESP são baixados manualmente (seção 1.1).");

h1("3. Base armazenada em banco de dados");
h2("3.1 Estrutura criada: esquema estrela com duas tabelas fato");
C.push({ img: path.join(__dirname, "diagrama_estrela.png"), w: 620, h: 319 });
ul(
  "**Por que estrela:** a finalidade é analítica (KPIs e dashboard da Fase 3). Poucos joins, consultas simples e rápidas.",
  "**Por que duas fatos:** as fontes têm grãos e medidas diferentes (SINESP: evento × sexo; SIM: raça × idade × meio). Uma tabela única criaria colunas vazias e somas erradas.",
  "**Dimensões conformadas** (tempo, município/UF, sexo) são compartilhadas e permitem cruzar as fontes sem misturá-las. A visão vw_comparativo_uf_ano coloca lado a lado feminicídios (SINESP) e óbitos de mulheres negras por agressão (SIM).",
  "**Integridade no banco:** FKs em todos os relacionamentos, CHECK em mês, ano e quantidades (> 0) e UNIQUE em códigos naturais.",
);

h2("3.2 Principais tabelas, campos e tipos");
const porTabela = {};
db.colunas.linhas.forEach(([t, c, tipo, nulo]) => { (porTabela[t] = porTabela[t] || []).push(`${c} (${tipo}${nulo === "YES" ? ", nulo" : ""})`); });
tab(["Tabela", "Campos (tipo)"], Object.entries(porTabela).map(([t, cs]) => [t, cs.join("; ")]), [2600, 6760]);

h2("3.3 Relacionamentos");
tab(["Tabela", "Coluna (FK)", "Referencia", "Coluna"], db.fks.linhas, [3000, 2000, 2600, 1760]);

h2("3.4 Quantidade de dados armazenados");
tab(["Tabela", "Registros"], db.contagem.linhas.map(([t, c]) => [t, n(c)]), [5000, 4360]);
p(`**Espaço ocupado pelo schema vde:** ${tamanhoMB.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MB de 1.024 MB do Free Tier (${(100 * tamanhoMB / 1024).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%), somando tabelas, índices e TOAST. Servidor: ${db.versao.split(" on ")[0]} — ${ambiente}.`);

h2("3.5 Consulta interseccional (vw_comparativo_uf_ano, 2024)");
tab(["Ano", "UF", "Feminicídios (SINESP)", "Óbitos mulheres por agressão (SIM)", "Óbitos mulheres negras (SIM)", "% negras"],
  db.comparativo.linhas.map((l) => [l[0], l[1], n(l[3]), n(l[5]), n(l[6]), Number(l[7]).toFixed(1).replace(".", ",") + "%"]),
  [800, 700, 1800, 2400, 2200, 1460]);

h2("3.6 Checagem de sanidade");
tab(["Ano", "Feminicídios (SINESP, todas as vítimas)", "Óbitos de mulheres por agressão (SIM)", "% mulheres negras (SIM)"], [
  ["2019", "1.312", "3.728", "66,0%"], ["2020", "1.341", "3.822", "67,4%"], ["2021", "1.356", "3.844", "67,4%"],
  ["2022", "1.446", "3.788", "66,3%"], ["2023", "1.462", "3.887", "68,1%"], ["2024", "1.491", "3.622", "67,5%"],
], [1000, 3000, 3000, 2360]);
p("Os totais ficam na faixa esperada (feminicídios na casa de mil e poucos por ano; óbitos de mulheres por agressão entre 3 e 4 mil), coerentes com o Anuário do FBSP e o Atlas da Violência.");

h1("4. Limitações e divergências");
const perdaFem = impacto.filter((r) => r[1] === "Feminicídio").map((r) => `${r[0]}: ${Number(r[6])}`).join("; ");
ul(
  `**4.1 DF reportado por Região Administrativa.** O DF lança várias linhas por mês com o mesmo município (BRASÍLIA), uma por Região Administrativa, sem coluna que as diferencie. A regra de remover duplicatas exatas trata linhas iguais como repetidas e reduz a contagem do DF. Impacto nacional medido em feminicídios por ano (${perdaFem}), menos de 1,5%; em tentativas de feminicídio, de 32 a 62 por ano. A medição completa está em docs/impacto_duplicatas.csv. A correção (agregar o DF antes de deduplicar) fica registrada para a próxima fase.`,
  "**4.2 Feminicídio com vítima masculina:** a SINESP traz de 3 a 9 vítimas do sexo masculino por ano em 'Feminicídio' (mais 1 a 4 sem sexo informado), provável erro de registro na origem. A quebra por sexo foi mantida como veio, sem correção.",
  "**4.3 Estupro e estupro de vulnerável** só têm abrangência estadual na SINESP; ficam na linha 'NÃO INFORMADO' da UF.",
  "**4.4 SIM 2024** foi publicado no OpenDataSUS como DO24OPEN; os números podem ser revisados pelo Ministério da Saúde.",
  "**4.5 Grão de comparação:** as fontes são cruzadas no nível UF × ano (e município × mês). Não há como ligar uma vítima da SINESP a um óbito do SIM, e isso é intencional (LGPD).",
);
if (!db.aiven) nota("Os números das seções 3.2 a 3.5 vieram de um ensaio de carga num PostgreSQL 16 local, com os mesmos dados e o mesmo DDL. Depois da carga no Aiven (python run_pipeline.py --sem-download), rode python -m scripts.verificar_banco e gere este documento de novo para trocar os números pelos do Aiven.");

h1("Anexo — evidências (prints do Aiven)");
ul(
  "Console do Aiven: serviço PostgreSQL ativo (plano Free).",
  "sql/03_verificacao.sql, consulta 1: contagem de registros por tabela.",
  "Consulta 2: tamanho do schema vde.",
  "Consulta 3: campos e tipos (information_schema).",
  "Consulta 4: chaves estrangeiras.",
  "Consulta 5: linhagem (meta_carga) com o SHA-256 dos arquivos originais.",
  "Consulta 6: amostra de vw_comparativo_uf_ano.",
);

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

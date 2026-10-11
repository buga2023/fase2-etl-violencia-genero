-- Consultas para evidenciar a entrega (rode no Aiven e tire print)
SET search_path TO vde;

-- 1. Quantidade de registros por tabela
SELECT 'dim_tempo' AS tabela, COUNT(*) FROM dim_tempo
UNION ALL SELECT 'dim_uf', COUNT(*) FROM dim_uf
UNION ALL SELECT 'dim_municipio', COUNT(*) FROM dim_municipio
UNION ALL SELECT 'dim_sexo', COUNT(*) FROM dim_sexo
UNION ALL SELECT 'dim_raca_cor', COUNT(*) FROM dim_raca_cor
UNION ALL SELECT 'dim_faixa_etaria', COUNT(*) FROM dim_faixa_etaria
UNION ALL SELECT 'dim_evento', COUNT(*) FROM dim_evento
UNION ALL SELECT 'dim_meio_agressao', COUNT(*) FROM dim_meio_agressao
UNION ALL SELECT 'fato_vitimas_sinesp', COUNT(*) FROM fato_vitimas_sinesp
UNION ALL SELECT 'fato_obitos_agressao_sim', COUNT(*) FROM fato_obitos_agressao_sim
UNION ALL SELECT 'meta_carga', COUNT(*) FROM meta_carga;

-- 2. Espaço ocupado (limite do Free Tier: 1 GB)
SELECT pg_size_pretty(SUM(pg_total_relation_size(c.oid))) AS tamanho_schema_vde
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'vde' AND c.relkind = 'r';   -- pg_total_relation_size já inclui índices e TOAST

-- 3. Estrutura: campos e tipos
SELECT table_name, column_name,
       data_type || COALESCE('(' || character_maximum_length || ')', '') AS data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'vde' AND table_name NOT LIKE 'vw\_%'
ORDER BY table_name, ordinal_position;

-- 4. Relacionamentos (chaves estrangeiras)
SELECT tc.table_name AS tabela, kcu.column_name AS coluna,
       ccu.table_name AS referencia, ccu.column_name AS coluna_ref
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'vde'
ORDER BY 1, 2;

-- 5. Linhagem: versão original de cada arquivo carregado
SELECT fonte, arquivo, LEFT(sha256, 12) AS sha256, arquivo_origem, LEFT(sha256_origem, 12) AS sha256_origem,
       linhas_lidas, linhas_apos_filtro, executado_em
FROM meta_carga ORDER BY id_carga;

-- 6. Amostra do cruzamento interseccional
SELECT * FROM vw_comparativo_uf_ano ORDER BY ano DESC, obitos_agressao_mulheres_sim DESC LIMIT 10;

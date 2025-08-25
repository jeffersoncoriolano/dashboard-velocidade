from textwrap import dedent

def get_equipamentos():
    return dedent("""
        SELECT 
            id, nome_processador, endereco, latitude, longitude, status, vel_regulamentada
        FROM equipamentos
        WHERE tipo_equipamento = 'radar'
            AND faixa_monitorada = 'A'
            AND latitude IS NOT NULL
            AND longitude IS NOT NULL
        ORDER BY nome_processador, faixa_monitorada
    """)

def get_distribuicao_velocidade():
    return dedent("""
        SELECT 
            velocidade, 
            COUNT(*) AS contagem
        FROM dados_velocidade
        WHERE equipamento = %(equipamento_id)s
          AND DATE_FORMAT(data, '%%m/%%Y') = %(mes)s
        GROUP BY velocidade
        ORDER BY velocidade
    """)

def get_fluxo(nome_processador, data_inicial, data_final):
    return dedent("""
        SELECT
            SUM(volume_veiculos) AS fluxo_total
        FROM dados_trafego dt
        JOIN equipamentos eq ON dt.id_equipamento = eq.id
        WHERE eq.nome_processador = %(nome_processador)s
          AND dt.data BETWEEN %(data_inicial)s AND %(data_final)s    
    """)

def get_limites_datas():
    return dedent("""
        SELECT 
            MIN(data) as data_minima,
            MAX(data) as data_maxima
        FROM dados_velocidade
        WHERE equipamento = %(equipamento_id)s
    """)

def get_inoperancia():
    return dedent("""
        WITH trafego_agrupado AS (
            SELECT
                e.nome_processador,
                t.data,
                t.hora,
                SUM(t.volume_veiculos) AS volume_veiculos_total
            FROM dados_trafego t
            JOIN equipamentos e ON t.id_equipamento = e.id
            WHERE t.data BETWEEN %(data_inicial)s AND %(data_final)s
            GROUP BY e.nome_processador, t.data, t.hora
        ),
        trafego_zerado AS (
            SELECT
                nome_processador,
                data,
                hora,
                volume_veiculos_total,
                CASE WHEN volume_veiculos_total = 0 THEN 1 ELSE 0 END AS inoperante,
                TIMESTAMP(data, hora) AS ts
            FROM trafego_agrupado
        ),
        marcado AS (
            SELECT
                *,
                ROW_NUMBER() OVER (PARTITION BY nome_processador ORDER BY ts) -
                ROW_NUMBER() OVER (PARTITION BY nome_processador, inoperante ORDER BY ts) AS grupo
            FROM trafego_zerado
        ),
        intervalos AS (
            SELECT
                nome_processador,
                grupo,
                MIN(ts) AS inicio_inoperancia,
                MAX(ts) AS fim_inoperancia,
                COUNT(*) AS horas_inoperante
            FROM marcado
            WHERE inoperante = 1
            GROUP BY nome_processador, grupo
        )
        SELECT
            nome_processador,
            SUM(horas_inoperante) AS horas_inoperantes
        FROM intervalos
        WHERE horas_inoperante >= 25
        GROUP BY nome_processador
        ORDER BY nome_processador;
    """)

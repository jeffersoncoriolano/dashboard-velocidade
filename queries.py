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

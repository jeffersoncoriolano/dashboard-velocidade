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

def get_limites_datas():
    return """
        SELECT 
            MIN(data) as data_minima,
            MAX(data) as data_maxima
        FROM dados_velocidade
        WHERE equipamento = %(equipamento_id)s
    """

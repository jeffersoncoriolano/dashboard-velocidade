# dashboard_velocidade/app.py

import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import pandas as pd
import plotly.express as px
import datetime
from dotenv import load_dotenv
from queries import *
from db_connector import executar_consulta

load_dotenv()

# URL de um ícone de radar (exemplo; use outro se preferir)
radar_icon_url = "icon/icone_radar2.png"  # Exemplo de ícone de radar

st.set_page_config(layout="wide")
st.title("Distribuição das Velocidades - Dashboard")

# Carregar equipamentos para o mapa
equipamentos_df = executar_consulta(get_equipamentos())

# Filtrar equipamentos válidos
equipamentos_validos = equipamentos_df[
    (equipamentos_df['latitude'] != 0) &
    (equipamentos_df['longitude'] != 0)
]

if equipamentos_validos.empty:
    st.error("Nenhum equipamento válido com latitude/longitude diferente de zero encontrado!")
    # Você pode definir um centro padrão para Macaé se quiser mostrar um mapa vazio:
    # macae_center = [-22.3763, -41.7848]
    # m = folium.Map(location=macae_center, zoom_start=12)
    # st_folium(m, height=500, width=900)
else:
    # Calcular o centro correto
    map_center = [
        equipamentos_validos['latitude'].mean(),
        equipamentos_validos['longitude'].mean()
    ]

# Criar mapa
m = folium.Map(location=map_center, zoom_start=12)

mapa_id_por_nome = {}

for _, row in equipamentos_validos.iterrows():
    popup_text = f"{row['nome_processador']}<br>{row['id']}"
    # Cria ícone personalizado
    icon = folium.CustomIcon(
        radar_icon_url,
        icon_size=(32, 32),  # Ajuste o tamanho conforme necessário
        icon_anchor=(16, 16)
    )
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        tooltip=row['nome_processador'],
        popup=popup_text,
        icon=icon
    ).add_to(m)
    mapa_id_por_nome[row['nome_processador']] = row['id']

# Mostrar mapa
st.markdown("### Selecione um equipamento clicando no mapa")
map_result = st_folium(m, height=500, width=900)


# Obter equipamento clicado (tooltip)
equipamento_selecionado = map_result.get("last_object_clicked_tooltip")

if equipamento_selecionado:
    st.success(f"Equipamento selecionado: {equipamento_selecionado}")
    equipamento_id = mapa_id_por_nome[equipamento_selecionado]

    # Descobre o menor e maior dia disponível na base (opcional, para limitar o range)
    # Pode usar datas fixas se preferir, ou uma consulta para obter o range real.
    data_minima = datetime.date(2024, 1, 1)   # Altere conforme a sua base!
    data_maxima = datetime.date(2024, 12, 31) # Altere conforme a sua base!

    # Intervalo de datas (sem selectbox de mês)
    data_intervalo = st.date_input(
        "Selecione o intervalo de dias:",
        value=(data_minima, data_maxima),
        min_value=data_minima,
        max_value=data_maxima,
        format="DD/MM/YYYY"
    )

    # Garante que é tupla e tem 2 datas
    if isinstance(data_intervalo, tuple) and len(data_intervalo) == 2:
        data_inicial, data_final = data_intervalo
    else:
        data_inicial, data_final = None, None

    if data_inicial and data_final and data_inicial <= data_final:
        query = """
            SELECT 
                velocidade, 
                COUNT(*) AS contagem
            FROM dados_velocidade
            WHERE equipamento = %(equipamento_id)s
              AND data BETWEEN %(data_inicial)s AND %(data_final)s
            GROUP BY velocidade
            ORDER BY velocidade
        """
        params = {
            "equipamento_id": equipamento_id,
            "data_inicial": data_inicial.strftime("%Y-%m-%d"),
            "data_final": data_final.strftime("%Y-%m-%d"),
        }
        df = executar_consulta(query, params)
        if df is None or df.empty:
            st.warning("Nenhum dado encontrado para o período e equipamento selecionados.")
        else:
            fig = px.bar(df, x="velocidade", y="contagem",
                            labels={"velocidade": "Velocidade (km/h)", "contagem": "Quantidade"},
                            title=f"Distribuição das Velocidades ({data_inicial} a {data_final})")
            st.plotly_chart(fig, use_container_width=True)
    elif data_inicial and data_final and data_inicial > data_final:
        st.info("A data inicial deve ser menor ou igual à data final.")
    # Senão, não mostra nada durante a seleção

else:
    st.info("Clique em um equipamento no mapa para começar.")

# dashboard_velocidade/app.py

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import datetime
from dotenv import load_dotenv
from queries import *
from db_connector import executar_consulta
import locale

# Define locale para Brasil (para separador de milhar)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

load_dotenv()

st.set_page_config(layout="wide")
st.title("Distribuição das Velocidades - Dashboard")

radar_icon_url = "icon/icone_radar2.png"

# Carregar equipamentos para o mapa
equipamentos_df = executar_consulta(get_equipamentos())
equipamentos_validos = equipamentos_df[
    (equipamentos_df['latitude'] != 0) & (equipamentos_df['longitude'] != 0)
]

# =========== SIDEBAR (FILTRO DE DATA) ===========
with st.sidebar:
    st.header("Filtros")
    data_minima = datetime.date(2024, 1, 1)
    data_maxima = datetime.date(2024, 12, 31)
    data_intervalo = st.date_input(
        "Selecione o intervalo de dias:",
        value=(data_minima, data_minima),
        min_value=data_minima,
        max_value=data_maxima,
        format="DD/MM/YYYY"
    )
    # Garante que é tupla e tem 2 datas
    if isinstance(data_intervalo, tuple) and len(data_intervalo) == 2:
        data_inicial, data_final = data_intervalo
    else:
        data_inicial, data_final = None, None

# =========== TELA PRINCIPAL ===========

if equipamentos_validos.empty:
    st.error("Nenhum equipamento válido com latitude/longitude diferente de zero encontrado!")
else:
    map_center = [
        equipamentos_validos['latitude'].mean(),
        equipamentos_validos['longitude'].mean()
    ]
    m = folium.Map(location=map_center, zoom_start=12)
    mapa_id_por_nome = {}

    for _, row in equipamentos_validos.iterrows():
        popup_text = f"Nome:{row['nome_processador']}<br>ID: {row['id']}"
        icon = folium.CustomIcon(
            radar_icon_url,
            icon_size=(32, 32),
            icon_anchor=(16, 16)
        )
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            tooltip=row['nome_processador'],
            popup=popup_text,
            icon=icon
        ).add_to(m)
        mapa_id_por_nome[row['nome_processador']] = row['id']

    st.markdown("### Selecione um equipamento clicando no mapa")
    map_result = st_folium(m, height=500, width=900)

    equipamento_selecionado = map_result.get("last_object_clicked_tooltip")
    equipamento_id = mapa_id_por_nome.get(equipamento_selecionado)

    if equipamento_selecionado:
        st.success(f"Equipamento selecionado: {equipamento_selecionado}")

        if data_inicial and data_final and data_inicial <= data_final:
            query = """
                SELECT velocidade, COUNT(*) AS contagem
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
                # ----- INDICADORES -----
                velocidade_max = df["velocidade"].max()
                velocidade_moda = df.loc[df['contagem'].idxmax(), "velocidade"]
                total_veiculos = df["contagem"].sum()
                # Define a velocidade regulamentada (ajuste se precisar)
                velocidade_regulamentada = 60

                acima_regulamentada = df[df["velocidade"] > velocidade_regulamentada]["contagem"].sum()
                margem_tolerancia = df[
                    (df["velocidade"] > velocidade_regulamentada) &
                    (df["velocidade"] <= velocidade_regulamentada + 7)
                ]["contagem"].sum()
                acima_margem = df[df["velocidade"] > velocidade_regulamentada + 7]["contagem"].sum()
                dentro_margem = total_veiculos - acima_regulamentada

                pct_dentro = dentro_margem / total_veiculos * 100 if total_veiculos > 0 else 0
                pct_margem = margem_tolerancia / total_veiculos * 100 if total_veiculos > 0 else 0
                pct_acima = acima_margem / total_veiculos * 100 if total_veiculos > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Velocidade mais praticada", f"{velocidade_moda} km/h")
                with col2:
                    st.metric("Velocidade máxima", f"{velocidade_max} km/h")
                with col3:
                    # Exibe com separador brasileiro de milhar
                    st.metric(
                        "Total de veículos",
                        locale.format_string("%.0f", total_veiculos, grouping=True)
                    )

                # ---- GRÁFICO DE DISTRIBUIÇÃO ----
                fig_bar = px.bar(
                    df, x="velocidade", y="contagem",
                    labels={"velocidade": "Velocidade (km/h)", "contagem": "Quantidade"},
                    title=f"Distribuição das Velocidades ({data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')})"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

                # ---- PIZZA ----
                donut_df = pd.DataFrame({
                    "Categoria": ["Dentro da margem", "Até +7km/h (tolerância)", "Acima da margem"],
                    "Percentual": [pct_dentro, pct_margem, pct_acima]
                })
                fig_pizza = px.pie(
                    donut_df, names="Categoria", values="Percentual",
                    hole=0.5,
                    color="Categoria",
                    color_discrete_map={
                        "Dentro da margem": "green",
                        "Até +7km/h (tolerância)": "orange",
                        "Acima da margem": "red"
                    },
                    title="Velocidade acima da regulamentada"
                )
                st.plotly_chart(fig_pizza, use_container_width=True)

                # ---- BOXPLOT / HORIZONTAL ----
                bins = [0, 20, 30, 40, 50, 60, 80, 90, 100, 200]
                labels = [
                    "Abaixo de 20 km/h", "21 a 30 km/h", "31 a 40 km/h", "41 a 50 km/h", "51 a 60 km/h",
                    "61 a 80 km/h", "81 a 90 km/h", "91 a 100 km/h", "Acima de 101 km/h"
                ]
                df["faixa"] = pd.cut(df["velocidade"], bins=bins, labels=labels, right=True)
                faixas = df.groupby("faixa")["contagem"].sum().reset_index()
                fig_box = px.bar(
                    faixas, x="contagem", y="faixa", orientation="h",
                    labels={"contagem": "Quantidade", "faixa": "Faixa de velocidade"},
                    title="Distribuição de veículos por faixa de velocidade"
                )
                st.plotly_chart(fig_box, use_container_width=True)

        elif data_inicial and data_final and data_inicial > data_final:
            st.info("A data inicial deve ser menor ou igual à data final.")
        # Senão, não mostra nada durante a seleção

    else:
        st.info("Clique em um equipamento no mapa para começar.")


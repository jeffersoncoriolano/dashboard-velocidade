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

# Locale para separador brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

load_dotenv()

st.set_page_config(layout="wide")
st.title("📈 Dashboard das Velocidades")

# Carregar equipamentos para o mapa (agora já traz status e velocidade regulamentada)
equipamentos_df = executar_consulta(get_equipamentos())
equipamentos_validos = equipamentos_df[
    (equipamentos_df['latitude'] != 0) & (equipamentos_df['longitude'] != 0)
]

# =========== SIDEBAR (FILTRO DE DATA) ===========
with st.sidebar:
    # forçando sidebar mais larga pra acomodar o filtro de data
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            min-width: 350px !important;
            width: 350px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("Filtros")
    hj = datetime.date.today()
    data_minima = datetime.date(2024, 1, 1)
    data_maxima = datetime.date(hj.year, hj.month, hj.day)
    data_intervalo = st.date_input(
        "Selecione o intervalo de dias:",
        value=(data_maxima, data_maxima),
        min_value=data_minima,
        max_value=data_maxima,
        format="DD/MM/YYYY"
    )
    if isinstance(data_intervalo, tuple) and len(data_intervalo) == 2:
        data_inicial, data_final = data_intervalo
    else:
        data_inicial, data_final = None, None

    # Botão de consulta de inoperância
    if st.button("Consultar Inoperâncias"):
        params = {
            "data_inicial": data_inicial.strftime("%Y-%m-%d"),
            "data_final": data_final.strftime("%Y-%m-%d"),
        }
        df_inoperancia = executar_consulta(get_inoperancia(), params)

        if df_inoperancia is not None and not df_inoperancia.empty:
            st.markdown("### Resultado de Inoperância no período selecionado")
            st.dataframe(df_inoperancia)
        else:
            st.info("Nenhuma inoperância de 25h ou mais encontrada no período.")

# =========== TELA PRINCIPAL ===========

if equipamentos_validos.empty:
    st.error("❌ Nenhum equipamento válido com latitude/longitude diferente de zero encontrado!")
else:
    map_center = [
        equipamentos_validos['latitude'].mean(),
        equipamentos_validos['longitude'].mean()
    ]
    m = folium.Map(location=map_center, zoom_start=12)
    mapa_id_por_nome = {}

    for _, row in equipamentos_validos.iterrows():
        popup_text = f"Nome: {row['nome_processador']}<br>ID: {row['id']}"

        # Escolhe a cor do ícone conforme status
        if row['status'] == 1:
            icon_path = "icon/icone_radar_ativo.png"
        else:
            icon_path = "icon/icone_radar_inativo.png"
       
        icon = folium.CustomIcon(
            icon_path,
            icon_size=(32,32),
            icon_anchor=(16,16)
        )

        folium.Marker(
            location=[row['latitude'], row['longitude']],
            tooltip=row['nome_processador'],
            popup=popup_text,
            icon=icon
        ).add_to(m)
        
        mapa_id_por_nome[row['nome_processador']] = row['id']

    st.markdown("#### Selecione um equipamento clicando no mapa ⤵️")
    map_result = st_folium(m, height=500, width=900, key="mapa")  # key para estabilidade

    # Persistir seleção entre interações
    if "equip_selecionado" not in st.session_state:
        st.session_state.equip_selecionado = None

    equipamento_clicado = map_result.get("last_object_clicked_tooltip")
    if equipamento_clicado:
        st.session_state.equip_selecionado = equipamento_clicado

    equipamento_selecionado = st.session_state.equip_selecionado  
    equipamento_id = mapa_id_por_nome.get(equipamento_selecionado)

    if equipamento_selecionado:
        st.info(f"✅ Equipamento selecionado: {equipamento_selecionado}")

        # Busca as infos do equipamento selecionado
        info_eq = equipamentos_validos[equipamentos_validos["id"] == equipamento_id].iloc[0]

        # ===== Linha 1 (duas colunas) =====
        colA, colB = st.columns([2,2])  # mantém apenas 2 cards na primeira linha

        with colA:
            st.markdown(
                f"""<div class="card-indicador">
                    <div class="sub-label">Velocidade Regulamentada</div>
                    <div class="destaque">{info_eq['vel_regulamentada']} km/h</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with colB:
            status_text = "ATIVO" if info_eq.get("status", 1) else "INATIVO"
            status_color = "#0c810c" if info_eq.get("status", 1) else "#c71111"
            st.markdown(
                f"""<div class="card-indicador">
                    <div class="sub-label">Status do Equipamento</div>
                    <div class="status" style="color:{status_color}">{status_text}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        # Pré-criar bloco de 3 colunas para as linhas seguintes (velocidades e fluxo)
        col2A, col2B, col2C = st.columns([2,2,2])

        # Inicializar variáveis para evitar NameError quando não houver dados de velocidade
        df_velocidade = pd.DataFrame()
        total_veiculos_ocr = 0
        pct_regulamentada = pct_dentro_tolerancia = pct_acima_tolerancia = 0.0

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
            df_velocidade = executar_consulta(query, params)

            if df_velocidade is None or df_velocidade.empty:
                st.warning("Nenhum dado de velocidade encontrado para o período e equipamento selecionados.")
            else:
                # ----- INDICADORES -----
                velocidade_max = df_velocidade["velocidade"].max()
                velocidade_moda = df_velocidade.loc[df_velocidade['contagem'].idxmax(), "velocidade"]
                total_veiculos_ocr = df_velocidade["contagem"].sum()
                velocidade_media = df_velocidade['velocidade'].mean()

                # Agora usa a velocidade do equipamento:
                velocidade_regulamentada = info_eq['vel_regulamentada']
                margem_tolerancia = (velocidade_regulamentada * 0.1)

                dentro_regulamentada = df_velocidade[df_velocidade["velocidade"] <= velocidade_regulamentada]["contagem"].sum()
                acima_tolerancia = df_velocidade[df_velocidade["velocidade"] > (velocidade_regulamentada + margem_tolerancia)]["contagem"].sum()
                dentro_tolerancia = total_veiculos_ocr - acima_tolerancia - dentro_regulamentada

                pct_regulamentada = round(dentro_regulamentada / total_veiculos_ocr * 100,  2) if total_veiculos_ocr > 0 else 0
                pct_dentro_tolerancia = round(dentro_tolerancia / total_veiculos_ocr * 100, 2) if total_veiculos_ocr > 0 else 0
                pct_acima_tolerancia = round(acima_tolerancia / total_veiculos_ocr * 100, 2) if total_veiculos_ocr > 0 else 0
   
                # ===== Linha 2 (três colunas) =====
                with col2A:
                    st.markdown(
                        f"""<div class="card-indicador">
                            <div class="sub-label">Velocidade Média</div>
                            <div class="destaque">{velocidade_media:.1f} km/h</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                with col2B:
                    st.markdown(
                        f"""<div class="card-indicador">
                            <div class="sub-label">Velocidade Mais Praticada</div>
                            <div class="destaque">{velocidade_moda:.1f} km/h</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                with col2C:
                    st.markdown(
                        f"""<div class="card-indicador">
                            <div class="sub-label">Velocidade Máxima</div>
                            <div class="destaque">{velocidade_max:.1f} km/h</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                # ===== Linha 3 (usa mesmas 3 colunas) — lado esquerdo =====
                with col2A:
                    st.markdown(
                        f"""<div class="card-indicador">
                            <div class="sub-label">Total de Veículos Lidos (OCR)</div>
                            <div class="destaque">{locale.format_string('%.0f', total_veiculos_ocr, grouping=True)}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        if data_inicial and data_final and data_inicial <= data_final:
            # Consulta dados de fluxo
            query_fluxo = get_fluxo(equipamento_selecionado, data_inicial, data_final)

            params_fluxo = {
                "nome_processador": equipamento_selecionado,
                "data_inicial": data_inicial.strftime("%Y-%m-%d"),
                "data_final": data_final.strftime("%Y-%m-%d"),
            }

            df_fluxo = executar_consulta(query_fluxo, params_fluxo)

            # Validar None/empty e somar para obter número (evita Series)
            if df_fluxo is None or df_fluxo.empty or df_fluxo["fluxo_total"].isnull().all():
                st.warning("Nenhum dado de fluxo encontrado para o período e equipamento selecionados.")
            else:
                total_veiculos = int(pd.to_numeric(df_fluxo['fluxo_total'], errors='coerce').fillna(0).sum())  

                aproveitamento_ocr = 0.0  # inicializa
                if total_veiculos > 0 and total_veiculos_ocr > 0:
                    aproveitamento_ocr = (total_veiculos_ocr / total_veiculos) * 100

                # ===== Linha 3 (complemento nas colunas do meio e direita) =====
                with col2B:
                    st.markdown(
                        f"""<div class="card-indicador">
                            <div class="sub-label">Total de Veículos no Período</div>
                            <div class="destaque">{locale.format_string('%.0f', total_veiculos, grouping=True)}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                with col2C:
                    st.markdown(
                        f"""<div class="card-indicador">
                            <div class="sub-label">Aproveitamento de OCR</div>
                            <div class="destaque">{locale.format_string('%.2f', aproveitamento_ocr, grouping=True)} %</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        # ----- INDICADORES VISUAIS EM CARDS -----
        st.markdown("""
            <style>
            .card-indicador {
                background: #f5f5f5;
                border-radius: 18px;
                padding: 22px 5px 15px 5px;
                margin: 0 10px 20px 0;
                min-width: 210px;
                text-align: center;
                display: flex;
                flex-direction: column;
                justify-content: center;
                height: 90px;
            }
            .destaque {
                font-size: 2.1rem;
                color: #005cb2;
                font-weight: bold;
                margin-top: 3px;
            }
            .status {
                font-size: 2rem;
                font-weight: bold;
                margin-top: 3px;
            }
            .sub-label {
                font-size: 1.06rem;
                color: #444;
                margin-bottom: 0.25rem;
            }
            </style>
        """, unsafe_allow_html=True)
        
        if df_velocidade is None or df_velocidade.empty:
            pass
        else:
            # =========== GRÁFICOS ===========
            fig_bar = px.bar(
                df_velocidade, x="velocidade", y="contagem",
                labels={"velocidade": "Velocidade (km/h)", "contagem": "Quantidade"},
                title=f"Distribuição das Velocidades ({data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}):"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            donut_df = pd.DataFrame({
                "Categoria": ["Abaixo da Regulamentada", "Dentro da Tolerância de 10%", "Excesso de Velocidade"],
                "Percentual": [pct_regulamentada, pct_dentro_tolerancia, pct_acima_tolerancia],
                "Valores": [dentro_regulamentada, dentro_tolerancia, acima_tolerancia]
            })
            fig_pizza = px.pie(
                donut_df, names="Categoria", values="Valores",
                hole=0.5,
                color="Categoria",
                color_discrete_map={
                    "Excesso de Velocidade": "red",
                    "Dentro da Tolerância de 10%": "orange",
                    "Abaixo da Regulamentada": "green"
                },
                title="Velocidades Acima da Regulamentada:"
            )
            st.plotly_chart(fig_pizza, use_container_width=True)

            bins = [0, 20, 30, 40, 50, 60, 80, 90, 100, 200]
            labels = [
                "Abaixo de 20 km/h", "21 a 30 km/h", "31 a 40 km/h", "41 a 50 km/h", "51 a 60 km/h",
                "61 a 80 km/h", "81 a 90 km/h", "91 a 100 km/h", "Acima de 101 km/h"
            ]
            df_velocidade["faixa"] = pd.cut(df_velocidade["velocidade"], bins=bins, labels=labels, right=True)
            faixas = df_velocidade.groupby("faixa")["contagem"].sum().reset_index()
            fig_box = px.bar(
                faixas, x="contagem", y="faixa", orientation="h",
                labels={"contagem": "Quantidade", "faixa": "Faixa de velocidade"},
                title="Distribuição de Veículos por Faixa de Velocidade:"
            )
            st.plotly_chart(fig_box, use_container_width=True)

    elif data_inicial and data_final and data_inicial > data_final:
        st.info("A data inicial deve ser menor ou igual à data final.")
    else:
        st.info("Clique em um equipamento no mapa para começar.")

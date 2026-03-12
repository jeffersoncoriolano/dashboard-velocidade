import streamlit as st 
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import datetime
from dotenv import load_dotenv
import locale
import base64
from pathlib import Path
from api_client import APIClient

def _img_b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""  # evita quebrar a página se faltar o arquivo
    return base64.b64encode(p.read_bytes()).decode("utf-8")

# Locale para separador brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

load_dotenv()

try:
    # O cliente HTTP encapsula autenticacao e formato das respostas da API.
    # Se a configuracao estiver incompleta, o dashboard para logo no inicio
    # com uma mensagem objetiva em vez de falhar em pontos aleatorios da tela.
    api_client = APIClient()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.set_page_config(page_title="Dashboard das Velocidades", layout="wide")
st.title("📈 Dashboard das Velocidades")

# >>> CSS para controle de impressão, quebras de página e tamanhos
st.markdown("""
<style>
/* --- TELA (normal) --- */
.print-only { display: none; }           /* aparece só na impressão */
.no-print  { display: block; }           /* aparece só na tela */

.report-section { margin-bottom: 18px; }
.avoid-break { break-inside: avoid; page-break-inside: avoid; }
.print-page-break { height: 0; }

/* Ajustes visuais dos gráficos na tela */
.plot-wrap { padding: 4px 8px; }

/* --- IMPRESSÃO --- */
@page { size: A4 portrait; margin: 12mm; }  /* mude para 'A4 landscape' p/ teste */

@media print {
  .print-only { display: block !important; }
  .no-print  { display: none !important; }

  header[data-testid="stHeader"],
  section[data-testid="stSidebar"],
  footer { display: none !important; }

  .main .block-container { padding-top: 0 !important; }

  .avoid-break { break-inside: avoid; page-break-inside: avoid; }
  .print-page-break { page-break-before: always; break-before: page; }

  /* Deixa as duas colunas de gráficos realmente 50/50 na impressão */
  .two-up { display: flex; gap: 12px; }
  .two-up > div { flex: 1 1 50%; }
}
</style>
""", unsafe_allow_html=True)

# Carregar equipamentos para o mapa (agora já traz status e velocidade regulamentada).
# Se a API estiver indisponivel, a tela para aqui com uma mensagem objetiva.
try:
    equipamentos_df = api_client.get_equipamentos()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

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
    # Streamlit pode devolver:
    # - tuple (start, end) quando o range está completo
    # - date (uma data) enquanto o usuário ainda está escolhendo
    # - tuple estranho/len != 2 em alguns casos de interação
    if isinstance(data_intervalo, tuple):
        if len(data_intervalo) == 2:
            data_inicial, data_final = data_intervalo
        elif len(data_intervalo) == 1:
            data_inicial = data_final = data_intervalo[0]
        else:
            data_inicial = data_final = None
    elif isinstance(data_intervalo, datetime.date):
        data_inicial = data_final = data_intervalo
    else:
        data_inicial = data_final = None

    # Botão de consulta de inoperância
    if st.button("Consultar Inoperâncias"):
        if not (data_inicial and data_final):
            st.warning("Selecione o intervalo completo antes de consultar inoperâncias.")
        else:
            # A API ja carrega a regra de negocio de inoperancia.
            # O dashboard so envia o periodo selecionado e exibe o retorno.
            try:
                df_inoperancia = api_client.get_inoperancia(
                    data_ini=data_inicial.strftime("%Y-%m-%d"),
                    data_fim=data_final.strftime("%Y-%m-%d"),
                )
            except RuntimeError as exc:
                st.error(str(exc))
                df_inoperancia = pd.DataFrame()

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

    col_map, col_leg = st.columns([4, 1], gap="large")

    with col_map:
        map_result = st_folium(m, height=500, width=None, key="mapa")  # width=None -> responsivo

    with col_leg:
        st.markdown(
            """
            <div style="
                border:1px solid rgba(0,0,0,0.12);
                border-radius:14px;
                padding:12px 12px;
                background:#ffffff;
                color:#111827;
            ">
            <div style="font-weight:700; margin-bottom:10px;">Legenda</div>

            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                <img src="data:image/png;base64,{RADAR_ATIVO}" style="width:28px; height:28px;" />
                <div><b>Ativo</b></div>
            </div>

            <div style="display:flex; align-items:center; gap:10px;">
                <img src="data:image/png;base64,{RADAR_INATIVO}" style="width:28px; height:28px;" />
                <div><b>Inativo</b></div>
            </div>
            </div>
            """.format(
                RADAR_ATIVO=_img_b64("icon/icone_radar_ativo.png"),
                RADAR_INATIVO=_img_b64("icon/icone_radar_inativo.png"),
            ),
            unsafe_allow_html=True,
        )

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
        if data_inicial and data_final:
            st.info(
                f"✅ Período selecionado: {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}"
            )
        else:
            st.info("✅ Selecione o período (intervalo completo) no calendário da sidebar.")

        # Busca as infos do equipamento selecionado
        info_eq = equipamentos_validos[equipamentos_validos["id"] == equipamento_id].iloc[0]

        # ===== Linha 1 (duas colunas) =====
        colA, colB = st.columns([2,2])  # mantém apenas 2 cards na primeira linha

        # >>> envolver os cards em contêiner que evita quebra
        st.markdown('<div class="avoid-break">', unsafe_allow_html=True)

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
            # A distribuicao continua sendo tratada no cliente porque os
            # graficos e cards ja dependem desse formato agregado.
            try:
                df_velocidade = api_client.get_distribuicao_velocidade(
                    equipamento_id=equipamento_id,
                    data_ini=data_inicial.strftime("%Y-%m-%d"),
                    data_fim=data_final.strftime("%Y-%m-%d"),
                )
            except RuntimeError as exc:
                st.error(str(exc))
                df_velocidade = pd.DataFrame()

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
            # O fluxo total agora tambem vem da API, ja alinhado com a regra
            # correta de somar volume_veiculos em dados_trafego.
            try:
                total_veiculos = api_client.get_fluxo(
                    nome_processador=equipamento_selecionado,
                    data_ini=data_inicial.strftime("%Y-%m-%d"),
                    data_fim=data_final.strftime("%Y-%m-%d"),
                )
            except RuntimeError as exc:
                st.error(str(exc))
                total_veiculos = 0

            if total_veiculos <= 0:
                st.warning("Nenhum dado de fluxo encontrado para o per?odo e equipamento selecionados.")
            else:
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

        # fecha o contêiner de cards que evita quebra na impressão
        st.markdown('</div>', unsafe_allow_html=True)

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
        
        # >>> quebra de página depois do mapa e dos cards (vai iniciar a página 2)
        st.markdown('<div class="print-page-break"></div>', unsafe_allow_html=True)

        if df_velocidade is None or df_velocidade.empty:
            pass
        else:
            # ======= GRÁFICOS =======

            # >>> tamanhos consistentes p/ caber 2 por página
            common_margins = dict(t=40, b=40, l=40, r=20)

            # ---- GRÁFICO DE DISTRIBUIÇÃO (barras) ----
            fig_bar = px.bar(
                df_velocidade, x="velocidade", y="contagem",
                labels={"velocidade": "Velocidade (km/h)", "contagem": "Quantidade"},
                title=f"Distribuição das Velocidades ({data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')})"
            )
            fig_bar.update_layout(height=420, margin=common_margins)

            # ---- PIZZA ----
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
                title="Excessos de Velocidade"
            )
            fig_pizza.update_layout(height=420, margin=common_margins, legend=dict(orientation="h"))

            # ---- FAIXAS (horizontal) ----
            bins = [0, 20, 30, 40, 50, 60, 80, 90, 100, 120, float("inf")]
            labels = [
                "Abaixo de 20 km/h", "21 a 30 km/h", "31 a 40 km/h", "41 a 50 km/h", "51 a 60 km/h",
                "61 a 80 km/h", "81 a 90 km/h", "91 a 100 km/h", "101 a 120 km/h", "Acima de 120 km/h"
            ]

            df_velocidade["faixa"] = pd.cut(
                df_velocidade["velocidade"],
                bins=bins,
                labels=labels,
                right=True
            )

            faixas = df_velocidade.groupby("faixa")["contagem"].sum().reset_index()

            fig_box = px.bar(
                faixas,
                x="contagem",
                y="faixa",
                orientation="h",
                text="contagem",  # adiciona valores nas barras
                labels={"contagem": "Quantidade", "faixa": "Faixa de velocidade"},
                title="Distribuição de Veículos por Faixa de Velocidade"
            )

            # posição do texto fora das barras
            fig_box.update_traces(textposition="outside")

            # calcula o maior valor para abrir espaço para o texto "fora" da barra
            mc = pd.to_numeric(faixas["contagem"], errors="coerce")
            max_contagem = float(mc.max()) if mc.notna().any() else 0.0
            xmax = (max_contagem * 1.18) if max_contagem > 0 else 10  # 15% de folga (ajuste se quiser)

            fig_box.update_layout(
                height=420,
                xaxis=dict(title="Quantidade", range=[0, xmax]),
                yaxis=dict(title="Faixa de Velocidade")
            )

            # ===== Página 2: gráfico de distribuição SOZINHO =====
            st.markdown('<div class="report-section avoid-break">', unsafe_allow_html=True)
            st.markdown('<div class="plot-wrap">', unsafe_allow_html=True)
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # >>> quebra para começar a seção seguinte (opcional; comente se não quiser quebrar página)
            # st.markdown('<div class="print-page-break"></div>', unsafe_allow_html=True)

            # ===== Página 3: DOIS gráficos lado a lado (pizza + faixas) =====
            st.markdown('<div class="report-section avoid-break two-up">', unsafe_allow_html=True)
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown('<div class="plot-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig_pizza, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col_right:
                st.markdown('<div class="plot-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig_box, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)


    elif data_inicial and data_final and data_inicial > data_final:
        st.info("A data inicial deve ser menor ou igual à data final.")
    else:
        st.info("Clique em um equipamento no mapa para começar.")

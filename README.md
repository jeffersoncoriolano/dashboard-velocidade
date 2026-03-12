# Dashboard de Velocidades

Painel em `Python + Streamlit` para visualizar dados de velocidade, fluxo e inoperancia de equipamentos de fiscalizacao eletronica.

Nesta versao, o dashboard **nao acessa mais o banco diretamente**. Ele consome a `mobilidade-api` por HTTP.

## Arquitetura

- Frontend: `Streamlit`
- Graficos: `Plotly`
- Mapa: `Folium`
- Fonte de dados: `mobilidade-api`
- Autenticacao da API: header `X-API-Key`

## O que o painel faz

- carrega equipamentos georreferenciados no mapa
- permite selecionar um equipamento pelo mapa
- consulta inoperancia por periodo
- monta distribuicao de velocidades
- calcula indicadores e percentuais no proprio cliente
- consulta fluxo total do equipamento pela API

## Dependencias principais

- `streamlit`
- `folium`
- `streamlit-folium`
- `pandas`
- `plotly`
- `python-dotenv`
- `requests`

## Configuracao local

Crie um `.env` na raiz do projeto com base em `.env.example`:

```env
API_BASE_URL=http://127.0.0.1:8080/api
API_KEY=sua-chave-da-api
```

Observacao:
- `API_BASE_URL` deve apontar para a URL base da API, incluindo o prefixo `/api`
- `API_KEY` deve ser a mesma chave configurada na `mobilidade-api`

## Execucao local

1. Crie e ative uma virtualenv

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instale as dependencias

```bash
pip install -r requirements.txt
```

3. Execute o dashboard

```bash
streamlit run app.py
```

4. Acesse no navegador

```text
http://localhost:8501
```

## Estrutura do projeto

```text
dashboard-velocidade/
|-- app.py
|-- api_client.py
|-- requirements.txt
|-- .env.example
|-- icon/
|-- screenshots/
```

## Observacoes de implementacao

- O dashboard usa `nome_processador` para consultar o fluxo total do equipamento completo.
- A distribuicao de velocidades continua sendo tratada no cliente para preservar os graficos e os cards atuais.
- O endpoint de inoperancia da API aceita no maximo 31 dias por consulta.

## Validacao esperada

Antes de considerar a migracao concluida, valide:

- mapa carregando equipamentos
- selecao de equipamento pelo mapa
- consulta de inoperancia
- cards de velocidade
- card de fluxo total
- card de aproveitamento OCR
- graficos de distribuicao, pizza e faixas

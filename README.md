# 📊 Dashboard de Velocidades

Painel interativo desenvolvido em **Python + Streamlit** para visualização e análise de velocidades de veículos registradas por equipamentos de fiscalização eletrônica.  
O sistema se conecta a um banco de dados **MySQL (AWS RDS)** e permite explorar estatísticas, indicadores e gráficos de tráfego de forma intuitiva.

---

## 🚀 Funcionalidades

- 🔎 **Seleção de período** via calendário interativo (filtro por intervalo de datas).  
- 🗺️ **Mapa interativo** (Folium) com os equipamentos georreferenciados e status (ativo/inativo).  
- 📈 **Indicadores em cards**:
  - Velocidade regulamentada  
  - Status do equipamento  
  - Velocidade média, moda e máxima  
  - Total de veículos lidos (OCR)  
  - Fluxo total de veículos  
  - Aproveitamento de OCR (%)  
- 📊 **Gráficos dinâmicos** (Plotly):  
  - Distribuição de velocidades (barras)  
  - Percentuais abaixo/dentro/acima da tolerância (pizza)  
  - Faixas de velocidade (bar chart horizontal)  
- ⚠️ **Consulta de inoperâncias** de equipamentos (quando ficaram 25h ou mais sem registrar veículos).  

---

## 🖼️ Screenshots

### Mapa interativo + seleção de equipamento
![Mapa](https://github.com/jeffersoncoriolano/dashboard-velocidade/blob/main/screenshots/mapa_interativo.png)

### Indicadores de velocidade e status
![Indicadores](https://github.com/jeffersoncoriolano/dashboard-velocidade/blob/main/screenshots/indicadores_de_velocidade.png)

### Distribuição das velocidades
![Gráfico](https://github.com/jeffersoncoriolano/dashboard-velocidade/blob/main/screenshots/distribuicao_de_velocidades.png)

### Excessos de velocidade
![Gráfico](https://github.com/jeffersoncoriolano/dashboard-velocidade/blob/main/screenshots/excessos_de_velocidade.png)

### Faixas de velocidade
![Fluxo](https://github.com/jeffersoncoriolano/dashboard-velocidade/blob/main/screenshots/faixas_de_velocidade.png)

---

## 🛠️ Tecnologias utilizadas

- **Linguagem:** Python 3.12  
- **Framework web:** [Streamlit](https://streamlit.io/)  
- **Visualizações:** Plotly, Folium  
- **Banco de dados:** MySQL (AWS RDS)  
- **Conexão:** PyMySQL + dotenv  
- **Manipulação de dados:** Pandas, Numpy  

---

## ⚙️ Instalação e uso local

1. Clone este repositório:
```bash
    git clone https://github.com/jeffersoncoriolano/dashboard-velocidade.git
    cd dashboard-velocidade
```

2. Crie e ative um ambiente virtual:
```bash
    python3 -m venv .venv
    source .venv/bin/activate   # Linux/Mac
    .venv\Scripts\activate      # Windows (PowerShell)
```

3. Instale as dependências:
```bash
    pip install -r requirements.txt
```

4. Crie um arquivo .env na raiz do projeto com as credenciais do banco:
```bash
    DB_HOST=seu_host
    DB_PORT=3306
    DB_USER=seu_usuario
    DB_PASSWORD=sua_senha
    DB_NAME=seu_banco
```

5. Execute o dashboard:
```bash
    streamlit run app.py
```

6. Acesse no navegador:
```bash
    http://localhost:8501
```

---

## ☁️ Deploy na AWS (produção)

O sistema foi implantado em:

- **Banco de dados**: Amazon RDS (MySQL).
- **Aplicação**: Amazon EC2 (Ubuntu), rodando como serviço systemd e exposto via Nginx.
- **Domínio customizado**: coriolano.app gerenciado pelo Cloudflare.

---

## 📂 Estrutura do projeto
   ```bash
    dashboard-velocidade/
    │── app.py              # Código principal do dashboard (Streamlit)
    │── db_connector.py     # Conexão ao banco de dados (PyMySQL + dotenv)
    │── queries.py          # Consultas SQL reutilizáveis
    │── requirements.txt    # Dependências do projeto
    │── icon/               # Ícones customizados para os marcadores no mapa
    │── .env (local)        # Variáveis de ambiente (não versionado)
    ```

---

## 📜 Licença

    Este projeto está sob a licença MIT.
    Sinta-se livre para usar, modificar e distribuir.

---
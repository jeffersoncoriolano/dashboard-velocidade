# Refatoracao - Dashboard Velocidade Consumindo API

## Objetivo
Refatorar o projeto `dashboard-velocidade` para deixar de acessar o MySQL/RDS diretamente e passar a consumir a `mobilidade-api`, preservando o comportamento visual e funcional atual do painel.

## Estado Atual Identificado

### Arquivos relevantes
- `app.py`
- `db_connector.py`
- `queries.py`
- `.env`
- `requirements.txt`

### Como o dashboard funciona hoje
- Carrega equipamentos diretamente do banco para montar o mapa.
- Consulta inoperancia diretamente no banco ao clicar no botao da sidebar.
- Consulta distribuicao de velocidades diretamente no banco para:
  - grafico de distribuicao
  - indicadores de media, moda, maxima
  - percentuais por faixa
  - total OCR
- Consulta fluxo diretamente no banco para:
  - total de veiculos no periodo
  - aproveitamento OCR

### Dependencias diretas do banco hoje
- `db_connector.py` abre conexao PyMySQL com `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`
- `queries.py` guarda SQLs do dashboard
- `app.py` chama `executar_consulta(...)` em varios pontos

### Endpoints da API que ja existem e podem ser usados
- `GET /health`
- `GET /equipamentos`
- `GET /equipamentos/inoperancia`
- `GET /velocidades/distribuicao`
- `GET /velocidades/indicadores`
- `GET /trafego/fluxo`

### Pontos de compatibilidade importantes
- A API esta exposta em `/api/...`
- A API exige `X-API-Key` para endpoints protegidos
- O dashboard hoje depende de:
  - `nome_processador`
  - `id`
  - `status`
  - `vel_regulamentada`
  - `latitude`
  - `longitude`
- O dashboard ainda calcula no cliente:
  - graficos
  - faixas de velocidade
  - layout e apresentacao

## Estrategia Recomendada

### Principio
Trocar apenas a camada de acesso a dados primeiro, sem reescrever layout, mapa, graficos ou fluxo de interacao.

### Abordagem
- Remover acesso direto ao banco.
- Criar cliente HTTP simples para a API.
- Substituir cada consulta SQL por chamada a endpoint equivalente.
- Manter transformacoes de `pandas` e `plotly` no cliente, desde que os dados da API entreguem o necessario.

## Plano de Execucao

- [x] 1. Criar cliente HTTP da API
  - Criar um modulo novo, por exemplo `api_client.py`.
  - Ler do `.env`:
    - `API_BASE_URL`
    - `API_KEY`
  - Implementar helper para `GET` com:
    - timeout
    - envio de header `X-API-Key`
    - tratamento minimo de erro
    - retorno em formato facil de converter para `pandas.DataFrame`
  - Objetivo: concentrar toda comunicacao HTTP em um lugar.

- [x] 2. Ajustar configuracao do projeto
  - Atualizar `.env.example` ou documentacao equivalente para deixar de pedir credenciais do MySQL e passar a pedir:
    - `API_BASE_URL`
    - `API_KEY`
  - Decidir se `DB_*` continuam temporariamente para transicao ou se saem de vez.
  - Objetivo: refletir corretamente a nova dependencia do dashboard.

- [x] 3. Remover dependencia do `db_connector.py`
  - Parar de usar `executar_consulta`.
  - Manter o arquivo temporariamente se ajudar na transicao, mas sem uso ativo no `app.py`.
  - Objetivo: eliminar acoplamento com PyMySQL e RDS.

- [x] 4. Substituir carregamento de equipamentos pelo endpoint da API
  - Hoje:
    - `get_equipamentos()` + `executar_consulta(...)`
  - Novo fluxo:
    - `GET /api/equipamentos`
  - Parametros recomendados:
    - `tipo_equipamento=radar`
    - `faixa_monitorada=A`
    - `only_valid_geo=true`
    - `limit` suficientemente alto para cobrir todos os equipamentos
  - Validar se a API retorna tudo que o mapa precisa:
    - `id`
    - `nome_processador`
    - `latitude`
    - `longitude`
    - `status`
    - `vel_regulamentada`
  - Se faltar campo no retorno, ajustar o dashboard para consumir o que existe ou abrir tarefa separada.

- [x] 5. Substituir consulta de inoperancia pelo endpoint da API
  - Hoje:
    - SQL em `get_inoperancia()`
  - Novo fluxo:
    - `GET /api/equipamentos/inoperancia?data_ini=...&data_fim=...`
  - Validar:
    - limite maximo de 31 dias
    - retorno de `items`
    - transformacao para DataFrame
  - Objetivo: usar a regra de negocio ja consolidada na API.

- [x] 6. Substituir consulta de distribuicao de velocidades pelo endpoint da API
  - Hoje:
    - SQL com `SELECT velocidade, COUNT(*) AS contagem ... GROUP BY velocidade`
  - Novo fluxo:
    - `GET /api/velocidades/distribuicao?equipamento_id=...&data_ini=...&data_fim=...`
  - Converter resposta da API em DataFrame.
  - Garantir que o restante do codigo continue funcionando com colunas:
    - `velocidade`
    - `contagem`
  - Objetivo: preservar os graficos e as agregacoes do cliente.

- [x] 7. Substituir consulta de fluxo pelo endpoint da API
  - Hoje:
    - SQL de `get_fluxo(nome_processador, data_inicial, data_final)`
  - Novo fluxo:
    - preferir `GET /api/trafego/fluxo?equipamento_id=...&data_ini=...&data_fim=...`
  - Motivo:
    - usar `equipamento_id` e mais robusto que `nome_processador`
  - Ajustar calculo de `total_veiculos` e `aproveitamento_ocr` para ler do JSON da API.

- [x] 8. Decidir o uso de `GET /velocidades/indicadores`
  - Hoje o dashboard calcula localmente:
    - media
    - moda
    - maxima
    - total OCR
    - percentuais por faixa
  - A API ja tem `GET /api/velocidades/indicadores`.
  - Decisao recomendada:
    - curto prazo: continuar calculando no cliente a partir da distribuicao, se isso ja estiver coerente
    - medio prazo: migrar para o endpoint de indicadores e reduzir logica local
  - Nesta refatoracao, avaliar qual opcao reduz risco e retrabalho.

- [x] 9. Remover `queries.py` do fluxo ativo
  - Depois que todos os pontos acima forem migrados:
    - `queries.py` deve deixar de ser dependencia do `app.py`
  - Pode ser mantido temporariamente ate a refatoracao estar validada, mas idealmente sem uso.

- [x] 10. Atualizar dependencias do projeto
  - Remover `PyMySQL` se o projeto nao usar mais banco direto.
  - Adicionar biblioteca HTTP, por exemplo:
    - `requests`
  - Manter `pandas`, `plotly`, `streamlit`, `python-dotenv`.

- [x] 11. Tratar erros de API de forma amigavel no dashboard
  - Exibir mensagens claras quando:
    - a API estiver indisponivel
    - a API retornar `401` ou `403`
    - a API retornar `422` por data invalida ou intervalo grande demais
  - Objetivo: evitar tela quebrada ou excecao crua no Streamlit.

- [x] 12. Revisar autenticacao do dashboard contra a API
  - Garantir que todas as chamadas para endpoints protegidos enviem `X-API-Key`.
  - Avaliar se `/health` precisa ou nao ser usado no dashboard.

- [ ] 13. Validar fluxo funcional completo
  - Checklist manual minimo:
    - mapa carrega equipamentos
    - selecao de equipamento funciona
    - consulta de inoperancia funciona
    - indicadores aparecem
    - graficos aparecem
    - fluxo total aparece
    - aproveitamento OCR aparece
  - Comparar visualmente com a versao antiga para garantir equivalencia.

- [ ] 14. Atualizar README
  - Trocar a documentacao de acesso direto ao MySQL por documentacao de consumo da API.
  - Documentar:
    - `API_BASE_URL`
    - `API_KEY`
    - como rodar localmente
    - dependencia da `mobilidade-api`

## Riscos e Pontos de Atencao

- A API pode nao retornar todos os campos exatamente com o mesmo formato esperado pelo dashboard.
- O dashboard hoje usa `nome_processador` em alguns pontos onde a API pode preferir `equipamento_id`.
- A consulta de indicadores pode continuar local no curto prazo para evitar retrabalho desnecessario.
- O endpoint de inoperancia na API tem limite de 31 dias; o dashboard precisa respeitar isso na UX e nas mensagens.

## Ordem Recomendada de Implementacao

1. Cliente HTTP da API
2. Equipamentos
3. Inoperancia
4. Distribuicao de velocidades
5. Fluxo
6. Tratamento de erro
7. Limpeza de dependencias antigas
8. README

## Definicao de Pronto

O trabalho sera considerado pronto quando:

- o dashboard nao abrir mais conexao direta com o banco;
- `db_connector.py` e `queries.py` nao forem mais necessarios no fluxo principal;
- o painel mantiver mapa, cards, graficos e consulta de inoperancia funcionando;
- a configuracao passar a depender de `API_BASE_URL` e `API_KEY`;
- o README refletir a arquitetura nova.

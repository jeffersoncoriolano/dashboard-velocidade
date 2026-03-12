import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


class APIClient:
    """
    Cliente HTTP simples para concentrar o consumo da mobilidade-api.

    A ideia aqui e isolar:
    - leitura de configuracao
    - autenticacao por API key
    - tratamento basico de erro
    - conversao de respostas JSON em DataFrame quando fizer sentido
    """

    def __init__(self) -> None:
        base_url = os.getenv("API_BASE_URL", "").strip().rstrip("/")
        api_key = os.getenv("API_KEY", "").strip()

        if not base_url:
            raise RuntimeError(
                "API_BASE_URL nao configurada. Defina a URL base da API no arquivo .env."
            )

        if not api_key:
            raise RuntimeError(
                "API_KEY nao configurada. Defina a chave de acesso da API no arquivo .env."
            )

        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Faz uma requisicao GET para a API com timeout curto e erro explicito.

        O dashboard nao precisa conhecer detalhes de requests. Se algo der errado,
        levantamos uma excecao amigavel para que o Streamlit decida como exibir.
        """

        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text.strip() or str(exc)
            raise RuntimeError(f"Erro ao consultar a API em {path}: {detail}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Erro de comunicacao com a API em {path}: {exc}"
            ) from exc

        return response.json()

    def get_equipamentos(self, limit: int = 2000) -> pd.DataFrame:
        payload = self._get(
            "/equipamentos",
            params={
                "tipo_equipamento": "radar",
                "faixa_monitorada": "A",
                "only_valid_geo": "true",
                "limit": limit,
            },
        )
        return pd.DataFrame(payload.get("items", []))

    def get_inoperancia(self, data_ini: str, data_fim: str) -> pd.DataFrame:
        payload = self._get(
            "/equipamentos/inoperancia",
            params={"data_ini": data_ini, "data_fim": data_fim},
        )
        return pd.DataFrame(payload.get("items", []))

    def get_distribuicao_velocidade(
        self, equipamento_id: int, data_ini: str, data_fim: str
    ) -> pd.DataFrame:
        payload = self._get(
            "/velocidades/distribuicao",
            params={
                "equipamento_id": equipamento_id,
                "data_ini": data_ini,
                "data_fim": data_fim,
            },
        )
        return pd.DataFrame(payload.get("items", []))

    def get_fluxo(
        self,
        data_ini: str,
        data_fim: str,
        equipamento_id: int | None = None,
        nome_processador: str | None = None,
    ) -> int:
        params: dict[str, Any] = {"data_ini": data_ini, "data_fim": data_fim}

        # Preferimos equipamento_id quando ele estiver disponivel porque e mais
        # estavel que depender de nome_processador como identificador funcional.
        if equipamento_id is not None:
            params["equipamento_id"] = equipamento_id
        elif nome_processador is not None:
            params["nome_processador"] = nome_processador
        else:
            raise ValueError("Informe equipamento_id ou nome_processador para consultar fluxo.")

        payload = self._get("/trafego/fluxo", params=params)
        return int(payload.get("fluxo_total") or 0)

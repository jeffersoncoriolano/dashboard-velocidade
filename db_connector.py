import pymysql
import pandas as pd
import os

from dotenv import load_dotenv
load_dotenv()

def conectar():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT")),
    )

def executar_consulta(query, params=None):
    con = conectar()
    try:
        df = pd.read_sql(query, con=con, params=params)
        return df
    finally:
        con.close()

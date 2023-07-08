import pandas as pd
import requests
from urllib import parse


def query(method: str, table_columns: list = None, **kwargs):
    """
    Sending query to ISS MOEX
    :param method:
    :param table_columns:
    :param kwargs:
    :return:
    """
    url = f'https://iss.moex.com/iss/{method}.json'
    if kwargs:
        url += "?" + parse.urlencode(kwargs)

    result = requests.get(url)
    result.encoding = 'utf-8'
    result = result.json()

    df = pd.DataFrame(result['securities']['data'],
                      columns=result['securities']['columns'])
    if table_columns:
        df = df[table_columns]
    return df

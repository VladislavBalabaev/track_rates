import pandas as pd
import requests
from urllib import parse


def query(method: str,
          json_key='securities',
          table_columns: list = None,
          **kwargs):
    """
    Sending query to ISS MOEX.
    """
    url = f'https://iss.moex.com/iss/{method}.json'
    if kwargs:
        url += "?" + parse.urlencode(kwargs)

    result = requests.get(url)
    result.encoding = 'utf-8'
    result = result.json()
    try:
        df = pd.DataFrame(result[json_key]['data'],
                          columns=result[json_key]['columns'])
        if table_columns:
            df = df[table_columns]
        return df
    except KeyError:
        return result

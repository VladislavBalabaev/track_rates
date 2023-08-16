import pandas as pd
import datetime as dt
from termcolor import colored


def dt_now_str():
    """
    Get current datetime painted green in string format.
    """
    now = dt.datetime.now().isoformat(sep=" ", timespec="seconds")
    return f"{colored(text=f'({now})', color='green')}"


def pandify(json_object, json_key='securities', columns: list = None):
    """
    Transform json object to pd.Dataframe.
    """
    df = pd.DataFrame(json_object[json_key]['data'],
                      columns=json_object[json_key]['columns'])
    if columns:
        df = df[columns]
    return df

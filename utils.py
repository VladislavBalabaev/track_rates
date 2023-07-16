import pandas as pd
import requests
from urllib import parse
# import datetime as dt


def query(method: str, details: dict = None):
    """
    Sending query to ISS MOEX.
    """
    url = f'https://iss.moex.com/iss/{method}.json'
    if details:
        url += "?" + parse.urlencode(details)

    result = requests.get(url)
    result.encoding = 'utf-8'
    return result.json()


def pandify(json_object, json_key='securities', table_columns: list = None):
    df = pd.DataFrame(json_object[json_key]['data'],
                      columns=json_object[json_key]['columns'])
    if table_columns:
        df = df[table_columns]
    return df


bond_columns_for_get_bond_info = {
    'secid', 'issuedate', 'matdate', 'buybackdate', 'initialfacevalue', 'faceunit',
    'facevalue', 'listlevel', 'includedbymoex', 'issuesize', 'isqualifiedinvestors',
    'couponfrequency', 'couponpercent', 'couponvalue', 'typename'
}


def get_bond_info(secid):
    global bond_columns_for_get_bond_info
    # def get_yield(secid):
    #     date = (dt.datetime.now() - dt.timedelta(days=7)).strftime("%Y-%m-%d")
    #     result = query(f"history/engines/stock/markets/bonds/sessions/3/securities/{secid}", details={'from': date})
    #     result = pandify(json_object=result, json_key='history')

    bond_info = query(f"securities/{secid}")

    bond_info = pandify(json_object=bond_info, json_key='description')
    bond_info['name'] = bond_info['name'].str.lower()
    bond_columns = list(set.intersection(bond_columns_for_get_bond_info, set(bond_info['name'])))
    bond_info = bond_info \
        .set_index('name') \
        .loc[bond_columns, ['value']] \
        .T
    return bond_info

def get_bonds(n_pages: int):
    all_bonds = []
    for page in range(n_pages):
        bonds = query(
            "securities",
            details={'group_by': 'group',
                     'group_by_filter': 'stock_bonds',
                     'limit': 100,
                     'start': page * 100}
        )
        bonds = pandify(
            json_object=bonds,
            table_columns=['secid', 'name', 'is_traded', 'type', 'primary_boardid']
        )
        if bonds.shape[0] == 0:
            break
        all_bonds.append(bonds)
    all_bonds = pd.concat(all_bonds)

    all_bonds_info = pd.concat([get_bond_info(secid=secid) for secid in all_bonds['secid']])

    all_bonds = pd.merge(all_bonds, all_bonds_info, on='secid', how='left')
    return all_bonds

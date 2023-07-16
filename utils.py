import pandas as pd
import requests
from urllib import parse
from tqdm import tqdm
from termcolor import colored
import datetime as dt


def dt_now_str():
    now = dt.datetime.now().isoformat(sep=" ", timespec="seconds")
    return colored(now, 'green')


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


def add_bonds_info(all_bonds):
    print(f'\n({dt_now_str()}) Start of adding info to bonds:')

    all_bonds_info = []
    for secid in tqdm(all_bonds['secid'].unique()):
        all_bonds_info.append(get_bond_info(secid=secid))
    all_bonds_info = pd.concat(all_bonds_info)

    print(f'({dt_now_str()}) End of adding info to bonds.')
    return pd.merge(all_bonds, all_bonds_info, on='secid', how='left')


def get_bonds(n_pages: int, add_info: bool = True):
    some_details = {'group_by': 'group',
                    'group_by_filter': 'stock_bonds',
                    'limit': 100}
    table_columns = ['secid', 'name', 'is_traded', 'type', 'primary_boardid']

    print(f'({dt_now_str()}) Start of pages parsing:')

    all_bonds = []
    for page in (pbar := tqdm(range(n_pages))):
        bonds = query("securities", details=some_details | {'start': page * 100})
        bonds = pandify(json_object=bonds, table_columns=table_columns)

        pbar.set_description(f"{bonds.shape[0]} bonds collected from {page}th page.")

        if bonds.shape[0] == 0:
            pbar.close()
            print(f'({dt_now_str()}) Pages ran out earlier that {n_pages}. All {page} pages are collected.')
            break

        all_bonds.append(bonds)
    else:
        print(f'({dt_now_str()}) All {n_pages} were parsed.')

    all_bonds = pd.concat(all_bonds)

    if add_info:
        all_bonds = add_bonds_info(all_bonds)
    return all_bonds

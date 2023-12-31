import time
import requests
import numpy as np
import pandas as pd
import datetime as dt
from tqdm import tqdm
from urllib import parse
from termcolor import colored

from timeout import timeout, TimeoutError


columns_for_info = {
    'secid', 'issuedate', 'matdate', 'buybackdate', 'initialfacevalue', 'faceunit',
    'facevalue', 'listlevel', 'includedbymoex', 'issuesize', 'isqualifiedinvestors',
    'couponfrequency', 'couponpercent', 'couponvalue', 'typename'
}


def dt_now_str():
    """
    Get current datetime painted green in string format.
    """
    now = dt.datetime.now().isoformat(sep=" ", timespec="seconds")

    return colored(text=f'({now})', color='green')


def pandify(json_object, json_key='securities', columns: list = None):
    """
    Transform json object to pd.Dataframe.
    """
    df = pd.DataFrame(json_object[json_key]['data'],
                      columns=json_object[json_key]['columns'])
    if columns:
        df = df[columns]

    return df


def query(method: str, details: dict = None):
    """
    Sending query to ISS MOEX.
    """
    if 'https://iss.moex.com/iss/' in method:
        raise ValueError('Please, provide only method, not actual link.')

    url = f'https://iss.moex.com/iss/{method}.json'
    if details:
        url += "?" + parse.urlencode(details)

    result = requests.get(url)
    result.encoding = 'utf-8'

    return result.json()


@timeout(seconds=60)
def get_bond_info(secid):
    """
    Get particular bond's information by its security id.
    """
    global columns_for_info

    datetime_now = dt.datetime.now()

    try:
        # general info
        info = query(method=f"securities/{secid}")

        info = pandify(json_object=info, json_key='description')
        info['name'] = info['name'].str.lower()
        bond_columns = list(set.intersection(columns_for_info, set(info['name'])))
        info = info \
            .set_index('name') \
            .loc[bond_columns, ['value']] \
            .T

        # recent prices and volumes
        history = query(
            method=f"history/engines/stock/markets/bonds/sessions/3/securities/{secid}",
            details={'from': (datetime_now - dt.timedelta(days=7)).strftime("%Y-%m-%d")}
        )
        history = pandify(json_object=history,
                          json_key='history',
                          columns=['NUMTRADES', 'WAPRICE', 'ACCINT'])
        history = history[history['NUMTRADES'] > 0].dropna()

        if history.shape[0] > 0:
            info['numtrades'] = history['NUMTRADES'].sum()
            info['waprice'] = np.average(history['WAPRICE'], weights=history['NUMTRADES'])
            info['accint'] = history['ACCINT'].iloc[-1]

        # coupon dates
        if 'matdate' in info and info.loc['value', 'matdate'] is not None:
            coupon_dates = []
            date = datetime_now.strftime("%Y-%m-%d")

            for _ in range(10):
                dates = query(
                    method=f'statistics/engines/stock/markets/bonds/bondization/{secid}',
                    details={
                        'iss.only': 'coupons',
                        'from': date,
                        'limit': 100
                        }
                )
                dates = pandify(json_object=dates, json_key='coupons', columns=['coupondate'])

                if dates.shape[0] == 0:
                    break
                else:
                    coupon_dates += dates['coupondate'].tolist()

                date = dates['coupondate'].max()

                if date == info.loc['value', 'matdate']:
                    break
                else:
                    date = dt.datetime.strptime(dates['coupondate'].max(), "%Y-%m-%d")
                    date = (date + dt.timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                print(f"Something wrong with {secid}")

            info['coupondates'] = str(sorted(list(set(coupon_dates))))

        return info

    except (ConnectionError, OSError) as e:
        print(colored(text=e, color='red'))
        time.sleep(10)
        return get_bond_info(secid)
    except TimeoutError:
        print(colored(text=f"{secid} caused TimeoutError.", color='red'))
        return pd.DataFrame()


def get_bonds(n_pages: int, add_info: bool = True):
    """
    Get bonds and their info from first N pages.
    """

    def add_bonds_info(secids):
        """
        Get information of bonds by their security ids.
        """
        print(f'{dt_now_str()} Start of adding info to bonds:')

        all_bonds_info = []
        for secid in tqdm(secids):
            all_bonds_info.append(get_bond_info(secid=secid))

        all_bonds_info = pd.concat(all_bonds_info)

        print(f'{dt_now_str()} End of adding info to bonds.')

        return all_bonds_info


    details = {
        'group_by': 'group',
        'group_by_filter': 'stock_bonds',
        'limit': 100
        }
    columns = ['secid', 'name', 'is_traded', 'type', 'primary_boardid']

    print(f'{dt_now_str()} Start of pages parsing:')

    all_bonds = []
    for page in (pbar := tqdm(range(n_pages))):
        bonds = query(method="securities", details=details | {'start': page * 100})
        bonds = pandify(json_object=bonds, columns=columns)

        pbar.set_description(f"{bonds.shape[0]} bonds collected from {page}th page.")

        if bonds.shape[0] == 0:
            pbar.close()
            print(f'{dt_now_str()} Pages ran out earlier that {n_pages}. All {page} pages are collected.')
            break

        all_bonds.append(bonds)
    else:
        print(f'{dt_now_str()} All {n_pages} were parsed.')

    all_bonds = pd.concat(all_bonds)

    if add_info:
        time.sleep(1)
        print('\n')

        secids_to_add_info = all_bonds.loc[all_bonds['is_traded'] == 1, 'secid'].unique()

        all_bonds_info = add_bonds_info(secids_to_add_info)

        all_bonds = pd.merge(all_bonds, all_bonds_info, on='secid', how='left')

    return all_bonds
  
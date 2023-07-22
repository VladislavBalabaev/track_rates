import time
import requests
import numpy as np
import sympy as sp
import pandas as pd
import datetime as dt
from tqdm import tqdm
from urllib import parse
from termcolor import colored
from scipy.optimize import fsolve


def dt_now_str():
    """
    Get current datetime painted green in string format.
    """
    now = dt.datetime.now().isoformat(sep=" ", timespec="seconds")
    return f"{colored(f'({now})', 'green')}"


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


def pandify(json_object, json_key='securities', columns: list = None):
    """
    Transform json object to pd.Dataframe.
    """
    df = pd.DataFrame(json_object[json_key]['data'],
                      columns=json_object[json_key]['columns'])
    if columns:
        df = df[columns]
    return df


columns_for_info = {
    'secid', 'issuedate', 'matdate', 'buybackdate', 'initialfacevalue', 'faceunit',
    'facevalue', 'listlevel', 'includedbymoex', 'issuesize', 'isqualifiedinvestors',
    'couponfrequency', 'couponpercent', 'couponvalue', 'typename'
}


def get_bond_info(secid):
    """
    Get particular bond's information by its security id.
    """
    global columns_for_info

    datetime_now = dt.datetime.now()

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
                details={'iss.only': 'coupons',
                         'from': date,
                         'limit': 100}
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


def get_bonds(n_pages: int, add_info: bool = True):
    """
    Get bonds and their info from first N pages.
    """
    details = {'group_by': 'group',
               'group_by_filter': 'stock_bonds',
               'limit': 100}
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


def process_bonds(df_raw):
    y = sp.symbols('y', real=True)
    datetime_now = dt.datetime.now()

    def calculate_bond_yield(row):
        nonlocal y

        coupon_cash_flows = sp.Matrix(row['coupon_maturities_years'])\
            .applyfunc(lambda i: row['couponvalue'] * sp.exp(-y * i))

        expr = sum(coupon_cash_flows) \
               + (row['facevalue'] * sp.exp(-y * row['maturity_years'])) \
               - (row['facevalue'] * row['waprice']) \
               - (row['accint'])

        lam_f = sp.lambdify(y, expr)

        return fsolve(lam_f, x0=np.array([0]))[0]

    def calculate_duration(row):
        vf = np.vectorize(lambda i: i * row['couponvalue'] * np.exp(-row['bond_yield'] * i))

        cash_flows = np.sum(vf(np.array(row['coupon_maturities_years'])))
        cash_flows += row['maturity_years'] * row['facevalue'] * np.exp(-row['bond_yield'] * row['maturity_years'])

        duration = cash_flows / (row['facevalue'] * row['waprice'] + row['accint'])

        return duration

    df = df_raw.set_index('secid').copy()
    df = df.loc[df['is_traded'].isin([1]) &
                ~df[['waprice', 'matdate', 'couponvalue']].isna().any(axis=1) &
                df['faceunit'].isin(['SUR'])]

    df['total_size_mil'] = df['issuesize'] * df['facevalue'] / 1_000_000

    df['couponpercent'] = df['couponpercent'] / 100
    df['coupon_percent_compounded'] = (((1 + (df['couponvalue'] / df['facevalue'])) ** df['couponfrequency']) - 1)

    df['waprice'] = df['waprice'] / 100

    df['maturity_years'] = (pd.to_datetime(df['matdate']) - datetime_now).dt.days.astype(float) / 365
    df['coupon_maturities_years'] = df['coupondates']\
        .map(eval)\
        .apply(lambda x: [(dt.datetime.strptime(date, '%Y-%m-%d') - datetime_now).days / 365 for date in x])

    df['bond_yield'] = df.apply(calculate_bond_yield, axis=1)

    df['duration_years'] = df.apply(calculate_duration, axis=1)
    df['dollar_duration'] = df['duration_years'] * df['waprice'] * df['facevalue']
    # df = df.loc[df['bond_yield'].between(df['bond_yield'].quantile(0.05), df['bond_yield'].quantile(0.95))]

    df = df.drop(['coupon_maturities_years'], axis=1)
    return df.copy()

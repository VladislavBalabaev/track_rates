import numpy as np
import sympy as sp
import pandas as pd
import datetime as dt
from scipy.optimize import fsolve


def process_bonds(df_raw):
    y = sp.symbols(names='y', real=True)


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


    df = df_raw.copy()

    df = df.loc[df['is_traded'].isin([1]) &
                ~df[['waprice', 'matdate', 'couponvalue']].isna().any(axis=1) &
                df['faceunit'].isin(['SUR'])]

    df['total_size_mil'] = df['issuesize'] * df['facevalue'] / 1_000_000

    df['couponpercent'] = df['couponpercent'] / 100
    df['coupon_percent_compounded'] = (((1 + (df['couponvalue'] / df['facevalue'])) ** df['couponfrequency']) - 1)

    df['waprice'] = df['waprice'] / 100

    df['parsing_date'] = pd.to_datetime(df['parsing_date'])
    df['maturity_years'] = (pd.to_datetime(df['matdate']) - df['parsing_date']).dt.days.astype(float) / 365
    df['coupondates'] = df['coupondates'].map(eval)
    df['coupon_maturities_years'] = df.apply(
        lambda row: [(dt.datetime.strptime(date, '%Y-%m-%d') - row['parsing_date']).days / 365 for date in row['coupondates']],
        axis=1
        )

    df['bond_yield'] = df.apply(calculate_bond_yield, axis=1)

    df['duration_years'] = df.apply(calculate_duration, axis=1)
    df['dollar_duration'] = df['duration_years'] * df['waprice'] * df['facevalue']

    return df.copy()
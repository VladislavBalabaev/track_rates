import datetime as dt
from pathlib import Path

from iss_moex_bonds import get_bonds


path = Path('data')

if __name__ == '__main__':
    path.mkdir(parents=True, exist_ok=True)

    current_date = str(dt.datetime.now().date())

    all_bonds = get_bonds(n_pages=1000, add_info=True)
    all_bonds['parsing_date'] = current_date

    all_bonds.to_csv(path_or_buf=path / f'all_bonds_{current_date}.csv', index=False)

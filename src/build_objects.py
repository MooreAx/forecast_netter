# tranform data frames into objects

import pandas as pd
from .simulation import Simulation
from .inventory import Inventory
from .read_data import df_forecast, df_inv_med, df_inv_rec_stamped, df_inv_rec_unstamped, df_production, df_inv_ul
from .globals import *

from collections import namedtuple

#for testing
sim = Simulation(start_date = FCSTART)

#tuple-keyed dict for forecast:
ForecastKey = namedtuple("ForecastKey", ["part", "prov", "channel", "week"])
ForecastVal = namedtuple("ForecastVal", ["qty", "pod"])

forecast_dict = {
    ForecastKey(part=row['part'], prov=row['prov'], channel=row['channel'], week=row['date']):
    ForecastVal(qty=int(row['fc']), pod=row['pod'])
    for _, row in df_forecast.iterrows()
}

#get part list:
part_list = df_forecast['part'].unique().tolist()

#lists for inventory

inv_med_list = [
    Inventory(
        part = row['part'],
        prov = 'MED',
        channel = 'MED',
        lot = row['lotnum'],
        qa_status = row['qa_status'],
        manufactured = row['manufactured'],
        available = row['available'],
        qty = int(row['qty']),
        group = 'medical (50*)',
        sim = sim
    )
    for _, row in df_inv_med.iterrows()
]

inv_rec_stamped_list = [
    Inventory(
        part = row['part'],
        prov = row['pool'],
        channel = 'REC',
        lot = row['lotnum'],
        qa_status = row['qa_status'],
        manufactured = row['manufactured'],
        available = row['available'],
        qty = int(row['qty']),
        group = 'stamped rec',
        sim = sim
    )
    for _, row in df_inv_rec_stamped.iterrows()
]

inv_any_unstamped_list = [
    Inventory(
        part = row['part'],
        prov = 'ANY',
        channel = 'ANY',
        lot = row['lotnum'],
        qa_status = row['qa_status'],
        manufactured = row['manufactured'],
        available = row['available'],
        qty = int(row['qty']),
        group = 'unstamped',
        sim = sim
    )
    for _, row in df_inv_rec_unstamped.iterrows()
]

inv_ul_list = [
    Inventory(
        part = row['part'],
        prov = 'ANY',
        channel = 'ANY',
        lot = row['lotnum'],
        qa_status = row['qa_status'],
        manufactured = row['manufactured'],
        available = row['available'],
        qty = int(row['qty']),
        group = 'unlabelled',
        sim = sim
    )
    for _, row in df_inv_ul.iterrows()
]

inv_production_list = []

if USE_PRODUCTION:
        
    for _, row in df_production.iterrows():
        plan_date       = row['plan_date']
        sow_date        = row['sow']
        release_date    = sow_date + timedelta(weeks=2)  #2 weeks lot release
        date_format = '%Y/%m/%d' #e.g., 2025/01/01

        lot_str = (
            f"Production. Planned {plan_date.strftime(date_format)}. "
            f"Produced {sow_date.strftime(date_format)}. "
            f"Released {release_date.strftime(date_format)}."
        )

        inv_production_list.append(
            Inventory(
                part = row['part'],
                prov = 'ANY',
                channel = 'ANY',
                lot = lot_str,
                qa_status = "A",
                manufactured = sow_date,
                available = release_date,
                qty = int(row['qty']),
                group = "production",
                sim = sim
            )
        )

print("build_objects.py complete")
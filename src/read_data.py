#pull forecast & inventory

import pandas as pd
import janitor as jn
from .globals import *


#forecast (and freshness req'ts)
df_forecast = pd.read_csv("input_data_frames/Forecast.csv", dtype = str).clean_names()

#internal inv
df_inv_med = pd.read_csv("input_data_frames/Inv_Med.csv", dtype = str).clean_names()
df_inv_rec_stamped = pd.read_csv("input_data_frames/Inv_Rec_Stamped.csv", dtype = str).clean_names()
df_inv_rec_unstamped = pd.read_csv("input_data_frames/Inv_Rec_Unstamped.csv", dtype = str).clean_names()

#production
df_production = pd.read_csv("input_data_frames/production_plan.csv", dtype = str).clean_names()

#clean up
df_forecast = (
    df_forecast
    .assign(
        date = lambda x: pd.to_datetime(x['date']).dt.date,
        fc = lambda x: pd.to_numeric(x['fc']),
        pod = lambda x: pd.to_numeric(x['pod']).fillna(float('inf'))
    )
)

df_production = (
    df_production
    .assign(
        sow = lambda x: pd.to_datetime(x['sow']).dt.date,
        plan_date = lambda x: pd.to_datetime(x['plan_date']).dt.date,
        qty = lambda x: pd.to_numeric(x['quantity'])
    )
)

def process_inv(df):

    quality_hold_status = {"QWP", "AWP", "QAP"}

    df2 = (
        df
        .assign(
            manufactured = lambda x: pd.to_datetime(x['manufactured']).dt.date,
            age = lambda x: pd.to_numeric(x['age']),
            qty = lambda x: pd.to_numeric(x['qty']),

            #if in a hold status, delay availability for 2 weeks
            available = lambda x: [
                m + timedelta(weeks = 2) if s in quality_hold_status else FCSTART
                for m, s in zip(x['manufactured'], x['qa_status'])
            ],
        )
    )
    return df2

df_inv_med = process_inv(df_inv_med)
df_inv_rec_stamped = process_inv(df_inv_rec_stamped)
df_inv_rec_unstamped = process_inv(df_inv_rec_unstamped)


# Print head
print("\n\nForecast:")
print(df_forecast.head())

print("\n\nMedical Inventory:")
print(df_inv_med.head())

print("\n\nRec Inventory (Stamped):")
print(df_inv_rec_stamped.head())

print("\n\nRec Inventory (Unstamped):")
print(df_inv_rec_unstamped.head())

print("\n\nProduction:")
print(df_production.head())
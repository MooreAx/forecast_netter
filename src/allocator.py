#main simulation loop

from datetime import datetime
from pprint import pprint
import pandas as pd
import copy

#get objects
from .build_objects import (
    forecast_dict, part_list,
    inv_med_list, inv_rec_stamped_list, inv_any_unstamped_list, inv_production_list, inv_ul_list,
    ForecastKey,
    sim
)

from .globals import *
from .simulation import SimulationState

prov_list = 'BC,AB,SK,MB,ON,QC,NB,NS,PE,NL,MED'.split(',')
channel_list = 'MED,REC'.split(',')

#function to return inventory snapshot as df
def inv_snapshot(inv_list):
    snapshot = pd.DataFrame([
        {
            'part': inv.part,
            'prov': inv.prov,
            'channel': inv.channel,
            'lot': inv.lot,
            'manufactured': inv.manufactured,
            'qty': inv.qty,
            'age': inv.age_days,
            'group': inv.group,
            'date': sim.date
        }
        for inv in inv_list
    ])
    return snapshot


#function to fifo inventory from lists
def fifo_inventory_list(inv_list, part, prov, channel, pod, demand, LOG):
    available_inv = [
        inv for inv in inv_list
        if (
            inv.part == part 
            and (inv.prov == prov or inv.prov == 'ANY')
            and (inv.channel == channel or inv.channel == 'ANY')
            and inv.qty > 0 
            and inv.age_days <= pod
            
            #add more conditions here based on lot release
            and inv.is_available
        )
    ]

    available_inv.sort(key=lambda inv: inv.manufactured) #oldest to newest (LIFO: set reverse=TRUE)
    remaining = demand
    for inv in available_inv:
        if remaining == 0:
            break
        
        initial_demand = remaining
        available = inv.qty
        used = min(available, remaining)
        inv.qty -= used
        remaining -= used

        LOG.append({
            'part': part,
            'prov': prov,
            'channel': channel,
            'date': sim.date,
            'pod': pod,
            'initial_demand': initial_demand,
            'remaining': remaining,
            'inv_consumed': used,
            'inv_channel': inv.channel,
            'inv_lot': inv.lot,
            'inv_group': inv.group,
            'inv_manufactured': inv.manufactured,
            'inv_age_at_ship': inv.age_days
        })

    return remaining

def short_reason_tuple(inv_list, part, prov, channel, remaining):
    aged_inv = [
        inv for inv in inv_list
        if (
            inv.part == part 
            and (inv.prov == prov or inv.prov == 'ANY')
            and (inv.channel == channel or inv.channel == 'ANY')
            and inv.qty > 0
            and inv.is_available
            #pod filter not required because all inventory will be aged at this point
        )
    ]
    total_aged = sum(inv.qty for inv in aged_inv)
    min_aged_days = min((inv.age_days for inv in aged_inv), default=None)
    
    if total_aged >= remaining:
        reason = "no fresh inventory (aged available)"
    else:
        reason = "insufficient inventory (fresh or aged)"

    return reason, total_aged, min_aged_days #tuple

#logs
SHIPMENTLOG = []
SHORTLOG = []
WOHLOG = []

#get inv snapshot before running
inventory_start_df = inv_snapshot(inv_med_list + inv_rec_stamped_list + inv_any_unstamped_list + inv_production_list + inv_ul_list)

def calculate_woh(state):
    main_sim_date = state.sim.date

    woh_sim = state.sim
    woh_inv = state.inventories

    #need a shipmente log - won't actually use this
    tempshiplog = []

    #unpack tuple
    (inv_med_list, inv_rec_stamped_list, inv_any_unstamped_list, inv_production_list, inv_ul_list) = woh_inv 
    
    #only get inventory that is on hand and released as at this pt, for woh calc
    inv_med_list = [inv for inv in inv_med_list if inv.is_available]
    inv_rec_stamped_list = [inv for inv in inv_rec_stamped_list if inv.is_available]
    inv_any_unstamped_list = [inv for inv in inv_any_unstamped_list if inv.is_available]
    inv_production_list = [inv for inv in inv_production_list if inv.is_available]
    inv_ul_list = [inv for inv in inv_ul_list if inv.is_available]

    for _ in range(100):
        done_pp = set() #keep track of completions, reset after every outer loop
        for part in part_list:
            for prov in prov_list:

                if (part, prov) in done_pp:
                    continue

                for channel in channel_list:

                    #get forecast            
                    key = ForecastKey(part=part, prov=prov, channel=channel, week=woh_sim.date)
                    fcval = forecast_dict.get(key)

                    if fcval: #key match
                        pod = fcval.pod
                        demand = fcval.qty

                        remaining = fifo_inventory_list(inv_med_list, part, prov, channel, pod, demand, tempshiplog)
                        remaining = fifo_inventory_list(inv_rec_stamped_list, part, prov, channel, pod, remaining, tempshiplog)
                        remaining = fifo_inventory_list(inv_any_unstamped_list, part, prov, channel, pod, remaining, tempshiplog)
                        remaining = fifo_inventory_list(inv_production_list, part, prov, channel, pod, remaining, tempshiplog)
                        remaining = fifo_inventory_list(inv_ul_list, part, prov, channel, pod, remaining, tempshiplog)

                        if remaining == 0:
                            pass
                        elif remaining > 0:

                            WOHLOG.append({
                                'part': part,
                                'prov': prov,
                                'channel': channel,
                                'main_sim_date': main_sim_date,
                                'sub_sim_date': woh_sim.date,
                                'demand': demand,
                                'pod': pod,
                                'forecast': demand,
                                'short': remaining
                            })

                            done_pp.add((part, prov))
                    else: #no key match
                        continue
        woh_sim.advance_week()

    


for _ in range(100):

    #deep copy for woh calculation
    all_inv = (inv_med_list, inv_rec_stamped_list, inv_any_unstamped_list, inv_production_list, inv_ul_list) #tuple
    state = SimulationState(sim, all_inv)
    state_copy = copy.deepcopy(state)

    #calculate WOH based on current state
    calculate_woh(state_copy)

    for part in part_list:
        for prov in prov_list:
            for channel in channel_list:

                #get forecast            
                key = ForecastKey(part=part, prov=prov, channel=channel, week=sim.date)
                fcval = forecast_dict.get(key)

                if fcval: #key match
                    pod = fcval.pod
                    demand = fcval.qty

                    remaining = fifo_inventory_list(inv_med_list, part, prov, channel, pod, demand, SHIPMENTLOG)
                    remaining = fifo_inventory_list(inv_rec_stamped_list, part, prov, channel, pod, remaining, SHIPMENTLOG)
                    remaining = fifo_inventory_list(inv_any_unstamped_list, part, prov, channel, pod, remaining, SHIPMENTLOG)
                    remaining = fifo_inventory_list(inv_production_list, part, prov, channel, pod, remaining, SHIPMENTLOG)
                    remaining = fifo_inventory_list(inv_ul_list, part, prov, channel, pod, remaining, SHIPMENTLOG)

                    if remaining == 0:
                        pass
                    elif remaining > 0:
                        
                        all_inv = inv_med_list + inv_rec_stamped_list + inv_any_unstamped_list + inv_production_list + inv_ul_list
                        reason, total_aged, min_aged_days = short_reason_tuple(all_inv, part, prov, channel, remaining) #unpack tuple

                        SHORTLOG.append({
                            'part': part,
                            'prov': prov, 
                            'channel': channel,
                            'date': sim.date,
                            'demand': demand,
                            'pod': pod,
                            'forecast': demand,
                            'short': remaining,
                            'short_reason': reason,
                            'total_aged': total_aged,
                            'freshest_aged': min_aged_days
                        })

                else: #no key match
                    continue
    sim.advance_week()


#get ending inv snapshot
inventory_end_df = inv_snapshot(inv_med_list + inv_rec_stamped_list + inv_any_unstamped_list + inv_production_list + inv_ul_list)

#convert logs to dfs and export
pd.DataFrame(SHIPMENTLOG).to_csv("outputs/shipmentlog.csv", index=False)
pd.DataFrame(SHORTLOG).to_csv("outputs/shortlog.csv", index=False)
pd.DataFrame(WOHLOG).to_csv("outputs/wohlog.csv", index=False)


#inventory snapshots to df:
inventory_start_df.to_csv("outputs/starting_inv.csv", index=False)
inventory_end_df.to_csv("outputs/ending_inv.csv", index=False)

print("Allocator complete")

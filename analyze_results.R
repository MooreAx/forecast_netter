#read in the outputs of the forecast netter

starting_inv <- read_csv("outputs/starting_inv.csv") %>% clean_names()
ending_inv <- read_csv("outputs/ending_inv.csv") %>% clean_names()
shipments <- read_csv("outputs/shipmentlog.csv") %>% clean_names()
shorts <- read_csv("outputs/shortlog.csv") %>% clean_names()
woh_log <- read_csv("outputs/wohlog.csv") %>% clean_names()

EffectiveDate <- min(FC$Date)

# xs inventory = on hand at the end

#BUILD TABLES TO PULL INTO EXCEL

#run list
rows <- FC %>%
  select(Part, Prov) %>%
  distinct() %>%
  group_by(Part) %>%
  summarise(
    Listings = str_flatten(Prov, collapse = ", "),
    .groups = "drop"
  )

#monthly forecast
MonthlyFC <- FC %>%
  mutate(
    Month = floor_date(Date, unit = "month")
  ) %>%
  group_by(Part, Month) %>%
  summarise(FC = sum(FC), .groups = "drop")

#filled demand, i.e. shipments:
filled_dmd <- shipments %>%
  mutate(Month = floor_date(date, unit = "month")) %>%
  group_by(part, Month) %>%
  summarise(shipments = sum(inv_consumed), .groups = "drop")

#shorts
monthly_shorts <- shorts %>%
  mutate(Month = floor_date(date, unit = "month")) %>%
  group_by(part, Month) %>%
  summarise(
    short = sum(short),
    .groups = "drop"
  )

#excess = unconsumed inventory
xs_existing <- ending_inv %>%
  filter(!str_detect(lot, "Production.")) %>%
  group_by(part) %>%
  summarise(qty = sum(qty)) %>%
  filter(qty > 0)

xs_production <- ending_inv %>%
  filter(str_detect(lot, "Production.")) %>%
  group_by(part) %>%
  summarise(qty = sum(qty), .groups = "drop") %>%
  filter(qty > 0)

pp_month <- production_plan %>%
  mutate(Month = floor_date(SOW, unit = "month")) %>%
  group_by(part, Month) %>%
  summarise(quantity = sum(quantity), .groups = "drop")

#get POs from supply model
#COME BACK TO THIS -- MAYBE GET A FRESH OR DAILY DOWNLOAD??
pos <- read_csv(
  paste(
    "C:/Users/alex.moore/OneDrive - Canopy Growth Corporation/Documents/Working Folder/supply_model/source-files",
    "processed_pos.csv",
    sep = "/"
  )
) %>%
  mutate(Month = floor_date(due_wk, unit = "month")) %>%
  group_by(part, Month) %>%
  summarise(qty = sum(remaining), .groups = "drop")



#analyze woh
woh <- woh_log %>%
  mutate(
    relwks = as.numeric(difftime(sub_sim_date, main_sim_date, unit = "weeks"))
  ) %>%
  
  #get first short per part, prov, channel, main_sim_date
  group_by(part, prov, channel, main_sim_date) %>%
  summarise(
    first_short = min(relwks)
  )

#get forward demand per part, prov, channel (for average weighting):
woh_calcs <- FC %>%
  group_by(Part, Prov, Channel) %>%
  arrange(desc(Date), .by_group = TRUE) %>%
  mutate(
    fwd_demand = cumsum(FC),
    fwd_wks = row_number()
  ) %>%
  ungroup() %>%
  select(Part, Prov, Channel, Date, fwd_demand, fwd_wks) %>%
  
  #bring in first shorts:
  left_join(
    woh,
    join_by(Part == part, Prov == prov, Channel == channel, Date == main_sim_date)
  ) %>%
  mutate(
    woh = case_when(
      is.na(first_short) ~ fwd_wks,
      .default = first_short
    ),
    fwd_demand_times_woh = woh * fwd_demand
  ) %>%
  group_by(Part, Date) %>%
  summarise(
    fwd_demand_times_woh = sum(fwd_demand_times_woh),
    fwd_demand = sum(fwd_demand),
    .groups = "drop"
  ) %>% mutate(
    wWOH = fwd_demand_times_woh / fwd_demand
  ) %>%
  select(Part, Date, wWOH)
  
woh_wide <- woh_calcs %>%
  pivot_wider(
    names_from = Date,
    values_from = wWOH,
  )






#write to outputs
rows %>% write_csv("outputs/R_OUT/rows.csv")
MonthlyFC %>% write_csv("outputs/R_OUT/monthly_fc.csv")
filled_dmd %>% write_csv("outputs/R_OUT/shipments.csv")
monthly_shorts %>% write_csv("outputs/R_OUT/shorts.csv")
pp_month %>% write_csv("outputs/R_OUT/pp_month.csv")
xs_existing %>% write_csv("outputs/R_OUT/xs_existing.csv")
xs_production %>% write_csv("outputs/R_OUT/xs_production.csv")
pos %>% write_csv("outputs/R_OUT/monthly_pos.csv")

woh_calcs %>% write_csv("outputs/R_OUT/woh.csv")
woh_wide %>% write_csv("outputs/R_OUT/woh_wide.csv")
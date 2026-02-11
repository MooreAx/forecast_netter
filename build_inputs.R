#build data frames for reading into Python:
# --> Inventory
# --> PODs
# --> Demand
# --> Supply

rm(list = ls())

library(tidyverse)
library(janitor)
library(readxl)
library(readr)

InvFldr <- "C:/Users/alex.moore/OneDrive - Canopy Growth Corporation/Documents/Working Folder/Inventory/OHWSI"
Downloads <- "C:/Users/alex.moore/Downloads"
MAPEBIAS <- "C:/Users/alex.moore/OneDrive - Canopy Growth Corporation/Documents/Working Folder/R/mape_bias"

##PICK UP HERE: READ REF PARTS:
RefParts <- read_csv(
  paste(MAPEBIAS, "Intermediates/RefParts.csv", sep = "/")
)

RefParts %>% write_csv("input_data_frames/RefParts.csv")

#POD REQUIREMENTS
POD_long <- read_csv(paste(MAPEBIAS,"POD_long.csv", sep = "/"))

#forecast
FC <- read_csv(paste(MAPEBIAS, "Intermediates/FC_Master.csv", sep = "/")) %>%
  filter(PublishDate == max(PublishDate)) %>%
  select(SKU, Part, Prov, Channel, Form, Date, FC) %>%
  
  left_join(
    POD_long,
    join_by(Prov, Form),
    relationship = "many-to-one"
  )

#write to csv
FC %>% write_csv("input_data_frames/Forecast.csv")

#PRODUCTION PLAN
production_plan <- read_csv(
  paste(MAPEBIAS, "WeeklyUploads/Production Plan.csv", sep="/")) %>%
  select(item, SOW, quantity, plan_date) %>%
  rename(part = item)

#do not remove the -ULs strings! these require careful processing.

production_plan %>% write_csv("input_data_frames/production_plan.csv")

#INTERNAL INVENTORY

# List all Excel files
files <- list.files(path = InvFldr, pattern = "\\.xlsx$", full.names = TRUE)

# Extract dates from filenames (expecting format like "2025-06-03" in the name)
file_dates <- str_extract(basename(files), "\\d{4}-\\d{2}-\\d{2}")
valid_dates <- !is.na(file_dates)

# Convert to Date and find the latest
latest_file <- files[valid_dates][which.max(ymd(file_dates[valid_dates]))]
latest_file_date <- max(ymd(file_dates[valid_dates]))

# Read the latest file
InvData <- read_xlsx(
  path = latest_file,
  skip = 1,
  col_types = "text"  # same as setting all columns to character
) %>%
  clean_names() %>%
  select(name, number, is_stamped, pool, qa_status, warehouse, id, manufactured, available) %>%
  mutate(
    manufactured = parse_number(manufactured),
    manufactured = as.Date(manufactured, origin = "1899-12-30"),
    age = interval(manufactured, latest_file_date),
    age = time_length(age, "days"),
    available = parse_number(available)
  ) %>%
  filter(
    qa_status %in% c("A", "eComm-A", "QWP", "AWP", "QAP"),
    available > 0
  ) %>%
  filter(
    #get rid of anything that has been hanging around in quality hold for a while...
    !(qa_status %in% c("QWP", "AWP", "QAP") & age > 28)
  ) %>%
  rename(
    part = name,
    lotnum = number,
    locid = id,
    qty = available
  ) %>%
  drop_na(manufactured)

Inv_Med <- InvData %>%
  filter(str_sub(locid, 1, 2) == "50") %>%
  group_by(part, qa_status, lotnum, manufactured, age) %>%
  summarise(qty = sum(qty), .groups = "drop") %>%
  mutate(pool = "MED")

Inv_Rec_Stamped <- InvData %>%
  filter(is_stamped == "Y") %>%
  group_by(part, qa_status, lotnum, pool, manufactured, age) %>%
  summarise(qty = sum(qty), .groups = "drop")

Inv_Rec_Unstamped <- InvData %>%
  filter(is_stamped == "N") %>%
  group_by(part, qa_status, lotnum, pool, manufactured, age) %>%
  summarise(qty = sum(qty), .groups = "drop")

#temp addition to add ULs
Inv_UL <- InvData %>%
  filter(
    str_detect(part, "\\d{6}-UL"),
    age < 360*1.5
  ) %>%
  group_by(part, qa_status, lotnum, pool, manufactured, age) %>%
  summarise(qty = sum(qty), .groups = "drop") %>%
  mutate(
    part = str_remove(part, "-UL")
  )

#write to csv
Inv_Med %>% write_csv("input_data_frames/Inv_Med.csv")
Inv_Rec_Stamped %>% write_csv("input_data_frames/Inv_Rec_Stamped.csv")
Inv_Rec_Unstamped %>% write_csv("input_data_frames/Inv_Rec_Unstamped.csv")
Inv_UL %>% write_csv("input_data_frames/Inv_UL.csv")

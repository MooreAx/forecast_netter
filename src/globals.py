#global variables

from datetime import datetime, timedelta

PUBLISH_DATE = datetime(2026, 2, 6).date()
FCSTART = PUBLISH_DATE + timedelta(days=3)
CURRENTWK = PUBLISH_DATE - timedelta(days=4)
LASTACTUALS = FCSTART - timedelta(days=7)

USE_PRODUCTION = True #toggle to use production plan (FALSE converts this to a simple run-down allocator)


#paths
mape_bias_folder = r"C:\Users\alex.moore\OneDrive - Canopy Growth Corporation\Documents\Working Folder\R\mape_bias"
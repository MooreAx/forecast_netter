from datetime import timedelta

class Simulation:
    def __init__(self, start_date):
        self.date = start_date
        self.week = 0
    
    def advance_week(self):
        self.date += timedelta(weeks=1)
        self.week += 1


class SimulationState:
    def __init__(self, sim, inventories):
        self.sim = sim
        self.inventories = inventories
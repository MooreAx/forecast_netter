from .simulation import Simulation


class Inventory:
    def __init__(self, part, prov, channel, lot, qa_status, manufactured, available, qty, sim):
        self.part = part
        self.prov = prov
        self.channel = channel
        self.lot = lot
        self.qa_status = qa_status
        self.manufactured = manufactured
        self.available = available
        self.qty = qty
        self.sim = sim # composition: reference to the simulation

    @property
    def age_days(self):
        return (self.sim.date - self.manufactured).days
    
    @property
    def is_available(self):
        return self.sim.date >= self.available

    def drawdown(self, amount):
        used = min(self.qty, amount)
        self.qty -= used
        return used
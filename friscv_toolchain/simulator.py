from .spike_interface import SpikeInterface


class VerilogInterface:
    def __init__(self, sim_cmd):
        self.sim_cmd = sim_cmd


    def step_cycle(self):
        return {}
    

    def stop(self):
        pass
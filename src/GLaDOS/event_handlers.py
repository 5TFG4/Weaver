from ..models import Trade
#from .glados_core import GLaDOSCore

class EventHandler:
    def __init__(self):
        #self.glados = GLaDOSCore()
        pass
        
    def handle_trade(self, trade: Trade):
        print("handle_trade")
        pass

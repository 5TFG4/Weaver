import asyncio

from GLaDOS import CoreState

class GLaDOS:
    _instance = None
    veda = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls.state = CoreState.not_running
            #cls.walle = WallE()
            #cls.veda = veda
            # cls.marvin = Marvin()
            # cls.greta = Greta()
            # cls.haro = Haro()
            #cls.event_handler = EventHandler()
        return cls._instance


    async def start_trading(self):
        while True:
            trade_data = await self.veda.get_trade_data()
            #trade = Trade.from_dict(trade_data[0])
            self.event_handler.handle_trade(trade_data[0])


    async def async_run(self, *, attach_signals: bool = True) -> int:
        """Weaver main entry point.

        Start Weaver and block until stopped.

        This method is a coroutine.
        """
        if self.state != CoreState.not_running:
            raise RuntimeError("Weaver is already running")

        # _async_stop will set this instead of stopping the loop
        self._stopped = asyncio.Event()

        await self.async_start()
        await self.veda.async_start()
        # if attach_signals:
        #     # pylint: disable-next=import-outside-toplevel
        #     from .helpers.signal import async_register_signal_handling

        #     async_register_signal_handling(self)

        await self._stopped.wait()
        return self.exit_code
    
    async def async_start(self) -> None:
        print("Glados async_start")
        return
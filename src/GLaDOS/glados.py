import asyncio
from collections.abc import (
    Awaitable,
    Callable,
    Collection,
    Coroutine,
    Iterable,
    Mapping,
)
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    NamedTuple,
    ParamSpec,
    TypeVar,
    cast,
    overload,
)

from GLaDOS import CoreState

_R = TypeVar("_R")
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

def callback(func: _CallableT) -> _CallableT:
    """Annotation to mark method as safe to call from within the event loop."""
    setattr(func, "_hass_callback", True)
    return func


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


    @callback
    def async_add_hass_job(
        self, hassjob: HassJob[..., Coroutine[Any, Any, _R] | _R], *args: Any
    ) -> asyncio.Future[_R] | None:
        """Add a HassJob from within the event loop.

        This method must be run in the event loop.
        hassjob: HassJob to call.
        args: parameters for method to call.
        """
        task: asyncio.Future[_R]
        if hassjob.job_type == HassJobType.Coroutinefunction:
            if TYPE_CHECKING:
                hassjob.target = cast(
                    Callable[..., Coroutine[Any, Any, _R]], hassjob.target
                )
            task = self.loop.create_task(hassjob.target(*args), name=hassjob.name)
        elif hassjob.job_type == HassJobType.Callback:
            if TYPE_CHECKING:
                hassjob.target = cast(Callable[..., _R], hassjob.target)
            self.loop.call_soon(hassjob.target, *args)
            return None
        else:
            if TYPE_CHECKING:
                hassjob.target = cast(Callable[..., _R], hassjob.target)
            task = self.loop.run_in_executor(None, hassjob.target, *args)

        self._tasks.add(task)
        task.add_done_callback(self._tasks.remove)

        return task
    

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
        self.state = CoreState.starting

        print("Glados async_start")

        self.state = CoreState.running
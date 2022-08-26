from __future__ import annotations
from .state_machine import StateMachineBase
import enum
import logging

logger = logging.getLogger(__name__)


class States(enum.Enum):
    SOLD_OUT = enum.auto()
    NO_COIN = enum.auto()
    HAS_COIN = enum.auto()


class GumballMachine(StateMachineBase):
    """This class simulates the operation of a simple gumball machine."""
    __slots__ = ('gumballs',)

    states = States

    def __init__(self, gumballs: int = 0) -> None:
        """Constructor

        Args:
            gumballs (int, optional): The number of gumballs in initial inventory. Defaults to 0.
        """
        super().__init__()
        self.gumballs = 0
        if gumballs > 0:
            self.add_gumballs(gumballs)

    def add_gumballs(self, gumballs: int) -> GumballMachine:
        """Adds new gumballs to the machine's inventory.

        Args:
            gumballs (int): The number of gumballs to add.

        Raises:
            ValueError: Raised when a non-positive number is given.

        Returns:
            GumballMachine: The current instance.
        """
        if gumballs < 1:
            raise ValueError('Number of gumballs must be positive')
        self.gumballs += gumballs
        if self.state == States.SOLD_OUT:
            self.transition(States.NO_COIN)
        return self

    def insert_coin(self) -> GumballMachine:
        """Inserts a coin. If a coin was already inserted
        without dispensing a gumball, then any additional
        coin inserted after this is ejected.

        Returns:
            GumballMachine: The current instance.
        """
        if self.state == States.NO_COIN:
            self.transition(States.HAS_COIN)
        else:
            self.eject_coin(is_extra=(self.state == States.HAS_COIN))
        return self

    def eject_coin(self, is_extra: bool = False) -> GumballMachine:
        """Ejects a coin.

        Args:
            is_extra (bool, optional): Whether or not the coin
            to eject isn't the first coin inserted. Defaults to False.

        Returns:
            GumballMachine: The current instance.
        """
        if self.state == States.HAS_COIN:
            if is_extra:
                logger.info('Dispensing extra coin')
            else:
                self.transition(States.NO_COIN)
        return self

    def turn_crank(self) -> GumballMachine:
        """Turns the crank to dispense a gumball if and
        only if a coin is currently inserted.

        Returns:
            GumballMachine: The current instance.
        """
        if self.state != States.HAS_COIN:
            logger.warning('Nothing happened')
        else:
            self.gumballs -= 1
            self.transition(States.SOLD_OUT if self.gumballs ==
                            0 else States.NO_COIN)
        return self

    def reset(self) -> GumballMachine:
        """Resets the state of the gumball machine to
        Sold Out as there are no gumballs.

        Returns:
            GumballMachine: The current instance.
        """
        super().reset()
        self.gumballs = 0

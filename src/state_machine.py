from abc import ABCMeta
from inspect import isclass
import enum
import logging


logger = logging.getLogger(__name__)


# My metaclass subclasses ABCMeta not only because I know a custom metaclass
# doen't have to directly subclass type but also because I could have future
# use of defining abstract methods on StateMachineBase.
class StateMachineMeta(ABCMeta):
    """Validates expectations for subclasses of StateMachineBase. Subclasses
    must define a states property on the class referencing an enumeration of
    all possible states. Optionally, one can also define an initial_state.
    By default, an initial_state is the first value in an enumeration."""

    def __new__(metacls, name, bases, attrs):
        # Validating StateMachineBase's class properties is not desirable
        # as there wouldn't be states common to every state machine the
        # developer wishes to define.
        if len(bases) > 0:
            states = attrs.get('states', None)
            initial_state = attrs.get('initial_state', None)
            # Enumerations are almost as convenient to use as strings
            # while having better possible tooling support and more
            # efficient comparisons.
            if states is None or not isclass(states) or not issubclass(states, enum.Enum):
                raise TypeError(f'states on {name} must be an enumeration')

            if initial_state is None:
                first_state = next(iter(states.__members__.values()))
                attrs['initial_state'] = first_state
            elif not isinstance(initial_state, states):
                raise TypeError(
                    f'initial_state {initial_state} of {name} must be from the enumeration specified by states')

        return super().__new__(metacls, name, bases, attrs)


class StateMachineBase(metaclass=StateMachineMeta):
    """This is a base class for to provide basic state machine functionality
    such as tracking the current state and providing a method for state
    transitions. Subclasses need to define the states class attribute as
    per the metaclass StateMachineMeta."""
    __slots__ = ('state',)

    def __init__(self) -> None:
        self.state = getattr(self.__class__, 'initial_state', None)
        if self.state is None:
            raise RuntimeError(f'{self.__class__.__name__} cannot be instantiated')

    def after_transition(self, from_state: enum.Enum, to_state: enum.Enum) -> None:
        """Override in a subclass to run code after the new state takes effect. There
        is no default functionality.

        Args:
            from_state (enum.Enum): The old state.
            to_state (enum.Enum): The new state.
        """
        pass

    def before_transition(self, from_state: enum.Enum, to_state: enum.Enum) -> None:
        """Override in a subclass to run code before the new state takes effect. The
        default behavior emits INFO logs recording the old state and what will be
        the new state.

        Args:
            from_state (enum.Enum): The old state.
            to_state (enum.Enum): The new state.
        """
        logger.info('%s is transitioning from %s to %s',
                    self.__class__.__name__, from_state.name, to_state.name)

    def transition(self, to_state: enum.Enum) -> None:
        """Transitions to a new internal state.

        Args:
            to_state (enum.Enum): The new internal state.

        Raises:
            TypeError: Raised if to_state is not valid.
        """
        if not isinstance(to_state, self.__class__.states):
            raise TypeError(
                f'{to_state.name} is not a valid state in {self.__class__.__name__}')
        from_state = self.state
        self.before_transition(from_state, to_state)
        self.state = to_state
        self.after_transition(from_state, to_state)

    def reset(self) -> None:
        """Resets the state machine to the intial state."""
        self.transition(self.__class__.initial_state)

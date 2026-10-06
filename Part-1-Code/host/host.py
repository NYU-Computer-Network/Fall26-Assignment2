from abc import abstractmethod, ABCMeta

"""
Hosts
============

All host implementations must implement this interface.

The run_one_tick() method is the entry point for the host.
During the simulation, the network simulator will load any packets sent to this host onto the Network Card's buffer.
The simulation controller will then hand off control of the to this host by invoking the run_one_tick() method.

While this method is running, this method should read packets off the Network Card and process them.
Then, implementing the specified protocol, it should then determine whether or not it should transmit any more data.
It should then use the network card to transmit that data to the network.

Finally, we should return the last sequence number such that all previous packets have been acknowledged.
For example, if we just received 4, and we already had 0, 1, 2, 3, 5, 7, we would return 5.
We now have all packets from 0 to 5, but we do not have 6, so cannot go further.
"""


class Host(metaclass=ABCMeta):

    @abstractmethod
    def run_one_tick(self) -> int | None: raise NotImplementedError

    """
    This is a method the simulator will call on the host after the simulation is complete.
    """
    def shutdown_hook(self): pass

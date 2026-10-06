from dataclasses import dataclass

@dataclass
class Packet:
    """
    The time at which this packet was sent from the host.
    """
    sent_timestamp: int
    """
    The sequence number for the message this packet represents. Should now change between retransmissions.
    """
    sequence_number: int
    """
    Flag to indicate whether this packet was sent as a retry of a dropped packet.
    """
    retransmission_flag: bool = False
    """
    Flag to indicate whether this packet was sent as an ACK to a message
    Note that, for this simulation, all packets sent from the host will not be ACKs (they will be new message),
    but all messages received by the host will be ACKs.
    """
    ack_flag: bool = False

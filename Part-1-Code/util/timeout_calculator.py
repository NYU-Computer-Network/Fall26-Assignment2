from .timeout_bounds import TimeoutBounds


class TimeoutCalculator:
    # default values for minimum and maximum timeout
    DEFAULT_MIN_TIMEOUT = 100
    DEFAULT_MAX_TIMEOUT = 10000

    """
    Timeout Calculator maintains the mean RTT and RTT variance.
    Data members of this class include alpha, beta and K
     (which have the same meaning as discussed in the lectures)
    """

    def __init__(
            self,
            alpha: float,
            beta: float,
            k: float,
            bounds: TimeoutBounds = None,
            initial_mean_estimate: float = None,
            initial_stddiv_estimate: float = None,
            initial_timeout: float = None,
    ):
        self.alpha = alpha
        self.beta = beta
        self.k = k

        # If a bound is "None", no trimming should occur
        self.bounds = bounds or TimeoutBounds(min=None, max=None)

        self.current_mean_estimate = initial_mean_estimate
        self.current_stddiv_estimate = initial_stddiv_estimate
        self.current_timeout = initial_timeout or self.bounds.min or 1.0

    """
    Helper Functions
    ================
    
    These functions are used to help compute the timeout using an estimate of the mean RTT and RTT standard deviation.
    These estimates are make using the EWMA algorithm.
    """

    @staticmethod
    def __compute_new_mean_estimate(old_mean: float, latest_rtt: float, alpha: float) -> float:
        # TODO: Implement this function to compute the new mean using an EWMA-based estimation algorithm
        return 0.0

    @staticmethod
    def __compute_new_stddiv_estimate(old_stddiv: float, mean: float, latest_rtt: float, beta: float) -> float:
        # TODO: Implement this function to compute the new stddiv using an EWMA-based estimation algorithm
        return 0.0


    @staticmethod
    def __compute_timeout(mean: float, stddiv: float, k: float, bounds: TimeoutBounds) -> float:
        # TODO: Use the mean and stddiv to compute the timeout. Then, if needed, trim to the min and max in self.bounds
        return 0.0

    """
    Return the most up-to-date mean estimate
    """
    def mean_estimate(self) -> float:
        return self.current_mean_estimate

    """
    Return the most up-to-date standard deviation estimate
    """
    def stddiv_estimate(self) -> float:
        return self.current_stddiv_estimate

    """
    Return the timeout recommendation based on the most up-to-date RTT data
    """
    def timeout(self) -> int:
        return int(self.current_timeout)

    """
    Add a new RTT data point and update the mean and standard deviation estimates.
    Then, update the timeout recommendation. 
    """
    def add_data_point(self, packet_rtt):
        # First, we update the mean
        if self.current_mean_estimate is None:
            self.current_mean_estimate = packet_rtt
        else:
            self.current_mean_estimate = self.__compute_new_mean_estimate(
                old_mean=self.current_mean_estimate,
                latest_rtt=packet_rtt,
                alpha=self.alpha
            )

        # Next, we update the standard deviation
        if self.current_stddiv_estimate is None:
            self.current_stddiv_estimate = self.current_mean_estimate / 2.0
        else:
            self.current_stddiv_estimate = self.__compute_new_stddiv_estimate(
                old_stddiv=self.current_stddiv_estimate,
                mean=self.current_mean_estimate,
                latest_rtt=packet_rtt,
                beta=self.beta
            )

        # Finally, update the timeout before the next message is sent
        self.current_timeout = self.__compute_timeout(
            mean=self.current_mean_estimate,
            stddiv=self.current_stddiv_estimate,
            k=self.k,
            bounds=self.bounds,
        )

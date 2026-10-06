import math


class Clock:
    def __init__(self):
        self.__current_tick = -math.inf

    def set_tick(self, tick):
        assert tick > self.__current_tick
        self.__current_tick = tick

    def read_tick(self):
        return self.__current_tick

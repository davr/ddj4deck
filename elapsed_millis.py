import time

class ElapsedMillis:
    def __init__(self):
        self.ms = self.millis()

    def millis(self):
        return int(round(time.time() * 1000))

    def __int__(self):        
        return self.millis() - self.ms

    def __eq__(self, other):
        if isinstance(other,ElapsedMillis):
            return self.ms == other.ms
        else:
            return int(self) == int(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other,ElapsedMillis):
            return self.ms < other.ms
        else:
            return int(self) < int(other)

    def __le__(self, other):
        if isinstance(other,ElapsedMillis):
            return self.ms <= other.ms
        else:
            return int(self) <= int(other)

    def __gt__(self, other):
        if isinstance(other,ElapsedMillis):
            return self.ms > other.ms
        else:
            return int(self) > int(other)

    def __ge__(self, other):
        if isinstance(other,ElapsedMillis):
            return self.ms >= other.ms
        else:
            return int(self) >= int(other)

    def __iadd__(self, val):
        self.ms -= val
        return self

    def __isub__(self, val):
        self.ms += val
        return self

    def __add__(self, val):
        result = ElapsedMillis()
        result.ms = self.ms - val
        return result

    def __sub__(self, val):
        result = ElapsedMillis()
        result.ms = self.ms + val
        return result

    def __repr__(self):
        return f"ElapsedMillis({self.millis() - self.ms})"

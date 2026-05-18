class Accumulator():
    def __init__(self):
        self.accumulator = {}

    def add_row(self, row):
        for key in row:
            if key not in self.accumulator:
                self.accumulator[key] = 0
            try:
                self.accumulator[key] += int(row.get(key))
            except Exception:
                pass

    def get_total(self):
        return self.accumulator

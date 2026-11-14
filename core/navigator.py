
class Navigator:
    def __init__(self, path):
        self.path = path or []
        self.index = 0
        self.finished = False

        if self.path:
            self.position = self.path[0][:2]
        else:
            self.position = None

    def update(self, current_time):
        if not self.path or self.finished:
            return

        while self.index + 1 < len(self.path):
            next_state = self.path[self.index + 1]
            x, y, t = next_state

            if current_time < t:
                break

            self.position = (x, y)
            self.index += 1

        if self.index >= len(self.path) - 1:
            self.finished = True

    def remaining_path(self):
        return self.path[self.index:]

    def reset(self):
        self.index = 0
        self.finished = False
        self.position = self.path[0][:2] if self.path else None

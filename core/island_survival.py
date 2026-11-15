"""Exploration, island loot, crew rations and material-based repairs."""
import random

DAY_SECONDS = 25.0
DAYS_BETWEEN_RESTS = 2


class IslandSurvival:
    def __init__(self, island_count, seed=2026):
        self.rng = random.Random(seed)
        self.island_count = island_count
        self.wood = 1
        self.rope = 0
        self.food = 4
        self.medicine = 0
        self.crew = 12
        self.morale = 100
        self.last_rest_day = 0
        self.visited = set()
        self.last_visit_day = {}
        self.message = 'Find an island to collect supplies. F: dock, E: repair.'
        self.failed = False

    def day(self, elapsed):
        return int(max(0, elapsed) // DAY_SECONDS)

    def rest_due(self, elapsed):
        return self.day(elapsed) - self.last_rest_day >= DAYS_BETWEEN_RESTS

    def dock(self, island_id, elapsed):
        if not 0 <= island_id < self.island_count:
            return False
        day = self.day(elapsed)
        if self.last_visit_day.get(island_id) == day:
            self.message = 'Island already searched today. Return tomorrow.'
            return False
        self.last_visit_day[island_id] = day
        self.visited.add(island_id)
        loot = {
            'wood': self.rng.randint(1, 3),
            'rope': self.rng.randint(0, 2),
            'food': self.rng.randint(2, 5),
            'medicine': self.rng.randint(0, 1),
        }
        for name, amount in loot.items():
            setattr(self, name, getattr(self, name) + amount)
        if self.rest_due(elapsed):
            self.rest(elapsed)
        self.message = (f"Island searched: +{loot['wood']} wood, +{loot['rope']} rope, "
                        f"+{loot['food']} rations, +{loot['medicine']} medicine")
        return True

    def rest(self, elapsed):
        if not self.rest_due(elapsed):
            self.message = 'Crew is rested. Next stop due after two days.'
            return False
        if self.food < 2:
            self.morale = max(0, self.morale - 25)
            self.message = 'Insufficient rations! Crew morale decreased.'
            self.failed = self.morale == 0
            return False
        self.food -= 2
        self.last_rest_day = self.day(elapsed)
        self.morale = min(100, self.morale + 10)
        self.message = 'Crew fed and rested. Continue your voyage.'
        return True

    def repair(self, survival):
        if self.wood < 2 or self.rope < 1:
            self.message = 'Repairs require 2 wood and 1 rope. Explore islands.'
            return False
        if survival.sunk or survival.hull >= survival.max_hull:
            self.message = 'Hull cannot be repaired right now.'
            return False
        self.wood -= 2
        self.rope -= 1
        survival.hull = min(survival.max_hull, survival.hull + 30)
        self.message = f'Hull repaired to {survival.hull}% (-2 wood, -1 rope).'
        return True

    def check_crew(self, elapsed):
        if self.rest_due(elapsed):
            self.message = 'CREW NEEDS REST! Dock at an island (F).'
            return True
        return False

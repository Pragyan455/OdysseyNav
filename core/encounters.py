"""Deterministic island encounters with meaningful resource tradeoffs.

This module has no Pygame dependency. The UI presents choices and calls resolve().
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Choice:
    label: str
    description: str


@dataclass(frozen=True)
class Encounter:
    island: str
    title: str
    story: str
    choices: tuple[Choice, Choice]


ENCOUNTERS = (
    Encounter('Aeolia', 'THE KEEPER OF WINDS',
              'Aeolus offers winds for the voyage, but demands provisions.',
              (Choice('Accept the winds', 'Spend 1 ration; receive 2 rope.'),
               Choice('Refuse the bargain', 'Gain 1 morale for your caution.'))),
    Encounter("Circe's Isle", 'THE ENCHANTRESS',
              'Circe offers a healing draught, at a price.',
              (Choice('Trust the potion', 'Gain 2 medicine; lose 12 morale.'),
               Choice('Gather herbs instead', 'Gain 1 medicine.'))),
    Encounter('The Sirens', 'THE SIRENS CALL',
              'A beautiful song tempts the crew toward hidden rocks.',
              (Choice('Follow the song', 'Gain 3 rations; risk 22 hull damage.'),
               Choice('Bind the crew to the mast', 'Spend 1 rope; gain 8 morale.'))),
    Encounter('Thrinacia', 'THE SACRED HERD',
              'The crew eyes sacred cattle grazing on the shore.',
              (Choice('Take the cattle', 'Gain 6 rations; lose 20 morale.'),
               Choice('Respect the gods', 'Gain 10 morale.'))),
    Encounter('Ogygia', 'THE FORGOTTEN GARDEN',
              'A quiet grove offers shelter, but the sea calls.',
              (Choice('Gather timber', 'Gain 3 wood; spend 1 ration.'),
               Choice('Forage for food', 'Gain 3 rations.'))),
    Encounter('Phaeacia', 'THE MERCHANTS',
              'A trader offers shipbuilding materials for food.',
              (Choice('Trade rations', 'Spend 2 rations; gain 2 wood and 2 rope.'),
               Choice('Trade timber', 'Spend 1 wood; gain 3 rations.'))),
    Encounter('Lotus Shore', 'THE LOTUS EATERS',
              'Sweet flowers promise rest and forgetfulness.',
              (Choice('Eat the lotus', 'Gain 2 rations; lose 18 morale.'),
               Choice('Keep your purpose', 'Gain 6 morale.'))),
    Encounter("Calypso's Haven", 'THE HIDDEN HAVEN',
              'A sheltered harbor promises a safer crossing.',
              (Choice('Repair the vessel', 'Spend 1 wood; restore 20 hull.'),
               Choice('Collect supplies', 'Gain 1 wood and 1 rope.'))),
)


class EncounterEngine:
    def __init__(self):
        self.completed = set()
        self.history = []

    def available(self, island_id):
        return 0 <= island_id < len(ENCOUNTERS) and island_id not in self.completed

    def get(self, island_id):
        return ENCOUNTERS[island_id] if self.available(island_id) else None

    def resolve(self, island_id, choice, inventory, survival):
        """Apply one decision once; return (success, narrative).

        Invalid/unaffordable choices do not consume the encounter.
        """
        if not self.available(island_id) or choice not in (0, 1):
            return False, 'No encounter is available.'
        inv = inventory
        if island_id == 0:
            if choice == 0:
                if inv.food < 1: return False, 'Need 1 ration to accept the winds.'
                inv.food -= 1; inv.rope += 2
                message = 'Aeolus gifts two coils of rope for your journey.'
            else:
                inv.morale = min(100, inv.morale + 1)
                message = 'You keep your provisions and sail under your own strength.'
        elif island_id == 1:
            if choice == 0:
                inv.medicine += 2; inv.morale = max(0, inv.morale - 12)
                message = 'The potion heals, but leaves the crew unsettled.'
            else:
                inv.medicine += 1
                message = 'Your crew gathers useful herbs along the shore.'
        elif island_id == 2:
            if choice == 0:
                inv.food += 3; survival.hull = max(0, survival.hull - 22)
                message = 'The song leads to supplies, but rocks tear at the hull.'
            else:
                if inv.rope < 1: return False, 'Need 1 rope to secure the crew.'
                inv.rope -= 1; inv.morale = min(100, inv.morale + 8)
                message = 'The crew survives the song without following it.'
        elif island_id == 3:
            if choice == 0:
                inv.food += 6; inv.morale = max(0, inv.morale - 20)
                message = 'The crew feasts, fearful of divine punishment.'
            else:
                inv.morale = min(100, inv.morale + 10)
                message = 'The crew leaves the sacred herd untouched.'
        elif island_id == 4:
            if choice == 0:
                if inv.food < 1: return False, 'Need 1 ration for the timber expedition.'
                inv.food -= 1; inv.wood += 3
                message = 'The crew returns with strong timber.'
            else:
                inv.food += 3
                message = 'The island provides fresh provisions.'
        elif island_id == 5:
            if choice == 0:
                if inv.food < 2: return False, 'Need 2 rations for this trade.'
                inv.food -= 2; inv.wood += 2; inv.rope += 2
                message = 'The merchants supply timber and rope.'
            else:
                if inv.wood < 1: return False, 'Need 1 wood for this trade.'
                inv.wood -= 1; inv.food += 3
                message = 'The merchants supply three rations.'
        elif island_id == 6:
            if choice == 0:
                inv.food += 2; inv.morale = max(0, inv.morale - 18)
                message = 'The lotus nourishes the crew, but weakens their resolve.'
            else:
                inv.morale = min(100, inv.morale + 6)
                message = 'Your sailors remember the road home.'
        else:
            if choice == 0:
                if inv.wood < 1: return False, 'Need 1 wood for the harbor repair.'
                if survival.sunk or survival.hull >= survival.max_hull:
                    return False, 'The hull cannot be repaired now.'
                inv.wood -= 1
                survival.hull = min(survival.max_hull, survival.hull + 20)
                message = 'Calypso’s harbor shelters the crew while they repair the hull.'
            else:
                inv.wood += 1; inv.rope += 1
                message = 'You collect timber and rope before departing.'
        self.completed.add(island_id)
        self.history.append((island_id, choice, message))
        inv.failed = inv.morale <= 0
        return True, message

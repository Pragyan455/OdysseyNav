"""The islands of the voyage home: all story text and choices live here.

Edit freely. Each episode is one island, in the order of the Odyssey.
On each leg the CORRECT island is the next episode (calm version); the
WRONG island is another episode in its HARSH version.

Effects change the four resources: food, health, crew, favor.
A choice is either sure:      {"text": ..., "effects": {...}, "result": ...}
or a gamble:                  {"text": ..., "chance": 0.6,
                               "win": {...}, "win_result": ...,
                               "lose": {...}, "lose_result": ...}
"""

EPISODES = [
    {
        "key": "lotus",
        "name": "THE LOTUS-EATERS",
        "book": "BOOK IX",
        "omen": "where sweet flowers scent the wind",
        "calm": {
            "story": "Gentle islanders offer your scouts the honey-sweet "
                     "lotus. Whoever tastes it forgets the way home.",
            "choices": [
                {"text": "Drag the scouts back to the ships",
                 "effects": {"favor": 2, "food": -2},
                 "result": "They weep for the lotus, but they row. Athena "
                           "smiles on your resolve."},
                {"text": "Let the crew feast",
                 "chance": 0.5,
                 "win": {"food": 8}, "win_result":
                     "The crew eats well and still remembers Ithaca.",
                 "lose": {"food": 6, "crew": -2}, "lose_result":
                     "Two men refuse to leave. They forget their homes."},
            ],
        },
        "harsh": {
            "story": "Half your scouts already lie dreaming in the lotus "
                     "fields, and the islanders keep feeding them.",
            "choices": [
                {"text": "Go in after them yourself",
                 "effects": {"health": -3, "food": -2},
                 "result": "You haul them back one by one, exhausted."},
                {"text": "Sail without them",
                 "effects": {"crew": -3, "favor": -1},
                 "result": "Three oars fall silent."},
            ],
        },
    },
    {
        "key": "cyclops",
        "name": "THE CYCLOPS",
        "book": "BOOK IX",
        "omen": "where sheep graze below a dark cave",
        "calm": {
            "story": "A giant's cave, full of cheese and fat sheep. "
                     "Polyphemus is out with his flocks.",
            "choices": [
                {"text": "Take what you need and leave quickly",
                 "effects": {"food": 6, "favor": -1},
                 "result": "You are gone before the giant returns."},
                {"text": "Wait to meet your host",
                 "chance": 0.4,
                 "win": {"food": 10}, "win_result":
                     "You blind him and escape beneath his sheep, laden "
                     "with food.",
                 "lose": {"crew": -3, "health": -2, "favor": -2},
                 "lose_result": "He eats three of your men. Poseidon, his "
                                "father, hears of it."},
            ],
        },
        "harsh": {
            "story": "Polyphemus is home and hungry. The boulder rolls "
                     "shut behind you.",
            "choices": [
                {"text": "Blind him with the burning stake",
                 "effects": {"crew": -2, "food": 6, "favor": -3},
                 "result": "You escape under the sheep. Poseidon swears "
                           "revenge."},
                {"text": "Ply him with wine and wait",
                 "chance": 0.5,
                 "win": {"crew": -1}, "win_result":
                     "He sleeps. You slip out, one man short.",
                 "lose": {"crew": -4, "health": -2}, "lose_result":
                     "He wakes too soon."},
            ],
        },
    },
    {
        "key": "aeolus",
        "name": "AEOLUS, KEEPER OF THE WINDS",
        "book": "BOOK X",
        "omen": "where a bronze wall rings the floating isle",
        "calm": {
            "story": "King Aeolus gives you a leather bag holding every "
                     "wind but the one that blows you home.",
            "choices": [
                {"text": "Guard the bag yourself, day and night",
                 "effects": {"favor": 2, "health": -2},
                 "result": "No sleep, but the west wind carries you on."},
                {"text": "Let the crew take turns",
                 "chance": 0.5,
                 "win": {"favor": 2, "food": 2}, "win_result":
                     "They keep faith. Fair winds all the way.",
                 "lose": {"food": -6, "favor": -2}, "lose_result":
                     "Curious men open the bag. The storm blows you back."},
            ],
        },
        "harsh": {
            "story": "Aeolus has heard of your curse. \"Begone, hated "
                     "of the gods!\"",
            "choices": [
                {"text": "Beg for one gentle breeze",
                 "effects": {"favor": -1, "food": -3},
                 "result": "He gives nothing. You row in dead calm."},
                {"text": "Leave at once",
                 "effects": {"food": -2},
                 "result": "You row away into still water."},
            ],
        },
    },
    {
        "key": "laestrygonians",
        "name": "THE LAESTRYGONIANS",
        "book": "BOOK X",
        "omen": "where smoke rises over a narrow harbor",
        "calm": {
            "story": "A perfect harbor between steep cliffs. Smoke rises "
                     "from a town of giants.",
            "choices": [
                {"text": "Moor outside the harbor and forage",
                 "effects": {"food": 4},
                 "result": "Cautious, and fed."},
                {"text": "Sail into the harbor to trade",
                 "chance": 0.4,
                 "win": {"food": 10}, "win_result":
                     "The giants are away. You fill the hold.",
                 "lose": {"crew": -4, "health": -2}, "lose_result":
                     "Boulders rain down from the cliffs."},
            ],
        },
        "harsh": {
            "story": "The giants are already on the cliffs, boulders "
                     "in hand.",
            "choices": [
                {"text": "Cut the anchor rope and row!",
                 "effects": {"crew": -2, "health": -1},
                 "result": "You escape. Not everyone does."},
                {"text": "Shelter under the cliff",
                 "chance": 0.5,
                 "win": {"health": -1}, "win_result":
                     "The rocks miss. You slip away at dusk.",
                 "lose": {"crew": -4}, "lose_result":
                     "The cliff is no shelter."},
            ],
        },
    },
    {
        "key": "circe",
        "name": "CIRCE'S ISLAND",
        "book": "BOOK X",
        "omen": "where wolves and lions walk tame around a stone hall",
        "calm": {
            "story": "The enchantress Circe turns visitors into swine. "
                     "Hermes offers you the herb moly.",
            "choices": [
                {"text": "Take the moly and face Circe",
                 "effects": {"health": 3, "food": 8, "favor": 1},
                 "result": "Her magic fails. She becomes your host for "
                           "a year."},
                {"text": "Send scouts to the hall",
                 "chance": 0.5,
                 "win": {"food": 6}, "win_result":
                     "They return with bread and wine.",
                 "lose": {"crew": -2}, "lose_result":
                     "Two scouts come back as pigs."},
            ],
        },
        "harsh": {
            "story": "Your scouts are already swine. No god offers you "
                     "an herb this time.",
            "choices": [
                {"text": "Bargain with Circe",
                 "effects": {"food": -2, "favor": -1, "crew": -1},
                 "result": "She frees most of them, for a price."},
                {"text": "Abandon them and flee",
                 "effects": {"crew": -3},
                 "result": "Their squeals follow you out to sea."},
            ],
        },
    },
    {
        "key": "sirens",
        "name": "THE SIRENS",
        "book": "BOOK XII",
        "omen": "where song drifts over a meadow of bones",
        "calm": {
            "story": "The Sirens sing of everything you long to know. "
                     "Circe warned you.",
            "choices": [
                {"text": "Wax in the crew's ears, tie yourself to the mast",
                 "effects": {"favor": 2, "health": -1},
                 "result": "You strain at the ropes, but the ship passes."},
                {"text": "Row hard and hope",
                 "chance": 0.5,
                 "win": {}, "win_result": "The wind drowns out the song.",
                 "lose": {"crew": -3}, "lose_result":
                     "Three men leap toward the voices."},
            ],
        },
        "harsh": {
            "story": "No wax left. The song is already in their heads.",
            "choices": [
                {"text": "Stop the oars and grab the men",
                 "effects": {"crew": -1, "health": -2, "food": -2},
                 "result": "You lose a day and a man, not more."},
                {"text": "Turn the ship away",
                 "chance": 0.5,
                 "win": {"food": -2}, "win_result": "You make it out.",
                 "lose": {"crew": -3}, "lose_result": "Not all of you."},
            ],
        },
    },
    {
        "key": "scylla",
        "name": "SCYLLA AND CHARYBDIS",
        "book": "BOOK XII",
        "omen": "where the strait roars between two cliffs",
        "calm": {
            "story": "On one side, six-headed Scylla. On the other, "
                     "the whirlpool Charybdis.",
            "choices": [
                {"text": "Hug Scylla's cliff",
                 "effects": {"crew": -2},
                 "result": "Six heads strike. You lose two men, not the "
                           "ship."},
                {"text": "Risk the whirlpool",
                 "chance": 0.5,
                 "win": {}, "win_result":
                     "Charybdis is resting. You slip through untouched.",
                 "lose": {"crew": -2, "health": -4, "food": -4},
                 "lose_result": "The sea swallows half your stores."},
            ],
        },
        "harsh": {
            "story": "Both monsters are awake.",
            "choices": [
                {"text": "Charge past Scylla",
                 "effects": {"crew": -4},
                 "result": "She takes her six."},
                {"text": "Ride the whirlpool's edge",
                 "chance": 0.4,
                 "win": {"health": -2}, "win_result": "Barely.",
                 "lose": {"crew": -3, "health": -4}, "lose_result":
                     "You cling to a fig tree as the ship spins down."},
            ],
        },
    },
    {
        "key": "thrinacia",
        "name": "THE CATTLE OF HELIOS",
        "book": "BOOK XII",
        "omen": "where golden cattle graze beside the sea",
        "calm": {
            "story": "The sun god's sacred cattle graze here. Your crew "
                     "is starving.",
            "choices": [
                {"text": "Forbid the slaughter",
                 "effects": {"food": -4, "favor": 3},
                 "result": "Hungry, but Helios is not angered."},
                {"text": "Let them eat",
                 "effects": {"food": 12, "favor": -5},
                 "result": "A feast. The sky darkens over you."},
            ],
        },
        "harsh": {
            "story": "Storms trap you here for a month. The cattle are "
                     "so close.",
            "choices": [
                {"text": "Fish and hunt birds",
                 "effects": {"food": -6, "health": -2},
                 "result": "Thin months, clean hands."},
                {"text": "Slaughter the cattle",
                 "effects": {"food": 10, "favor": -6, "crew": -2},
                 "result": "Zeus answers with lightning."},
            ],
        },
    },
]

ITHACA = {
    "name": "ITHACA",
    "book": "BOOK XIII",
    "story": "The rocky island of your home rises from the mist. Penelope "
             "has waited twenty years.",
}

ROUTE_LEGS = len(EPISODES)        # 8 islands, then Ithaca

# ODYSSEY — Milestone 12: The Trials of Odysseus

## Installation

In `~/UTA/OdysseyNav` with your existing Milestone 11 installation:

```bash
cp main.py main_before_m12.py
unzip -o ~/Downloads/odyssey_m12_trials.zip
source .venv/bin/activate
python -m pytest tests/ -v
python main.py
```

This ZIP contains only `main.py`, `core/encounters.py`, and `tests/test_encounters.py`, plus this README. It **requires your existing Milestone 11 and earlier modules**, including `core/survival.py` and `core/island_survival.py`.

## How to play

1. Click BEGIN VOYAGE and sail to an island shoreline.
2. Press **F** when close enough to dock.
3. A story encounter appears. Press **1** or **2** to choose. The game pauses while deciding.
4. Successful choices apply resource and hull/morale consequences, then the island's normal randomized loot and mandatory crew rest process occurs.
5. If you cannot afford a choice, the dialogue remains open; choose the other option or press **ESC** to close it.
6. Each island's unique encounter happens once per voyage. Normal loot can be collected again on later in-game days.
7. Press **R** to start a new voyage and reset encounters.

## Island encounters

- Aeolia: trade food for rope or refuse.
- Circe's Isle: risk morale for medicine or forage herbs.
- The Sirens: accept hull damage for food or spend rope to protect the crew.
- Thrinacia: gain food at a morale cost or respect the sacred herd.
- Ogygia: gather wood or forage rations.
- Phaeacia: trade food for repair materials or timber for food.
- Lotus Shore: accept tempting provisions at a morale cost or maintain resolve.
- Calypso's Haven: repair using wood or collect building materials.

## Engineering notes

- The encounter rules are independent of Pygame, implemented in `core/encounters.py`.
- All choices have deterministic effects and are testable.
- Encounter state is separate from the island-loot visit cooldown.
- Time does not advance during dialogue, and gameplay input is suppressed.
- Some risky choices can sink the ship or end the voyage if morale reaches zero.
- These are original myth-inspired scenarios, not adapted film dialogue.

## Validation

The 10 new encounter tests passed. A reconstructed suite assembled from earlier milestone archives passed **55 tests**. Run the full suite in your own local project to verify all your existing files and versions.

# TABLE HOCKEY

**A fast-paced, single-player arcade air hockey game built with Python and Pygame-CE.**

Table Hockey puts the player against an increasingly competitive CPU opponent in a 30-level campaign. Move your paddle with the mouse, return the puck, defend your goal, and clear levels to unlock new challenges and collectible paddle skins.

## Gameplay at a glance

- **30-level campaign:** Select any unlocked level. Win a match to advance and unlock the next level; a loss lets you retry.
- **Progressive CPU opponent:** The AI becomes faster, more responsive, accurate, and aggressive as the campaign advances. There is no separate difficulty selector.
- **Mouse-controlled paddle:** Move the mouse to control the blue player paddle. The CPU controls the opposing paddle.
- **Paddle skin rewards:** Winning campaign levels unlocks themed paddle skins. The game includes 30 skin designs, with campaign rewards saved locally.
- **Arcade match flow:** Pre-serve countdown, active play, goal celebrations, pause, victory, and game-over screens.
- **Anime-inspired presentation:** Neon arena visuals, puck trails and speed streaks, paddle afterimages, hit sparks, impact particles, screen shake, and goal effects.
- **Synthesized audio:** Background music and match sound effects with separate volume controls.
- **Customizable presentation:** Neon, Cyber, and Sunset table themes; Low, Medium, and High graphics quality; fullscreen and resolution settings.
- **Frame-rate options:** Select a 30, 60, or 120 FPS cap, or unlimited, and toggle the FPS counter.
- **Persistent progress and settings:** Campaign progress, unlocked/equipped skins, and user preferences are stored locally.

## Architecture

The diagram below is the current high-level module map. It follows the project structure and shows how the application loop, state manager, match simulation, presentation, audio, and configuration fit together.

![Table Hockey application architecture](docs/architecture.png)

### Module responsibilities

| Module | Responsibility |
|---|---|
| `main.py` | Initializes Pygame, settings, audio, match objects, rendering, and the main application loop. |
| `states.py` | Owns the screen-state manager and menu, level selection, settings, how-to-play, gameplay, pause, victory, and game-over screens. It also saves campaign results. |
| `match.py` | Coordinates match lifecycle, player/CPU updates, scoring, countdowns, and match events. |
| `ai.py` | Calculates CPU paddle movement and attack/defense decisions. Its challenge scales with campaign level. |
| `player.py` | Holds player/controller data used by the match. |
| `paddle.py` | Implements paddle movement, collision-related state, skin appearance, and motion effects. |
| `puck.py` | Holds puck movement state, trail history, and puck rendering. |
| `physics.py` | Handles puck movement, sub-stepped collision resolution, wall/post/paddle impacts, and goal detection. |
| `effects.py` | Manages match particles, impacts, goal effects, celebrations, and screen shake. |
| `skins.py` | Defines the 30 campaign paddle-skin designs and skin lookup helpers. |
| `ui.py` | Draws and caches the air-hockey table and shared presentation elements. |
| `menu_ui.py` | Provides reusable arcade menu widgets and background/panel drawing helpers. |
| `settings.py` | Loads, validates, persists user preferences, and calculates resolution-dependent layout geometry. |
| `audio.py` | Manages synthesized background music, sound effects, and volume controls. |
| `config.py` | Centralizes display settings, table geometry, colors, physics tuning, AI baseline values, and graphics-quality flags. |

## Campaign and progression

The campaign contains **30 levels**. Only levels reached through campaign progress are selectable.

1. Start a game from the main menu and choose an unlocked campaign level.
2. Win the match to clear that level and unlock the next one.
3. Each new level raises the CPU challenge.
4. A level victory unlocks its corresponding paddle skin and equips the newly earned reward.
5. If a match is lost, the level remains available to retry.

Campaign progress is saved in `TABLE_HOCKEY/save/high_scores.json`. The file tracks the unlocked campaign frontier, per-level completion/attempt/win/loss records, unlocked skins, and the equipped skin.

## Controls

| Action | Input |
|---|---|
| Move player paddle | Move the mouse |
| Pause / resume a match | `Esc` or `P` |
| Navigate menus | Mouse or `W` / `S` / arrow keys |
| Select a menu item | Mouse click, `Enter`, or `Space` |
| Navigate campaign levels | Mouse or arrow keys |
| Return / back in menus | `Esc` or `Backspace` where shown |

The player paddle is mouse-controlled during gameplay. Keyboard navigation is available for menus; movement-key remapping is not part of the current settings screen.

## Settings

The Settings screen includes:

- Master, music, and sound-effect volume sliders.
- Music enable/disable.
- Fullscreen mode and supported display resolutions.
- FPS counter and screen-shake toggles.
- FPS cap: 30, 60, 120, or unlimited.
- Graphics quality: Low, Medium, or High.
- Table theme: Neon, Cyber, or Sunset.
- Apply, cancel/rollback, and reset-to-default actions.

Graphics quality controls optional visual effects. High quality enables the fullest configured trails, glow, particles, and blur options; lower presets reduce selected effects for less demanding systems.

## Project structure

```text
Table-Hockey/
├── TABLE_HOCKEY/
│   ├── main.py          # Application entry point and game loop
│   ├── states.py        # Screen state manager, campaign, and menus
│   ├── match.py         # Match lifecycle and coordination
│   ├── ai.py            # Progressive CPU opponent
│   ├── player.py        # Player/controller data
│   ├── physics.py       # Puck collision and goal simulation
│   ├── paddle.py        # Paddle entity and movement effects
│   ├── puck.py          # Puck entity and trails
│   ├── effects.py       # Particles, impacts, and celebrations
│   ├── skins.py         # 30 paddle skin definitions
│   ├── ui.py            # Table renderer
│   ├── menu_ui.py       # Reusable menu widgets
│   ├── audio.py         # Synthesized music and sound effects
│   ├── settings.py      # Settings persistence and layout
│   ├── config.py        # Shared constants and tuning
│   └── save/            # Runtime settings and campaign records
├── docs/
│   └── architecture.png # Current application architecture diagram
└── README.md
```

Runtime save files are created as the game is used and may not exist in a fresh clone.

## Requirements

- Python **3.12**
- Pygame-CE (dependencies are listed in `TABLE_HOCKEY/requirements.txt`)
- Windows, macOS, or Linux with a display and audio environment supported by Pygame

## Installation and launch

### Windows PowerShell

```powershell
git clone https://github.com/sharpp08/Table-Hockey.git
cd Table-Hockey

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r .\TABLE_HOCKEY\requirements.txt
python .\TABLE_HOCKEY\main.py
```

### macOS / Linux

```bash
git clone https://github.com/sharpp08/Table-Hockey.git
cd Table-Hockey

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r TABLE_HOCKEY/requirements.txt
python TABLE_HOCKEY/main.py
```

## Local save data

The game stores player-specific data in `TABLE_HOCKEY/save/`:

- `settings.json` — display, audio, graphics, and gameplay preferences.
- `high_scores.json` — campaign level progress, per-level results, unlocked skins, and equipped skin.

These files are generated at runtime. Back them up before deleting or replacing local save data if you want to keep your campaign progress and preferences.

## Development notes

- This is a **Python + Pygame-CE** project; gameplay is not implemented in Godot.
- Keep match simulation, screen-state handling, rendering, audio, and settings responsibilities separated.
- Put shared tuning constants in `config.py`.
- Preserve existing local save data when changing campaign or settings formats.
- When testing gameplay changes, cover mouse paddle control, CPU behavior across multiple campaign levels, collisions and goals, pause/resume, victory and loss progression, skin rewards, settings apply/cancel, and display modes.
- Performance work should preserve the visual effects and quality options rather than silently disabling them.

## Repository

[sharpp08/Table-Hockey](https://github.com/sharpp08/Table-Hockey)

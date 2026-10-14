# League of Legends Scraping & Scouting Suite

> **Note for AI Agents & LLMs:** This document describes the purpose, architecture, input/output contracts, and execution interfaces of the League of Legends scraping and scouting tools in this repository.

---

## 1. Project Overview

This repository provides high-speed, reliable, zero-auth data extraction tools for **League of Legends** (focused on region **EUW**, but extensible to any Riot region).

It solves two primary use cases:
1. **Real-time Contemporary Builds:** Optimal items, boots, starter kits, full rune trees (primary + secondary keystones), and skill level-up order for any champion in any role for the current patch.
2. **Competitive Scouting & Team Building:** Batch extraction and deep analysis of player profiles using their **Riot ID** (`GameName#TagLine`), generating tactical scouting reports (comfort picks, OTP traps, damage profiles, playstyle metrics, target bans, and team synergies).

---

## 2. Technical Architecture & Scraping Mechanism

Traditional scraping on LoL statistics sites (e.g., using BeautifulSoup or Selenium on OP.GG / LeagueOfGraphs) is fragile due to:
- **Cloudflare Anti-Bot Protections:** Direct HTML requests often return `403 Forbidden` or challenge pages.
- **Next.js React Server Components (RSC):** Modern frontends stream data via `self.__next_f.push` rather than static HTML tables.

### Solution Implemented
1. **OP.GG Open Streamable HTTP / MCP API (`https://mcp-api.op.gg/mcp`):**
   - Implements the Model Context Protocol (MCP) over JSON-RPC 2.0 via standard HTTP POST.
   - Provides structured endpoints (`lol_get_champion_analysis`, `lol_get_summoner_profile`, `lol_list_summoner_matches`).
   - Requires **no API keys**, experiences **no Cloudflare blocks**, and responds in sub-second times.
2. **Schema.org & Metadata Parsing:**
   - For fast batch operations, `advanced_scouting.py` parses OP.GG's server-rendered `<meta name="description">` and `<script type="application/ld+json">` payloads.
   - Decodes HTML entities (e.g., `Kai'Sa`), extracts seasonal champion distributions, recent match histories (KDA, winrates, streaks), and fallback Flex rankings when players are unranked in SoloQ.

---

## 3. Repository Structure & Scripts

```
.
├── giocatori.md                 # Default input file: team player list (- Name#Tag)
├── lol_scraper.py               # Core library & CLI for single player / champion builds
├── scrape_players.py            # Basic batch scraper (exports to single CSV)
├── advanced_scouting.py         # Advanced scouting suite (exports 5 CSVs to output/)
├── output/                      # Output directory for advanced scouting files
│   ├── 01_roster_overview.csv
│   ├── 02_champion_pool_analitica.csv
│   ├── 03_in_game_playstyle_metrics.csv
│   ├── 04_scouting_report_tattico.csv
│   └── 05_sinergie_squadra.csv
└── ai.md                        # This documentation file
```

---

## 4. Input File Format (`giocatori.md` or custom)

The input file must contain Riot IDs, one per line. Markdown lists (`- `, `* `), numbered lists (`1. `), or raw lines are automatically sanitized:

```markdown
- Fang Arroway#EUW
- ClippeteCloppete#8279
- ExodiaTheOnly1#EUW
- Jimbo Cataza#1994
- shineless#light
- UnluckyTeemo#995
- Ándre Agassi#8884
- Vitreous#COPS
```

---

## 5. Script Documentation & Usage

### A. `lol_scraper.py` (Core Engine & CLI)
Use for ad-hoc champion build queries or individual player lookups.

#### CLI Commands:
```bash
# 1. Fetch current optimal build for a champion
python lol_scraper.py build "Ahri" --position mid --mode ranked
python lol_scraper.py build "Aatrox" --position top

# 2. Fetch summoner profile
python lol_scraper.py player "Kaori#EUW33" --region euw
```

#### Python API:
```python
from lol_scraper import LoLScraper

scraper = LoLScraper()

# Champion Build
build = scraper.get_champion_build(champion="Ahri", position="mid", game_mode="ranked")
# Returns: dict with starter_items, core_items, boots, runes (primary/secondary), skill_order

# Player Info
player = scraper.get_player_info(game_name="Kaori", tag_line="EUW33", region="euw")
# Returns: dict with riot_id, level, ranked stats (tier, division, lp, wins, losses, winrate)
```

---

### B. `scrape_players.py` (Basic Batch Scraper)
Iterates through a list of players from an input file and outputs their base ranking and level into a single CSV.

#### CLI Usage:
```bash
# Default (reads giocatori.md -> writes giocatori_output.csv)
python scrape_players.py

# Custom input/output
python scrape_players.py --input my_team.md --output team_stats.csv --region euw
```

---

### C. `advanced_scouting.py` (Competitive Scouting Suite)
The flagship analytics engine designed for **Clash, tournament preparation, and roster building**. It generates five distinct CSV files with `;` delimiters and `utf-8-sig` encoding (ready for Excel/Sheets).

#### CLI Usage:
```bash
# Default execution (reads giocatori.md -> generates output/*)
python advanced_scouting.py

# Custom parameters
python advanced_scouting.py --input opponents.md --output-dir tournament_scout --region euw
```

#### Output Artifacts Description:

1. **`01_roster_overview.csv`**:
   - High-level player card: Level, Primary/Secondary role, SoloQ and Flex ranks, seasonal winrates, top comfort picks, OTP syndrome assessment, global damage profile (AP/AD/Tank), recent 10-match streak, and tilt risk.
2. **`02_champion_pool_analitica.csv`**:
   - Deep dive into every champion in the player's pool: games played, winrate %, pool share %, champion class, role, damage type, first-pick safety, and scouting classification (`COMFORT PICK`, `PICK SOLIDO`, `TRAP PICK (WR < 45%)`, `SOTTO MEDIA`).
3. **`03_in_game_playstyle_metrics.csv`**:
   - Behavioral profiling: AD vs AP flexibility, Comfort vs Meta alignment, Macro resource allocation (*Strongside Priority* vs *Weakside Friendly*), early game aggression, teamfight damage role, and gank/camping vulnerability.
4. **`04_scouting_report_tattico.csv`**:
   - **Tactical Strategy Guide:**
     - `TARGET_BAN_CHIRURGICI`: Exact 2 champions to ban against the player (high volume + high winrate).
     - `NON_BANNARE_LASCIARE_OPEN`: High volume champions with low winrate (<45%) that should intentionally be left open.
     - `PUNTI_DI_FORZA_CHIAVE`: Key strengths to respect.
     - `DEBOLEZZE_SFRUTTABILI`: Exploitable tactical flaws (e.g., rigid full-AP pool, tilt vulnerability).
     - `COME_GIOCARE_CON_LUI`: Team building recommendations when playing with this player.
     - `COME_GIOCARE_CONTRO_DI_LUI`: Step-by-step gameplan to shut down the player when facing them.
     - `STATO_MENTALE_E_TILT`: Psychological state based on recent win/loss streaks.
5. **`05_sinergie_squadra.csv`**:
   - Lineup balance, lane synergy recommendations (Mid-Jungle, Bot-Support), and draft composition alerts.

---

## 6. Dependencies & Requirements

- **Python:** 3.10+
- **HTTP Client:** `httpx` (version 0.24.0 or newer)
  ```bash
  pip install httpx
  ```
- **Operating System Compatibility:** Fully Windows, Linux, and macOS compatible. All scripts enforce UTF-8 console output and `utf-8-sig` CSV export to eliminate encoding errors on Windows terminal (`cp1252`).

---

## 7. Guidelines for Extending or Automating

- **Adding new regions:** Pass `--region <region>` (e.g. `na`, `kr`, `eune`, `br`). The endpoint dynamically adapts to the selected server.
- **Adding champion archetypes:** Update the `CHAMPION_DB` dictionary in `advanced_scouting.py` when Riot releases new champions.
- **Headless Execution:** All scripts run synchronously or background-safe without GUI, suitable for cron jobs, Discord bot backends, or agentic workflows.

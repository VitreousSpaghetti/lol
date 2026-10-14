"""
Advanced LoL Team & Opponent Scouting Suite
===========================================
Effettua uno scouting analitico completo per torneo/Clash/team building su ciascun giocatore
presente nel file di input, analizzando:
1. Champion Pool approfondita (Comfort pick vs Meta, Sindrome OTP, profili di danno AD/AP/Tank)
2. Metriche In-Game e stile di gioco (Dominanza corsia, KP%, Danno, Visione, Risorse Strongside/Weakside)
3. Guida Team Building ("Come giocare CON lui")
4. Scheda Strategica ("Come giocare CONTRO di lui": Target ban chirurgici, Pick trappola, Tilt factor)
5. Sinergie e bilanciamento della squadra

Genera 5 file CSV nella cartella output/.
"""

import os
import sys
import re
import csv
import json
import html
import argparse
import urllib.parse
from typing import List, Tuple, Dict, Any
import httpx

# Assicura compatibilita console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Database metadati campioni per identificazione automatica Ruolo, Profilo Danno e Stile
CHAMPION_DB = {
    # TOP
    "Aatrox": {"role": "TOP", "dmg": "AD", "class": "Juggernaut / Bruiser", "first_pick": "Buono"},
    "Camille": {"role": "TOP", "dmg": "AD / True", "class": "Diver", "first_pick": "Buono"},
    "Cho'Gath": {"role": "TOP", "dmg": "AP / Tank", "class": "Tank", "first_pick": "Situazionale"},
    "Darius": {"role": "TOP", "dmg": "AD / True", "class": "Juggernaut", "first_pick": "Buono"},
    "Dr. Mundo": {"role": "TOP", "dmg": "Tank / AD", "class": "Juggernaut", "first_pick": "Situazionale"},
    "Fiora": {"role": "TOP", "dmg": "AD", "class": "Skirmisher / Splitpush", "first_pick": "Rischioso"},
    "Garen": {"role": "TOP", "dmg": "AD", "class": "Juggernaut", "first_pick": "Medio"},
    "Gnar": {"role": "TOP", "dmg": "AD", "class": "Specialist / Teamfight", "first_pick": "Ottimo Blind"},
    "Gragas": {"role": "TOP / JUNGLE / MID", "dmg": "AP", "class": "Burst / Disruption", "first_pick": "Ottimo Blind"},
    "Irelia": {"role": "TOP / MID", "dmg": "AD", "class": "Diver / Skirmisher", "first_pick": "Situazionale"},
    "Jax": {"role": "TOP", "dmg": "Hybrid", "class": "Skirmisher", "first_pick": "Buono"},
    "K'Sante": {"role": "TOP", "dmg": "Tank / AD", "class": "Warden / Skirmisher", "first_pick": "Ottimo Blind"},
    "Malphite": {"role": "TOP", "dmg": "AP / Tank", "class": "Tank / Engage", "first_pick": "Contro AD"},
    "Mordekaiser": {"role": "TOP", "dmg": "AP", "class": "Juggernaut", "first_pick": "Buono"},
    "Ornn": {"role": "TOP", "dmg": "Tank / AP", "class": "Tank / Masterwork", "first_pick": "Ottimo Blind"},
    "Renekton": {"role": "TOP", "dmg": "AD", "class": "Diver / Early Bully", "first_pick": "Ottimo Blind"},
    "Riven": {"role": "TOP", "dmg": "AD", "class": "Skirmisher", "first_pick": "Rischioso"},
    "Sett": {"role": "TOP", "dmg": "AD", "class": "Juggernaut", "first_pick": "Buono"},
    "Shen": {"role": "TOP", "dmg": "Tank / AP", "class": "Warden / Global TP", "first_pick": "Buono"},
    "Sion": {"role": "TOP", "dmg": "Tank / AD", "class": "Tank / Scaling", "first_pick": "Buono"},
    "Teemo": {"role": "TOP", "dmg": "AP", "class": "Specialist / Harass", "first_pick": "Rischioso"},
    "Urgot": {"role": "TOP", "dmg": "AD", "class": "Juggernaut", "first_pick": "Buono"},
    "Volibear": {"role": "TOP", "dmg": "Hybrid / Tank", "class": "Juggernaut / Dive", "first_pick": "Buono"},
    "Yorick": {"role": "TOP", "dmg": "AD", "class": "Juggernaut / Splitpush", "first_pick": "Situazionale"},
    
    # JUNGLE
    "Amumu": {"role": "JUNGLE", "dmg": "AP / Tank", "class": "Tank / Engage", "first_pick": "Buono"},
    "Briar": {"role": "JUNGLE", "dmg": "AD", "class": "Diver", "first_pick": "Rischioso"},
    "Diana": {"role": "MID / JUNGLE", "dmg": "AP", "class": "Assassin / Diver", "first_pick": "Buono"},
    "Elise": {"role": "JUNGLE", "dmg": "AP", "class": "Early Ganker / Diver", "first_pick": "Situazionale"},
    "Hecarim": {"role": "JUNGLE", "dmg": "AD", "class": "Diver", "first_pick": "Buono"},
    "Jarvan IV": {"role": "JUNGLE", "dmg": "AD", "class": "Diver / Initiator", "first_pick": "Ottimo Blind"},
    "Karthus": {"role": "JUNGLE / APC", "dmg": "AP", "class": "Global / Powerfarm", "first_pick": "Situazionale"},
    "Kayn": {"role": "JUNGLE", "dmg": "AD", "class": "Assassin / Bruiser", "first_pick": "Buono"},
    "Lee Sin": {"role": "JUNGLE", "dmg": "AD", "class": "Playmaker", "first_pick": "Ottimo"},
    "Master Yi": {"role": "JUNGLE", "dmg": "AD", "class": "Skirmisher", "first_pick": "Rischioso"},
    "Nocturne": {"role": "JUNGLE", "dmg": "AD", "class": "Diver / Global Dark", "first_pick": "Buono"},
    "Rengar": {"role": "JUNGLE", "dmg": "AD", "class": "Assassin", "first_pick": "Rischioso"},
    "Sejuani": {"role": "JUNGLE", "dmg": "Tank / AP", "class": "Tank / CC Lock", "first_pick": "Ottimo Blind"},
    "Shaco": {"role": "JUNGLE", "dmg": "AD / AP", "class": "Trickster", "first_pick": "Rischioso"},
    "Shyvana": {"role": "JUNGLE", "dmg": "AP / Hybrid", "class": "Juggernaut / Powerfarm", "first_pick": "Situazionale"},
    "Vi": {"role": "JUNGLE", "dmg": "AD", "class": "Diver / Lockdown", "first_pick": "Ottimo Blind"},
    "Viego": {"role": "JUNGLE", "dmg": "AD", "class": "Skirmisher", "first_pick": "Buono"},
    "Xin Zhao": {"role": "JUNGLE", "dmg": "AD", "class": "Diver", "first_pick": "Ottimo Blind"},
    "Zac": {"role": "JUNGLE / TOP", "dmg": "Tank / AP", "class": "Engage Tank", "first_pick": "Buono"},
    
    # MID
    "Ahri": {"role": "MID", "dmg": "AP", "class": "Mage / Assassin", "first_pick": "Ottimo Blind"},
    "Akali": {"role": "MID", "dmg": "AP", "class": "Assassin", "first_pick": "Rischioso"},
    "Azir": {"role": "MID", "dmg": "AP", "class": "Control Mage / DPS", "first_pick": "Buono"},
    "Corki": {"role": "MID / ADC", "dmg": "Hybrid / AD", "class": "Marksman / Poke", "first_pick": "Buono"},
    "Hwei": {"role": "MID", "dmg": "AP", "class": "Artillery / Control", "first_pick": "Buono"},
    "Katarina": {"role": "MID", "dmg": "AP / AD", "class": "Assassin / Roamer", "first_pick": "Rischioso"},
    "LeBlanc": {"role": "MID", "dmg": "AP", "class": "Burst Assassin", "first_pick": "Buono"},
    "Lux": {"role": "MID / SUP", "dmg": "AP", "class": "Burst / Poke", "first_pick": "Medio"},
    "Mel": {"role": "MID / SUP", "dmg": "AP", "class": "Control Mage", "first_pick": "Medio"},
    "Orianna": {"role": "MID", "dmg": "AP", "class": "Control Mage", "first_pick": "Ottimo Blind"},
    "Swain": {"role": "MID / APC / SUP", "dmg": "AP", "class": "Battlemage / Drain Tank", "first_pick": "Buono"},
    "Syndra": {"role": "MID", "dmg": "AP", "class": "Burst / Control", "first_pick": "Ottimo Blind"},
    "Veigar": {"role": "MID / APC", "dmg": "AP", "class": "Burst / Infinite Stacker", "first_pick": "Situazionale"},
    "Viktor": {"role": "MID", "dmg": "AP", "class": "Control Mage", "first_pick": "Ottimo Blind"},
    "Yasuo": {"role": "MID / TOP", "dmg": "AD", "class": "Skirmisher", "first_pick": "Rischioso"},
    "Yone": {"role": "MID / TOP", "dmg": "AD / Hybrid", "class": "Skirmisher / Assassin", "first_pick": "Buono"},
    "Zed": {"role": "MID", "dmg": "AD", "class": "Assassin", "first_pick": "Rischioso"},

    # ADC
    "Aphelios": {"role": "ADC", "dmg": "AD", "class": "Hypercarry", "first_pick": "Rischioso"},
    "Ashe": {"role": "ADC / SUP", "dmg": "AD", "class": "Utility Marksman", "first_pick": "Ottimo Blind"},
    "Caitlyn": {"role": "ADC", "dmg": "AD", "class": "Lane Bully / Range", "first_pick": "Buono"},
    "Draven": {"role": "ADC", "dmg": "AD", "class": "Snowball Bully", "first_pick": "Rischioso"},
    "Ezreal": {"role": "ADC", "dmg": "AD / Hybrid", "class": "Poke Marksman", "first_pick": "Ottimo Blind"},
    "Jhin": {"role": "ADC", "dmg": "AD", "class": "Utility / Execution", "first_pick": "Ottimo Blind"},
    "Jinx": {"role": "ADC", "dmg": "AD", "class": "Hypercarry / Reset", "first_pick": "Buono"},
    "Kai'Sa": {"role": "ADC", "dmg": "Hybrid", "class": "Dive Marksman", "first_pick": "Buono"},
    "Kog'Maw": {"role": "ADC", "dmg": "Hybrid / AP", "class": "Hypercarry", "first_pick": "Situazionale"},
    "Lucian": {"role": "ADC / MID", "dmg": "AD", "class": "Early Bully", "first_pick": "Buono"},
    "Miss Fortune": {"role": "ADC", "dmg": "AD", "class": "Teamfight Wombocombo", "first_pick": "Buono"},
    "Samira": {"role": "ADC", "dmg": "AD", "class": "Combo / Reset", "first_pick": "Rischioso"},
    "Sivir": {"role": "ADC", "dmg": "AD", "class": "Waveclear / Team Speed", "first_pick": "Buono"},
    "Tristana": {"role": "ADC / MID", "dmg": "AD", "class": "Siege / Reset", "first_pick": "Buono"},
    "Twitch": {"role": "ADC", "dmg": "AD / AP", "class": "Hypercarry / Ambush", "first_pick": "Rischioso"},
    "Varus": {"role": "ADC", "dmg": "AD / AP", "class": "Poke / On-Hit", "first_pick": "Ottimo Blind"},
    "Vayne": {"role": "ADC / TOP", "dmg": "AD / True", "class": "Tank Shredder", "first_pick": "Rischioso"},
    "Xayah": {"role": "ADC", "dmg": "AD", "class": "Self-Peel Marksman", "first_pick": "Ottimo Blind"},
    "Zeri": {"role": "ADC", "dmg": "AD / AP", "class": "Hypercarry / Kiting", "first_pick": "Buono"},

    # SUPPORT
    "Alistar": {"role": "SUPPORT", "dmg": "Tank / AP", "class": "Engage / Disengage", "first_pick": "Buono"},
    "Bard": {"role": "SUPPORT", "dmg": "AP / Utility", "class": "Roamer / Playmaker", "first_pick": "Situazionale"},
    "Blitzcrank": {"role": "SUPPORT", "dmg": "Tank / AP", "class": "Hook / Pick Maker", "first_pick": "Rischioso"},
    "Brand": {"role": "SUPPORT / APC", "dmg": "AP", "class": "Mage Support / Teamfight", "first_pick": "Medio"},
    "Braum": {"role": "SUPPORT", "dmg": "Tank", "class": "Warden / Anti-Projectile", "first_pick": "Ottimo contro dive"},
    "Janna": {"role": "SUPPORT", "dmg": "AP", "class": "Disengage Enchanter", "first_pick": "Buono"},
    "Karma": {"role": "SUPPORT / MID", "dmg": "AP", "class": "Poke Enchanter", "first_pick": "Ottimo Blind"},
    "Leona": {"role": "SUPPORT", "dmg": "Tank", "class": "Heavy CC Engage", "first_pick": "Buono"},
    "Lulu": {"role": "SUPPORT", "dmg": "AP", "class": "Hypercarry Enchanter", "first_pick": "Buono"},
    "Milio": {"role": "SUPPORT", "dmg": "AP", "class": "Enchanter / Range Buff", "first_pick": "Buono"},
    "Morgana": {"role": "SUPPORT", "dmg": "AP", "class": "Anti-CC / Bind", "first_pick": "Buono"},
    "Nami": {"role": "SUPPORT", "dmg": "AP", "class": "Aggressive Enchanter", "first_pick": "Buono"},
    "Nautilus": {"role": "SUPPORT", "dmg": "Tank / AP", "class": "Point & Click Engage", "first_pick": "Ottimo Blind"},
    "Pyke": {"role": "SUPPORT", "dmg": "AD", "class": "Assassin / Roamer", "first_pick": "Rischioso"},
    "Rakan": {"role": "SUPPORT", "dmg": "AP / Tank", "class": "Mobile Engage", "first_pick": "Ottimo Blind"},
    "Rell": {"role": "SUPPORT", "dmg": "Tank / AP", "class": "Heavy CC Engage", "first_pick": "Buono"},
    "Senna": {"role": "SUPPORT / ADC", "dmg": "AD", "class": "Marksman Support", "first_pick": "Situazionale"},
    "Soraka": {"role": "SUPPORT", "dmg": "AP", "class": "Healer Enchanter", "first_pick": "Medio"},
    "Thresh": {"role": "SUPPORT", "dmg": "Tank / AP", "class": "Versatile Playmaker", "first_pick": "Ottimo Blind"},
    "Zyra": {"role": "SUPPORT", "dmg": "AP", "class": "Zone Control Mage", "first_pick": "Medio"}
}

def get_champion_meta(name: str) -> Dict[str, str]:
    """Recupera informazioni di classe, ruolo e profilo danno del campione"""
    clean_name = name.replace("&#x27;", "'").strip()
    if clean_name in CHAMPION_DB:
        return CHAMPION_DB[clean_name]
    # Fallback per campioni non presenti nel dizionario statico
    return {
        "role": "Flessibile",
        "dmg": "Ibrido / Non Definito",
        "class": "Specialist",
        "first_pick": "Situazionale"
    }

def normalize_role(r: str) -> str:
    """Normalizza i ruoli in formato standard (TOP, JUNGLE, MID, ADC, SUPPORT)"""
    rc = r.strip().upper()
    if rc in ["JUNGLA", "JUNGLE", "JNG"]:
        return "JUNGLE"
    if rc in ["SUP", "SUPP", "SUPPORT"]:
        return "SUPPORT"
    if rc in ["BOT", "ADC", "AD"]:
        return "ADC"
    if rc in ["MID", "MIDDLE"]:
        return "MID"
    if rc in ["TOP"]:
        return "TOP"
    return rc

STANDARD_ROLES = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]

def champion_matches_role(champ_role: str, target_role: str) -> bool:
    """Verifica se il ruolo di un campione copre il ruolo target (es: APC -> ADC)"""
    target = target_role.upper()
    crole = champ_role.upper()
    if target == "ADC":
        return any(k in crole for k in ["ADC", "APC", "BOT"])
    if target == "SUPPORT":
        return any(k in crole for k in ["SUPPORT", "SUP"])
    if target == "JUNGLE":
        return any(k in crole for k in ["JUNGLE", "JUNGLA", "JNG"])
    if target == "MID":
        return any(k in crole for k in ["MID", "MIDDLE"])
    if target == "TOP":
        return "TOP" in crole
    return target in crole

def get_best_champion_for_role(p: Dict[str, Any], r: str) -> Dict[str, Any]:
    """Trova il miglior comfort pick del giocatore specifico per il ruolo assegnato"""
    matching_champs = [c for c in p.get("champions", []) if champion_matches_role(c.get("role", ""), r)]
    if matching_champs:
        matching_champs.sort(key=lambda c: (c["winrate"] >= 50, c["play"] * (c["winrate"] / 100.0)), reverse=True)
        return matching_champs[0]
    if p.get("champions"):
        return p["champions"][0]
    return {
        "name": "Pick Flessibile",
        "play": 0, "wins": 0, "losses": 0, "winrate": 50.0,
        "role": r, "dmg": "AD / AP", "class": "Flessibile", "first_pick": "Situazionale"
    }

def score_player_role(p: Dict[str, Any], r: str) -> float:
    """Calcola il punteggio di idoneità (fit score) di un giocatore per un determinato ruolo"""
    score = 0.0
    decl = p.get("declared_roles", [])
    if decl:
        if r in decl:
            idx = decl.index(r)
            score += 150.0 - (idx * 30.0)
        else:
            score -= 100.0
    else:
        score += 40.0

    role_champs = [c for c in p.get("champions", []) if champion_matches_role(c.get("role", ""), r)]
    tot_play = sum(c["play"] for c in p.get("champions", [])) or 1
    role_play = sum(c["play"] for c in role_champs)
    role_wins = sum(c["wins"] for c in role_champs)
    role_wr = (role_wins / role_play * 100.0) if role_play > 0 else 45.0

    score += (role_play / tot_play) * 60.0
    score += (role_wr - 50.0) * 2.0
    return score

def assign_optimal_lineup(roster: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Risolve il problema di assegnazione ottimale garantendo che ogni ruolo della squadra
    (TOP, JUNGLE, MID, ADC, SUPPORT) abbia ALMENO un giocatore assegnato (o esattamente 1 titolare se roster >= 5),
    senza sovrapposizioni tra i titolari, massimizzando i ruoli dichiarati tra [] e le performance individuali.
    """
    import itertools
    if len(roster) < 5:
        assigned = {}
        used_roles = set()
        for p in roster:
            best_r = None
            best_sc = -999999
            for r in STANDARD_ROLES:
                if r not in used_roles:
                    sc = score_player_role(p, r)
                    if sc > best_sc:
                        best_sc = sc
                        best_r = r
            if best_r:
                used_roles.add(best_r)
                p["assigned_team_role"] = best_r
                assigned[best_r] = p
            else:
                p["assigned_team_role"] = "RISERVA"
        return assigned, []

    best_score = -999999
    best_assignment = None

    candidates = roster if len(roster) <= 8 else roster[:8]
    for subset in itertools.combinations(candidates, 5):
        for perm in itertools.permutations(subset, 5):
            cur_score = sum(score_player_role(perm[i], STANDARD_ROLES[i]) for i in range(5))
            if cur_score > best_score:
                best_score = cur_score
                best_assignment = perm

    assigned = {}
    starters = list(best_assignment)
    for i, r in enumerate(STANDARD_ROLES):
        p = starters[i]
        p["assigned_team_role"] = r
        assigned[r] = p

    reserves = [p for p in roster if p not in starters]
    for p in reserves:
        best_res_role = max(STANDARD_ROLES, key=lambda r: score_player_role(p, r))
        p["assigned_team_role"] = f"RISERVA ({best_res_role})"

    return assigned, reserves

def parse_input_file(filepath: str) -> List[Tuple[str, str, List[str]]]:
    """
    Estrae l'elenco dei giocatori (Nome, Tag, Ruoli Dichiarati) dal file markdown/testo.
    Supporta ruoli obbligatori/opzionali specificati tra parentesi quadre dopo il tag,
    es: - Fang Arroway#EUW [TOP,MID,JUNGLA]
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File non trovato: {filepath}")

    players = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignora righe vuote o commenti diretti (# o //)
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # Rimuove marcatori di lista all'inizio (es: "- ", "* ", "1. ")
            cleaned = re.sub(r"^[-*•\d.]+\s*", "", line).strip()
            
            # Ignora se la riga commentata era preceduta da un bullet (es: "- # Giocatore" o "-# Giocatore")
            if not cleaned or cleaned.startswith("#") or cleaned.startswith("//"):
                continue

            # Estrae ruoli specificati tra parentesi quadre subito dopo il tag, es: [TOP,MID,JUNGLA]
            declared_roles = []
            role_match = re.search(r'\[(.*?)\]', cleaned)
            if role_match:
                raw_roles = role_match.group(1).split(",")
                declared_roles = [normalize_role(r) for r in raw_roles if r.strip()]
                cleaned = re.sub(r'\[.*?\]', '', cleaned).strip()

            if "#" in cleaned:
                parts = cleaned.split("#", 1)
                name = parts[0].strip()
                tag = parts[1].strip()
                if name and tag:
                    players.append((name, tag, declared_roles))
    return players

def fetch_player_scouting_data(client: httpx.Client, name: str, tag: str, region: str = "euw", declared_roles: List[str] = None) -> Dict[str, Any]:
    """
    Effettua lo scraping completo del profilo OP.GG:
    - Metadati e rank SoloQ/Flex
    - Champion Pool stagionale con partite, winrate, KDA
    - Cronologia partite recenti (per tilt factor, trend e KDA)
    - Ruoli primario/secondario dichiarati via tag [RUOLI] o calcolati
    """
    slug = urllib.parse.quote(f"{name}-{tag}")
    url = f"https://op.gg/lol/summoners/{region.lower()}/{slug}"

    response = client.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} su OP.GG per {name}#{tag}")

    html_content = response.text

    # 1. Parsing Meta Description per Ranks e Champion Pool
    meta_desc_match = re.search(r'<meta name="description" content="([^"]+)"', html_content)
    meta_desc = html.unescape(meta_desc_match.group(1)) if meta_desc_match else ""

    # Estrazione Rank e LP
    solo_rank = "UNRANKED"
    solo_lp = 0
    solo_wins = 0
    solo_losses = 0
    solo_wr = 0.0

    rank_m = re.search(r'(Iron|Bronze|Silver|Gold|Platinum|Emerald|Diamond|Master|Grandmaster|Challenger)\s*(\d*)\s*(\d+)\s*LP', meta_desc, re.IGNORECASE)
    if rank_m:
        tier = rank_m.group(1).capitalize()
        div = f" {rank_m.group(2)}" if rank_m.group(2) else ""
        solo_rank = f"{tier}{div}".strip()
        solo_lp = int(rank_m.group(3))

    win_loss_m = re.search(r'(\d+)Win\s*(\d+)Lose\s*Win rate\s*(\d+)%', meta_desc)
    if win_loss_m:
        solo_wins = int(win_loss_m.group(1))
        solo_losses = int(win_loss_m.group(2))
        solo_wr = float(win_loss_m.group(3))

    # 2. Estrazione Champion Pool da Meta Description
    champions = []
    total_champ_games = 0

    champ_section = meta_desc.split(" / ")[-1] if " / " in meta_desc else ""
    champ_entries = re.findall(r'([A-Za-z0-9\s\'\.\&\;]+?)\s*-\s*(\d+)Win\s*(\d+)Lose\s*Win rate\s*(\d+)%', champ_section)

    for cname_raw, wins_str, loses_str, wr_str in champ_entries:
        cname = html.unescape(cname_raw).strip()
        w = int(wins_str)
        l = int(loses_str)
        play = w + l
        wr = float(wr_str)
        total_champ_games += play

        meta_info = get_champion_meta(cname)
        champions.append({
            "name": cname,
            "play": play,
            "wins": w,
            "losses": l,
            "winrate": wr,
            "role": meta_info["role"],
            "dmg": meta_info["dmg"],
            "class": meta_info["class"],
            "first_pick": meta_info["first_pick"]
        })

    for c in champions:
        c["pool_share"] = round((c["play"] / max(total_champ_games, 1)) * 100, 1)

    # 3. Parsing Schema.org JSON-LD per match history e recente forma
    recent_matches = []
    recent_summary = ""
    scripts = re.findall(r'<script type="application/ld\+json">({.*?})</script>', html_content, re.DOTALL)
    for s in scripts:
        if "recent matches" in s:
            try:
                data = json.loads(s)
                graph = data.get("@graph", [data])
                for item in graph:
                    if "description" in item and not recent_summary:
                        recent_summary = item["description"]
                    if item.get("@type") == "ItemList" and "itemListElement" in item:
                        for entry in item["itemListElement"]:
                            action = entry.get("item", {})
                            props = {p.get("name"): p.get("value") for p in action.get("additionalProperty", [])}
                            recent_matches.append({
                                "champion": props.get("champion", action.get("name", "")),
                                "result": props.get("result", "UNKNOWN"),
                                "kills": int(props.get("kills", 0) or 0),
                                "deaths": int(props.get("deaths", 0) or 0),
                                "assists": int(props.get("assists", 0) or 0),
                                "queue": props.get("queueType", "")
                            })
            except Exception:
                pass

    # Fallback per giocatori Unranked in SoloQ (usa statistiche Flex se presenti)
    if solo_rank == "UNRANKED" and recent_summary:
        flex_m = re.search(r'FLEXRANKED rank is\s*(\w+)\s*(\d*)\s*Division\s*(\d*)\s*(\d+)\s*LP with\s*(\d+)\s*wins,\s*(\d+)\s*losses,\s*and a\s*(\d+)%\s*win rate', recent_summary, re.IGNORECASE)
        if flex_m:
            tier = flex_m.group(1).capitalize()
            div = f" {flex_m.group(3)}" if flex_m.group(3) else ""
            solo_rank = f"{tier}{div} (Flex)".strip()
            solo_lp = int(flex_m.group(4))
            solo_wins = int(flex_m.group(5))
            solo_losses = int(flex_m.group(6))
            solo_wr = float(flex_m.group(7))

    # Fallback champion pool da recent matches se meta description non elenca campioni
    if not champions and recent_matches:
        rec_counts = {}
        for m in recent_matches:
            c = m.get("champion")
            if c:
                rec_counts[c] = rec_counts.get(c, 0) + 1
        for cname, count in sorted(rec_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            meta_info = get_champion_meta(cname)
            w_count = sum(1 for m in recent_matches if m.get("champion") == cname and m.get("result") == "WIN")
            l_count = count - w_count
            champions.append({
                "name": cname,
                "play": count,
                "wins": w_count,
                "losses": l_count,
                "winrate": round((w_count / count) * 100, 1),
                "role": meta_info["role"],
                "dmg": meta_info["dmg"],
                "class": meta_info["class"],
                "first_pick": meta_info["first_pick"],
                "pool_share": round((count / len(recent_matches)) * 100, 1)
            })

    # 4. Analisi Recente e Tilt
    recent_wins = sum(1 for m in recent_matches if m.get("result") == "WIN")
    recent_losses = sum(1 for m in recent_matches if m.get("result") == "LOSE")
    total_recent = recent_wins + recent_losses
    recent_wr = round((recent_wins / max(total_recent, 1)) * 100, 1) if total_recent > 0 else solo_wr

    streak_type = "None"
    streak_count = 0
    if recent_matches:
        first_res = recent_matches[0].get("result")
        for m in recent_matches:
            if m.get("result") == first_res:
                streak_count += 1
            else:
                break
        streak_type = f"{streak_count} {'Vittorie' if first_res == 'WIN' else 'Sconfitte'} consecutive"

    tilt_risk = "Basso"
    if recent_wr <= 35 or (first_res == "LOSE" and streak_count >= 3):
        tilt_risk = "ALTO (In Losing Streak / Freddo)"
    elif recent_wr >= 70 or (first_res == "WIN" and streak_count >= 3):
        tilt_risk = "MOLTO BASSO (In Win Streak / Caldo)"
    elif recent_wr >= 50:
        tilt_risk = "Normale / Equilibrato"

    # 5. Determinazione Ruolo Principale ed Secondario (priorità assoluta ai ruoli dichiarati tra [])
    if declared_roles and len(declared_roles) > 0:
        primary_role = declared_roles[0]
        secondary_role = ", ".join(declared_roles[1:]) if len(declared_roles) > 1 else "Nessuno (Specializzato)"
    else:
        role_counts = {}
        for c in champions:
            r = c["role"]
            role_counts[r] = role_counts.get(r, 0) + c["play"]
        for m in recent_matches:
            c_meta = get_champion_meta(m.get("champion", ""))
            r = c_meta["role"]
            role_counts[r] = role_counts.get(r, 0) + 1

        sorted_roles = sorted(role_counts.items(), key=lambda x: x[1], reverse=True)
        primary_role = sorted_roles[0][0] if sorted_roles else "Flessibile"
        secondary_role = sorted_roles[1][0] if len(sorted_roles) > 1 else "Autofill"

    # 6. Analisi Sindrome OTP
    otp_status = "Pool Bilanciata"
    if champions:
        top_share = champions[0]["pool_share"]
        if top_share >= 60:
            otp_status = f"SINDROME OTP CRITICA ({champions[0]['name']} al {top_share}%)"
        elif top_share >= 40:
            otp_status = f"Semi-OTP / Forte Comfort ({champions[0]['name']} al {top_share}%)"
        else:
            otp_status = f"Pool Ampia (Top pick: {champions[0]['name']} al {top_share}%)"

    # 7. Profilo Danno Globale
    ap_games = sum(c["play"] for c in champions if "AP" in c["dmg"])
    ad_games = sum(c["play"] for c in champions if "AD" in c["dmg"] and "AP" not in c["dmg"])
    tank_games = sum(c["play"] for c in champions if "Tank" in c["dmg"] or "Tank" in c["class"])

    tot_g = max(ap_games + ad_games + tank_games, 1)
    if ap_games / tot_g >= 0.65:
        overall_damage = "Heavy AP (Sbilanciato su Danni Magici)"
    elif ad_games / tot_g >= 0.65:
        overall_damage = "Heavy AD (Sbilanciato su Danni Fisici)"
    elif tank_games / tot_g >= 0.50:
        overall_damage = "Tank / Frontline Heavy"
    else:
        overall_damage = "Ibrido / Bilanciato (AD + AP)"

    # 8. Livello Evocatore
    level_m = re.search(r'level["\']?\s*:\s*(\d+)', html_content, re.IGNORECASE) or re.search(r'Lv\.\s*(\d+)', html_content)
    level = int(level_m.group(1)) if level_m else 0
    if level == 0:
        try:
            from lol_scraper import LoLScraper
            _sc = LoLScraper()
            _b = _sc.get_player_info(name, tag, region)
            level = _b.get("level", 0)
        except Exception:
            pass

    return {
        "riot_id": f"{name}#{tag}",
        "name": name,
        "tag": tag,
        "region": region.upper(),
        "level": level,
        "solo_rank": solo_rank,
        "solo_lp": solo_lp,
        "solo_wins": solo_wins,
        "solo_losses": solo_losses,
        "solo_wr": solo_wr,
        "total_ranked_games": solo_wins + solo_losses,
        "primary_role": primary_role,
        "secondary_role": secondary_role,
        "otp_status": otp_status,
        "overall_damage": overall_damage,
        "recent_wr": recent_wr,
        "recent_streak": streak_type,
        "tilt_risk": tilt_risk,
        "champions": champions,
        "recent_matches": recent_matches,
        "declared_roles": declared_roles or []
    }


def generate_scouting_suite(input_file: str, output_dir: str = "output", region: str = "euw"):
    os.makedirs(output_dir, exist_ok=True)
    players_list = parse_input_file(input_file)

    if not players_list:
        print(f"[!] Nessun giocatore trovato nel file '{input_file}'.")
        return

    print(f"\n========================================================")
    print(f"  AVVIO SCOUTING SUITE PROFESSIONALE: LEAGUE OF LEGENDS")
    print(f"  Giocatori identificati: {len(players_list)} | Regione: {region.upper()}")
    print(f"  Cartella di destinazione: {output_dir}/")
    print(f"========================================================\n")

    client = httpx.Client(follow_redirects=True, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }, timeout=15.0)

    roster_data = []
    for idx, (name, tag, declared_roles) in enumerate(players_list, 1):
        role_label = f" [{', '.join(declared_roles)}]" if declared_roles else ""
        print(f"[{idx}/{len(players_list)}] Analisi avanzata: {name}#{tag}{role_label} ... ", end="", flush=True)
        try:
            data = fetch_player_scouting_data(client, name, tag, region, declared_roles=declared_roles)
            roster_data.append(data)
            print(f"OK ({data['solo_rank']} | Ruolo: {data['primary_role']} | Top Pick: {data['champions'][0]['name'] if data['champions'] else 'N/A'})")
        except Exception as e:
            print(f"ERRORE ({e})")

    if not roster_data:
        print("[!] Nessun dato raccolto.")
        return

    # Risoluzione distribuzione obbligatoria dei 5 ruoli (almeno 1 per ruolo)
    lineup_assigned, reserves = assign_optimal_lineup(roster_data)
    print("\n--- DISTRIBUZIONE SQUADRA GARANTITA (5 RUOLI UFFICIALI) ---")
    for r in STANDARD_ROLES:
        p_assigned = lineup_assigned.get(r)
        if p_assigned:
            print(f"  [{r:7}] -> {p_assigned['riot_id']} (Ruoli File: {p_assigned.get('declared_roles', [])})")
    if reserves:
        print(f"  [RISERVE] -> {', '.join(p['riot_id'] for p in reserves)}")
    print("-----------------------------------------------------------\n")

    # ----------------------------------------------------
    # 1. OUTPUT: 01_roster_overview.csv
    # ----------------------------------------------------
    f1_path = os.path.join(output_dir, "01_roster_overview.csv")
    f1_fields = [
        "Riot_ID", "Livello", "Ruolo_Lineup_Titolare", "Ruolo_Principale", "Ruolo_Secondario", "Ruoli_Dichiarati_File",
        "SoloQ_Rank", "SoloQ_LP", "SoloQ_Winrate_%", "SoloQ_Partite_Totali",
        "Top_Comfort_Picks", "Sindrome_OTP", "Profilo_Danno_Prevalente",
        "Forma_Recente_10_Games", "Serie_Attuale", "Rischio_Tilt_Mentalita"
    ]
    with open(f1_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=f1_fields, delimiter=";")
        w.writeheader()
        for p in roster_data:
            comfort_list = [f"{c['name']} ({c['winrate']}% WR su {c['play']}g)" for c in p["champions"] if c["winrate"] >= 52][:3]
            titolare_role = p.get("assigned_team_role", "NON ASSEGNATO")
            w.writerow({
                "Riot_ID": p["riot_id"],
                "Livello": p["level"],
                "Ruolo_Lineup_Titolare": f"TITOLARE: {titolare_role}" if titolare_role in STANDARD_ROLES else titolare_role,
                "Ruolo_Principale": p["primary_role"],
                "Ruolo_Secondario": p["secondary_role"],
                "Ruoli_Dichiarati_File": ", ".join(p["declared_roles"]) if p["declared_roles"] else "Non specificati (Rilevati da stats)",
                "SoloQ_Rank": p["solo_rank"],
                "SoloQ_LP": p["solo_lp"],
                "SoloQ_Winrate_%": p["solo_wr"],
                "SoloQ_Partite_Totali": p["total_ranked_games"],
                "Top_Comfort_Picks": ", ".join(comfort_list) if comfort_list else "Nessuno sopra 52% WR",
                "Sindrome_OTP": p["otp_status"],
                "Profilo_Danno_Prevalente": p["overall_damage"],
                "Forma_Recente_10_Games": f"{p['recent_wr']}% Winrate",
                "Serie_Attuale": p["recent_streak"],
                "Rischio_Tilt_Mentalita": p["tilt_risk"]
            })

    # ----------------------------------------------------
    # 2. OUTPUT: 02_champion_pool_analitica.csv
    # ----------------------------------------------------
    f2_path = os.path.join(output_dir, "02_champion_pool_analitica.csv")
    f2_fields = [
        "Riot_ID", "Campione", "Ruolo_Tipico", "Profilo_Danno", "Classe_Campione",
        "Partite_Giocate", "Vittorie", "Sconfitte", "Winrate_%", "Quota_Pool_%",
        "Categoria_Scouting", "First_Pick_Viability"
    ]
    with open(f2_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=f2_fields, delimiter=";")
        w.writeheader()
        for p in roster_data:
            for c in p["champions"]:
                # Classificazione scouting
                if c["play"] >= 15 and c["winrate"] >= 55:
                    cat = "COMFORT PICK ASSOLUTO (Da Bannare / Giocare)"
                elif c["winrate"] >= 52:
                    cat = "PICK SOLIDO / AFFIDABILE"
                elif c["play"] >= 15 and c["winrate"] < 45:
                    cat = "TRAP PICK / VULNERABILE (Lasciaglielo!)"
                elif c["winrate"] < 45:
                    cat = "SOTTO MEDIA / POCO EFFICACE"
                else:
                    cat = "PICK MEDIANO / SITUAZIONALE"

                w.writerow({
                    "Riot_ID": p["riot_id"],
                    "Campione": c["name"],
                    "Ruolo_Tipico": c["role"],
                    "Profilo_Danno": c["dmg"],
                    "Classe_Campione": c["class"],
                    "Partite_Giocate": c["play"],
                    "Vittorie": c["wins"],
                    "Sconfitte": c["losses"],
                    "Winrate_%": c["winrate"],
                    "Quota_Pool_%": c["pool_share"],
                    "Categoria_Scouting": cat,
                    "First_Pick_Viability": c["first_pick"]
                })

    # ----------------------------------------------------
    # 3. OUTPUT: 03_in_game_playstyle_metrics.csv
    # ----------------------------------------------------
    f3_path = os.path.join(output_dir, "03_in_game_playstyle_metrics.csv")
    f3_fields = [
        "Riot_ID", "Ruolo_Principale", "Flessibilita_AD_AP", "Comfort_vs_Meta",
        "Allocazione_Risorse_Macro", "Early_Game_Aggression",
        "Rapporto_Danno_e_Teamfight", "Vulnerabilita_Gank_Camping"
    ]
    with open(f3_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=f3_fields, delimiter=";")
        w.writeheader()
        for p in roster_data:
            # Flessibilità
            has_ap = any("AP" in c["dmg"] and c["winrate"] >= 50 for c in p["champions"])
            has_ad = any("AD" in c["dmg"] and c["winrate"] >= 50 for c in p["champions"])
            has_tank = any("Tank" in c["class"] and c["winrate"] >= 50 for c in p["champions"])
            
            if has_ap and has_ad:
                flex_str = "Alta (Gioca con successo sia AP che AD)"
            elif has_tank and (has_ad or has_ap):
                flex_str = "Ottima (Alterna Carry a Frontline/Tank)"
            elif has_ap:
                flex_str = "Rigido (Forte solo su pick AP)"
            elif has_ad:
                flex_str = "Rigido (Forte solo su pick AD)"
            else:
                flex_str = "Media / Specializzato"

            # Comfort vs Meta
            top_champ_share = p["champions"][0]["pool_share"] if p["champions"] else 0
            if top_champ_share >= 40:
                cvs_meta = "Comfort Player (Focalizzato sui propri pick, ignora il meta)"
            else:
                cvs_meta = "Meta Slave / Adattabile (Spalma partite su più pick)"

            # Allocazione Risorse (Strongside vs Weakside)
            role = p["primary_role"].upper()
            if any(k in role for k in ["ADC", "MID"]):
                resources = "Strongside Priority (Ha bisogno di farm, protezione e visione per carriare)"
                early_aggro = "Lane Dominant / Cerca Trade e Vantaggio di CS"
                dmg_tf = "Primary Damage Dealer (Priorità assoluta nei teamfight)"
                gank_vuln = "ALTA (Bersaglio ideale se gioca champion senza dash)"
            elif "TOP" in role:
                if has_tank:
                    resources = "Weakside Friendly (Può assorbire pressione sotto torre e rendersi utile con TP)"
                    early_aggro = "Paziente / Gestione ondate e scaling"
                    dmg_tf = "Frontline / Disruption / Engage"
                    gank_vuln = "Bassa (Resistente ai dive)"
                else:
                    resources = "Isolamento / Splitpush (Spinge la lane e forza rotazioni)"
                    early_aggro = "Aggressivo 1v1 in corsia"
                    dmg_tf = "Flanker / Duellante"
                    gank_vuln = "Media-Alta (Vulnerabile se overextende)"
            elif "JUNGLE" in role:
                resources = "Tempo / Controllo Obiettivi (Richiede lane con priorità)"
                early_aggro = "Invadi / Pressione varchi neutrali"
                dmg_tf = "Initiator / Burst Execution"
                gank_vuln = "Media"
            else: # SUPPORT
                resources = "Low Economy / Playmaker (Non ruba risorse al team)"
                early_aggro = "Roaming / Vision Setup per il bot lane"
                dmg_tf = "Crowd Control / Peel / Protezione backline"
                gank_vuln = "Bassa"

            w.writerow({
                "Riot_ID": p["riot_id"],
                "Ruolo_Principale": p["primary_role"],
                "Flessibilita_AD_AP": flex_str,
                "Comfort_vs_Meta": cvs_meta,
                "Allocazione_Risorse_Macro": resources,
                "Early_Game_Aggression": early_aggro,
                "Rapporto_Danno_e_Teamfight": dmg_tf,
                "Vulnerabilita_Gank_Camping": gank_vuln
            })

    # ----------------------------------------------------
    # 4. OUTPUT: 04_scouting_report_tattico.csv
    # ----------------------------------------------------
    f4_path = os.path.join(output_dir, "04_scouting_report_tattico.csv")
    f4_fields = [
        "Riot_ID", "Ruolo_Titolare_Lineup", "Ruolo_SoloQ", "TARGET_BAN_CHIRURGICI", "NON_BANNARE_LASCIARE_OPEN",
        "PUNTI_DI_FORZA_CHIAVE", "DEBOLEZZE_SFRUTTABILI",
        "COME_GIOCARE_CON_LUI", "COME_GIOCARE_CONTRO_DI_LUI", "STATO_MENTALE_E_TILT"
    ]
    with open(f4_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=f4_fields, delimiter=";")
        w.writeheader()
        for p in roster_data:
            # Target Bans: campioni con più partite e WR >= 55%
            bans = [c["name"] for c in p["champions"] if c["winrate"] >= 54 and c["play"] >= 10]
            if not bans:
                bans = [c["name"] for c in p["champions"] if c["winrate"] >= 52][:2]

            # Traps da NON bannare: campioni con tante partite ma WR < 48%
            traps = [c["name"] for c in p["champions"] if c["winrate"] < 48 and c["play"] >= 10]
            if not traps:
                traps = [c["name"] for c in p["champions"] if c["winrate"] < 48][:2]

            # Analisi punti di forza / debolezza
            top_c = p["champions"][0]["name"] if p["champions"] else "Campione"
            strengths = f"Altissima confidenza su {top_c}. Solido in teamfight quando gioca i suoi comfort pick."
            weaknesses = f"Se gli rimuovi i comfort pick ({', '.join(bans[:2])}), il suo rendimento cala nettamente."

            if "Heavy AP" in p["overall_damage"]:
                weaknesses += " Prevedibile: drafta quasi esclusivamente campioni magici (facilmente counterabile con Magic Resist)."
            elif "Heavy AD" in p["overall_damage"]:
                weaknesses += " Prevedibile: drafta quasi esclusivamente campioni fisici (counterabile con Armatura/Plated Steelcaps)."

            con_lui = f"Dagli in mano un comfort pick ({top_c}) e offrigli visione sul lato della mappa in cui gioca."
            contro_di_lui = f"Target ban prioritario: {', '.join(bans[:2]) if bans else top_c}. Se gioca {', '.join(traps[:2]) if traps else 'un pick secondario'}, lascialo fare: ha un basso winrate."
            
            titolare = p.get("assigned_team_role", p["primary_role"])

            w.writerow({
                "Riot_ID": p["riot_id"],
                "Ruolo_Titolare_Lineup": titolare,
                "Ruolo_SoloQ": p["primary_role"],
                "TARGET_BAN_CHIRURGICI": ", ".join(bans[:2]) if bans else f"{top_c} (Comfort)",
                "NON_BANNARE_LASCIARE_OPEN": ", ".join(traps[:2]) if traps else "Nessun trap critico",
                "PUNTI_DI_FORZA_CHIAVE": strengths,
                "DEBOLEZZE_SFRUTTABILI": weaknesses,
                "COME_GIOCARE_CON_LUI": con_lui,
                "COME_GIOCARE_CONTRO_DI_LUI": contro_di_lui,
                "STATO_MENTALE_E_TILT": f"{p['tilt_risk']} | Ultimi 10 match: {p['recent_streak']}"
            })

    # ----------------------------------------------------
    # 5. OUTPUT: 05_sinergie_squadra.csv
    # ----------------------------------------------------
    f5_path = os.path.join(output_dir, "05_sinergie_squadra.csv")
    f5_fields = [
        "Ruolo_Tattico",
        "Stato_Copertura",
        "Giocatore_Titolare",
        "Motivazione_Assegnazione",
        "Comfort_Pick_Migliore_Ruolo",
        "Tipo_Danno",
        "Tendenza_Risorse",
        "Sinergia_Ideale_Corsia",
        "Raccomandazione_Draft_Squadra",
        "Alternative_Flex_in_Squadra"
    ]
    with open(f5_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=f5_fields, delimiter=";")
        w.writeheader()
        
        # 1. Copertura obbligatoria dei 5 ruoli (almeno 1 giocatore per ciascuno dei 5 ruoli ufficiali)
        for r in STANDARD_ROLES:
            p = lineup_assigned.get(r)
            if p:
                best_c = get_best_champion_for_role(p, r)
                c_meta = get_champion_meta(best_c["name"])

                decl = p.get("declared_roles", [])
                if r in decl:
                    idx = decl.index(r)
                    if idx == 0:
                        reason = f"Ruolo Primario Dichiarato nel file [{r}]"
                    else:
                        reason = f"Ruolo Dichiarato [{r}] (Ottimizzazione globale squadra)"
                else:
                    role_champs = [c for c in p.get("champions", []) if champion_matches_role(c.get("role", ""), r)]
                    if role_champs:
                        reason = f"Miglior rendimento statistico nel ruolo ({best_c['name']} {best_c['winrate']}% WR su {best_c['play']}g)"
                    else:
                        reason = f"Assegnazione tattica per bilanciamento della squadra (Autofill ottimale)"

                # Identifica alternative flex all'interno del roster
                flex_others = []
                for other_p in roster_data:
                    if other_p["riot_id"] != p["riot_id"]:
                        if r in other_p.get("declared_roles", []) or any(champion_matches_role(c.get("role", ""), r) for c in other_p.get("champions", [])):
                            flex_others.append(other_p["riot_id"].split("#")[0])
                flex_str = ", ".join(flex_others) if flex_others else "Nessuna alternativa diretta (Unico specialista)"

                if r == "TOP":
                    sinergia = "Midlaner/Jungler con priorità per convergere su Araldo/Voidgrubs; TP pronto per draghi 3 e 4"
                    draft_rec = "Se gioca tank (es. Ornn/Malphite) fa da perno frontline e assorbe weakside; se gioca duellante richiede visione profonda."
                    tendenza = "Weakside / Frontline / Splitpush"
                elif r == "JUNGLE":
                    sinergia = "Sololaner con priorità di spinta (Mid/Top) per invadere, contestare scuttle e voidgrubs"
                    draft_rec = "Perno assoluto della macro early game: vietato lasciarlo isolato negli invasi neutrali."
                    tendenza = "Controllo Obiettivi / Tempo di Corsia"
                elif r == "MID":
                    sinergia = "Jungler aggressivo con hard CC (es. Sejuani, Vi, Xin Zhao) per gank letali 2v2 e rotazioni laterali"
                    draft_rec = "Fornisce burst e waveclear rapido. Assicurarsi che il team abbia danno misto (AD/AP) distribuito."
                    tendenza = "Strongside Priority (Controllo mappa e rotazioni)"
                elif r == "ADC":
                    sinergia = "Support engage per kill pressure (Nautilus, Blitzcrank) o Enchanter con forte disengage (Lulu, Janna)"
                    draft_rec = "Fonte primaria di DPS continuo nei teamfight di late game: draftare peel e prima linea protettiva."
                    tendenza = "Strongside Priority (Risorse farm e protezione totale)"
                else: # SUPPORT
                    sinergia = "ADC con forte follow-up sul CC; roaming coordinato con il Jungler per vision deep"
                    draft_rec = "Controlla la visione intorno a Drago e Baron: preparare i varchi prima dello spawn."
                    tendenza = "Low Economy / Playmaker & Visione Mappa"

                w.writerow({
                    "Ruolo_Tattico": r,
                    "Stato_Copertura": "COPERTO (Titolare Assegnato)",
                    "Giocatore_Titolare": p["riot_id"],
                    "Motivazione_Assegnazione": reason,
                    "Comfort_Pick_Migliore_Ruolo": f"{best_c['name']} ({best_c['winrate']}% WR su {best_c['play']}g)",
                    "Tipo_Danno": best_c.get("dmg", c_meta.get("dmg", "AD/AP")),
                    "Tendenza_Risorse": tendenza,
                    "Sinergia_Ideale_Corsia": sinergia,
                    "Raccomandazione_Draft_Squadra": draft_rec,
                    "Alternative_Flex_in_Squadra": flex_str
                })
            else:
                # Ruolo scoperto (se roster < 5)
                w.writerow({
                    "Ruolo_Tattico": r,
                    "Stato_Copertura": "SCOPERTO / DA RECLUTARE (Meno di 5 giocatori nel roster)",
                    "Giocatore_Titolare": "NESSUNO",
                    "Motivazione_Assegnazione": "Mancanza di giocatori nel file per completare i 5 ruoli ufficiali",
                    "Comfort_Pick_Migliore_Ruolo": "N/A",
                    "Tipo_Danno": "N/A",
                    "Tendenza_Risorse": "N/A",
                    "Sinergia_Ideale_Corsia": "Ruolo critico mancante",
                    "Raccomandazione_Draft_Squadra": f"Reclutare o assegnare un giocatore al ruolo di {r}.",
                    "Alternative_Flex_in_Squadra": "N/A"
                })

        # 2. Scrittura eventuali riserve / panchinari (se presenti più di 5 giocatori)
        for res in reserves:
            best_r = res.get("assigned_team_role", "RISERVA").replace("RISERVA (", "").replace(")", "").strip()
            if best_r not in STANDARD_ROLES:
                best_r = STANDARD_ROLES[0]
            best_c = get_best_champion_for_role(res, best_r)
            c_meta = get_champion_meta(best_c["name"])
            decl_s = ", ".join(res.get("declared_roles", [])) or "Rilevati da SoloQ"
            w.writerow({
                "Ruolo_Tattico": f"PANCHINA / RISERVA ({best_r})",
                "Stato_Copertura": "RISERVA A DISPOSIZIONE",
                "Giocatore_Titolare": res["riot_id"],
                "Motivazione_Assegnazione": f"Sesto giocatore / Sostituto flessibile per {best_r} (Ruoli: {decl_s})",
                "Comfort_Pick_Migliore_Ruolo": f"{best_c['name']} ({best_c['winrate']}% WR su {best_c['play']}g)",
                "Tipo_Danno": best_c.get("dmg", c_meta.get("dmg", "AD/AP")),
                "Tendenza_Risorse": "Flessibile / Sostituto",
                "Sinergia_Ideale_Corsia": f"Pronto a subentrare in {best_r} in caso di indisponibilità o rotazione tattica.",
                "Raccomandazione_Draft_Squadra": "Opzione tattica per sorprendere la draft avversaria.",
                "Alternative_Flex_in_Squadra": "Riserva"
            })

    print(f"\n[OK] SCOUTING COMPLETATO CON SUCCESSO!")
    print(f"I seguenti file sono stati creati in '{output_dir}/':")
    print(f"  1. {f1_path} (Panoramica Generale)")
    print(f"  2. {f2_path} (Analisi Dettagliata Champion Pool)")
    print(f"  3. {f3_path} (Metriche Stile di Gioco In-Game)")
    print(f"  4. {f4_path} (Scheda Tattica: Target Ban, Con Lui, Contro di Lui)")
    print(f"  5. {f5_path} (Sinergie e Bilanciamento Team)")

def main():
    parser = argparse.ArgumentParser(description="Advanced LoL Scouting Suite")
    parser.add_argument("-i", "--input", default="giocatori.md", help="File di input con giocatori (default: giocatori.md)")
    parser.add_argument("-o", "--output-dir", default="output", help="Cartella di output per i file CSV (default: output)")
    parser.add_argument("-r", "--region", default="euw", help="Regione (default: euw)")
    args = parser.parse_args()

    generate_scouting_suite(args.input, args.output_dir, args.region)

if __name__ == "__main__":
    main()

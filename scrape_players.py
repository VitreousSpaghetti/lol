"""
Batch LoL Player Scraper
========================
Legge un file di input (markdown o testo) contenente un elenco di giocatori
formattati come Riot ID (es: - Nome#Tag oppure Nome#Tag) ed esporta tutte le loro
statistiche aggiornate in un file CSV.

Uso:
    python scrape_players.py
    python scrape_players.py --input giocatori.md --output statistiche_giocatori.csv --region euw
"""

import os
import sys
import re
import csv
import argparse
from typing import List, Tuple, Dict, Any
from lol_scraper import LoLScraper

# Assicura compatibilità con la console Windows (evita UnicodeEncodeError su cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def parse_players_from_file(filepath: str) -> List[Tuple[str, str]]:
    """
    Legge un file di testo/markdown ed estrae le coppie (GameName, TagLine).
    Supporta elenchi puntati (-, *), numerati o righe semplici.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File di input non trovato: {filepath}")

    players = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # Ignora righe vuote o commenti diretti (# o //)
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # Rimuove marcatori di lista all'inizio (es: "- ", "* ", "1. ")
            cleaned = re.sub(r"^[-*•\d.]+\s*", "", line).strip()
            
            # Ignora se la riga commentata era preceduta da un bullet (es: "- # Giocatore" o "-# Giocatore")
            if not cleaned or cleaned.startswith("#") or cleaned.startswith("//"):
                continue

            # Rimuove eventuali ruoli tra parentesi quadre [...]
            cleaned = re.sub(r'\[.*?\]', '', cleaned).strip()

            if "#" in cleaned:
                parts = cleaned.split("#", 1)
                name = parts[0].strip()
                tag = parts[1].strip()
                if name and tag:
                    players.append((name, tag))
            else:
                print(f"[!] Riga {line_num} ignorata (nessun tag '#' trovato): {line}")

    return players

def extract_queue_stats(ranked_stats: List[Dict[str, Any]], queue_name: str) -> Dict[str, Any]:
    """Estrae i dati di una specifica coda (SOLORANKED o FLEXRANKED)"""
    for stat in ranked_stats:
        if stat.get("queue") == queue_name:
            return {
                "tier": stat.get("tier", "UNRANKED"),
                "division": stat.get("division", ""),
                "lp": stat.get("lp", 0),
                "wins": stat.get("wins", 0),
                "losses": stat.get("losses", 0),
                "winrate": stat.get("winrate", 0.0)
            }
    return {
        "tier": "UNRANKED",
        "division": "",
        "lp": 0,
        "wins": 0,
        "losses": 0,
        "winrate": 0.0
    }

def scrape_players_to_csv(input_path: str, output_path: str, region: str = "euw"):
    scraper = LoLScraper()
    players = parse_players_from_file(input_path)

    if not players:
        print("[!] Nessun giocatore valido trovato nel file di input.")
        return

    print(f"\n[+] Trovati {len(players)} giocatori in '{input_path}'. Inizio scraping (Regione: {region.upper()})...\n")

    fieldnames = [
        "Riot_ID",
        "Game_Name",
        "Tag_Line",
        "Region",
        "Level",
        "SoloQ_Tier",
        "SoloQ_Division",
        "SoloQ_LP",
        "SoloQ_Wins",
        "SoloQ_Losses",
        "SoloQ_Winrate_%",
        "Flex_Tier",
        "Flex_Division",
        "Flex_LP",
        "Flex_Wins",
        "Flex_Losses",
        "Flex_Winrate_%",
        "Status"
    ]

    rows = []
    for idx, (name, tag) in enumerate(players, 1):
        full_id = f"{name}#{tag}"
        print(f"[{idx}/{len(players)}] Analisi: {full_id} ... ", end="", flush=True)

        try:
            info = scraper.get_player_info(name, tag, region=region)
            ranked_list = info.get("ranked", [])

            solo_stats = extract_queue_stats(ranked_list, "SOLORANKED")
            flex_stats = extract_queue_stats(ranked_list, "FLEXRANKED")

            rows.append({
                "Riot_ID": info.get("riot_id", full_id),
                "Game_Name": name,
                "Tag_Line": tag,
                "Region": region.upper(),
                "Level": info.get("level", 0),
                "SoloQ_Tier": solo_stats["tier"],
                "SoloQ_Division": solo_stats["division"],
                "SoloQ_LP": solo_stats["lp"],
                "SoloQ_Wins": solo_stats["wins"],
                "SoloQ_Losses": solo_stats["losses"],
                "SoloQ_Winrate_%": solo_stats["winrate"],
                "Flex_Tier": flex_stats["tier"],
                "Flex_Division": flex_stats["division"],
                "Flex_LP": flex_stats["lp"],
                "Flex_Wins": flex_stats["wins"],
                "Flex_Losses": flex_stats["losses"],
                "Flex_Winrate_%": flex_stats["winrate"],
                "Status": "OK"
            })
            print(f"OK (Livello: {info.get('level')} | Solo: {solo_stats['tier']} {solo_stats['division']} | Flex: {flex_stats['tier']} {flex_stats['division']})")

        except Exception as e:
            print(f"ERRORE ({e})")
            rows.append({
                "Riot_ID": full_id,
                "Game_Name": name,
                "Tag_Line": tag,
                "Region": region.upper(),
                "Level": 0,
                "SoloQ_Tier": "ERROR",
                "SoloQ_Division": "",
                "SoloQ_LP": 0,
                "SoloQ_Wins": 0,
                "SoloQ_Losses": 0,
                "SoloQ_Winrate_%": 0.0,
                "Flex_Tier": "ERROR",
                "Flex_Division": "",
                "Flex_LP": 0,
                "Flex_Wins": 0,
                "Flex_Losses": 0,
                "Flex_Winrate_%": 0.0,
                "Status": f"ERROR: {str(e)}"
            })

    # Scrittura su file CSV (con encoding utf-8-sig per massima compatibilità con Excel)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[OK] Completato con successo! Dati salvati in: '{output_path}'")

def main():
    parser = argparse.ArgumentParser(
        description="Scraping batch di profili League of Legends da file di testo/markdown a CSV"
    )
    parser.add_argument(
        "-i", "--input",
        default="giocatori.md",
        help="Percorso del file di input (default: giocatori.md)"
    )
    parser.add_argument(
        "-o", "--output",
        default="giocatori_output.csv",
        help="Percorso del file CSV di output (default: giocatori_output.csv)"
    )
    parser.add_argument(
        "-r", "--region",
        default="euw",
        help="Regione LoL dei giocatori (default: euw)"
    )

    args = parser.parse_args()
    scrape_players_to_csv(args.input, args.output, args.region)

if __name__ == "__main__":
    main()

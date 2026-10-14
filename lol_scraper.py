"""
LoL Scraper & Data Extractor
============================
Modulo per l'estrazione in tempo reale di:
1. Build contemporanee (oggetti core, scarpe, start, rune, ordine abilità)
2. Informazioni e statistiche giocatori (Rank, Tier, LP, Winrate, Livello) su regione EUW (o altre)

Basato sull'interfaccia ad alte prestazioni Streamable HTTP di OP.GG (nessun ban Cloudflare, nessun browser headless pesante).
"""

import sys
import re
import argparse
import httpx
from typing import Dict, Any, Optional

class LoLScraper:
    MCP_ENDPOINT = "https://mcp-api.op.gg/mcp"

    def __init__(self, timeout: float = 10.0):
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.client = httpx.Client(headers=self.headers, timeout=timeout)

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Invia una chiamata RPC al server MCP di OP.GG"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        response = self.client.post(self.MCP_ENDPOINT, json=payload)
        response.raise_for_status()
        res_json = response.json()
        
        if "error" in res_json:
            raise RuntimeError(f"Errore API OP.GG: {res_json['error']}")
            
        content = res_json.get("result", {}).get("content", [])
        if not content or "text" not in content[0]:
            raise ValueError("Risposta inattesa o vuota dal server")
            
        return content[0]["text"]

    def _parse_dsl_to_dict(self, raw_dsl: str, root_class_name: str) -> Dict[str, Any]:
        """Converte il formato pseudo-classi compatto restituito da OP.GG in dizionario Python"""
        # Trova la riga dell'istanza principale
        instance_lines = [line for line in raw_dsl.split("\n") if line.startswith(root_class_name)]
        if not instance_lines:
            raise ValueError(f"Nessuna istanza trovata per {root_class_name}")
        instance_line = instance_lines[0]

        # Mappatura definizioni classi
        class_defs = {}
        for line in raw_dsl.split("\n"):
            if line.startswith("class "):
                parts = line[6:].split(":")
                if len(parts) == 2:
                    cname = parts[0].strip()
                    fields = [f.strip() for f in parts[1].split(",") if f.strip()]
                    class_defs[cname] = fields

        class Node:
            def __init__(self, cls_name):
                self._cls_name = cls_name
                self._args = []
            def set_args(self, *args):
                self._args = args
                return self
            def __repr__(self):
                return f"{self._cls_name}{self._args}"

        ns = {"null": None, "true": True, "false": False}
        for cls in re.findall(r"class (\w+):", raw_dsl):
            # Crea un costruttore che assegna il nome classe
            ns[cls] = lambda *args, c=cls: Node(c).set_args(*args)

        root_node = eval(instance_line, {"__builtins__": {}}, ns)

        def node_to_dict(val):
            if isinstance(val, Node):
                fields = class_defs.get(val._cls_name, [])
                res = {}
                for idx, arg in enumerate(val._args):
                    fname = fields[idx] if idx < len(fields) else f"field_{idx}"
                    res[fname] = node_to_dict(arg)
                return res
            elif isinstance(val, list):
                return [node_to_dict(item) for item in val]
            return val

        return node_to_dict(root_node)

    def get_player_info(self, game_name: str, tag_line: str, region: str = "euw") -> Dict[str, Any]:
        """
        Recupera il profilo di un giocatore conoscendo Nome e Tag su regione EUW (o altra).
        """
        args = {
            "game_name": game_name,
            "tag_line": tag_line,
            "region": region.lower(),
            "desired_output_fields": [
                "data.summoner.{game_name,tagline,level}",
                "data.summoner.league_stats[].{game_type,win,lose}",
                "data.summoner.league_stats[].tier_info.{tier,division,lp}"
            ]
        }
        raw_text = self._call_tool("lol_get_summoner_profile", args)
        parsed = self._parse_dsl_to_dict(raw_text, "LolGetSummonerProfile")
        
        summoner = parsed.get("data", {}).get("summoner", {})
        ranked_stats = []
        for stat in summoner.get("league_stats", []):
            tier_info = stat.get("tier_info", {})
            tier = tier_info.get("tier")
            if not tier:
                continue
            wins = stat.get("win", 0) or 0
            losses = stat.get("lose", 0) or 0
            total = wins + losses
            winrate = round((wins / total) * 100, 1) if total > 0 else 0.0
            ranked_stats.append({
                "queue": stat.get("game_type"),
                "tier": tier,
                "division": tier_info.get("division"),
                "lp": tier_info.get("lp"),
                "wins": wins,
                "losses": losses,
                "winrate": winrate
            })

        return {
            "riot_id": f"{summoner.get('game_name', game_name)}#{summoner.get('tagline', tag_line)}",
            "region": region.upper(),
            "level": summoner.get("level"),
            "ranked": ranked_stats
        }

    def get_champion_build(self, champion: str, position: str = "mid", game_mode: str = "ranked") -> Dict[str, Any]:
        """
        Recupera la build contemporanea più performante per un campione.
        position: 'top', 'jungle', 'mid', 'adc', 'support'
        """
        args = {
            "champion": champion.lower(),
            "position": position.lower(),
            "game_mode": game_mode.lower(),
            "desired_output_fields": [
                "data.core_items[].{ids_names,win,pick_rate}",
                "data.boots[].{ids_names,win,pick_rate}",
                "data.starter_items[].{ids_names,win,pick_rate}",
                "data.runes[].{primary_page_name,primary_rune_names,secondary_page_name,secondary_rune_names,win,pick_rate}",
                "data.skills[].{order,win,pick_rate}"
            ]
        }
        raw_text = self._call_tool("lol_get_champion_analysis", args)
        parsed = self._parse_dsl_to_dict(raw_text, "LolGetChampionAnalysis")
        data = parsed.get("data", {})

        # Formatta i dati della build
        core_items = data.get("core_items", {})
        boots = data.get("boots", {})
        starter_items = data.get("starter_items", {})
        runes = data.get("runes", {})
        skills = data.get("skills", {})

        return {
            "champion": champion.capitalize(),
            "position": position.upper(),
            "game_mode": game_mode.capitalize(),
            "starter_items": starter_items.get("ids_names", []),
            "core_items": core_items.get("ids_names", []),
            "boots": boots.get("ids_names", []),
            "runes": {
                "primary": {
                    "tree": runes.get("primary_page_name"),
                    "keystones": runes.get("primary_rune_names", [])
                },
                "secondary": {
                    "tree": runes.get("secondary_page_name"),
                    "runes": runes.get("secondary_rune_names", [])
                }
            },
            "skill_order": skills.get("order", [])
        }


def main():
    parser = argparse.ArgumentParser(description="League of Legends Scraper per Build e Giocatori EUW")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando player
    p_player = subparsers.add_parser("player", help="Ottieni informazioni su un giocatore")
    p_player.add_argument("riot_id", help="Riot ID nel formato Nome#Tag (es: Kaori#EUW33 o 'Spear Shot#1111')")
    p_player.add_argument("--region", default="euw", help="Regione (default: euw)")

    # Subcomando build
    p_build = subparsers.add_parser("build", help="Ottieni la build contemporanea per un campione")
    p_build.add_argument("champion", help="Nome del campione (es: Ahri, Aatrox, Jinx)")
    p_build.add_argument("--position", default="mid", choices=["top", "jungle", "mid", "adc", "support"], help="Ruolo (default: mid)")
    p_build.add_argument("--mode", default="ranked", help="Modalità di gioco (default: ranked)")

    args = parser.parse_args()
    scraper = LoLScraper()

    if args.command == "player":
        if "#" not in args.riot_id:
            print("Errore: specifica il Riot ID nel formato Nome#Tag (es. Faker#KR1 o Kaori#EUW33)")
            sys.exit(1)
        name, tag = args.riot_id.split("#", 1)
        print(f"\n[+] Ricerca giocatore {name}#{tag} su {args.region.upper()}...")
        try:
            info = scraper.get_player_info(name, tag, args.region)
            print("=" * 45)
            print(f"Giocatore: {info['riot_id']} ({info['region']})")
            print(f"Livello  : {info['level']}")
            print("-" * 45)
            if not info["ranked"]:
                print("Nessun rank registrato in coda classificata.")
            else:
                for r in info["ranked"]:
                    div_str = f" {r['division']}" if r['division'] else ""
                    print(f"[{r['queue']}] {r['tier']}{div_str} - {r['lp']} LP")
                    print(f"  Vittorie: {r['wins']} | Sconfitte: {r['losses']} | Winrate: {r['winrate']}%")
            print("=" * 45)
        except Exception as e:
            print(f"Errore durante il recupero del giocatore: {e}")

    elif args.command == "build":
        print(f"\n[+] Recupero build contemporanea per {args.champion} ({args.position.upper()})...")
        try:
            build = scraper.get_champion_build(args.champion, args.position, args.mode)
            print("=" * 45)
            print(f"CAMPIONE: {build['champion']} | RUOLO: {build['position']} ({build['game_mode']})")
            print("=" * 45)
            print(f"Oggetti Iniziali : {', '.join(build['starter_items'])}")
            print(f"Scarpe           : {', '.join(build['boots'])}")
            print(f"Oggetti Core     : {' -> '.join(build['core_items'])}")
            print("-" * 45)
            print(f"Rune Primarie    ({build['runes']['primary']['tree']}):")
            for r in build['runes']['primary']['keystones']:
                print(f"  * {r}")
            print(f"Rune Secondarie  ({build['runes']['secondary']['tree']}):")
            for r in build['runes']['secondary']['runes']:
                print(f"  * {r}")
            print("-" * 45)
            if build['skill_order']:
                print(f"Ordine Abilita    : {' > '.join(build['skill_order'])}")
            print("=" * 45)
        except Exception as e:
            print(f"Errore durante il recupero della build: {e}")

if __name__ == "__main__":
    main()

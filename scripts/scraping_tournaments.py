from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, asdict
import aiohttp
import asyncio
import os
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

base_url = "https://play.limitlesstcg.com"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36'
}

# Dataclasses used for json generation
@dataclass
class DeckListItem:
    type: str
    url: str
    name: str
    count: int

@dataclass
class Player:
    id: str
    name: str
    placing: str
    country: str
    decklist: list

@dataclass
class MatchResult:
    player_id: str
    score: int

@dataclass
class Match:
    match_results: list

@dataclass
class Tournament:
    id: str
    name: str
    date: str
    organizer: str
    format: str
    nb_players: str
    players: list
    matches: list

# Extract the tr tags from a table, omiting the first header
def extract_trs(soup: BeautifulSoup, table_class: str):
    trs = soup.find(class_=table_class).find_all("tr")
    trs.pop(0)  # Remove header
    return trs

# Urls helpers
def construct_standings_url(tournament_id: str):
    return f"/tournament/{tournament_id}/standings?players"

def construct_pairings_url(tournament_id: str):
    return f"/tournament/{tournament_id}/pairings"

def construct_decklist_url(tournament_id: str, player_id: str):
    return f"/tournament/{tournament_id}/player/{player_id}/decklist"

# Extract the previous pairing pages urls
def extract_previous_pairings_urls(pairings: BeautifulSoup):
    pairing_urls = pairings.find(class_="mini-nav")
    if pairing_urls is None:
        return []
    pairing_urls = pairing_urls.find_all("a")
    pairing_urls.pop(-1)  # Remove current page
    pairing_urls = [a.attrs["href"] for a in pairing_urls]
    return pairing_urls

def is_bracket_pairing(pairings: BeautifulSoup):
    return pairings.find("div", class_="live-bracket") is not None

regex_tournament_id = re.compile(r'[a-zA-Z0-9_\-]*')
def is_table_pairing(pairings: BeautifulSoup):
    pairings_div = pairings.find("div", class_="pairings")
    if pairings_div is not None:
        table = pairings_div.find("table", {'data-tournament': regex_tournament_id})
        if table is not None:
            return True
    return False

def extract_matches_from_bracket_pairings(pairings: BeautifulSoup):
    matches = []
    matches_div = pairings.find("div", class_="live-bracket").find_all("div", class_="bracket-match")
    for match in matches_div:
        if match.find("a", class_="bye") is not None:
            continue
        players_div = match.find_all("div", class_="live-bracket-player")
        match_results = []
        for player in players_div:
            match_results.append(MatchResult(
                player.attrs["data-id"],
                int(player.find("div", class_="score").attrs["data-score"])
            ))
        matches.append(Match(match_results))
    return matches

def extract_matches_from_table_pairings(pairings: BeautifulSoup):
    matches = []
    matches_tr = pairings.find_all("tr", {'data-completed': '1'})
    for match in matches_tr:
        p1 = match.find("td", class_="p1")
        p2 = match.find("td", class_="p2")
        if (p1 is not None and p2 is not None):
            matches.append(Match([
                MatchResult(p1.attrs["data-id"], int(p1.attrs["data-count"])),
                MatchResult(p2.attrs["data-id"], int(p2.attrs["data-count"]))
            ]))
    return matches

regex_card_url = re.compile(r'pocket\.limitlesstcg\.com/cards/.*')
def extract_decklist(decklist: BeautifulSoup) -> list:
    decklist_div = decklist.find("div", class_="decklist")
    cards = []
    if decklist_div is not None:
        cards_a = decklist_div.find_all("a", {'href': regex_card_url})
        for card in cards_a:
            cards.append(DeckListItem(
                card.parent.parent.find("div", class_="heading").text.split(" ")[0],
                card.attrs["href"],
                card.text[2:],
                int(card.text[0])
            ))
    return cards

# Extract a beautiful soup object from a url
async def async_soup_from_url(session: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str):
    if url is None:
        return None
    if not url.startswith("http"):
        url = base_url + url
    async with sem:
        async with session.get(url, headers=headers) as resp:
            html = await resp.text()
    return BeautifulSoup(html, 'html.parser')

regex_player_id = re.compile(r'/tournament/[a-zA-Z0-9_\-]*/player/[a-zA-Z0-9_]*')
regex_decklist_url = re.compile(r'/tournament/[a-zA-Z0-9_\-]*/player/[a-zA-Z0-9_]*/decklist')

async def extract_players(session, sem, standings_page, tournament_id):
    async def empty_soup():
        return None

    players = []
    player_trs = extract_trs(standings_page, "striped")
    player_ids = [player_tr.find("a", {'href': regex_player_id}).attrs["href"].split('/')[4] for player_tr in player_trs]
    has_decklist = [player_tr.find("a", {'href': regex_decklist_url}) is not None for player_tr in player_trs]
    player_names = [player_tr.attrs['data-name'] for player_tr in player_trs]
    player_placings = [player_tr.attrs.get("data-placing", -1) for player_tr in player_trs]
    player_countries = [player_tr.attrs.get("data-country", None) for player_tr in player_trs]
    decklist_urls = [construct_decklist_url(tournament_id, pid) if has else None for pid, has in zip(player_ids, has_decklist)]
    player_decklists = await asyncio.gather(
        *[async_soup_from_url(session, sem, url) if url else empty_soup() for url in decklist_urls]
    )
    for i in range(len(player_ids)):
        if player_decklists[i] is None:
            continue
        players.append(Player(
            player_ids[i],
            player_names[i],
            player_placings[i],
            player_countries[i],
            extract_decklist(player_decklists[i])
        ))
    return players

async def extract_matches(session, sem, tournament_id):
    matches = []
    last_pairings = await async_soup_from_url(session, sem, construct_pairings_url(tournament_id))
    previous_pairings_urls = extract_previous_pairings_urls(last_pairings)
    pairings = await asyncio.gather(*[async_soup_from_url(session, sem, url) for url in previous_pairings_urls])
    pairings.append(last_pairings)
    for pairing in pairings:
        if is_bracket_pairing(pairing):
            matches.extend(extract_matches_from_bracket_pairings(pairing))
        elif is_table_pairing(pairing):
            matches.extend(extract_matches_from_table_pairings(pairing))
        else:
            raise Exception("Unrecognized pairing type")
    return matches

async def handle_tournament_standings_page(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    standings_page: BeautifulSoup,
    tournament_id: str, 
    tournament_name: str,
    tournament_date: str,
    tournament_organizer: str,
    tournament_format: str,
    tournament_nb_players: int):

    output_file = f"sample_output/{tournament_id}.json"
    print(f"extracting tournament {tournament_id}", end="... ")

    # If the json file for this tournament already exists, we don't recreate it
    if os.path.isfile(output_file):
        print("skipping because tournament is already in output")
        return
    else:
        directory = os.path.dirname(output_file)
        if not os.path.exists(directory):
            os.makedirs(directory)

    players = await extract_players(session, sem, standings_page, tournament_id)
    if len(players) == 0:
        print("skipping because no decklist was detected")
        return

    nb_decklists = sum(1 for player in players if len(player.decklist) > 0)
    matches = await extract_matches(session, sem, tournament_id)
    tournament = Tournament(
        tournament_id,
        tournament_name,
        tournament_date,
        tournament_organizer,
        tournament_format,
        tournament_nb_players,
        players,
        matches
    )
    print(f"{len(players)} players, {nb_decklists} decklists, {len(matches)} matches")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(asdict(tournament), f, indent=2, ensure_ascii=False)

first_tournament_page = "/tournaments/completed?game=POCKET&format=STANDARD&platform=all&type=online&time=all"
regex_standings_url = re.compile(r'/tournament/[a-zA-Z0-9_\-]*/standings')
async def handle_tournament_list_page(session, sem, url):
    soup = await async_soup_from_url(session, sem, url)
    current_page = int(soup.find("ul", class_="pagination").attrs["data-current"])
    max_page = int(soup.find("ul", class_="pagination").attrs["data-max"])
    print(f"extracting completed tournaments page {current_page}")
    tournament_trs = extract_trs(soup, "completed-tournaments")
    tournament_ids = [tr.find("a", {'href': regex_standings_url}).attrs["href"].split('/')[2] for tr in tournament_trs]
    tournament_names = [tr.attrs['data-name'] for tr in tournament_trs]
    tournament_dates = [tr.attrs['data-date'] for tr in tournament_trs]
    tournament_organizers = [tr.attrs['data-organizer'] for tr in tournament_trs]
    tournament_formats = [tr.attrs['data-format'] for tr in tournament_trs]
    tournament_nb_players = [tr.attrs['data-players'] for tr in tournament_trs]
    standings_urls = [construct_standings_url(tid) for tid in tournament_ids]
    standings = await asyncio.gather(*[async_soup_from_url(session, sem, url) for url in standings_urls])
    for i in range(len(tournament_ids)):
        await handle_tournament_standings_page(
            session, sem, standings[i], tournament_ids[i], tournament_names[i],
            tournament_dates[i], tournament_organizers[i], tournament_formats[i], tournament_nb_players[i]
        )
    if current_page < max_page:
        await handle_tournament_list_page(session, sem, f"{first_tournament_page}&page={current_page+1}")

async def main():
    connector = aiohttp.TCPConnector(limit=20)
    sem = asyncio.Semaphore(50)
    async with aiohttp.ClientSession(base_url=base_url, connector=connector) as session:
        await handle_tournament_list_page(session, sem, first_tournament_page)

if __name__ == "__main__":
    asyncio.run(main())

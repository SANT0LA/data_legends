import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import plotly.graph_objects as go

st.set_page_config(page_title="Data Legends", layout="wide")

API_KEY = st.secrets["RIOT_API_KEY"] if "RIOT_API_KEY" in st.secrets else "SUA_CHAVE_AQUI"
HEADERS = {"X-Riot-Token": API_KEY}

REGION = "br1"
MATCH_REGION = "americas"

champion_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.6.1/data/en_US/champion.json").json()
champion_id_to_name = {
    int(data["key"]): data["id"] for data in champion_data["data"].values()
}

spell_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.6.1/data/en_US/summoner.json").json()
spell_id_to_name = {
    int(data["key"]): data["id"] for data in spell_data["data"].values()
}

def get_account_data(game_name, tag_line):
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.status_code == 200 else None

def get_summoner_data(puuid):
    url = f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.status_code == 200 else None

def get_rank_data(summoner_id):
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.status_code == 200 else []

def get_match_ids(puuid):
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.status_code == 200 else []

def get_match_data(match_id):
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.status_code == 200 else None

def show_rank_graph(rank_data):
    if not rank_data:
        return
    df = pd.DataFrame(rank_data)
    fig = go.Figure(data=[
        go.Bar(
            x=df["queueType"],
            y=df["wins"],
            name="Vitórias",
            marker_color="green"
        ),
        go.Bar(
            x=df["queueType"],
            y=df["losses"],
            name="Derrotas",
            marker_color="red"
        )
    ])
    fig.update_layout(barmode='stack', title="Vitórias e Derrotas por Tipo de Fila")
    st.plotly_chart(fig, use_container_width=True)

def show_role_pie(matches, puuid):
    roles = {}
    for match in matches:
        for p in match['info']['participants']:
            if p['puuid'] == puuid:
                role = p['teamPosition']
                roles[role] = roles.get(role, 0) + 1
    if roles:
        fig = go.Figure(data=[go.Pie(labels=list(roles.keys()), values=list(roles.values()))])
        fig.update_layout(title="Distribuição de Posições")
        st.plotly_chart(fig, use_container_width=True)

def show_winrate_gauge(wins, losses):
    total = wins + losses
    if total == 0:
        return
    win_rate = int((wins / total) * 100)
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = win_rate,
        title = {'text': "Taxa de Vitória (%)"},
        gauge = {'axis': {'range': [None, 100]}}
    ))
    st.plotly_chart(fig, use_container_width=True)

def show_match_stats_bar(player):
    labels = ['Dano Total', 'Visão', 'Minions']
    values = [player['totalDamageDealtToChampions'], player['visionScore'], player['totalMinionsKilled']]
    fig = go.Figure(data=[
        go.Bar(x=labels, y=values, marker_color=["#3498db", "#9b59b6", "#f1c40f"])
    ])
    fig.update_layout(
        title="Estatísticas da Partida",
        yaxis_title="Valor",
        xaxis_title="Métrica",
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)

# UI
st.title("📊 Data Legends")

game_name = st.text_input("Nome do Invocador", value="smoke")
tag_line = st.text_input("Tag", value="071")

if st.button("Buscar Informações"):
    account = get_account_data(game_name, tag_line)
    if not account:
        st.error("Invocador não encontrado.")
    else:
        summoner = get_summoner_data(account["puuid"])
        rank = get_rank_data(summoner["id"])
        matches_ids = get_match_ids(account["puuid"])
        matches_data = [get_match_data(mid) for mid in matches_ids if get_match_data(mid)]

        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/profileicon/{summoner['profileIconId']}.png", width=100)
            st.subheader(f"{account['gameName']}#{account['tagLine']}")
            st.caption(f"Nível {summoner['summonerLevel']}")
        with col2:
            show_rank_graph(rank)
            wins = sum([r['wins'] for r in rank])
            losses = sum([r['losses'] for r in rank])
            show_winrate_gauge(wins, losses)

        show_role_pie(matches_data, account["puuid"])

        st.markdown("---")
        st.subheader("🔎 Partidas Recentes")
        for match in matches_data:
            for p in match['info']['participants']:
                if p['puuid'] == account['puuid']:
                    champ = champion_id_to_name.get(p['championId'], "Desconhecido")
                    champ_icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/champion/{champ}.png"
                    color = "#2ecc71" if p['win'] else "#e74c3c"
                    spells = [spell_id_to_name.get(p['summoner1Id'], ""), spell_id_to_name.get(p['summoner2Id'], "")]
                    spell_icons = [f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/spell/{s}.png" for s in spells if s]
                    items = [f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/item/{p[f'item{i}']}.png" for i in range(6) if p[f'item{i}'] > 0]

                    with st.container():
                        st.markdown(
                            f"""
                            <div style='background-color:{color}; padding:10px; border-radius:10px;'>
                                <img src="{champ_icon_url}" width="40" style="vertical-align:middle; border-radius:5px;"> 
                                <b>{match['info']['gameMode']}</b> - {champ} - <b>Nível:</b> {p['champLevel']}<br>
                                <b>KDA:</b> {p['kills']}/{p['deaths']}/{p['assists']} | 
                                <b>Ouro:</b> {p['goldEarned']} | 
                                <b>Tempo:</b> {int(match['info']['gameDuration']/60)}min <br>
                                <b>Feitiços:</b> {' '.join([f'<img src="{icon}" width="25">' for icon in spell_icons])}<br>
                                <b>Itens:</b> {' '.join([f'<img src="{item}" width="25">' for item in items])}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        show_match_stats_bar(p)

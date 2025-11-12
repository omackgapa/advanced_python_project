import streamlit as st
import requests
import urllib.parse
import pandas as pd

# --- (전역) 중요 설정 ---
# 1. API 키 설정 (Streamlit Secrets)
API_KEY = st.secrets.get("API_KEY", "YOUR_RIOT_API_KEY_HERE")
REGION_API = "asia"
REGION_PLATFORM = "kr"

# --- (전역) API 헬퍼 함수들 (캐시 기능 포함) ---

@st.cache_data(ttl=3600)
def get_puuid(game_name, tag_line):
    """Riot ID(게임 이름 + 태그)를 기반으로 PUUID를 가져옵니다."""
    # 중요 수정: game_name과 tag_line 모두 인코딩 (특수문자 및 한글 처리)
    encoded_game_name = urllib.parse.quote(game_name)
    encoded_tag_line = urllib.parse.quote(tag_line)
    
    # 중요 수정: https 뒤에 ':' 추가. (기존: f"https{REGION_API}..." -> 수정: f"https://{REGION_API}..."
    url = f"https://{REGION_API}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()['puuid']
        elif response.status_code == 403:
             st.error(f"API 키가 만료되었거나 유효하지 않습니다. (코드: 403)")
             return None
        elif response.status_code == 404:
            st.error(f"Riot ID를 찾을 수 없습니다: '{game_name}#{tag_line}' (코드: 404)")
            return None
        else:
            st.error(f"PUUID 조회 오류 (코드: {response.status_code}) - 응답: {response.text[:100]}...")
            return None
    except requests.exceptions.ConnectionError:
        st.error("네트워크 연결 오류: Riot API 서버에 접속할 수 없습니다.")
        return None
    except Exception as e:
        st.error(f"PUUID 조회 중 오류: {e}")
        return None

@st.cache_data(ttl=3600)
def get_summoner_id_by_puuid(puuid):
    """PUUID를 기반으로 암호화된 Summoner ID를 가져옵니다."""
    url = f"https://{REGION_PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()['id']
        else:
            return None
    except Exception:
        return None

@st.cache_data(ttl=3600)
def get_challenge_data(puuid):
    """PUUID를 기반으로 도전과제 데이터를 가져옵니다."""
    # 중요 수정: https 뒤에 ':' 추가. (기존: f"https{REGION_API}..." -> 수정: f"https://{REGION_API}..."
    url = f"https://{REGION_API}.api.riotgames.com/lol/challenges/v1/player-data/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"도전과제 정보 조회 오류 (코드: {response.status_code})")
            return None
    except Exception as e:
        st.error(f"도전과제 조회 중 오류: {e}")
        return None

@st.cache_data(ttl=3600)
def get_mastery_data_by_puuid(puuid):
    """PUUID를 기반으로 Top 5 챔피언 숙련도 데이터를 가져옵니다."""
    url = f"https://{REGION_PLATFORM}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=5"
    headers = {"X-Riot-Token": API_KEY}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"숙련도 정보 조회 오류 (코드: {response.status_code})")
            return None
    except Exception as e:
        st.error(f"숙련도 조회 중 오류: {e}")
        return None

@st.cache_data(ttl=3600)
def get_rank_data_by_summoner_id(summoner_id):
    """Summoner ID를 기반으로 랭크 데이터를 가져옵니다."""
    url = f"https://{REGION_PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": API_KEY}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"랭크 정보 조회 오류 (코드: {response.status_code})")
            return None
    except Exception as e:
        st.error(f"랭크 조회 중 오류: {e}")
        return None

# --- [Window 1] 메인 화면 (사이드바) ---

st.sidebar.title("🎮 픽 모스트 최대 숙련도 랭크") 
st.sidebar.caption(f"팀원: 이주현, 황보현준")

page = st.sidebar.radio(
    "메인 메뉴",
    ("🛡️ 숙련도/랭크 조회하기", "🏆 도전과제 조회하기")
)

# --- API 키 유효성 검사 ---
if API_KEY == "YOUR_RIOT_API_KEY_HERE":
    st.error("API 키가 설정되지 않았습니다! .streamlit/secrets.toml 파일을 생성하고 API_KEY를 입력해주세요.")
    st.stop() 

# --- [Window 3] 숙련도/랭크 페이지 ---
if page == "🛡️ 숙련도/랭크 조회하기":
    st.title("🛡️ 숙련도 및 랭크 조회기")

    # (수정) 기본값을 '96년생 티모장인#9202'로 변경하여 테스트 용이
    full_riot_id = st.text_input("Riot ID (이름#태그):", 
                                 value="96년생 티모장인#9202", # 테스트를 위해 사용자가 제공한 ID로 기본값 변경
                                 help="Riot ID를 '이름#태그' 형식으로 입력하세요.")

    if full_riot_id:
        try:
            game_name, tag_line = full_riot_id.strip().split('#')
        except ValueError:
            st.error("'이름#태그' 형식으로 입력해주세요.")
            st.stop()
        
        with st.spinner(f"'{game_name}#{tag_line}' 님 정보 조회 중... (캐시 확인 중)"):
            # 수정된 get_puuid 호출
            puuid = get_puuid(game_name, tag_line)
            
            if puuid:
                summoner_id = get_summoner_id_by_puuid(puuid)
                
                # --- 랭크 정보 표시 ---
                st.subheader(f"✅ {game_name}#{tag_line} 님의 랭크")
                if summoner_id:
                    rank_data = get_rank_data_by_summoner_id(summoner_id)
                    if rank_data:
                        col1, col2 = st.columns(2)
                        solo_rank_text = "Unranked"
                        flex_rank_text = "Unranked"
                        
                        for queue in rank_data:
                            if queue.get('queueType') == 'RANKED_SOLO_5x5':
                                solo_rank_text = f"{queue['tier']} {queue['rank']} ({queue['leaguePoints']} LP)"
                            elif queue.get('queueType') == 'RANKED_FLEX_SR':
                                flex_rank_text = f"{queue['tier']} {queue['rank']} ({queue['leaguePoints']} LP)"
                        
                        col1.metric("솔로 랭크", solo_rank_text)
                        col2.metric("자유 랭크", flex_rank_text)
                    else:
                        st.info("조회된 랭크 정보가 없습니다.")
                else:
                    st.warning("Summoner ID를 조회할 수 없어 랭크 정보를 가져올 수 없습니다.")
                
                st.divider() 

                # --- 숙련도 정보 표시 ---
                st.subheader("⭐ Top 5 챔피언 숙련도")
                mastery_data = get_mastery_data_by_puuid(puuid)
                if mastery_data:
                    data_for_df = []
                    for champ in mastery_data:
                        data_for_df.append({
                            "챔피언 ID": champ['championId'],
                            "레벨": champ['championLevel'],
                            "숙련도 점수": f"{champ['championPoints']:,}" # 가독성 향상
                        })
                    df = pd.DataFrame(data_for_df)
                    st.dataframe(df, use_container_width=True)
                    st.caption("참고: 챔피언 ID를 이름으로 변환하려면 라이엇 'Data Dragon'의 champion.json 파일이 필요합니다.")
                else:
                    st.info("조회된 숙련도 정보가 없습니다.")

# --- [Window 2] 도전과제 페이지 ---
elif page == "🏆 도전과제 조회하기":
    st.title("🏆 도전과제 세부 조회기")

    # (수정) 기본값을 '96년생 티모장인#9202'로 변경하여 테스트 용이
    full_riot_id = st.text_input("Riot ID (이름#태그):", 
                                 value="96년생 티모장인#9202", # 테스트를 위해 사용자가 제공한 ID로 기본값 변경
                                 help="Riot ID를 '이름#태그' 형식으로 입력하세요.")
    
    if full_riot_id:
        try:
            game_name, tag_line = full_riot_id.strip().split('#')
        except ValueError:
            st.error("'이름#태그' 형식으로 입력해주세요.")
            st.stop()

        with st.spinner(f"'{game_name}#{tag_line}' 님 정보 조회 중... (캐시 확인 중)"):
            # 수정된 get_puuid 호출
            puuid = get_puuid(game_name, tag_line)
            
            if puuid:
                challenge_data = get_challenge_data(puuid)
                if challenge_data:
                    # --- 총점 표시 ---
                    try:
                        total_points = challenge_data['totalPoints']['current']
                        level = challenge_data['totalPoints']['level']
                        st.metric(label=f"🥇 {game_name}#{tag_line} 님의 도전과제 등급", 
                                     value=level, 
                                     delta=f"총 {total_points:,} 점")
                    except KeyError:
                        st.error("총점 데이터를 파싱하는 데 실패했습니다.")
                    
                    st.divider()

                    # --- 개별 도전과제 표시 ---
                    st.subheader("📊 개별 도전과제 진행 현황")
                    challenges = challenge_data.get('challenges', [])
                    if challenges:
                        with st.expander("모든 도전과제 목록 보기 (데이터가 많습니다)"):
                            data_for_df = []
                            for chal in challenges:
                                data_for_df.append({
                                    "ID": chal.get('challengeId', 'N/A'),
                                    "등급": chal.get('level', 'N/A'),
                                    "현재 값": f"{chal.get('current', 0):,}" # 가독성 향상
                                })
                            df = pd.DataFrame(data_for_df)
                            st.dataframe(df, use_container_width=True)
                    else:
                        st.info("조회된 개별 도전과제 정보가 없습니다.")
                else:
                    st.error("도전과제 정보를 가져오는데 실패했습니다.")
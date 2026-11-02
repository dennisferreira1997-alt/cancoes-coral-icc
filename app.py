"""
Canções do coral nos cultos — página para buscar e ouvir no celular.

Rodar no computador:   streamlit run app.py
Lê o resultados.csv gerado pelo buscar_musicas.py (na mesma pasta ou em resultado_busca/).
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Canções do coral", page_icon="🎵", layout="centered")

AQUI = Path(__file__).parent
CANDIDATOS = [AQUI / "resultados.csv", AQUI / "resultado_busca" / "resultados.csv"]


def sem_acento(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def segundos(hms: str) -> int:
    p = [int(x) for x in str(hms).split(":")]
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def data_do_titulo(titulo: str):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", str(titulo))
    if not m:
        return pd.NaT
    ano = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
    try:
        return pd.Timestamp(ano, int(m[2]), int(m[1]))
    except ValueError:
        return pd.NaT


@st.cache_data
def carregar(caminho: str, _mtime: float):
    df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig")
    df["id"] = df["link"].str.extract(r"v=([\w-]{11})")
    df["ini"] = df["inicio"].map(segundos)
    df["fim_s"] = df["fim"].map(segundos)
    df["data"] = df["video"].map(data_do_titulo)
    df["culto"] = df["video"].str.strip(" |")
    df["busca"] = df["musica"].map(sem_acento)
    return df


arquivo = next((c for c in CANDIDATOS if c.exists()), None)
if arquivo is None:
    st.error("Não achei o resultados.csv. Rode o buscar_musicas.py antes.")
    st.stop()
df = carregar(str(arquivo), arquivo.stat().st_mtime)

st.markdown("### 🎵 Canções do coral")
st.caption(f"{df['musica'].nunique()} canções · {len(df)} gravações · {df['id'].nunique()} cultos")

termo = st.text_input("Buscar canção", placeholder="ex.: senhor poderoso",
                      label_visibility="collapsed")
ordem = st.radio("Ordenar", ["A–Z", "Mais gravadas"], horizontal=True,
                 label_visibility="collapsed")

filtro = df[df["busca"].str.contains(sem_acento(termo), regex=False)] if termo else df
contagem = filtro.groupby("musica").size()
nomes = (sorted(contagem.index, key=sem_acento) if ordem == "A–Z"
         else contagem.sort_values(ascending=False).index.tolist())

if not nomes:
    st.info("Nenhuma canção encontrada com esse nome.")

for nome in nomes:
    versoes = filtro[filtro["musica"] == nome].sort_values("data", ascending=False)
    with st.expander(f"**{nome}** · {len(versoes)} gravação(ões)", expanded=bool(termo) and len(nomes) <= 3):
        for _, r in versoes.iterrows():
            data = r["data"].strftime("%d/%m/%Y") if pd.notna(r["data"]) else ""
            cab = f"**{data}** · {r['culto']}" if data else f"**{r['culto']}**"
            st.markdown(f"{cab}  \n⏱ {r['inicio']} – {r['fim']}")
            c1, c2 = st.columns(2)
            c1.link_button("▶ Abrir no YouTube", f"https://www.youtube.com/watch?v={r['id']}&t={r['ini']}s",
                           width="stretch")
            chave = f"ouvir_{r['id']}_{r['ini']}"
            if c2.button("🎧 Ouvir aqui", key=chave, width="stretch"):
                st.session_state["tocando"] = chave
            if st.session_state.get("tocando") == chave:
                st.video(f"https://www.youtube.com/watch?v={r['id']}",
                         start_time=int(r["ini"]), end_time=int(r["fim_s"]))
            st.divider()

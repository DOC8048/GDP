
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(layout="wide")
st.title("Мировой ВВП  (1925–2022)")

# Читаем .dta
@st.cache_data()
def load_maddison():
    df = pd.read_stata("maddison2023_web.dta")
    # Фильтруем с 1925, только строки с данными 
    df = df[(df['year'] >= 1925) & (df['gdppc'].notna()) & (df['pop'].notna())].copy()
    # Считаем ВВП: gdppc * pop * 1000 (население в тысячах)
    df['gdp'] = df['gdppc'] * df['pop'] * 1000
    return df
@st.cache_data()
def load_weo():   
    weo = pd.read_excel('weoapr2025all.xlsx')
    weo_growth = weo[weo['WEO Subject Code'] == 'NGDP_RPCH'].copy()
    return weo_growth
df_medison = load_maddison()
weo_growth = load_weo()
years_weo = [ 2023, 2024, 2025, 2026]
code_map = {
    'SUN': None,   # Former USSR — нет в WEO, игнорируем
    'CSK': None,   # Czechoslovakia — нет в WEO
    'YUG': None,   # Former Yugoslavia — нет в WEO
}

base_countries = df_medison[df_medison['year'] == 1925]['countrycode'].unique()
df_fixed = df_medison[df_medison['countrycode'].isin(base_countries)].copy()
# --- Мировой ВВП: фиксированный набор (1925–2022) ---
world_fixed = df_fixed.groupby('year')['gdp'].sum().reset_index().sort_values('year')
world_fixed['growth_pct'] = world_fixed['gdp'].pct_change() * 100
# --- Мировой ВВП: все страны (1925–2022) ---
world_all = df_medison.groupby('year')['gdp'].sum().reset_index().sort_values('year')
world_all['growth_pct'] = world_all['gdp'].pct_change() * 100

# Добавь это ПЕРЕД строкой "growth_by_country = {}"
all_countries = df_medison['countrycode'].unique()
growth_by_country = {}
for code in base_countries:
    iso3 = code_map.get(code, code)  # если нет в маппе — код совпадает
    if iso3 is None:
        continue
    row = weo_growth[weo_growth['ISO'] == iso3]
    if row.empty:
        continue
    growth_by_country[code] = {}
    for yr in years_weo:
        val = row[yr].values[0]
        try:
            growth_by_country[code][int(yr)] = float(val)
        except (ValueError, TypeError):
            growth_by_country[code][int(yr)] = None
            
gdp_2022 = df_fixed[df_fixed['year'] == 2022].set_index('countrycode')['gdp']
# продление годов
extension_rows = []
for code in base_countries:
    if code not in growth_by_country:
        continue
    prev_gdp = gdp_2022.get(code)
    if prev_gdp is None or pd.isna(prev_gdp):
        continue
    for yr in [2023, 2024, 2025, 2026]:
        g = growth_by_country[code].get(yr)
        if g is None or pd.isna(g):
            continue
        prev_gdp = prev_gdp * (1 + g / 100)
        extension_rows.append({'year': yr, 'gdp': prev_gdp})

# Суммируем продление по годам
if extension_rows:
    ext_df = pd.DataFrame(extension_rows)
    ext_world = ext_df.groupby('year')['gdp'].sum().reset_index()
    # Склеиваем
    world_fixed = world_fixed[world_fixed['year'] < 2023]
    world_fixed = pd.concat([world_fixed[['year', 'gdp']], ext_world], ignore_index=True)
    world_fixed = world_fixed.sort_values('year').reset_index(drop=True)
growth_all = {}
for code in all_countries:
    iso3 = code_map.get(code, code)
    if iso3 is None:
        continue
    row = weo_growth[weo_growth['ISO'] == iso3]
    if row.empty:
        continue
    growth_all[code] = {}
    for yr in years_weo:
        val = row[yr].values[0]
        try:
            growth_all[code][int(yr)] = float(val)
        except (ValueError, TypeError):
            growth_all[code][int(yr)] = None

gdp_2022_all = df_medison[df_medison['year'] == 2022].set_index('countrycode')['gdp']

ext_rows_all = []
for code in all_countries:
    if code not in growth_all:
        continue
    prev_gdp = gdp_2022_all.get(code)
    if prev_gdp is None or pd.isna(prev_gdp):
        continue
    for yr in [2023, 2024, 2025, 2026]:
        g = growth_all[code].get(yr)
        if g is None or pd.isna(g):
            continue
        prev_gdp = prev_gdp * (1 + g / 100)
        ext_rows_all.append({'year': yr, 'gdp': prev_gdp})

if ext_rows_all:
    ext_all_df = pd.DataFrame(ext_rows_all)
    ext_all_world = ext_all_df.groupby('year')['gdp'].sum().reset_index()
    world_all = pd.concat([world_all[['year', 'gdp']], ext_all_world], ignore_index=True)
    world_all = world_all.sort_values('year').reset_index(drop=True)

world_all['growth_pct'] = world_all['gdp'].pct_change() * 100
world_fixed['growth_pct'] = world_fixed['gdp'].pct_change() * 100
# --- График ---
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=(
        "Мировой ВВП: фиксированный набор (сплошная) vs все страны (пунктир)",
        "Годовой рост ВВП (%) — провалы кризисов"
    ),
    vertical_spacing=0.12
)

# Верхний: фиксированный набор — Maddison (сплошная)
mask_mad = world_fixed['year'] <= 2022
mask_weo = world_fixed['year'] >= 2022

fig.add_trace(go.Scatter(
    x=world_fixed.loc[mask_mad, 'year'], y=world_fixed.loc[mask_mad, 'gdp'],
    mode='lines', name='Фикс. набор — Maddison (1925–2022)',
    line={"color": '#2E86AB', "width": 2}
), row=1, col=1)

# Верхний: фиксированный набор — WEO (пунктир)
fig.add_trace(go.Scatter(
    x=world_fixed.loc[mask_weo, 'year'], y=world_fixed.loc[mask_weo, 'gdp'],
    mode='lines', name='Фикс. набор — IMF WEO (2022–2026)',
    line={"color": '#2E86AB', "width": 2, "dash": 'dash'}
), row=1, col=1)
# Верхний: все страны — Maddison (сплошная до 2022)
mask_mad_all = world_all['year'] <= 2022
fig.add_trace(go.Scatter(
    x=world_all.loc[mask_mad_all, 'year'], y=world_all.loc[mask_mad_all, 'gdp'],
    mode='lines', name='Все страны — Maddison (1925–2022)',
    line={"color": '#F18F01', "width": 2}
), row=1, col=1)

# Верхний: все страны — WEO (пунктир с 2022)
mask_weo_all = world_all['year'] >= 2022
fig.add_trace(go.Scatter(
    x=world_all.loc[mask_weo_all, 'year'], y=world_all.loc[mask_weo_all, 'gdp'],
    mode='lines', name='Все страны — IMF WEO (2022–2026)',
    line={"color": '#F18F01', "width": 2, "dash": 'dash'},
    opacity=0.7
), row=1, col=1)

fig.update_yaxes(title_text="ВВП, $", row=1, col=1)

# Нижний: темпы роста (фиксированный набор)
fig.add_trace(go.Bar(
    x=world_fixed['year'], y=world_fixed['growth_pct'],
    name='Рост (фикс. набор)',
    marker_color=world_fixed['growth_pct'].apply(lambda x: '#A23B72' if x < 0 else '#2E86AB'),
    width=0.8
), row=2, col=1)

# Нижний: темпы роста (все страны)
fig.add_trace(go.Scatter(
    x=world_all['year'], y=world_all['growth_pct'],
    mode='lines', name='Рост (все страны)',
    line={"color": '#F18F01', "width": 1.5, "dash": 'dash'},
    opacity=0.7
), row=2, col=1)

fig.update_yaxes(title_text="Рост, %", row=2, col=1)

# Аннотации кризисов
for year, label in [(1929, "Великая депрессия"), (1939, "WWII"),
                     (1973, "Нефтяной кризис"), (2009, "Кризис 2009"),
                     (2020, "COVID"),
                     (2023, 'Банковский кризис')]:
    if year in world_fixed['year'].values:
        val = world_fixed.loc[world_fixed['year'] == year, 'growth_pct'].values[0]
        fig.add_annotation(x=year, y=val, text=label, showarrow=True,
                          arrowhead=2, ax=0, ay=-80, font={"size": 12},
                          row=2, col=1)

fig.update_layout(
    height=700,
    title_text="Источники: Eurostat, OECD, IMF, and World Bank (2026)Bolt and van Zanden – Maddison Project Database 2023",
    hovermode="x unified",
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

# Подпись-оговорка
st.caption(
    f"Фиксированный набор: {len(base_countries)} стран, у которых есть данные за 1925 год. "
    f"Пунктир — все страны (скачок в 1950 — появление новых данных, а не реальный рост)."
)

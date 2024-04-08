# Libs
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import warnings
warnings.filterwarnings('ignore')
import requests
import pandas as pd
import locale
import numpy as np
import plotly.graph_objects as go

# Configurar a localidade para o formato de moeda brasileira
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Page Config STARTS
st.set_page_config(layout="wide")

st.sidebar.title("Contato")
st.sidebar.info(
    """
        Cauê Oliveira Miranda \n
        caue.oliveira99@gmail.com \n
        [GitHub](https://github.com/caue-oliveira) | [LinkedIn](https://www.linkedin.com/in/caueoliveira99) | [Currículo](https://www.canva.com/design/DAF4RWCBOuk/zsbheu6nUrXpw8PWQpcpjw/view?utm_content=DAF4RWCBOuk&utm_campaign=designshare&utm_medium=link&utm_source=viewer)
    """
)

st.title("Mapa Coroplético - Distribuição da CFEM por município")
st.markdown(
    """
A CFEM, Compensação Financeira pela Exploração de Recursos Minerais, representa a contrapartida financeira que as empresas mineradoras pagam à União, aos Estados, ao Distrito Federal e aos Municípios pela exploração econômica dos recursos minerais em seus territórios. Essa distribuição tem como objetivo principal compensar os municípios impactados pela atividade mineradora, promovendo o desenvolvimento local e a mitigação de impactos ambientais.\n
O web app utiliza informações detalhadas sobre a distribuição da CFEM desde 2007, disponibilizadas pela Agência Nacional de Mineração (ANM) por meio do portal [dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/sistema-arrecadacao). Os dados estão disponíveis no mapa coroplético e em dois gráficos que ilustram a distribuição por estado e a evolução ao longo do tempo para um município específico.
"""
)

# Getting CFEM data
@st.cache_data
def load_data():
    cfem_csv = 'https://app.anm.gov.br/DadosAbertos/ARRECADACAO/CFEM_Distribuicao.csv'
    dtype_specification = {
        'NúmeroDeDistribuição': int,
        'Ano': int,
        'Mês': int,
        'Ente': str,
        'SiglaEstado': str,
        'NomeEnte': str,
        'TipoDistribuição': str,
        'Substância': str,
        'TipoAfetamento': str,
        'Valor': float
    }
    dataframe = pd.read_csv(cfem_csv, delimiter=';', quotechar='"', encoding='latin1', dtype=dtype_specification, decimal=',')
    # Arredondando as casas decimais para 2
    dataframe['Valor'] = round(dataframe['Valor'], 2)
    # Selecionando apenas as colunas 'Ano', 'Substância' e 'Valor'
    dataframe = dataframe.loc[:, ['Ano', 'Substância', 'Valor', 'NomeEnte', 'SiglaEstado']]
    return dataframe

dataframe = load_data()
# Widgets: select boxes
substancias = ["Selecione uma opção"]+sorted(pd.unique(dataframe['Substância']))
subs_selection = st.selectbox("Escolha a substância que deseja consultar", substancias, index=100)

years = ["Selecione o ano de consulta"]+sorted(pd.unique(dataframe['Ano']))
year_selection = st.selectbox("Escolha o ano que deseja consultar", years, index=18)

df_filtro = dataframe.groupby(['Ano', 'Substância','NomeEnte','SiglaEstado'])['Valor'].sum().reset_index()
# Agrupando por Ano e Substância e calculando a soma dos valores
df_filt = df_filtro[
                    (df_filtro['Ano'] == year_selection) &
                    (df_filtro['Substância'] == subs_selection)
                    ]


# Page config ENDS

# Map config STARTS
m = folium.Map(location=[-16.39374927779391, -51.663956293293964], tiles='openstreetmap', zoom_start=4)



# Importa o GeoJson do Brasil
br = requests.get(
    "https://raw.githubusercontent.com/jonates/opendata/master/arquivos_geoespaciais/geojs-100-mun.json"
).json()
# Deixar o nome dos municípios em maiúsculo
for feature in br['features']:
    nome_ente = feature['properties']['description']
    feature['properties']['description'] = nome_ente.upper()

# Adiciona informações ao GeoJSON
for feature in br['features']:
        nome_ente = feature['properties']['description']

        # Encontrar a entrada correspondente no DataFrame
        filtro = df_filt['NomeEnte'] == nome_ente
        informacoes_ente = df_filt[filtro]

        # Adicionar as informações ao GeoJSON
        feature['properties']['Ano'] = informacoes_ente['Ano'].values.tolist()  # Adiciona a lista de anos
        feature['properties']['Substância'] = informacoes_ente[
            'Substância'].values.tolist()  # Adiciona a lista de substâncias
        feature['properties']['SiglaEstado'] = informacoes_ente[
            'SiglaEstado'].values.tolist()  # Adiciona a lista de siglas de estado
        feature['properties']['Valor'] = informacoes_ente['Valor'].values.tolist()

# Mapa choroplético
cp = folium.Choropleth(
        geo_data=br,
        name="Mapa cloroplético completo",
        data=df_filt,
        columns=["NomeEnte", "Valor"],
        key_on="feature.properties.description",  # Usando a coluna 'description' como chave
        fill_color="RdYlGn",
        fill_opacity=0.7,
        line_color='White',
        line_opacity=0.3,
        legend_name=f"CFEM {year_selection}",
    ).add_to(m)

# Adicionar tooltips personalizados
for feature in cp.geojson.data['features']:
    nome_ente = feature['properties']['description']
    # Encontrar o valor correspondente no DataFrame df_filt
    valor_municipio = df_filt.loc[df_filt['NomeEnte'] == nome_ente, 'Valor'].values
    if len(valor_municipio) > 0:
        valor_municipio = locale.currency(valor_municipio[0], grouping=True)
    else:
        valor_municipio = 0
    feature['properties']['Valor'] = valor_municipio

# Adicionar tooltips personalizados ao GeoJSON
folium.GeoJsonTooltip(['description', 'Valor'], aliases=['Município:', 'Valor de distribuição CFEM:']).add_to(
    cp.geojson)

folium.plugins.Geocoder().add_to(m)
folium.LayerControl().add_to(m)  # Add o controle de layers
st_folium(m, width=1000, returned_objects=[])  # Mapa ao streamlit

# Gráficos START
    # Configurando o gráfico 2

fig2 = go.Figure()

# Formatando os valores como moeda brasileira (R$)
soma_por_estado = df_filt.groupby('SiglaEstado')['Valor'].sum()
valores_formatados = [f'R$ {valor:,.2f}' for valor in soma_por_estado]

fig2.add_trace(go.Histogram(
    x=df_filt['SiglaEstado'],
    y=df_filt['Valor'],
    histfunc='sum',
    name=f'Distribuição CFEM por estado {year_selection} - {subs_selection} ',
    text=valores_formatados,
    hoverinfo='text+y',
    hovertemplate='<b>%{x}</b><br>Total: %{text}',
)).update_xaxes(categoryorder='total descending')

# Atualizar layout do gráfico
fig2.update_layout(
    title=f'Distribuição CFEM por estado {year_selection} - {subs_selection}',
    xaxis_title='Estado',
    yaxis_title='Valor',
    showlegend=False,
    plot_bgcolor='white',
)

st.plotly_chart(fig2, use_container_width=True)

    # Configurando o gráfico 1

    # Índice da municípios
municipios = ["Selecione uma opção"]+sorted((df_filt['NomeEnte']))
municipio_selection = st.selectbox("Escolha o município que deseja consultar", municipios, index=0)
graph_data = df_filtro[(df_filtro['NomeEnte'] == municipio_selection) & (df_filtro['Substância'] == subs_selection)]
fig = go.Figure()

# Texto dos markers
marker_text = [f'Ano: {ano}, {locale.currency(valor, grouping=True)}' for ano, valor in zip(graph_data['Ano'], graph_data['Valor'])]

# Adicionar uma linha para cada valor de CFEM ao longo dos anos
fig.add_trace(go.Scatter(
    x=graph_data['Ano'],
    y=graph_data['Valor'],
    mode='lines+markers',
    name=f'Distribuição CFEM - {municipio_selection} - {subs_selection}',
    line=dict(color='rgb(67,67,67)', width=2),
    marker=dict(size=8),
    text=marker_text,  # Texto para os marcadores
))

fig.update_layout(
    title=f'Evolução multitemporal da distribuição da CFEM em {municipio_selection} - {subs_selection}',
    xaxis=dict(title='Ano'),
    yaxis=dict(title='Valor da CFEM'),
    showlegend=False,
    plot_bgcolor='white',
)

st.plotly_chart(fig, use_container_width=True)
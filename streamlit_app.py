import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd

# ----------------------
#     Configuración
# ----------------------
st.set_page_config(
    page_title="Exploratorio Risk Load",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_data():
    df = pd.read_excel("base_agrup.xlsx", sheet_name="kmeans_com_ward")
    # Eliminamos columnas irrelevantes
    drop_cols = ["accgrpid","streetname","addrmatch","numstories","year_built","region","occtype"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    # Convertir variables agrupadas a categoría
    for c in ["numst_group","year_band","cluster_geo","occtype_grp"]:
        if c in df.columns:
            df[c] = df[c].astype('category')
    return df

df = load_data()

# Cargar GeoJSON de regiones y comunas
@st.cache_data
def load_geodata():
    url_reg = "https://raw.githubusercontent.com/robertoflores/chile-geodata/master/regiones.geojson"
    url_com = "https://raw.githubusercontent.com/robertoflores/chile-geodata/master/comunas.geojson"
    gdf_reg = gpd.read_file(url_reg)
    gdf_com = gpd.read_file(url_com)
    return gdf_reg, gdf_com

gdf_reg, gdf_com = load_geodata()

# Sidebar
st.sidebar.title("Menú")
section = st.sidebar.radio("Sección:",
    ["Visión General","Univariada","Bivariada","Correlación","Mapa Regiones","Mapa Comunas RM"]
)

# ----------------------
#  Visión General
# ----------------------
if section == "Visión General":
    st.title("Visión General de la Base de Datos")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Observaciones", df.shape[0])
        st.metric("Variables", df.shape[1])
    with col2:
        st.dataframe(df.head(10))
    st.markdown("---")
    st.subheader("Estadísticas Descriptivas")
    st.dataframe(df.describe(include='all').T)

# ----------------------
#  Univariada
# ----------------------
elif section == "Univariada":
    st.title("Análisis Univariado")
    var = st.selectbox("Seleccionar variable:", df.columns.tolist())
    if str(df[var].dtype) == 'category':
        ct = df[var].value_counts().reset_index()
        ct.columns = [var, 'count']
        ct['prop'] = (ct['count']/ct['count'].sum()).round(3)
        fig = px.bar(ct, x=var, y='count', text='prop', title=f"Distribución de {var}", color=var)
    else:
        fig = px.histogram(df, x=var, nbins=30, marginal="box", title=f"Histograma y Boxplot de {var}")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------
#  Bivariada
# ----------------------
elif section == "Bivariada":
    st.title("Análisis Bivariado")
    num_cols = df.select_dtypes(include='number').columns.tolist()
    x_var = st.selectbox("Eje X:", num_cols)
    y_var = st.selectbox("Eje Y:", [c for c in num_cols if c!=x_var])
    cat_cols = df.select_dtypes(['category']).columns.tolist()
    color_var = st.selectbox("Color:", cat_cols)
    fig = px.scatter(df, x=x_var, y=y_var, color=color_var, trendline="ols",
                     title=f"Scatter: {x_var} vs {y_var}")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------
#  Correlación
# ----------------------
elif section == "Correlación":
    st.title("Mapa de Calor de Correlaciones")
    corr = df.select_dtypes(include='number').corr()
    fig, ax = plt.subplots(figsize=(10,8))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', ax=ax)
    st.pyplot(fig)

# ----------------------
#  Mapa Régiones
# ----------------------
elif section == "Mapa Régiones":
    st.title("Cuentas y Métricas por Región")
    # Agregar AAL y risk_load promedio
    agg = df.groupby('cluster_geo').agg(
        cuentas=('risk_load','size'),
        risk_avg=('risk_load','mean'),
        AAL_avg=('AAL_usd','mean')
    ).reset_index()
    # Unir con geodata
    gmap = gdf_reg.merge(agg, left_on='properties.region_id', right_on='cluster_geo', how='left')
    gmap['cuentas'] = gmap['cuentas'].fillna(0)
    # Choropleth interactivo
    fig = px.choropleth_mapbox(
        gmap,
        geojson=gmap.geometry,
        locations=gmap.index,
        color='risk_avg',
        mapbox_style='carto-positron',
        zoom=4,
        center={'lat':-33.5,'lon':-70.7},
        opacity=0.6,
        hover_data=['cluster_geo','cuentas','risk_avg','AAL_avg'],
        title="Recargo de Seguridad Promedio por Región"
    )
    st.plotly_chart(fig, use_container_width=True)

# ----------------------
#  Mapa Comunas RM
# ----------------------
elif section == "Mapa Comunas RM":
    st.title("Métricas por Comuna en RM")
    # Filtrar comuna RM en geodata
    rm_com = gdf_com[gdf_com['properties']['region_name']=='Región Metropolitana'].copy()
    # Agregar datos: agrupa por comuna id (ajustar key si difiere)
    # Supongamos df tiene columna 'city' con mismo código
    if 'city' in df.columns:
        agg_com = df.groupby('city').agg(
            cuentas=('risk_load','size'),
            risk_avg=('risk_load','mean'),
            AAL_avg=('AAL_usd','mean')
        ).reset_index()
        rm_com = rm_com.merge(agg_com, left_on='properties.city', right_on='city', how='left')
        rm_com[['cuentas','risk_avg','AAL_avg']] = rm_com[['cuentas','risk_avg','AAL_avg']].fillna(0)
        fig2 = px.choropleth_mapbox(
            rm_com,
            geojson=rm_com.geometry,
            locations=rm_com.index,
            color='risk_avg',
            mapbox_style='carto-positron',
            zoom=10,
            center={'lat':-33.45,'lon':-70.65},
            opacity=0.7,
            hover_data=['properties.comuna_name','cuentas','risk_avg','AAL_avg'],
            title="Risk Load Promedio por Comuna (RM)"
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.error("Falta columna 'city' en el dataset para mapear comunas.")

# Footer
st.markdown("---")
st.caption("Dashboard interactivo para exploración de Risk Load")

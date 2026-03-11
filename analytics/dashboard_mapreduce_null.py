# CORRECCIÓN DE PATH
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# IMPORTACIONES
import streamlit as st
from config.mongo_spark_conexion import get_spark_session
from pyspark.sql.functions import sum, avg, count
import matplotlib.pyplot as plt
import pandas as pd


# CONFIGURACIÓN STREAMLIT
st.set_page_config(page_title="Dashboard MapReduce", layout="wide")
st.title("Dashboard MapReduce - Análisis de Ventas")


# CARGA DE DATOS

@st.cache_resource
def load_data():
    spark, df, _ = get_spark_session()

    # LIMPIEZA DESDE SPARK
    # Eliminamos registros donde producto sea null
    df = df.filter(df["producto"].isNotNull())

    return spark, df

# Evita que datos sucios entren al pipeline
# Más eficiente que limpiar en Pandas
# Arquitectura correcta en Big Data

spark, df = load_data()


# FILTROS
st.sidebar.header("Filtros")

# Ahora ya no habrá None porque filtramos arriba
productos = [
    row["producto"]
    for row in df.select("producto").distinct().collect()
]

producto_seleccionado = st.sidebar.multiselect(
    "Selecciona producto",
    productos,
    default=productos
)

# Aplicamos filtro sobre el DataFrame limpio
df_filtrado = df.filter(df["producto"].isin(producto_seleccionado))


# MAPREDUCE (AGREGACIONES)
st.header("Análisis Agregado (MapReduce)")

# Aquí ocurre exactamente MapReduce
resumen = df_filtrado.groupBy("producto").agg(
    sum("ingreso").alias("ingreso_total"),
    sum("cantidad").alias("cantidad_total"),
    avg("precio").alias("precio_promedio"),
    count("*").alias("numero_ventas")
)

resumen_pd = resumen.toPandas()

# Protección extra (buena práctica)
resumen_pd = resumen_pd.dropna(subset=["producto"])
resumen_pd["producto"] = resumen_pd["producto"].astype(str)

st.dataframe(resumen_pd)

# Previene errores en visualización
# Convierte todo a string (Matplotlib lo necesita)

# GRÁFICA DE INGRESOS

st.subheader("Ingreso Total por Producto")

if not resumen_pd.empty:  # Evita que la app se rompa si no hay datos

    fig = plt.figure(figsize=(10,6))

    plt.bar(
        resumen_pd["producto"],
        resumen_pd["ingreso_total"]
    )

    plt.xticks(rotation=45)
    plt.xlabel("Producto")
    plt.ylabel("Ingreso Total")
    plt.title("Ingreso Total por Producto")

    st.pyplot(fig)

else:
    st.warning("No hay datos para graficar.")


# INTERPRETACIÓN AUTOMÁTICA
st.subheader("Interpretación Automática")

if not resumen_pd.empty:

    max_ingreso = resumen_pd["ingreso_total"].max()
    max_cantidad = resumen_pd["cantidad_total"].max()

    for _, row in resumen_pd.iterrows():

        if row["ingreso_total"] == max_ingreso:
            st.success(f"{row['producto']} → Producto Estrella (Mayor ingreso)")

        elif row["cantidad_total"] == max_cantidad:
            st.info(f"{row['producto']} → Alta Rotación")

        else:
            st.warning(f"{row['producto']} → Producto Secundario")

else:
    st.warning("No hay datos para mostrar.")


# CIERRE
st.write("Análisis distribuido usando Spark (MapReduce)")

# Flujo correcto ahora

# 1 MongoDB
# 2 Spark limpia nulos
# 3 Agregación distribuida (MapReduce)
# 4 Conversión controlada a Pandas
# 5 Visualización segura

# Qué es MapReduce?
#MapReduce es un modelo de procesamiento distribuido que tiene 2 fases:
# MAP
# Transforma o prepara los datos en paralelo.
# REDUCE
# Agrupa y agrega resultados para obtener un resumen.

# Fue popularizado por:
# Google (paper original)
# Implementado masivamente en Apache Hadoop
# Hoy optimizado en Apache Spark

# Fase MAP (implícita)

# Spark divide el DataFrame en particiones:

# Nodo 1 → Producto A → ingreso parcial
# Nodo 2 → Producto A → ingreso parcial
# Nodo 3 → Producto B → ingreso parcial

# Cada nodo calcula sumas parciales.

# Eso es el MAP.

# Fase REDUCE

# Después Spark combina los resultados:

# Ingreso total A = parcial1 + parcial2
# Ingreso total B = parcial3

# Eso es el REDUCE.
# CORRECCIÓN DE PATH (IMPORTANTE PARA STREAMLIT)
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
st.title(" Dashboard MapReduce - Análisis de Ventas")


# CARGA DE DATOS
@st.cache_resource
def load_data():
    spark, df, _ = get_spark_session()
    return spark, df


spark, df = load_data()


# FILTROS
st.sidebar.header("Filtros")

productos = [row["producto"] for row in df.select("producto").distinct().collect()]

# Si en MongoDB existe algún documento con:
# { "producto": null }
# Entonces productos contendrá None, y eso provoca después:
# TypeError: 'value' must be an instance of str or bytes, not a None
# cuando Matplotlib intenta graficar.
# La limpieza debe hacerse en Spark (no en Pandas).


producto_seleccionado = st.sidebar.multiselect(
    "Selecciona producto",
    productos,
    default=productos
)

df_filtrado = df.filter(df["producto"].isin(producto_seleccionado))


# MAPREDUCE (AGREGACIONES)
st.header(" Análisis Agregado (MapReduce)")

resumen = df_filtrado.groupBy("producto").agg(
    sum("ingreso").alias("ingreso_total"),
    sum("cantidad").alias("cantidad_total"),
    avg("precio").alias("precio_promedio"),
    count("*").alias("numero_ventas")
)

resumen_pd = resumen.toPandas()

st.dataframe(resumen_pd)


# GRÁFICA DE INGRESOS
st.subheader("Ingreso Total por Producto")

fig = plt.figure()
plt.bar(resumen_pd["producto"], resumen_pd["ingreso_total"])
plt.xticks(rotation=45)
plt.xlabel("Producto")
plt.ylabel("Ingreso Total")
plt.title("Ingreso Total por Producto")

st.pyplot(fig)


# INTERPRETACIÓN AUTOMÁTICA
st.subheader("Interpretación Automática")

if not resumen_pd.empty:

    max_ingreso = resumen_pd["ingreso_total"].max()
    max_cantidad = resumen_pd["cantidad_total"].max()

    for _, row in resumen_pd.iterrows():

        if row["ingreso_total"] == max_ingreso:
            st.success(f" {row['producto']} → Producto Estrella (Mayor ingreso)")
        elif row["cantidad_total"] == max_cantidad:
            st.info(f" {row['producto']} → Alta Rotación")
        else:
            st.warning(f"{row['producto']} → Producto Secundario")

else:
    st.warning("No hay datos para mostrar.")


# CIERRE
st.write(" Análisis distribuido usando Spark (MapReduce)")
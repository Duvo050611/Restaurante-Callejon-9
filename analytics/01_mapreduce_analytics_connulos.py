from config.mongo_spark_conexion import get_spark_session
from pyspark.sql.functions import sum, avg, count
import matplotlib.pyplot as plt
import pandas as pd

# FUNCIÓN: INTERPRETACIÓN AUTOMÁTICA
def interpretar_mapreduce(resumen_df):

    resumen_pd = resumen_df.toPandas()

    print("\n")
    print("INTERPRETACIÓN AUTOMÁTICA MAPREDUCE")
    print("\n")

    max_ingreso = resumen_pd["ingreso_total"].max()
    max_cantidad = resumen_pd["cantidad_total"].max()

    for _, row in resumen_pd.iterrows():

        producto = row["producto"]
        ingreso = round(row["ingreso_total"], 2)
        cantidad = row["cantidad_total"]

        print(f"Producto: {producto}")
        print(f"  Ingreso Total: {ingreso}")
        print(f"  Cantidad Total Vendida: {cantidad}")

        if ingreso == max_ingreso:
            print("  → Producto Estrella (Mayor ingreso)")
        elif cantidad == max_cantidad:
            print("  → Producto de Alta Rotación")
        else:
            print("  → Producto Secundario")

        print()


# FUNCIÓN: GRÁFICA DE INGRESOS POR PRODUCTO
def graficar_ingresos(resumen_df):

    pdf = resumen_df.toPandas()

    plt.figure()
    plt.bar(pdf["producto"], pdf["ingreso_total"])

    plt.xlabel("Producto")
    plt.ylabel("Ingreso Total")
    plt.title("Ingreso Total por Producto")
    plt.xticks(rotation=45)

    plt.show()


# FUNCIÓN: GRÁFICA DE CANTIDAD VENDIDA
def graficar_cantidad(resumen_df):

    pdf = resumen_df.toPandas()

    plt.figure()
    plt.bar(pdf["producto"], pdf["cantidad_total"])

    plt.xlabel("Producto")
    plt.ylabel("Cantidad Total")
    plt.title("Cantidad Vendida por Producto")
    plt.xticks(rotation=45)

    plt.show()


# FUNCIÓN PRINCIPAL
def main():

    spark, df, _ = get_spark_session()

    print("\n")
    print("EJECUTANDO MAPREDUCE AVANZADO")
    print("\n")

    # MAP PHASE → Selección implícita
    # REDUCE PHASE → Agregación

    resumen = df.groupBy("producto").agg(
        sum("ingreso").alias("ingreso_total"),
        sum("cantidad").alias("cantidad_total"),
        avg("precio").alias("precio_promedio"),
        count("*").alias("numero_ventas")
    )

    resumen.show()

    # Interpretación automática
    interpretar_mapreduce(resumen)

    # Visualizaciones
    graficar_ingresos(resumen)
    graficar_cantidad(resumen)

    spark.stop()


# EJECUCIÓN
if __name__ == "__main__":
    main()
# config/mongo_spark_conexion.py
"""
Módulo de conexión entre MongoDB y Spark para análisis de datos.
Proporciona una sesión de Spark configurada para leer desde MongoDB.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.ml.feature import VectorAssembler
from dotenv import load_dotenv
from pathlib import Path
import os
from urllib.parse import quote_plus


def get_spark_session(app_name="MongoSparkAnalytics"):
    """
    Crea y devuelve una SparkSession configurada para conectar con MongoDB.
    También devuelve un DataFrame con los datos procesados.
    
    Args:
        app_name (str): Nombre de la aplicación Spark
        
    Returns:
        tuple: (spark, df, df_vector) - Sesión de Spark, DataFrame y DataFrame vectorizado
    """
    # 1.- Cargar variables de entorno
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    user = os.getenv("MONGO_USER")
    password = quote_plus(os.getenv("MONGO_PASSWORD"))
    cluster = os.getenv("MONGO_CLUSTER")
    database = os.getenv("MONGO_DB")
    collection_name = os.getenv("MONGO_COLLECTION")

    mongo_uri = f"mongodb+srv://{user}:{password}@{cluster}"

    # 2.- Crear sesión Spark con configuración MongoDB
    spark = (
        SparkSession.builder
        .appName(app_name)
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.13:10.3.0")
        .config("spark.mongodb.read.connection.uri", mongo_uri)
        .config("spark.mongodb.read.database", database)
        .config("spark.mongodb.read.collection", collection_name)
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    # 3.- Leer datos de MongoDB
    try:
        df = spark.read.format("mongodb").load()
        
        # 4.- Limpieza y tipado (si las columnas existen)
        columns_to_select = []
        for col_name in ["producto", "cantidad", "precio"]:
            if col_name in df.columns:
                if col_name in ["cantidad", "precio"]:
                    columns_to_select.append(col(col_name).cast("double"))
                else:
                    columns_to_select.append(col(col_name))
        
        if columns_to_select:
            df = df.select(columns_to_select)
        
        # 5.- Eliminar nulos
        numeric_cols = [c for c in df.columns if c in ["cantidad", "precio"]]
        if numeric_cols:
            df = df.dropna(subset=numeric_cols)
        
        # 6.- Feature Engineering (si las columnas lo permiten)
        df_vector = None
        if "cantidad" in df.columns and "precio" in df.columns:
            df = df.withColumn("ingreso", col("cantidad") * col("precio"))
            
            # 7.- Vectorización
            input_cols = ["cantidad", "precio"]
            if "ingreso" in df.columns:
                input_cols.append("ingreso")
            
            try:
                assembler = VectorAssembler(
                    inputCols=input_cols,
                    outputCol="features",
                    handleInvalid="skip"
                )
                df_vector = assembler.transform(df)
            except Exception:
                df_vector = None
        
        return spark, df, df_vector
        
    except Exception as e:
        # Si hay error al leer de MongoDB, devolver la sesión vacía
        print(f"⚠️ Error al cargar datos de MongoDB: {e}")
        return spark, None, None

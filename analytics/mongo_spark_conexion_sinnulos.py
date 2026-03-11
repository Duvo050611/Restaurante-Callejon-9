from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.ml.feature import VectorAssembler
from dotenv import load_dotenv
from pathlib import Path
import os
from urllib.parse import quote_plus


def get_spark_session():

    # 1.- Cargar variables de entorno
    
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    user = os.getenv("MONGO_USER")
    password = quote_plus(os.getenv("MONGO_PASSWORD"))
    cluster = os.getenv("MONGO_CLUSTER")
    database = os.getenv("MONGO_DB")
    collection_name = os.getenv("MONGO_COLLECTION")

    mongo_uri = f"mongodb+srv://{user}:{password}@{cluster}"

    # 2.- Crear sesión Spark
    
    spark = SparkSession.builder \
        .appName("BigDataMLModule") \
        .config("spark.jars.packages",
                "org.mongodb.spark:mongo-spark-connector_2.13:10.3.0") \
        .config("spark.mongodb.read.connection.uri", mongo_uri) \
        .config("spark.mongodb.read.database", database) \
        .config("spark.mongodb.read.collection", collection_name) \
        .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")

    # 3.- Leer datos
    df = spark.read.format("mongodb").load()

    # 4.- Limpieza y tipado (CRÍTICO)
    
    df = df.select(
        col("producto"),
        col("cantidad").cast("double"),
        col("precio").cast("double")
    )

    # 5.- Eliminar nulos antes de crear features
    df = df.dropna(subset=["cantidad", "precio"])

    # 6.- Feature Engineering
    
    df = df.withColumn("ingreso", col("cantidad") * col("precio"))

    # 7.- Vectorización segura
    assembler = VectorAssembler(
        inputCols=["cantidad", "precio", "ingreso"],
        outputCol="features",
        handleInvalid="skip"  # clave para evitar crash
    )

    df_vector = assembler.transform(df)

    return spark, df, df_vector
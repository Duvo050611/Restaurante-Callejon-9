import sys
import os

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
parent_root = os.path.dirname(project_root)
sys.path.insert(0, parent_root)

from config.mongo_spark_conexion import get_spark_session

# Aquí estás importando una función personalizada que: Crea la sesión Spark Conecta con MongoDB (o tu fuente), Devuelve el DataFrame listo para trabajar
# Entonces esta línea representa: Capa de configuración, Separación de responsabilidades, Arquitectura modular.

from pyspark.sql.functions import sum

# Aquí importancia la función sum() de Spark SQL. Importante: No es el sum() nativo de Python.
# Es el sum() distribuido de Spark, que funciona en cluster.

spark, df, _ = get_spark_session()

# Aquí estás desempaquetando lo que devuelve tu función:
# Variable	Qué es
# spark	    Sesión Spark
# df	    DataFrame con ventas
# _	        Algo que no necesitas

#El _ significa: “No me interesa esta variable” Es buena práctica.


print("=== MAPREDUCE ===") #Solo imprime texto para identificar el algoritmo que estás ejecutando.
df.groupBy("producto") \
 .agg(sum("ingreso").alias("total_ingreso")) \
 .orderBy("total_ingreso", ascending=False) \
 .show()
    

# linea 23 Agrupa los registros por esa columna.
# linea 24 Aplica una función de agregación.
# linea 25 Aplica un ordenamiento.
# linea 26 Imprime el resultado en consola.

# Aquí está ocurriendo el procesamiento distribuido.
# Conceptualmente esto es MapReduce
# MAP

# Spark toma los datos y los agrupa por producto:

# Laptop → 1200
# Laptop → 1500
# Mouse  → 200
# Mouse  → 300

# SHUFFLE (fase intermedia)

# Spark redistribuye los datos entre nodos por clave (producto).

# REDUCE

# Aplica la suma por cada grupo:

# Laptop → 2700
# Mouse  → 500

spark.stop()

#¿Qué hace? Esto ejecuta el modelo clásico de Big Data:

# Map → Spark divide los datos entre nodos

# Shuffle → redistribuye por clave (producto)

# Reduce → suma ingresos

# Es el corazón de Hadoop y Spark.
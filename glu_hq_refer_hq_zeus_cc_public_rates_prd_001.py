#%help

import sys
import boto3
from datetime import datetime
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from functools import reduce
from pyspark.sql import functions as F
  
sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
job = Job(glueContext)

#RAW
bucket = "s3-hq-raw-prd-refer"
prefix = "zeus_public_rates_sftp/public_rates_"
prefix_raw = "pblc_rts"
#STD
bucket_std = "s3-hq-std-prd-refer"
prefix_std = "pblc_rts_std"
#COUNTRY
countries = ["bo", "hn", "gt"]

def getDate():
    current = datetime.now()
    date_format = current.strftime("%Y%m%d")    
    return date_format

def cleanSupplyName(df):
    df = df.withColumn("SPLY_NM",F.when(
            #GUATEMALA
            F.col("SPLY_NM_FULL")==F.lit("DISTRIBUIDORA DE ELECTRICIDAD DE ORIENTE SA"),F.lit("DEORSA")
        ).when(
            F.col("SPLY_NM_FULL")==F.lit("EMPRESA ELECTRICA DE GUATEMALA S A"),F.lit("EEGSA")
        ).when(
            F.col("SPLY_NM_FULL")==F.lit("DISTRIBUIDORA DE ELECTRICIDAD DE OCCIDENTE SA"),F.lit("DEOCSA")
        ).when(
            F.col("SPLY_NM_FULL")==F.lit("EMPRESA ELECTRICA DE GUATEMALA SA"),F.lit("EEGSA")
        ).when(
            #HONDURAS
            F.col("SPLY_NM_FULL")==F.lit("ENEE"),F.lit("ENEE")
        ).when(
            #BOLIVIA
            F.col("SPLY_NM_FULL")==F.lit("EMPRESA DE LUZ Y FUERZA ELECTRICA COCHABAMBA S A"),F.lit("ELFEC")
        ).when(
            F.col("SPLY_NM_FULL")==F.lit("COMPAÑIA ELECTRICA SUCRE S A"),F.lit("CESSA")
        ).when(
            F.col("SPLY_NM_FULL")==F.lit("SERVICIOS ELECTRICOS POTOSI SA"),F.lit("SEPSA")
        ).when(
            F.col("SPLY_NM_FULL")==F.lit("COOPERATIVA RURAL DE ELECTRIFICACION L T D A"),F.lit("CRE")
        ).when(
            F.col("SPLY_NM_FULL")==F.lit("ELECTRICIDAD DE LA PAZ S A"),F.lit("DELAPAZ")
        ).otherwise(
            F.lit("Unknown")
        )
    )
    return df

def getAcronymCountry(df):
    df = df.withColumn("CTRY_CD", F.when(
        F.col("CTRY_CD") == F.lit("Bolivia"), F.lit("BO")
    ).when(
        F.col("CTRY_CD") == F.lit("Guatemala"), F.lit("GT")
    ).when(
        F.col("CTRY_CD") == F.lit("Honduras"), F.lit("HN")
    ).otherwise(F.lit(None)))
    return df

def run():
    s3 = boto3.client('s3')
    dfs = []

    for country in countries:    
        # Listar los archivos en el bucket de S3
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix+country)  
        # Filtrar los archivos que cumplen con el patrón y extraer las fechas
        files = [obj['Key'] for obj in response.get('Contents', []) if 'public_rate_'+country+'_' in obj['Key']]
        #if files:
        dates = [datetime.strptime(file.split('_')[-1].split('.')[0], "%Y%m%d") for file in files]
        # Encontrar la fecha máxima y el archivo correspondiente
        max_date = max(dates)
        index_max_date = dates.index(max_date)
        latest_file = files[index_max_date]   
            # Leer el archivo con fecha maxima
        path = f"s3a://{bucket}/{latest_file}"
        df = spark.read.csv(path, header=True)
        dfs.append(df)
    # Unir todos los DataFrames
    union_df = reduce(lambda df1, df2: df1.unionByName(df2, allowMissingColumns=True), dfs)
    

    output_path = "s3a://{}/{}/".format(bucket,prefix_raw)
    # Sobreescribir el archivo en S3 en formato Parquet
    union_df.write.mode("overwrite").parquet(output_path)
    
    # Leer de RAW
    public_rates_raw = spark.read.parquet(output_path)
    
    # Se renombra Fecha Reporte a RPRT_DT
    public_rates_raw = public_rates_raw.withColumnRenamed("fecha_de_reporte","RPRT_DT")
    
    # Se convierte RPRT_DT a formato fecha
    public_rates_raw = public_rates_raw.withColumn("RPRT_DT",F.to_date(F.col("RPRT_DT"), "MM/dd/yyyy"))
    
    # Se renombra el campo Pais a CTRY_CD
    public_rates_raw = public_rates_raw.withColumnRenamed("pais","CTRY_CD")
    
    # Se convierte CTRY_CD a formato abreviado
    #############LIMPIEZA MANUAL#################
    public_rates_raw = getAcronymCountry(public_rates_raw)
    #############################################

    # rename proveedor a SPLY_NM_FULL
    public_rates_raw = public_rates_raw.withColumnRenamed("proveedor","SPLY_NM_FULL")
    
    ##############LIMPIEZA MANUAL#################
    # Se convierte SPLY_NM_FULL a SPLY_NM abreviado
    public_rates_raw = cleanSupplyName(public_rates_raw)
    ##############################################

    # renombrar categoría a RT
    public_rates_raw = public_rates_raw.withColumnRenamed("categoria","RT")
    
    # renombrar tipo_de_cargo a TP_CHRG
    public_rates_raw = public_rates_raw.withColumnRenamed("tipo_de_cargo","TP_CHRG")
    
    # recombrar consumo a CNSMPT
    public_rates_raw = public_rates_raw.withColumnRenamed("consumo","CNSMPT")
    
    # renombrar precio_kwh a PRC_PER_KWH_WH_IVA_PBL_RT
    public_rates_raw = public_rates_raw.withColumnRenamed("precio_kwh","PRC_PER_KWH_WH_IVA_PBL_RT")
    
    # renombrar precio_potencia a PRC_PER_KW_WH_IVA_POT
    public_rates_raw = public_rates_raw.withColumnRenamed("precio_potencia","PRC_PER_KW_WH_IVA_POT")
    
    # renobrar tarifa_cargo a PRC_PER_TRF_CHRG
    public_rates_raw = public_rates_raw.withColumnRenamed("tarifa_cargo","PRC_PER_TRF_CHRG")
    
    # renombrar inicio_tarifa a INV_PBL_RT_START
    public_rates_raw = public_rates_raw.withColumnRenamed("inicio_tarifa","INV_PBL_RT_START")
    
    # renombrar fin_tarifa a INV_PBL_RT_END
    public_rates_raw = public_rates_raw.withColumnRenamed("fin_tarifa","INV_PBL_RT_END")
    
    # Se convierte INV_PBL_RT_END a formato fecha
    public_rates_raw = public_rates_raw.withColumn("INV_PBL_RT_END",F.to_date(F.col("INV_PBL_RT_END"), "MM/dd/yyyy"))
    
    # Se convierte INV_PBL_RT_START a formato fecha
    public_rates_raw = public_rates_raw.withColumn("INV_PBL_RT_START",F.to_date(F.col("INV_PBL_RT_START"), "MM/dd/yyyy"))
    
    #GUARDAR PUBLIC RATES EN TABLA STD
    output_path_std = "s3a://{}/{}/".format(bucket_std,prefix_std)
    public_rates_raw.write.mode("overwrite").parquet(output_path_std)

run()

job.commit()
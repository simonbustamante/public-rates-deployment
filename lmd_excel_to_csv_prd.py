import boto3
import pandas as pd
from io import BytesIO
import re
from datetime import datetime

s3 = boto3.client('s3')

#COUNTRY
countries = ["bo", "hn", "gt"]

def lambda_handler(event, context):
    for country in countries:
        bucket_name = 's3-hq-raw-prd-refer'
        prefix = f'zeus_public_rates_sftp/public_rates_{country}/'
    
        # Lista los archivos en el bucket
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.xlsx')]
    
        # Encuentra el archivo con la fecha más reciente
        latest_file = max(files, key=lambda x: datetime.strptime(re.search(r'(\d{8})', x).group(), '%Y%m%d'))
    
        # Lee el archivo Excel
        obj = s3.get_object(Bucket=bucket_name, Key=latest_file)
        data = pd.read_excel(BytesIO(obj['Body'].read()), engine='openpyxl')
    
        # Formatea las columnas de fecha
        date_columns = ['fecha_de_reporte', 'inicio_tarifa', 'fin_tarifa']
        for col in date_columns:
            if col in data.columns:
                data[col] = pd.to_datetime(data[col]).dt.strftime('%m/%d/%Y')
    
        # Convierte a CSV
        csv_buffer = BytesIO()
        data.to_csv(csv_buffer, index=False)
    
        # Guarda el CSV en S3
        s3.put_object(Bucket=bucket_name, Key=latest_file.replace('.xlsx', '.csv'), Body=csv_buffer.getvalue())
    
    return {
        'statusCode': 200,
        'body': f'los archivos excel han convertido a CSV y guardado en S3'
    }

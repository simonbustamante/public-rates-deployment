import json
import boto3
import time
import datetime

def lambda_handler(event, context):
    
    athena = boto3.client('athena')
    s3_output = 's3://<your-bucker>/lmd-hq-raw-prd-refer-zeus-public-rates-check-fin-tarifa/'
    
    # La fecha de hoy en el formato MM/DD/YYYY
    fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")
    #fecha_hoy = "2023-11-01"
    query = f"""SELECT * FROM "hq-std-prd-refer-link"."pblc_rts_std" WHERE "inv_pbl_rt_end" <= DATE '{fecha_hoy}'"""
    
    # Ejecuta el query en Athena y guarda el resultado en un bucket de S3
    response = athena.start_query_execution(
        QueryString=query,
        ResultConfiguration={'OutputLocation': s3_output}
    )
    
    query_execution_id = response['QueryExecutionId']
    
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_execution_id)['QueryExecution']['Status']['State']
        if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        time.sleep(1)  # Espera un segundo antes de consultar el estado nuevamente
    
    if status == 'SUCCEEDED':
        results = athena.get_query_results(QueryExecutionId=query_execution_id)
        print(results['ResultSet']['Rows'])
        return {
            'Msg':"ZEUS_PUBLIC_RATES OUT OF DATE",
            'statusCode': 200,
            'results': results['ResultSet']['Rows']
        }
    
    else:
        return {
            'statusCode': 204,
            'results': "ZEUS_PUBLIC_RATES UP TO DATE"
        }


#### #### #### #### #### #### #### #### #### #### #### #### 
#### #### #### #### #### #### #### #### #### #### #### #### 
#### #### #### #### #### #### #### #### #### #### #### #### 
#### aws.bi.LakeH.hq.prd #525196274797 #### #### #### #####
#### #### #### #### #### #### #### #### #### #### #### #### 
#### #### #### #### #### #### #### #### #### #### #### #### 
#### #### #### #### #### #### #### #### #### #### #### #### 

locals {
  profile = "525196274797_AWSAdministratorAccess"
  region = "us-east-1"
  file_cp_to_bucket = "glu_hq_refer_hq_zeus_cc_public_rates_prd_001"
  file_cp_to_bucket2 = "lmd-hq-raw-prd-refer-zeus-public-rates-check-fin-tarifa_001"
  bucket_install_script = "s3-hq-raw-prd-intec"
  prefix_install_script = "app_glu_hq_refer_hq_zeus_cc_public_rates_prd_001"
  prefix_install_script2 = "app_lmd-hq-raw-prd-refer-zeus-public-rates-check-fin-tarifa_001"
  bucket_to_crawl = "s3-hq-std-prd-refer"
  prefix_to_crawl = "pblc_rts_std"
  svc_role_arn = "arn:aws:iam::525196274797:role/svc-role-data-mic-development-integrations"
  crawler_name = "crwl-hq-std-prd-refer-zeus-public-rates"
  db_target = "hq-std-prd-refer-link"
  step_function_name = "stp-fnc-hq-refer-zeus-public-rates-prd"
  step_function_path = "zeus_public_rates_step_function_prd.json"
  sns_name = "zeus-hq-public-rates-out-of-date-prd"
}

# # Lista de correos electrónicos
variable "emails" {
  description = "Lista de correos electrónicos para suscripción."
  type        = list(string)
  default     = [
    "simon.bustamante@millicom.com", 
    #"email2@gmail.com", 
  ]
}

provider "aws" {
  alias = "aws-bi-LakeH-hq-prd"
  profile = local.profile
  region  = local.region
}

## INSTALAR SCRIPT

# borrar el viejo y copiar el archivo al bucket
resource "null_resource" "copy_source_code" {
  triggers = {
    always_run = "${timestamp()}"
  }
  provisioner "local-exec" {
    command = "aws s3 cp ${local.file_cp_to_bucket}.py s3://${local.bucket_install_script}/${local.prefix_install_script}/ --profile ${local.profile}"
  }
}

# borrar el viejo y copiar el archivo al bucket
resource "null_resource" "copy_source_code2" {
  triggers = {
    always_run = "${timestamp()}"
  }
  provisioner "local-exec" {
    command = "aws s3 cp ${local.file_cp_to_bucket2}.zip s3://${local.bucket_install_script}/${local.prefix_install_script2}/ --profile ${local.profile}"
  }
}

## Definición del trabajo de Glue
resource "aws_glue_job" "create_job_public_rates_glue" {
  provider = aws.aws-bi-LakeH-hq-prd
  name     = local.file_cp_to_bucket
  role_arn = local.svc_role_arn
  glue_version = "4.0"

  command {
    script_location = "s3://${local.bucket_install_script}/${local.prefix_install_script}/${local.file_cp_to_bucket}.py" 
    python_version  = "3"                          
  }

  default_arguments = {
    "--TempDir"             = "s3://${local.bucket_install_script}/${local.prefix_install_script}/temp-dir/"
    "--job-bookmark-option" = "job-bookmark-enable"
    #"--extra-py-files"      = "s3://${local.bucket_to_create}/extra-files.zip"  # Si necesitas archivos adicionales
  }

  max_retries  = 0      # Número de reintentos en caso de fallo
  timeout      = 60     # Tiempo máximo de ejecución en minutos
  number_of_workers = 5 # numero de workers del job
  worker_type = "G.1X"  # tipo de worker
}


## CONFIGURAR CRAWLERS
# la step function se encuentra en otra cuenta


resource "aws_glue_crawler" "public_rates_crawler" {
  provider = aws.aws-bi-LakeH-hq-prd
  name          = local.crawler_name
  role          = local.svc_role_arn  # Asegúrate de reemplazar esto con el ARN de tu rol de IAM para Glue

  database_name = "${local.db_target}"  # Reemplaza con el nombre de tu base de datos de Glue

  s3_target {
    path = "s3://${local.bucket_to_crawl}/${local.prefix_to_crawl}/"
  }


}

# ## CONFIGURAR STEP FUNCTION

resource "aws_sfn_state_machine" "daily_rate_state_machine" {
  provider = aws.aws-bi-LakeH-hq-prd
  name     = local.step_function_name
  role_arn = local.svc_role_arn

  # Lee la definición de la máquina de estados del archivo JSON
  definition = file("${local.step_function_path}")
}


# NOTIFICACIONES SNS

resource "aws_sns_topic" "logging_error_topic_prd" {
  provider = aws.aws-bi-LakeH-hq-prd
  name = local.sns_name
}

resource "aws_sns_topic_subscription" "elogging_error_subscription_prd" {
  provider = aws.aws-bi-LakeH-hq-prd
  for_each  = toset(var.emails)

  topic_arn = aws_sns_topic.logging_error_topic_prd.arn
  protocol  = "email"
  endpoint  = each.value
}

# CREAR LAMBDA



resource "aws_lambda_function" "lambda_function" {
  provider = aws.aws-bi-LakeH-hq-prd
  function_name = local.file_cp_to_bucket2
  role          = local.svc_role_arn

  handler       = "${local.file_cp_to_bucket2}.lambda_handler" # Asegúrate de cambiar esto al nombre de tu archivo y método handler
  runtime       = "python3.11" # Asegúrate de usar la versión correcta de Python

  s3_bucket     = local.bucket_install_script
  s3_key        = "${local.prefix_install_script2}/${local.file_cp_to_bucket2}.zip"

  # Configuraciones adicionales como variables de entorno, memoria, tiempo de ejecución máximo, etc.
  timeout       = 15 #segundos
}



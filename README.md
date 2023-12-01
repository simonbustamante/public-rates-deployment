

# AWS Terraform and AWS Glue/Lambda Configuration

This repository contains Terraform configuration for AWS and scripts for AWS Glue and Lambda. It is designed to set up and automate specific data handling and analysis processes in AWS.

## Repository Structure

The repository is divided into several main sections:

1. **Terraform Configuration**: Contains the Terraform configuration files to establish necessary resources on AWS.
2. **AWS Glue Scripts**: Includes Python scripts for processing data using AWS Glue.
3. **AWS Lambda Functions**: Contains a Lambda function script to perform specific tasks in response to events.

### 1. Terraform Configuration

The Terraform configuration includes the definition of resources such as S3 buckets, Glue jobs, crawlers, step functions, and SNS notifications. Local variables and resources like `null_resource` are used for script management and Glue job configuration. 

#### Configuration Example

```terraform
locals {
  ...
}

resource "aws_glue_job" "create_job_public_rates_glue" {
  ...
}

resource "aws_sns_topic" "logging_error_topic_prd" {
  ...
}
```

### 2. AWS Glue Scripts

The AWS Glue scripts are written in Python and are used for data processing and transformation. An example is included that demonstrates data handling, field name transformation, and writing to S3.

#### Script Example

```python
import boto3
from awsglue.transforms import *
...

def run():
    ...
```

### 3. AWS Lambda Functions

A Lambda function is included that is designed to run queries in Athena and perform actions based on the results. It uses the Boto3 SDK to interact with other AWS services.

#### Lambda Function Example

```python
import json
import boto3

def lambda_handler(event, context):
    ...
```

## Usage

To use this repository:

1. Ensure you have Terraform installed and AWS credentials configured.
2. Run `terraform init` to initialize the working directory.
3. Modify the configuration files as needed.
4. Execute `terraform apply` to apply the changes in AWS.


import boto3
from boto3.dynamodb.conditions import Attr
import json
import pandas as pd
import time
import hashlib
from datetime import date
import os
import ast
from botocore.config import Config


config = Config(
   retries = {
      'max_attempts': 5,
      'mode': 'standard'
   }
)


bedrock = boto3.client("bedrock")
bedrock_runtime = boto3.client("bedrock-runtime", config=config)
ddb = boto3.resource('dynamodb')
dynamodb = boto3.client('dynamodb')

response_s = dynamodb.scan(
    TableName=os.environ['prompt_catalog'])

table = ddb.Table(os.environ['benchmark_table'])

model_shape = json.loads(os.environ['model_shape'])
model_shape = ast.literal_eval(str(model_shape))
 
supported_models = os.environ['supported_models']
supported_models = ast.literal_eval(supported_models)

today_date = date.today()

def computeMD5hash(my_string):
    m = hashlib.md5()
    m.update(my_string.encode('utf-8'))
    return m.hexdigest()

def get_prompt_result(model_id,body):
    body = json.dumps(body)
    print(body)
    resp = bedrock_runtime.invoke_model(modelId=model_id, body=body)
    return json.loads(resp['body'].read()), resp
    
def put_item_anthropic(model, response, today_date, resp, metadata, model_shape):
    table.put_item(
    Item={
        "model_prompt_id" : model + "_" + response['id'].get('S') ,
        "date" : str(today_date),
        "output_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-output-token-count"],
        "output" : resp["content"][0]["text"],
        "output_hash" : computeMD5hash(resp["content"][0]["text"]),
        "prompt_model_id" : response['id'].get('S') + "_" + model,
        "latency" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-invocation-latency"],
        "model_config": str(model_shape),
        "input_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-input-token-count"]
    })

def put_item_amazon(model, response, today_date, resp, metadata, model_shape):
    table.put_item(
        Item={
            "model_prompt_id" : model + "_" + response['id'].get('S'),
            "date" : str(today_date),
            "output_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-output-token-count"],
            "output" : resp["results"][0]["outputText"],
            "output_hash" : computeMD5hash(resp["results"][0]["outputText"]),
            "prompt_model_id" : response['id'].get('S') + "_" + model,
            "latency" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-invocation-latency"],
            "model_config": str(model_shape),
            "input_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-input-token-count"],
            
    })  

def put_item_ai21(model, response, today_date, resp, metadata, model_shape):
    table.put_item(
        Item={
            "model_prompt_id" : model + "_" + response['id'].get('S') ,
            "date" : str(today_date),
            "output_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-output-token-count"],
            "output" : resp["completions"][0]["data"]["text"],
            "output_hash" : computeMD5hash(resp["completions"][0]["data"]["text"]),
            "prompt_model_id" : response['id'].get('S') + "_" + model,
            "latency" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-invocation-latency"],
            "model_config": str(model_shape),
            "input_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-input-token-count"]
    })
    
def put_item_cohere(model, response, today_date, resp, metadata, model_shape):
    table.put_item(
        Item={
            "model_prompt_id" : model + "_" + response['id'].get('S') ,
            "date" : str(today_date),
            "output_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-output-token-count"],
            "output" : resp["text"],
            "output_hash" : computeMD5hash(resp["text"]),
            "prompt_model_id" : response['id'].get('S') + "_" + model,
            "latency" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-invocation-latency"],
            "model_config": str(model_shape[1]),
            "input_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-input-token-count"]
    })

def put_item_meta(model, response, today_date, resp, metadata, model_shape): 
    table.put_item(
        Item={
            "model_prompt_id" : model + "_" + response['id'].get('S') ,
            "date" : str(today_date),
            "output_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-output-token-count"],
            "output" : resp["generation"].lstrip(),
            "output_hash" : computeMD5hash(resp["generation"].lstrip()),
            "prompt_model_id" : response['id'].get('S') + "_" + model,
            "latency" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-invocation-latency"],
            "model_config": str(model_shape),
            "input_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-input-token-count"]
    })

def put_item_mistral(model, response, today_date, resp, metadata, model_shape):
    table.put_item(
    Item={
        "model_prompt_id" : model + "_" + response['id'].get('S') ,
        "date" : str(today_date),
        "output_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-output-token-count"],
        "output" : resp['outputs'][0]['text'],
        "output_hash" : computeMD5hash(resp['outputs'][0]['text']),
        "prompt_model_id" : response['id'].get('S') + "_" + model,
        "latency" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-invocation-latency"],
        "model_config": str(model_shape),
        "input_token_count" : metadata["ResponseMetadata"]["HTTPHeaders"]["x-amzn-bedrock-input-token-count"]
    })

def try_prompts():
    for response in response_s["Items"]:
        for model in supported_models:
            print(f"\tModel: {model}")
            body = model_shape.copy()

            if model.startswith("anthropic"):
                body["messages"][0]["content"] = response['prompt'].get('S')
            elif model.startswith("amazon.titan"):
                body["inputText"] = response['prompt'].get('S')
            elif model.startswith("ai21"):
                body["prompt"] = response['prompt'].get('S')
            elif model.startswith("cohere.command-r"):
                body = body[1]
                body["message"] = response['prompt'].get('S')
            elif model.startswith("meta"):
                body["prompt"] = response['prompt'].get('S')
            elif model.startswith("mistral"):
                body["prompt"] = response['prompt'].get('S')
            
            resp, metadata = get_prompt_result(model, body)
            
            data_old = []
            scan_kwargs = {
                "FilterExpression": Attr('model_prompt_id').eq(f"{model}_{response['id'].get('S')}")
            }
            
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs["ExclusiveStartKey"] = start_key
                response_old = table.scan(**scan_kwargs)
                data_old.extend(response_old.get("Items", []))
                start_key = response_old.get("LastEvaluatedKey", None)
                done = start_key is None
            
            if model.startswith("anthropic"):
                if len(data_old) == 0:
                    put_item_anthropic(model, response, today_date, resp, metadata, model_shape)
                elif computeMD5hash(resp["content"][0]["text"]) != data_old[-1]['output_hash']:
                    put_item_anthropic(model, response, today_date, resp, metadata, model_shape)
    
            elif model.startswith("amazon.titan"):
                if len(data_old) == 0:
                    put_item_amazon(model, response, today_date, resp, metadata, model_shape)
                elif computeMD5hash(resp["results"][0]["outputText"]) != data_old[-1]['output_hash']:
                    put_item_amazon(model, response, today_date, resp, metadata, model_shape)
            
            elif model.startswith("ai21"):
                if len(data_old) == 0:
                    put_item_ai21(model, response, today_date, resp, metadata, model_shape)
                elif computeMD5hash(resp["completions"][0]["data"]["text"]) != data_old[-1]['output_hash']:
                    put_item_ai21(model, response, today_date, resp, metadata, model_shape)
                
            elif model.startswith("cohere.command-r-v1:0") or model.startswith("cohere.command-r-plus-v1:0"):
                if len(data_old) == 0:
                    put_item_cohere(model, response, today_date, resp, metadata, model_shape)
                elif computeMD5hash(resp["text"]) != data_old[-1]['output_hash']:
                    put_item_cohere(model, response, today_date, resp, metadata, model_shape)

            elif model.startswith("meta"):
                if len(data_old) == 0:
                    put_item_meta(model, response, today_date, resp, metadata, model_shape)
                elif computeMD5hash(resp["generation"].lstrip()) != data_old[-1]['output_hash']:
                    put_item_meta(model, response, today_date, resp, metadata, model_shape)

            elif model.startswith("mistral"):
                if len(data_old) == 0:
                    put_item_mistral(model, response, today_date, resp, metadata, model_shape)
                elif computeMD5hash(resp['outputs'][0]['text']) != data_old[-1]['output_hash']:
                    put_item_mistral(model, response, today_date, resp, metadata, model_shape)

def lambda_handler(event, context):

    try_prompts()

    return {
        'statusCode': 200,
        'body': json.dumps('Done!')
    }

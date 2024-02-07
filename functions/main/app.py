import boto3
from boto3.dynamodb.conditions import Attr
import json
import pandas as pd
import time
import hashlib
from datetime import date
import os
import ast


bedrock = boto3.client("bedrock")
bedrock_runtime = boto3.client("bedrock-runtime")
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
    start_time = time.time()
    resp = bedrock_runtime.invoke_model(modelId=model_id, body=body)
    end_time = time.time()
    elapsed_time = end_time - start_time
    return json.loads(resp['body'].read()), elapsed_time

def put_item_anthropic(model, response, today_date, resp, elapsed_time, model_shape):
    table.put_item(
    Item={
        "model_prompt_id" : model + "_" + response['id'].get('S') ,
        "date" : str(today_date),
        "token_size" : len(resp["completion"].replace(" ","")),
        "output" : resp["completion"],
        "output_hash" : computeMD5hash(resp["completion"]),
        "prompt_model_id" : response['id'].get('S') + "_" + model,
        "latency": str(elapsed_time),
        "model_config": str(model_shape)
    })

def put_item_amazon(model, response, today_date, resp, elapsed_time, model_shape):
    table.put_item(
        Item={
            "model_prompt_id" : model + "_" + response['id'].get('S'),
            "date" : str(today_date),
            "token_size" : resp["results"][0]["tokenCount"],
            "output" : resp["results"][0]["outputText"],
            "output_hash" : computeMD5hash(resp["results"][0]["outputText"]),
            "prompt_model_id" : response['id'].get('S') + "_" + model,
            "latency": str(elapsed_time),
            "model_config": str(model_shape)
    })  

def put_item_ai21(model, response, today_date, resp, elapsed_time, model_shape):
    table.put_item(
        Item={
            "model_prompt_id" : model + "_" + response['id'].get('S') ,
            "date" : str(today_date),
            "token_size" : len(resp["completions"][0]["data"]["tokens"]),
            "output" : resp["completions"][0]["data"]["text"],
            "output_hash" : computeMD5hash(resp["completions"][0]["data"]["text"]),
            "prompt_model_id" : response['id'].get('S') + "_" + model,
            "latency": str(elapsed_time),
            "model_config": str(model_shape)
    })
    
def put_item_cohere(model, response, today_date, resp, elapsed_time, model_shape): 
    table.put_item(
        Item={
            "model_prompt_id" : model + "_" + response['id'].get('S') ,
            "date" : str(today_date),
            "token_size" : len(resp["generations"][0]["text"].replace(" ","")),
            "output" : resp["generations"][0]["text"],
            "output_hash" : computeMD5hash(resp["generations"][0]["text"]),
            "prompt_model_id" : response['id'].get('S') + "_" + model,
            "latency": str(elapsed_time),
            "model_config": str(model_shape)
    })


def try_prompts():
    for response in response_s["Items"]:
        for model in supported_models:
            print(f"\tModel: {model}")
            body = model_shape.copy()

            if model.startswith("anthropic"):
                body["prompt"] = f"\n\nHuman:{response['prompt'].get('S')}\n\nAssistant:"
            elif model.startswith("amazon.titan"):
                body["inputText"] = response['prompt'].get('S')
            elif model.startswith("ai21"):
                body["prompt"] = response['prompt'].get('S')
            elif model.startswith("cohere"):
                body["prompt"] = response['prompt'].get('S')
            
            resp, elapsed_time = get_prompt_result(model, body)
            
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
                    put_item_anthropic(model, response, today_date, resp, elapsed_time, model_shape)
                elif computeMD5hash(resp["completion"]) != data_old[-1]['output_hash']:
                    put_item_anthropic(model, response, today_date, resp, elapsed_time, model_shape)
    
            elif model.startswith("amazon.titan"):
                if len(data_old) == 0:
                    put_item_amazon(model, response, today_date, resp, elapsed_time, model_shape)
                elif computeMD5hash(resp["results"][0]["outputText"]) != data_old[-1]['output_hash']:
                    put_item_amazon(model, response, today_date, resp, elapsed_time, model_shape)
            
            elif model.startswith("ai21"):
                if len(data_old) == 0:
                    put_item_ai21(model, response, today_date, resp, elapsed_time, model_shape)
                elif computeMD5hash(resp["completions"][0]["data"]["text"]) != data_old[-1]['output_hash']:
                    put_item_ai21(model, response, today_date, resp, elapsed_time, model_shape)
                
            elif model.startswith("cohere"):
                if len(data_old) == 0:
                    put_item_cohere(model, response, today_date, resp, elapsed_time, model_shape)
                elif computeMD5hash(resp["generations"][0]["text"]) != data_old[-1]['output_hash']:
                    put_item_cohere(model, response, today_date, resp, elapsed_time, model_shape)

def lambda_handler(event, context):

    try_prompts()

    return {
        'statusCode': 200,
        'body': json.dumps('Done!')
    }

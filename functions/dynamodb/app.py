import json
import logging
from botocore.exceptions import ClientError
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
import requests
import boto3

def send_response(event, context, response_status):
    response_body = {'Status': response_status,
                     'Reason': 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
                     'PhysicalResourceId': context.log_stream_name,
                     'StackId': event['StackId'],
                     'RequestId': event['RequestId'],
                     'LogicalResourceId': event['LogicalResourceId']}

    LOG.info(f'RESPONSE BODY: {json.dumps(response_body)}')

    try:
        req = requests.put(event['ResponseURL'], data=json.dumps(response_body))
        if req.status_code != 200:
            LOG.error(req)
            raise Exception('Recieved non 200 response while sending response to CFN.')
        return
    except requests.exceptions.RequestException as e:
        LOG.error('Exception while sending back the request to CFN', e)


def lambda_handler(event, context):
    LOG.info(f'REQUEST RECEIVED: {event}')
    # For Delete requests, immediately send a SUCCESS response.
    if event['RequestType'] == 'Delete':
        LOG.info('Entering Delete')
        send_response(event, context, "SUCCESS")
        return
    
    response_status = 'FAILED'
    try:
        table_name = event['ResourceProperties']['TableName']
        dynamo_db = boto3.resource('dynamodb')
        ddbclient = boto3.client('dynamodb')
        table = dynamo_db.Table(table_name)
        prompts_to_test = {
                "code": [
                    {
                        "prompt": "Explain simply what this function does:\n```\ndef func(lst):\n    if len(lst) == 0:\n        return []\n    if len(lst) == 1:\n        return [lst]\n    l = []\n    for i in range(len(lst)):\n        x = lst[i]\n        remLst = lst[:i] + lst[i+1:]\n        for p in func(remLst):\n            l.append([x] + p)\n    return l\n```"
                    },
                    {
                        "prompt": "Explain the bug in the following code:\n\n```\nfrom time import sleep\nfrom multiprocessing.pool import ThreadPool\n \ndef task():\n    sleep(1)\n    return 'all done'\n\nif __name__ == '__main__':\n    with ThreadPool() as pool:\n        result = pool.apply_async(task())\n        value = result.get()\n        print(value)\n```"
                    },
                    {
                        "prompt": "Write a Python function that prints the next 20 leap years. Reply with only the function."
                    },
                    {
                        "prompt": "Write a Python function to find the nth number in the Fibonacci Sequence."
                    },
                ],
                "creativity": [
                    {
                    "prompt": "Give me the SVG code for a smiley. It should be simple. Reply with only the valid SVG code and nothing else."
                    },
                    {"prompt": "Tell a joke about going on vacation."},
                    {"prompt": "Write a 12-bar blues chord progression in the key of E"},
                    {
                        "prompt": "Write me a product description for a 100W wireless fast charger for my website."
                    },
                ],
                "instruct": [
                    {
                        "prompt": "Extract the name of the vendor from the invoice: PURCHASE #0521 NIKE XXX3846. Reply with only the name."
                    },
                    {
                        "prompt": 'Help me find out if this customer review is more "positive" or "negative".\n\nQ: This movie was watchable but had terrible acting.\nA: negative\nQ: The staff really left us our privacy, we’ll be back.\nA: '
                    },
                    {
                        "prompt": 'What are the 5 planets closest to the sun? Reply with only a valid JSON array of objects formatted like this:\n\n```\n[{\n  "planet": string,\n  "distanceFromEarth": number,\n  "diameter": number,\n  "moons": number\n}]\n```'
                    },
                ],
                "knowledge": [
                    {
                        "prompt": "Explain in a short paragraph quantum field theory to a high-school student."
                    },
                    {"prompt": "Is Taiwan an independent country?"},
                    {
                        "prompt": 'Translate this to French, you can take liberties so that it sounds nice: "blossoms paint the spring, nature’s rebirth brings delight and beauty fills the air."'
                    },
                ],
                "reflexion": [
                    {
                        "prompt": "Argue for and against the use of kubernetes in the style of a haiku."
                    },
                    {
                        "prompt": "Give two concise bullet-point arguments against the Münchhausen trilemma (don't explain what it is)."
                    },
                    {
                        "prompt": "I went to the market and bought 10 apples. I gave 2 apples to the neighbor and 2 to the repairman. I then went and bought 5 more apples and ate 1. I also gave 3 bananas to my brother. How many apples did I remain with? Let's think step by step."
                    },
                    {
                        "prompt": "Sally (a girl) has 3 brothers. Each brother has 2 sisters. How many sisters does Sally have?"
                    },
                    {
                        "prompt": "Sally (a girl) has 3 brothers. Each brother has 2 sisters. How many sisters does Sally have? Let's think step by step."
                    },
                ],
        }
        id = 100
        for category, prompts in prompts_to_test.items():
            #print("category: ", category)
            for prompt in prompts:
                #print("prompt: ", prompt)
                
                table.put_item(
                    Item={
                        "id": category + "_" + str(id),
                        "prompt": prompt['prompt'],
                    })
                id = id + 100

        describe_response = ddbclient.describe_table(
            TableName= table_name
        )
    except ClientError as e:
        LOG.error(e.response['Error']['Code'])
    except Exception as e:
        LOG.error(f'Exception in the lambda handler, {e}')
    
    if describe_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        LOG.info(f'table: {table_name} is updated with prompts')
        response_status = "SUCCESS"
        send_response(event, context, response_status)
    
    else:
        LOG.info(f'prompts are not added')
        send_response(event, context, response_status) 


    
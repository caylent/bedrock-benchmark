# Bedrock Benchmark
This project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders:

- functions - Code for the application's Lambda functions to Call Bedrock APIs.
- statemachines - Definition for the state machine that orchestrates the bedrock benchmark workflow.
- template.yaml - A template that defines the application's AWS resources.

This application creates a bedrock bemchmark workflow which runs on a pre-defined schedule. The application uses several AWS resources, including Step Functions state machines, DynamoDB, Lambda functions and an EventBridge rule trigger. These resources are defined in the template.yaml file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Deploy the sample application
To use the SAM CLI, you need the following tools:

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build
sam validate
sam deploy --guided
```

## adding the prompts to DynamoDB
After successfully deploying the solution you need to run the 'create_prompt_catalog.py' inside /scripts folder to populate the example prompts. You can alwaysre-run the scripts to add/modify the prompt list at any time.

## UI
We used Streamlit for a simple UI and deployed it to SageMaker Studio. Follow these steps to run the streamlit app.

```
sh setup.sh #install dependencies
sh run.sh #run the streamlit app
sh cleanup.sh #clean up 
```

## Cleanup
To delete the application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
sam delete --stack-name "bedrockbenchmark"
```

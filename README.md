# News Headlines Sentiment Analyzer

## Table of Contents

1. [Architecture](#architecture)
   1. [Buckets](#buckets)
   2. [Model Pipeline](#model-pipeline)
      1. [Data](#data)
   3. [Deployment Pipeline](#deployment-pipeline)
   4. [ECS Application](#ecs-application)
2. [Deployment Instructions](#deployment-instructions)

## Architecture

![sentiment-analysis drawio](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/25a8bc08-8557-4c2e-b99b-7569dc0c04a9)

### Buckets
1. **data-bucket**: This bucket holds raw data that will be used for preprocessing.
2. **sagemaker-default-bucket**: This is the default bucket created by SageMaker. It stores various code and data artifacts related to the SageMaker pipeline structure and execution.

### Model Pipeline
   
1. Operator manually triggers the execution of the model pipeline.
2. The Preprocessing step retrieves data from the raw bucket and generates `train.csv` and `validation.csv`, which are used for training and validation. It also creates `test.jsonl` and `labels.csv`, which are utilized for batch transformation and evaluation.
3. The Training step trains the model using the training and validation datasets.
4. The CreateModel step creates the model based on the training artifacts.
5. The BatchTransform step applies the model to `test.jsonl` and produces `test.jsonl.out` containing prediction labels and confidence scores.
6. The ModelEvaluation step evaluates the model by comparing the values in `test.jsonl.out` and `labels.csv`. It generates an evaluation file, `evaluation.json`, which includes precision, recall, accuracy, and f-score.
7. The RegisterModel step registers the model with the quality metrics obtained from `evaluation.json`.
8. The Operator can then review the model metrics and approve the model if necessary.

#### Data 

1. **data.csv**
   
   ```
   2,"According to Gran , the company has no plans to move all production to Russia , although that is where the company is growing ."
   2,"Technopolis plans to develop in stages an area of no less than 100,000 square meters in order to host companies working in computer technologies and telecommunications , the statement said ."
   0,"The international electronic industry company Elcoteq has laid off tens of employees from its Tallinn facility ; contrary to earlier layoffs the company contracted the ranks of its office workers , the daily Postimees reported ."
   ...
   ```

2. **train.csv**
   
   ```
   __label__good "teleste and sentry 360 have formed an integration partnership between sentry s advanced 360 degree immersive camera product line and teleste s enterprise video management systems"
   __label__good "altimo and teliasonera said yesterday that usmanov would be welcome to join the new company"
   __label__neutral "the market value of one crane is some usd6m reported

3. **validation.csv**
   
   ```
   __label__neutral "According to CEO Hannu Syrjänen, a new common name and visual identity is required as the group has grown and internationalized."
   __label__neutral "Currently, YIT builds a housing estate, Zapadnye Vorota, covering an area of 26,000 square meters in the city and a house of 9,910 square meters, which will be completed at the end of 2009."
   __label__neutral "The recruitment is related to the relocation of Stora Enso's research operations to Karlstad, central Sweden."
   ...
   ```

4. **test.jsonl**
   
   ```
   {"source": "Automation makes it possible to conduct several tests simultaneously."}
   {"source": "The Estonian Parliament was set to vote on amendments to the excise duty law on Wednesday that would add 0.42 kroons to the price of a liter of diesel and 0.45 kroons to the price of a liter of gasoline from the start of 2010."}
   {"source": "Helsinki (Thomson Financial) - Kone said it has won four orders in Saudi Arabia, United Arab Emirates, and Qatar worth 40 million euros."}
   ```

5. **labels.csv**
   
   ```
   __label__neutral
   __label__neutral
   __label__good
   ```

6. **test.jsonl.out**
   
   ```
   {"label": ["__label__neutral"], "prob": [0.9413388967514038]}
   {"label": ["__label__good"], "prob": [0.4687191843986511]}
   {"label": ["__label__neutral"], "prob": [0.7470827698707581]}
   ```

7. **evaluation.json**
   
   ```
   {"regression_metrics": {"accuracy": {"value": 0.48760330578512395}, "precision": {"value": 0.28342173262613896}, "recall": {"value": 0.30607037335482135}, "f-score": {"value": 0.29269601677148843}}}
   ```

### Deployment Pipeline

The deployment pipeline consists of several steps that are triggered based on the approval of a model version:

1. Operator Approval: The operator has the authority to approve or reject a model version. If they reject it, no further action is taken. If they approve it, the pipeline progresses to the next steps.

2. Model Package State Change Event: When a model version is approved, a [Model Package State Change](https://docs.aws.amazon.com/sagemaker/latest/dg/automating-sagemaker-with-eventbridge.html#eventbridge-model-package) event is emitted.

3. EventBridge Rule: An EventBridge rule is set up to trigger the **TriggerModelDeploy Lambda** whenever a model version with the status "Approved" is detected.

4. TriggerModelDeploy Lambda: The **TriggerModelDeploy Lambda** retrieves the ARN of the approved model package version from the event. It then writes this information to the **s3://data-bucket/approved-model.json** file.

5. CodePipeline Source Stage: A **CodePipeline** is configured to monitor changes in the **s3://data-bucket/approved-model.json** file. Whenever the file is updated, it triggers the initial source action of the pipeline.

6. CodePipeline Deploy Stage: The **CodePipeline** invokes the **CreateOrUpdateEndpoint Lambda** in the deploy stage. This lambda creates an EndpointConfig and either creates a new Endpoint or updates the existing one with the specified EndpointConfig. It then waits for the endpoint to reach the "InService" state.

Note: EndpointConfigs, which do not incur any charges, are not removed as part of this pipeline.

By following this pipeline, the approved model versions can be seamlessly deployed to the endpoint for serving predictions.   

### ECS Application
   
1. User Interface:
   - A Flask application serves a frontend rendered with Vue.js to the browser.
   - Users can input a headline and click the "Analyze" button.
   - The browser receives a confirmation of whether the headline is categorized as **Good**, **Bad**, or **Neutral**.

2. Containerization:
   - The Flask application is containerized using a Docker file.

3. Deployment:
   - The containerized Flask application is deployed using ECS (Elastic Container Service).
   - The ECS tasks are hosted behind an Application Load Balancer.
   - **Note**: For simplicity, in this application, the ECS tasks are deployed over public subnets, and the same security group is used for both the Application Load Balancer and ECS. In practice, it is recommended to deploy the ECS tasks over private subnets and configure the security group of the ECS tasks to only allow traffic from the Application Load Balancer. The Application Load Balancer should be internet-facing and accept traffic from the internet.
   - Other considerations such as scaling, redundancy, monitoring, etc., are not fully implemented in this application beyond the basic requirements needed for a functional demo with ECS logging for debugging.
   
## Deployment Instructions

1. Prepare your Python environment. I recommend using Conda with Python 3.9. Execute the following commands:

   ```shell
   conda create -n test-news python=3.9
   pip install -r requirements.txt
   ```

2. Configure AWS (if you haven't done so already) by running:

   ```shell
   aws configure
   ```

3. Before proceeding, you need to configure an AWS role. Otherwise, the following error message is thrown: "ValueError: The current AWS identity is not a role.":

   - See [AWS CLI Configure Role documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-role.html) for more information.
   - I named my role **sagemaker-role** and granted it **AdministratorAccess**.

        ![sagemaker-role](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/fcda9033-701d-403e-b2c6-2699229e7ee3)

        ![sagemaker-trust-entity](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/956136dc-82c2-486c-9365-8e153ffa6f85)

   - Update the `~/.aws/config` file with the following content:

     ```ini
     [default]
     region = us-east-1
     
     [profile sagemaker-role]
     role_arn = arn:aws:iam::<account-id>:role/sagemaker-role
     source_profile = default
     ```

   - Update your environment variables by executing the following commands:

     ```shell
     export AWS_PROFILE=sagemaker-role
     export AWS_DEFAULT_REGION=us-east-1
     ```

4. Let's check the available stacks by running `cdk list`:

   ```
   DataBucketStack
   DataUploadStack
   SagemakerSetupStack
   SagemakerModelPipelineStack
   DeploymentPipelineLambdasStack
   DeploymentPipelineStack
   DeploymentPipelineTriggerStack
   EcsApplicationStack
   ```

5. Deploy the `SagemakerModelPipelineStack`, which will automatically deploy all of the stacks above it in the aforementioned list:

   ```shell
   cdk deploy --require-approval never SagemakerModelPipelineStack
   ```

   This will:
   1. Create a bucket to store raw data.
   2. Upload the raw data to the newly created bucket.
   3. Create a domain named `news-headlines` and a user profile named `my-user`.
   4. Set up the entire model pipeline, which can be manually executed in Sagemaker Studio.

   ![open-studio](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/2e042d18-8a16-4521-b619-879df827d8d2)
   ![pipeline](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/a7b25cab-46c5-4d71-b658-1867be479fe0)
   ![model-quality](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/e914c320-ae1e-40fe-9577-b0e0c6b87e83)
6. Deployment Pipeline:
   - Deploy the `DeploymentPipelineTriggerStack` and the `DeploymentPipelineStack`.
   - These stacks will perform the following actions:
     1. Create the **Trigger Lambda**, which triggers the code pipeline by writing to **s3://data-bucket/approved-model.json**.
     2. Create the **CreateOrUpdateEndpoint Lambda**, which creates or updates the endpoint to the approved SageMaker model version.
     3. Create an EventBridge rule that triggers the **Trigger Lambda** whenever a model is approved.
     4. Create a CodePipeline with a Source stage that watches for changes to **s3://data-bucket/approved-model.json**. This is followed by a Deploy stage that triggers the **CreateOrUpdateEndpoint Lambda** to deploy the SageMaker endpoint.
   ![update-model-version-status](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/d65e4b9e-1f33-4953-9aad-edbddaa77029)
   ![trigger-logs](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/824cf15d-7437-46c4-809d-3f1b6ce99e28)
   ![codepipeline](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/a032ea04-cf52-41cd-b02f-ba01f3588f7e)
   ![create-or-update-logs](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/93c87f49-bf99-46e9-92f6-450addde4c8c)

![Endpoints](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/4da71971-8652-4557-895b-e5a4c919881a)

7. Application Deployment:
   - Deploy the `EcsApplicationStack` to launch the application.
   - Navigate to EC2 > Load Balancers and find the corresponding Load Balancer.
   - Copy and paste the DNS name of the Load Balancer in a browser using HTTP to access the application.

   ![alb](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/ff9cf6a3-0c00-4aaa-8374-8e4542c0b6a6)
   ![analyze-good](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/acc91543-b055-4bab-a304-a264f8e60fc6)
   ![analyze-bad](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/253c0b19-eb03-4b70-95e4-03020e817be8)

Note: When debugging ECS tasks, it can be helpful to refer to the ECS Task logs.

   ![ecs-task-logs](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/df75101c-57fc-46cf-b9d3-2e3491feaadf)

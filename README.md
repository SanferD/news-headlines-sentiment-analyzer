# News Headlines Sentiment Analyzer

## Table of Contents

The hamburger button on the left side of README.md title contains the table of contents.

## Architecture

![sentiment-analysis drawio](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/990a70dd-a1c0-4735-8a7d-d6169c74dd16)

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

        ![sagemaker-role](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/9a1313ba-a42e-4762-8b15-309ae3bf6c8b)
        ![sagemaker-trust-entity](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/eeeeff25-8fdd-4cb6-b344-584f690300fc)

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

   ![open-studio](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/e94ddbd6-610e-4557-9cbe-46e7ab1ee38d)
   ![sagemaker-model-pipeline](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/4eeae6f8-d3cb-451b-8369-b80c49949754)
   ![model-quality](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/4257fe93-0797-4c46-99b0-0f177cd1870e)
6. Deployment Pipeline:
   - Deploy the `DeploymentPipelineTriggerStack` and the `DeploymentPipelineStack`.
   - These stacks will perform the following actions:
     1. Create the **Trigger Lambda**, which triggers the code pipeline by writing to **s3://data-bucket/approved-model.json**.
     2. Create the **CreateOrUpdateEndpoint Lambda**, which creates or updates the endpoint to the approved SageMaker model version.
     3. Create an EventBridge rule that triggers the **Trigger Lambda** whenever a model is approved.
     4. Create a CodePipeline with a Source stage that watches for changes to **s3://data-bucket/approved-model.json**. This is followed by a Deploy stage that triggers the **CreateOrUpdateEndpoint Lambda** to deploy the SageMaker endpoint.
   ![update-model-version-status](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/909b9320-cf76-4da4-86bf-b90435231da5)
   ![trigger-logs](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/75338f59-5c0c-47ac-a868-d187649c8a86)
   ![codepipeline](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/9b5e7a6e-9408-4573-a863-e0fcaedbdb97)
   ![create-or-update-logs](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/e50b0273-6c65-4b52-990a-c51df913ad4d)
   ![endpoints](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/e0b955e8-9a89-4ceb-9f7f-df2e9d9f3895)

7. Application Deployment:
   - Deploy the `EcsApplicationStack` to launch the application.
   - Navigate to EC2 > Load Balancers and find the corresponding Load Balancer.
   - Copy and paste the DNS name of the Load Balancer in a browser using HTTP to access the application.

   ![alb](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/cbd3dbf0-4ceb-4e67-8911-77c558fd15df)
   ![analyze-good](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/59080396-ffa1-40e0-a514-e0633af71af9)
   ![analyze-bad](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/d7c956eb-230e-496e-845f-79ec589c2d6a)

Note: When debugging ECS tasks, it can be helpful to refer to the ECS Task logs.

   ![ecs-task-logs](https://github.com/SanferD/news-headlines-sentiment-analyzer/assets/9338001/edd3ed7c-c604-49b7-ad0d-a26ff251d225)
   
## TODOs

Although there is no guarantee that I will have the opportunity to investigate these areas, here are some topics I would like to explore:

1. Model monitoring and automated retraining for addressing model drift.
2. Enhancing model accuracy.
3. Designing an improved ModelPipeline to support multiple data scientists submitting custom PyTorch and TensorFlow models.
4. Implementing the ability to reject a model version and revert to the latest approved version.
5. Improving error handling in cases where a SageMaker endpoint is unavailable.

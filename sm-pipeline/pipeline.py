import json
import os
from os.path import join

import sagemaker
from sagemaker import Session, get_execution_role
from sagemaker.amazon.amazon_estimator import get_image_uri
from sagemaker.inputs import TrainingInput
from sagemaker.model import Model
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.transformer import Transformer
from sagemaker.workflow import parameters
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep, TrainingStep, TransformStep
from sagemaker.workflow.functions import Join

from scripts import constants

sagemaker_session = Session()
boto_session = sagemaker_session.boto_session
current_file_dir = os.path.dirname(__file__)
role = get_execution_role()

data_bucket_name = parameters.ParameterString(name="DataBucketName")

BASE_JOB_NAME = "news-headlines-sentiment-analysis"
IS_LOCAL_PIPELINE = False
MODEL_PACKAGE_GROUP_NAME = "news-headlines"
PIPELINE_DEFINITION_JSON_FILE_NAME = "pipeline.json"
PIPELINE_NAME = "news-headlines"
PRINT_DEFINITION = True
SKLEARN_FRAMEWORK_VERSION = "1.0-1"

preprocessing_instance_type = parameters.ParameterString(
    name="PreprocessingInstanceType", default_value="ml.m5.large")
preprocessing_instance_count = parameters.ParameterInteger(
    name="PreprocessingInstanceCount", default_value=1)

training_instance_type = parameters.ParameterString(
    name="TrainingInstanceType", default_value="ml.c4.4xlarge")
training_instance_count = parameters.ParameterInteger(
    name="TrainingInstanceCount", default_value=1)
training_instance_max_run = parameters.ParameterInteger(
    name="TrainingInstanceMaxRun", default_value=3600)

model_instance_type = parameters.ParameterString(
    name="ModelInstanceType", default_value="ml.m5.xlarge")

transform_instance_type = parameters.ParameterString(
    name="TransfromInstanceType", default_value="ml.m5.xlarge")
transform_instance_count = parameters.ParameterInteger(
    name="TransfromInstanceCount", default_value=1)

evaluation_instance_type = parameters.ParameterString(
    name="EvaluationInstanceType", default_value="ml.m5.xlarge")
evaluation_instance_count = parameters.ParameterInteger(
    name="EvaluationInstanceCount", default_value=1)

inference_instance_type = parameters.ParameterString(
    name="InferenceInstanceType", default_value="ml.m5.xlarge")


def generate_step_name(step):
    """Generate a step name for the given step.

    Args:
        step: The step for which to generate the name.

    Returns:
        The generated step name.
    """
    return f"{step}"


if IS_LOCAL_PIPELINE:
    pipeline_session = sagemaker.workflow.pipeline_context.LocalPipelineSession()
else:
    pipeline_session = sagemaker.workflow.pipeline_context.PipelineSession()


# Preprocessing Step
preprocessing_sklearn_processor = SKLearnProcessor(
    framework_version=SKLEARN_FRAMEWORK_VERSION,
    instance_type=preprocessing_instance_type,
    instance_count=preprocessing_instance_count,
    base_job_name=BASE_JOB_NAME,
    role=role,
    sagemaker_session=pipeline_session,
)

preprocessing_step = ProcessingStep(
    name=generate_step_name("Preprocessing"),
    processor=preprocessing_sklearn_processor,
    inputs=[
        ProcessingInput(
            source=join(current_file_dir, "scripts"),
            destination=str(constants.SCRIPTS_DIR),
        ),
        ProcessingInput(
            source=Join(
                on="/",
                values=["s3:/", data_bucket_name, "raw", "sentiment", "data", "data.csv"],
            ),
            destination=str(constants.INPUT_DIR),
        ),
    ],
    outputs=[
        ProcessingOutput(output_name=output_name, source=str(source))
        for (output_name, source) in [
            (constants.TRAIN_CHANNEL, constants.TRAIN_DIR),
            (constants.VAL_CHANNEL, constants.VAL_DIR),
            (constants.TEST_CHANNEL, constants.TEST_DIR),
            (constants.LABELS_CHANNEL, constants.LABELS_DIR),
        ]
    ],
    code=join(current_file_dir, "scripts/run_preprocessing.py"),
)

# Training Step
blazing_text_container = get_image_uri(boto_session.region_name, "blazingtext", "latest")
blazing_text_estimator = sagemaker.estimator.Estimator(
    blazing_text_container,
    role,
    instance_count=training_instance_count,
    instance_type=training_instance_type,
    volume_size=30,
    max_run=training_instance_max_run,
    input_mode="File",
    hyperparameters={
        "mode": "supervised",
        "epochs": 100,
        "min_count": 2,
        "learning_rate": 0.05,
        "vector_dim": 10,
        "early_stopping": True,
        "patience": 4,
        "min_epochs": 5,
        "word_ngrams": 2,
    },
)

preproc_step_outputs = preprocessing_step.properties.ProcessingOutputConfig.Outputs

estimator_inputs = {
    constants.TRAIN_CHANNEL: TrainingInput(
        s3_data=preproc_step_outputs[constants.TRAIN_CHANNEL].S3Output.S3Uri,
        distribution="FullyReplicated",
        content_type="text/plain",
        s3_data_type="S3Prefix",
    ),
    constants.VAL_CHANNEL: TrainingInput(
        s3_data=preproc_step_outputs[constants.VAL_CHANNEL].S3Output.S3Uri,
        distribution="FullyReplicated",
        content_type="text/plain",
        s3_data_type="S3Prefix",
    ),
}

training_step = TrainingStep(
    name=generate_step_name("Training"),
    estimator=blazing_text_estimator,
    inputs=estimator_inputs,
)

# Create Model step
model = Model(
    image_uri=blazing_text_estimator.training_image_uri(),
    model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
    sagemaker_session=pipeline_session,
    role=role,
)

model_step = ModelStep(
   name=generate_step_name("CreateModel"),
   step_args=model.create(instance_type=model_instance_type),
)

# Batch Transform step
transformer = Transformer(
    model_name=model_step.properties.ModelName,
    instance_count=transform_instance_count,
    instance_type=transform_instance_type,
    sagemaker_session=pipeline_session,
    assemble_with="Line",
    strategy="SingleRecord",
)

transform_step = TransformStep(
    name=generate_step_name("BatchTransform"),
    step_args=transformer.transform(
        data=preproc_step_outputs[constants.TEST_CHANNEL].S3Output.S3Uri,
        split_type="Line",
        content_type="application/jsonlines",
    ),
)

# Model Evaluation step
evaluation_sklearn_processor = sagemaker.sklearn.processing.SKLearnProcessor(
    framework_version=SKLEARN_FRAMEWORK_VERSION,
    instance_type=evaluation_instance_type,
    instance_count=evaluation_instance_count,
    base_job_name=BASE_JOB_NAME,
    role=role,
    sagemaker_session=pipeline_session,
)

evaluation_step = ProcessingStep(
    name=generate_step_name("ModelEvaluation"),
    processor=evaluation_sklearn_processor,
    inputs=[
        ProcessingInput(
            source=join(current_file_dir, "scripts"),
            destination=str(constants.SCRIPTS_DIR),
        ),
        ProcessingInput(
            source=transform_step.properties.TransformOutput.S3OutputPath,
            destination=str(constants.INPUT_TRANSFORM_DIR),
        ),
        ProcessingInput(
            source=preproc_step_outputs[constants.LABELS_CHANNEL].S3Output.S3Uri,
            destination=str(constants.INPUT_LABELS_DIR),
        ),
    ],
    outputs=[
        ProcessingOutput(
            output_name=constants.EVALUATION_CHANNEL,
            source=str(constants.EVALUATION_DIR),
        ),
    ],
    code=join(current_file_dir, 'scripts/run_evaluation.py'),
)

# Register Model step
evaluation_step_outputs = evaluation_step.properties.ProcessingOutputConfig.Outputs

register_model_step_args = model.register(
    content_types=["application/json"],
    response_types=["application/json"],
    inference_instances=[inference_instance_type],
    transform_instances=[transform_instance_type],
    model_package_group_name=MODEL_PACKAGE_GROUP_NAME,
    model_metrics=ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri=Join(
                on="/",
                values=[
                    evaluation_step_outputs[constants.EVALUATION_CHANNEL].S3Output.S3Uri,
                    constants.EVALUATION_FILE_NAME,
                ],
            ),
            content_type="application/json"
        ),
    ),
    image_uri=blazing_text_container,
)

register_model_step = ModelStep(
    name=generate_step_name("RegisterModel"),
    step_args=register_model_step_args,
    depends_on=[evaluation_step], # sagemaker unable to infer this without help
)

# Create pipeline
pipeline = Pipeline(
   name=PIPELINE_NAME, 
   parameters=[
        data_bucket_name,
        preprocessing_instance_type,
        preprocessing_instance_count,
        training_instance_type,
        training_instance_count,
        training_instance_max_run,
        model_instance_type,
        transform_instance_type,
        transform_instance_count,
        evaluation_instance_type,
        evaluation_instance_count,
        inference_instance_type,
   ],
   steps=[
        preprocessing_step,
        training_step,       
        model_step,
        transform_step,
        evaluation_step,
        register_model_step,
   ],
   sagemaker_session=pipeline_session,
)

# save the pipeline definition
definition = json.loads(pipeline.definition())
if PRINT_DEFINITION:
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(definition)

with open(join(current_file_dir, PIPELINE_DEFINITION_JSON_FILE_NAME), "w+") as f:
    json.dump(definition, f)

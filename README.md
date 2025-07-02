# SIEM Lake for Identity Logs - Proof of Concept (PoC) - MSK Version

This PoC demonstrates a SIEM (Security Information and Event Management) Lake built on AWS services, refactored to use Amazon MSK (Managed Streaming for Apache Kafka) as the primary streaming backbone. It focuses on ingesting, transforming, storing, and visualizing identity-related logs from multiple simulated application tenants and identity providers.

## Table of Contents

1.  [Architecture Overview (MSK Version)](#architecture-overview-msk-version)
2.  [Core Components (MSK Version)](#core-components-msk-version)
3.  [Prerequisites (MSK Version)](#prerequisites-msk-version)
4.  [Setup and Deployment (Manual - For understanding the flow)](#setup-and-deployment-manual---for-understanding-the-flow)
    *   [Terraform for Infrastructure](#terraform-for-infrastructure)
    *   [Post-Terraform Manual Steps](#post-terraform-manual-steps)
5.  [End-to-End Automation with `run_app.sh` (MSK Version)](#end-to-end-automation-with-run_appsh-msk-version)
6.  [Simulating and Ingesting Logs (MSK Version)](#simulating-and-ingesting-logs-msk-version)
7.  [Querying Logs in OpenSearch](#querying-logs-in-opensearch)
8.  [Setting Up the Dashboard](#setting-up-the-dashboard)
9.  [Testing and Validation (MSK Version)](#testing-and-validation-msk-version)
10. [Scaling the Solution (MSK Version)](#scaling-the-solution-msk-version)
11. [Security Considerations (MSK Version)](#security-considerations-msk-version)
12. [Artifacts Included (MSK Version)](#artifacts-included-msk-version)


## 1. Architecture Overview (MSK Version)

The system follows this general flow when refactored to use Amazon MSK:

```mermaid
graph TD
    subgraph "Log Sources (Simulated)"
        A[Log Generator Script with Kafka Client]
    end

    subgraph "Ingestion & Streaming Layer"
        B[Amazon MSK (Kafka Cluster)]
        C[MSK Topic: identity-logs]
    end

    subgraph "Consumption & Transformation Layer"
        D[AWS Lambda (MSK Consumer & Transformer)]
    end

    subgraph "Storage & Analysis Layer"
        E[AWS OpenSearch Service (in VPC)]
    end

    subgraph "Visualization Layer"
        F[AWS OpenSearch Dashboards]
    end

    A -- Kafka Messages --> B
    B -- Topic Messages --> C
    C -- Event Source Mapping --> D
    D -- Standardized JSON Logs (Bulk API) --> E
    E -- Queried Data --> F
```

*   **Simulated Log Source:** The `sample_log_generator.py` (modified with a Kafka client) produces identity logs.
*   **Ingestion & Streaming:** Logs are sent as messages to a topic (e.g., `identity-logs`) in an Amazon MSK (Managed Streaming for Apache Kafka) cluster.
*   **Consumption & Transformation:** An AWS Lambda function is triggered by new messages in the MSK topic. This Lambda:
    *   Consumes batches of messages from MSK.
    *   Transforms the raw log data into the standardized schema (reusing existing transformation logic).
*   **Storage:** The Lambda function bulk-ingests the transformed logs directly into AWS OpenSearch Service (deployed within a VPC).
*   **Visualization:** AWS OpenSearch Dashboards provide visualizations for login failure insights.

This architecture replaces AWS Kinesis Data Streams and Kinesis Data Firehose with Amazon MSK and a custom Lambda consumer. The original `architecture_diagram.md` may still be in the repository but reflects the Kinesis architecture.

## 2. Core Components (MSK Version)

*   **`sample_log_generator.py`**: Python script (modified) to simulate identity logs and produce them to an MSK Kafka topic. Requires `kafka-python`.
*   **`terraform/lambda_code/msk_consumer_lambda.py`**: Python script for the AWS Lambda function that consumes from MSK, transforms logs, and ingests into OpenSearch. Requires `opensearch-py` and `boto3` (for AWSV4SignerAuth).
*   **`opensearch_index_template.json`**: JSON defining the OpenSearch index mapping (remains largely the same).
*   **`sample_opensearch_query.json`**: Sample OpenSearch Query DSL (remains the same).
*   **`dashboard_configuration.md`**: Markdown describing the OpenSearch Dashboard setup (remains largely the same).
*   **`run_app.sh`**: Script (modified) to orchestrate the PoC setup (Terraform deployment) and log generation flow for the MSK architecture.
*   **`terraform/`**: Directory containing Terraform scripts (modified) for MSK-based infrastructure.
    *   **`terraform/run.sh`**: Helper script to manage Terraform deployment (remains largely the same).

(Note: The original `transformation_lambda.py` is no longer directly deployed as a separate Lambda function; its logic is incorporated into `msk_consumer_lambda.py`.)

## 3. Prerequisites (MSK Version)

*   AWS Account with appropriate permissions.
*   Python 3.x installed locally.
*   **Python Libraries**:
    *   `kafka-python`: For `sample_log_generator.py`. Install via `pip install kafka-python`.
    *   `opensearch-py` and `boto3`: For `msk_consumer_lambda.py`. These need to be packaged with the Lambda or provided via a Lambda Layer. The current Terraform setup for Lambda packaging is basic.
*   AWS CLI configured.
*   Terraform CLI (>= 1.0).
*   Access to OpenSearch Dashboards endpoint once deployed.

## 4. Setup and Deployment (Manual - For understanding the flow)

The primary method for deployment is using the `run_app.sh` script. However, understanding the manual steps is useful.

### Terraform for Infrastructure
The infrastructure is defined in the `terraform/` directory. See `terraform/README.md` for detailed instructions on manual Terraform usage (init, plan, apply, destroy) and environment variable setup (`terraform/.env`). The Terraform scripts will set up the VPC, MSK cluster, Lambda consumer, OpenSearch domain, and necessary IAM roles.

### Post-Terraform Manual Steps
1.  **Apply OpenSearch Index Template**: After the OpenSearch domain is active, apply `opensearch_index_template.json` via OpenSearch Dashboards Dev Tools.
2.  **Configure OpenSearch Dashboards**: Set up index patterns and visualizations as per `dashboard_configuration.md`.

## 5. End-to-End Automation with `run_app.sh` (MSK Version)

The `run_app.sh` script in the project root automates infrastructure deployment via Terraform and initiates log generation for the MSK architecture.

### Prerequisites for `run_app.sh` (MSK Version)
*   All prerequisites listed in `terraform/README.md` (Terraform CLI, AWS CLI configured).
*   Python 3.x.
*   **Python Libraries**:
    *   `kafka-python`: For `sample_log_generator.py` to send logs to MSK. Install using:
        ```bash
        pip install kafka-python
        ```
        If `kafka-python` is not installed, the generator will print logs to the console.
    *   The `msk_consumer_lambda.py` requires `opensearch-py` and `boto3`. These are assumed to be part of the Lambda deployment package (see notes in `terraform/lambda_msk_consumer.tf` and `terraform/README.md` about Lambda packaging).

### Using `run_app.sh` (MSK Version)

1.  **Navigate to the project root directory.**
2.  **Ensure `run_app.sh` is executable:**
    ```bash
    chmod +x run_app.sh
    ```
3.  **Configure Terraform Environment:**
    *   Navigate to the `terraform/` directory.
    *   Copy `terraform/.env.example` to `terraform/.env`.
    *   Edit `terraform/.env` with your VPC CIDRs, MSK configurations (broker type, Kafka version), OpenSearch details, etc., as per the updated `variables.tf`.
    *   Return to the project root directory.

### To Deploy MSK-based Infrastructure and Generate Initial Logs:

```bash
./run_app.sh
```
This script will:
1.  Perform pre-flight checks.
2.  Execute `terraform/run.sh` to deploy the MSK-based AWS infrastructure (this includes `terraform init`, `plan`, and prompting for `apply`).
3.  Retrieve MSK bootstrap server details, topic name, and OpenSearch Dashboard URL from Terraform outputs.
4.  Run `sample_log_generator.py` with MSK connection details, attempting to send logs directly to the MSK topic.
5.  Remind you of manual post-deployment steps (OpenSearch index template, dashboard setup).

### To Destroy MSK-based Infrastructure:

```bash
./run_app.sh destroy
```
This will navigate to the `terraform/` directory and execute `terraform/run.sh destroy`.

**Note:** Always review the output of the scripts carefully, especially the Terraform plan, before confirming actions that create or destroy resources.

## 6. Simulating and Ingesting Logs (MSK Version)

The `sample_log_generator.py` script has been updated:
*   It now accepts `--bootstrap-servers` and `--topic` arguments to connect and send messages to your MSK cluster.
*   It uses the `kafka-python` library.
*   If connection parameters are not provided or `kafka-python` is missing, it defaults to printing logs.

Refer to the output of `./run_app.sh` or `terraform output` (from the `terraform` directory) for MSK bootstrap server details and the topic name.

Example (after infrastructure is up):
```bash
python sample_log_generator.py \
  --bootstrap-servers <your-msk-bootstrap-servers-tls> \
  --topic <your-msk-topic-name> \
  --num-logs 10
```

## 7. Querying Logs in OpenSearch
(This section remains the same as the original README)
1.  In OpenSearch Dashboards, go to **Dev Tools**.
2.  You can use the `sample_opensearch_query.json` to query your `siem-identity-logs-*` indices (or whatever index prefix you configured).

## 8. Setting Up the Dashboard
(This section remains the same as the original README, using `dashboard_configuration.md`)

## 9. Testing and Validation (MSK Version)

*   **MSK Connectivity:** Ensure the `sample_log_generator.py` can connect to MSK brokers and produce messages. Check MSK CloudWatch metrics.
*   **Lambda MSK Consumer:** Monitor CloudWatch Logs for the `msk_consumer_lambda` for processing messages, transformation errors, or issues writing to OpenSearch. Check Lambda invocation metrics and errors.
*   **OpenSearch Ingestion:** Verify transformed logs appear in the correct OpenSearch indices.
*   **Dashboard Accuracy & Tenant Isolation:** As before.
*   **Timestamps:** As before.

## 10. Scaling the Solution (MSK Version)

*   **Amazon MSK:**
    *   Scale brokers by changing instance type or increasing the number of brokers.
    *   Increase EBS storage per broker.
    *   Increase topic partitions for higher parallelism.
*   **Lambda MSK Consumer:**
    *   Lambda scales automatically based on incoming MSK messages (up to concurrency limits).
    *   Adjust Lambda memory, timeout, and MSK event source mapping `batch_size` for performance.
*   **OpenSearch Service:** As before (scale nodes, instance types, optimize shards, use ISM).

## 11. Security Considerations (MSK Version)

*   **VPC Security:** All core components (MSK, Lambda, OpenSearch) are now within a VPC. Use Security Groups and Network ACLs effectively.
*   **MSK Security:**
    *   Enable encryption in transit (TLS, default for this refactor) and at rest.
    *   Implement client authentication (e.g., SASL/SCRAM, mTLS, or IAM access control - current setup relies on TLS and network controls).
*   **IAM Roles:** Least privilege for Lambda (MSK consume, OpenSearch write, VPC access, CloudWatch Logs).
*   **OpenSearch FGAC:** As before.
*   Other considerations from the original README still apply.

## 12. Artifacts Included (MSK Version)

*   `README.md`: This file (updated for MSK).
*   `architecture_diagram.md`: (Original Kinesis architecture diagram - may need a new one for MSK).
*   `sample_log_generator.py`: (Updated for MSK Kafka client).
*   `opensearch_index_template.json`: (Unchanged).
*   `sample_opensearch_query.json`: (Unchanged).
*   `dashboard_configuration.md`: (Unchanged).
*   `run_app.sh`: (Updated for MSK workflow).
*   `terraform/`: Directory with Terraform scripts (updated for MSK).
    *   `terraform/lambda_code/msk_consumer_lambda.py`: New Lambda code.
    *   (Kinesis/Firehose related `.tf` files are removed in this version).
```

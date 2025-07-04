```mermaid
graph TD
    subgraph "User / Log Source"
        A[Log Generator Script <br>(sample_log_generator.py<br>with Kafka client)]
    end

    subgraph "AWS Cloud - VPC: siem-vpc"
        subgraph "Streaming Layer (Private Subnets)"
            B[Amazon MSK Cluster <br>(e.g., 2 brokers across 2 AZs)]
            C[MSK Topic: identity-logs]
        end

        subgraph "Processing Layer (Private Subnets)"
            D[AWS Lambda Function <br>(msk_consumer_lambda.py <br> Consumes from MSK, Transforms)]
        end

        subgraph "Storage & Analysis Layer (Private Subnets)"
            E[AWS OpenSearch Service Domain <br>(e.g., 2 data nodes across 2 AZs)]
        end

        subgraph "Public Subnets (for NAT)"
            F[NAT Gateway AZ1]
            G[NAT Gateway AZ2]
        end
        H[Internet Gateway]
    end

    subgraph "User Access / Visualization"
        I[AWS OpenSearch Dashboards <br>(Accessed via VPC endpoint, VPN, or restricted public IP through FGAC)]
    end

    A -- Kafka Messages --> B
    B -- Stores Messages --> C
    D -- Triggered by / Consumes from --> C
    D -- Transformed Logs (Bulk API) --> E
    E -- Queried Data --> I

    D -- Outbound via NAT (for AWS SDKs, e.g. OpenSearch client if not using VPC endpoint for OS) --> F & G
    F & G -- Internet Access --> H

    classDef vpc fill:#lightgrey,stroke:#333,stroke-width:2px;
    classDef subnet fill:#white,stroke:#777,stroke-width:1px,linetype:dashed;
    classDef criticalService fill:#f9f,stroke:#333,stroke-width:2px;
    classDef processingService fill:#cfc,stroke:#333,stroke-width:2px;

    class B,E criticalService;
    class D processingService;
    class C,F,G,H subnet;

```

## Architecture Explanation (MSK Version)

This diagram illustrates the SIEM PoC architecture refactored to use Amazon MSK (Managed Streaming for Apache Kafka).

1.  **Log Source (User / Simulated)**:
    *   `Log Generator Script (sample_log_generator.py)`: A Python script, now equipped with a Kafka client (e.g., `kafka-python`), simulates identity-related logs from sources like Okta and Azure AD. It produces these logs as messages to an Apache Kafka topic.

2.  **AWS Cloud - VPC (Virtual Private Cloud)**:
    *   The entire backend infrastructure is deployed within a custom VPC for enhanced security and network isolation.
    *   **Public Subnets**: Contain NAT Gateways to allow resources in private subnets (like Lambda, if it needs to reach external services or AWS SDK endpoints not available via VPC endpoints) to access the internet without being directly exposed. An Internet Gateway provides connectivity for these public subnets.
    *   **Streaming Layer (Private Subnets)**:
        *   `Amazon MSK Cluster`: A managed Apache Kafka cluster. It's deployed across multiple Availability Zones (AZs) using private subnets for high availability.
        *   `MSK Topic (identity-logs)`: A specific topic within the MSK cluster where the raw identity logs are published by the generator.
    *   **Processing Layer (Private Subnets)**:
        *   `AWS Lambda Function (msk_consumer_lambda.py)`: This function is also deployed in private subnets.
            *   It's configured with an **Event Source Mapping** to be triggered by new messages arriving in the `identity-logs` MSK topic.
            *   It consumes messages in batches.
            *   It performs transformations on the log data (parsing heterogeneous formats and mapping to a standardized schema).
    *   **Storage & Analysis Layer (Private Subnets)**:
        *   `AWS OpenSearch Service Domain`: The transformed, standardized logs are ingested into an OpenSearch domain, also deployed in private subnets within the VPC. The Lambda function uses the OpenSearch Bulk API for efficient ingestion.

3.  **User Access / Visualization**:
    *   `AWS OpenSearch Dashboards`: Used to create and display dashboards for visualizing login failure insights and other analytics. Access to Dashboards is typically managed through:
        *   A VPC endpoint for OpenSearch (if users are within the VPC or connected via VPN/Direct Connect).
        *   A reverse proxy or load balancer in a public subnet (with appropriate security).
        *   Direct public access to the OpenSearch domain endpoint (if configured, and heavily secured by Fine-Grained Access Control and IP whitelisting).

**Data Flow (MSK Version):**

1.  The `Log Generator Script` produces log messages and sends them to the `identity-logs` topic in the `Amazon MSK Cluster`.
2.  The `AWS Lambda Function` (MSK Consumer) is triggered by these new messages.
3.  The Lambda function consumes the messages, decodes them, and transforms them into the standardized JSON schema.
4.  The transformed logs are then sent in bulk by the Lambda function to the `AWS OpenSearch Service Domain` for indexing and storage.
5.  `AWS OpenSearch Dashboards` queries the OpenSearch domain to retrieve data for visualizations and analysis.
6.  Lambda functions in private subnets use `NAT Gateways` (in public subnets) for any required outbound internet connectivity (e.g., to reach AWS SDK endpoints if VPC endpoints for those services are not configured).

This MSK-based architecture provides a robust, scalable, and fault-tolerant streaming backbone suitable for high-throughput log ingestion and processing, leveraging Kafka's capabilities within the managed AWS environment.
</xaiArtifact>

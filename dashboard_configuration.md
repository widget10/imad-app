# AWS OpenSearch Dashboard Configuration for SIEM Lake PoC

This document outlines the configuration for an AWS OpenSearch Dashboard to visualize login failure insights from the SIEM Lake. The dashboard will focus on data from the last 30 days.

**Dashboard Title:** Identity Event Monitoring - Login Failures (Last 30 Days)

**Overall Dashboard Filter:**
*   **Time Range:** Default to "Last 30 days". Users should be able to adjust this.
*   **Primary Index Pattern:** `siem-identity-logs-*` (or whatever pattern is used for the identity logs).

## Visualizations:

All visualizations should be configured to filter for:
*   `event_status: "failure"`
*   `event_type: "login"` OR `event_type: "auth_failure"` (Use a KQL filter like `event_status: "failure" and (event_type: "login" or event_type: "auth_failure")` at the visualization or dashboard level if not using the specific query from `sample_opensearch_query.json` as a base for each).

---

### 1. Total Login Failures by Tenant

*   **Visualization Type:** Vertical Bar Chart
*   **Title:** Total Login Failures by Tenant (Last 30 Days)
*   **Description:** Displays the number of login failures for each tenant.
*   **Configuration:**
    *   **Y-axis (Metrics):**
        *   Aggregation: Count
    *   **X-axis (Buckets):**
        *   Aggregation: Terms
        *   Field: `tenant_id`
        *   Order by: Metric: Count (Descending)
        *   Size: 10 (or as appropriate for the number of tenants)
*   **Data Source:** Aggregation `total_login_failures_by_tenant` from `sample_opensearch_query.json`.

---

### 2. Top 5 Users with Login Failures

*   **Visualization Type:** Pie Chart (or Table if preferred for more than 5 users)
*   **Title:** Top 5 Users with Most Login Failures (Last 30 Days)
*   **Description:** Shows the users who have experienced the highest number of login failures.
*   **Configuration (Pie Chart):**
    *   **Metrics:**
        *   Aggregation: Count
    *   **Buckets:**
        *   Aggregation: Terms
        *   Field: `user_id`
        *   Order by: Metric: Count (Descending)
        *   Size: 5
*   **Configuration (Table - alternative):**
    *   **Metrics:**
        *   Aggregation: Count
    *   **Buckets:**
        *   Split Rows: Terms
        *   Field: `user_id`
        *   Order by: Metric: Count (Descending)
        *   Size: 5
*   **Data Source:** Aggregation `top_users_with_login_failures` from `sample_opensearch_query.json`.

---

### 3. Login Failure Trends Over Time

*   **Visualization Type:** Line Chart
*   **Title:** Login Failure Trends (Last 30 Days - Daily)
*   **Description:** Visualizes the trend of login failures on a daily basis.
*   **Configuration:**
    *   **Y-axis (Metrics):**
        *   Aggregation: Count
    *   **X-axis (Buckets):**
        *   Aggregation: Date Histogram
        *   Field: `timestamp`
        *   Interval: Daily
        *   Min_doc_count: 0 (to show days with no failures)
        *   Extended bounds: Use "Last 30 days" to ensure the full range is displayed.
*   **Data Source:** Aggregation `login_failure_trends_over_time` from `sample_opensearch_query.json`.

---

### 4. Source IPs with Most Login Failures

*   **Visualization Type:** Table (Heatmap can be an option if geographical data is available and relevant, but a table is more direct for IPs)
*   **Title:** Top Source IPs Associated with Login Failures (Last 30 Days)
*   **Description:** Lists the source IP addresses from which the most login failures originate.
*   **Configuration (Table):**
    *   **Metrics:**
        *   Aggregation: Count
        *   Label: "Failure Count"
    *   **Buckets:**
        *   Split Rows: Terms
        *   Field: `source_ip`
        *   Order by: Metric: Failure Count (Descending)
        *   Size: 10
*   **Data Source:** Aggregation `source_ips_with_most_login_failures` from `sample_opensearch_query.json`.

---

### 5. (Optional) Login Failures by Application ID

*   **Visualization Type:** Horizontal Bar Chart or Donut Chart
*   **Title:** Login Failures by Application (Last 30 Days)
*   **Description:** Shows which applications are experiencing the most login failures.
*   **Configuration:**
    *   **Metrics:**
        *   Aggregation: Count
    *   **Buckets:**
        *   Aggregation: Terms
        *   Field: `application_id`
        *   Order by: Metric: Count (Descending)
        *   Size: 10
*   **Data Source:** Aggregation `failures_by_app_id` from `sample_opensearch_query.json`.

---

## Dashboard Filters & Controls:

*   **Tenant Filter:** Add a "Controls" visualization (dropdown or multi-select) linked to the `tenant_id` field. This will allow users to filter the entire dashboard for one or more specific tenants.
*   **Application ID Filter:** (Optional) Add a "Controls" visualization for `application_id`.
*   **Time Picker:** Ensure the standard OpenSearch Dashboards time picker is available and defaults to "Last 30 days".

## General Instructions for Creating Visualizations:

1.  Navigate to the "Visualize" library in OpenSearch Dashboards.
2.  Click "Create new visualization" and select the appropriate chart type.
3.  Choose the `siem-identity-logs-*` index pattern.
4.  Apply the base KQL filter for login failures: `event_status: "failure" and (event_type: "login" or event_type: "auth_failure")`.
5.  Configure the Metrics and Buckets as described above for each visualization.
6.  Save each visualization with a descriptive name.
7.  Once all visualizations are created, navigate to "Dashboard", click "Create new dashboard", and add the saved visualizations.
8.  Arrange the visualizations on the dashboard and add controls as needed.
9.  Save the dashboard.
```

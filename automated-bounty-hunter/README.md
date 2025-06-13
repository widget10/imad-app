# Automated Bounty Hunter

## Overview

The Automated Bounty Hunter is a Python-based tool designed to automate parts of the software development and bug-fixing process, specifically targeting issues listed with bounties or otherwise flagged for automated processing. It aims to:

1.  Scrape or load issue details (currently from a local JSON file).
2.  Utilize a Large Language Model (LLM) like OpenAI's GPT series to generate potential solutions.
3.  Interact with GitHub to fetch repository context, create branches, commit changes, and open pull requests with the proposed solutions.

**Current Status**: Initial development version / Proof of concept.

## Features (Current)

*   Loads issue data from a local `issues.json` file.
*   Parses GitHub repository URLs to identify target repositories.
*   Fetches issue details and specified file contents from GitHub for context.
*   Utilizes an LLM (OpenAI GPT models) to generate explanations and code solutions for issues.
*   Parses structured LLM output to separate explanations from file changes.
*   Creates new branches in the target GitHub repository.
*   Commits new files or changes to existing files as suggested by the LLM.
*   Creates pull requests with the AI-generated changes and explanation.
*   Configurable via environment variables (`.env` file).
*   Basic logging implemented throughout the application.

## Prerequisites

*   **Python**: 3.9+ (developed with 3.10)
*   **Git**: For cloning the repository.
*   **OpenAI API Key**: Required to use OpenAI models for solution generation.
*   **GitHub Personal Access Token (PAT)**: With `repo` scope (full control of private and public repositories) to allow the tool to create branches, commit files, and open pull requests.

## Setup Instructions

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/automated-bounty-hunter.git
    # Replace with the actual URL of your repository
    ```

2.  **Navigate to the project directory**:
    ```bash
    cd automated-bounty-hunter
    ```

3.  **Create and activate a Python virtual environment**:
    *   On macOS and Linux:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv .venv
        .\.venv\Scripts\activate
        ```

4.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure Environment Variables**:
    *   Copy the example `.env.example` file to a new file named `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file with your actual credentials and desired settings:
        ```
        # GitHub API Configuration
        GITHUB_TOKEN=your_github_personal_access_token_here

        # OpenAI API Configuration
        OPENAI_API_KEY=your_openai_api_key_here

        # --- Optional: Paths and Logging ---
        # Path to the JSON file containing issues to process
        ISSUES_FILE_PATH=issues.json

        # Logging Configuration
        LOG_LEVEL=INFO # (e.g., DEBUG, INFO, WARNING, ERROR)
        LOG_FILE=app.log # (Optional: if you want to log to a file)

        # --- Optional: LLM Configuration ---
        # Name of the OpenAI model to use
        LLM_MODEL_NAME=gpt-3.5-turbo
        # LLM_PROMPT_TEMPLATE_STRING= (Leave blank to use default, or provide a full custom prompt string)

        # --- Optional: Git Configuration ---
        # Prefix for branches created by the bot
        BRANCH_PREFIX=ai-solution/
        # Default branch to base new branches off and target for PRs
        SOURCE_BRANCH_NAME=main
        # Disclaimer added to PR bodies
        # PR_DISCLAIMER="---\n*This PR was AI-generated. Review carefully.*"
        ```

## How to Run

1.  **Prepare your `issues.json` file**:
    *   Ensure the `issues.json` file (or the file specified by `ISSUES_FILE_PATH` in your `.env`) is present in the project root.
    *   Populate it with the issues you want the bot to process. Each issue should specify `github_repo_url` and `issue_number`.
    *   **Important**: For initial testing, use repositories where you have write access or test repositories to avoid unintended consequences.

2.  **Execute the main script**:
    ```bash
    python main.py
    ```
    The script will:
    *   Load issues from the configured JSON file.
    *   For each issue:
        *   Connect to the specified GitHub repository.
        *   Fetch issue details and relevant file context.
        *   Query the LLM for a solution.
        *   If a solution with code changes is generated:
            *   Create a new branch.
            *   Commit the changes to the new branch.
            *   Create a pull request with the proposed solution.

## Project Structure

The project is organized into several main directories:

*   `.github/workflows/`: Contains GitHub Actions CI workflows (e.g., `test-pr.yml` for testing the tool's codebase).
*   `core/`: Contains the main orchestration logic (`main.py`) that ties other components together.
*   `github_handler/`: Module for interacting with the GitHub API (`handler.py`).
*   `llm_handler/`: Module for interacting with Large Language Models like OpenAI (`handler.py`).
*   `scraper/`: Module for loading issue data (currently from a local JSON file via `scraper.py`).
*   `.venv/`: (Typically) The local Python virtual environment directory (gitignored).
*   `main.py`: The main entry point of the application.
*   `requirements.txt`: Lists Python package dependencies.
*   `.env.example`: Example template for environment variable configuration.
*   `issues.json`: Default file for listing issues to be processed.
*   `logger_config.py`: Basic logging setup.

## Workflow Overview

The automated process follows these general steps:

1.  **Load Issues**: Issues are loaded from a JSON file (e.g., `issues.json`).
2.  **Process Each Issue**: For every issue in the list:
    a.  **Initialize**: The `GitHubHandler` is initialized for the specific repository mentioned in the issue.
    b.  **Fetch Context**: Details about the GitHub issue (title, body, labels) and content of relevant files (e.g., `README.md` or files specified in `issues.json`) are fetched.
    c.  **Generate Solution**: The issue details and file context are passed to the `LLMHandler`, which queries an OpenAI model to generate a potential solution (explanation and code changes).
    d.  **Parse Solution**: The LLM's response is parsed to separate the textual explanation from the structured code modifications.
    e.  **Version Control & PR**:
        i.  A new branch is created in the target repository.
        ii. The code changes suggested by the LLM are committed to this new branch.
        iii. A pull request is created, proposing the changes, with the LLM's explanation included in the PR body.

## CI Pipeline

This project includes a GitHub Actions CI/CD pipeline defined in `.github/workflows/test-pr.yml`. This pipeline is triggered on pushes and pull requests to the `main` (or `master`) branch. It performs the following checks on the `automated-bounty-hunter` codebase itself:

*   Sets up a Python environment.
*   Installs dependencies.
*   Runs `flake8` for linting to ensure code quality and style consistency.
*   Runs `pytest` to execute any available automated tests (currently minimal, focused on framework integration).

This helps ensure that the tool's own code remains healthy and maintainable.

## Disclaimer & Future Work

**Disclaimer**: This tool is currently in an initial development phase and should be considered a proof of concept. Exercise caution when using it, especially with public repositories or issues you do not own. Always review generated pull requests thoroughly. The creators are not responsible for any misuse or unintended consequences.

**Future Work**:
*   **Live Scraping**: Implement modules to scrape issues directly from platforms like Gitcoin, Bountysource, or GitHub itself based on labels/keywords.
*   **Advanced LLM Interaction**:
    *   Iterative prompting or feedback loops with the LLM.
    *   Support for more complex solution structures or interactive debugging.
    *   Cost estimation and control for LLM API usage.
*   **Improved Context Gathering**: More intelligent selection of relevant files or code snippets for LLM context.
*   **Testing Framework for Generated Code**: Explore ways to automatically run tests on the code generated by the LLM within a sandboxed environment before creating a PR.
*   **Broader VCS Support**: Potentially extend to other version control systems (e.g., GitLab).
*   **User Interface**: A simple web UI or CLI for managing issues and monitoring the bot.
*   **More Robust Error Handling and Recovery**: Enhanced mechanisms for dealing with API failures, unexpected output, etc.

---
Contributions and suggestions are welcome! Please open an issue or submit a pull request.

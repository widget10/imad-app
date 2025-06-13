import os
from typing import Optional, Dict, Any, Union
from openai import OpenAI, APIError, RateLimitError, AuthenticationError

# Assuming logger_config.py is in the parent directory and configured
import sys
sys.path.append("..") # Adds the parent directory to the Python path
from logger_config import get_logger

logger = get_logger(__name__)

DEFAULT_PROMPT_TEMPLATE = """
You are an expert software developer tasked with solving a GitHub issue.
Your goal is to provide a complete and actionable solution that can be directly applied to the repository.

Please provide a solution that includes:
1. A brief explanation of the root cause of the issue and the proposed fix. This explanation should be concise and clear.
2. The specific code changes required. For each file to be changed, you MUST clearly indicate the file path and the new content using the specified format. If a new file needs to be created, specify its path and content using the same format.

Use the following strict format for EACH file change (whether new or existing):
---
File: path/to/your/file.py
```python
# Your complete code for this file (or the relevant section if only a part is changed)
# Ensure to include necessary imports if they are part of the change.
# If you are updating an existing file, provide the full new version of the code block that needs to be changed,
# or the full file if it's small or significantly refactored.
```
---
(Repeat the '--- File: ... --- ... ``` ... ``` ---' block for every file that needs to be created or modified)

Issue Title: {issue_title}
Issue Body:
{issue_body}

Relevant files from the repository for context (path and content):
{formatted_repo_files_context}

Based on the issue and the provided file context, please generate the complete solution including the explanation and all necessary code changes in the specified format.
If no code changes are needed, or if the issue cannot be resolved with code changes (e.g., it's a documentation request or a question), please state that clearly in the explanation.
If a file is too large to be included in the context, its content might be truncated or summarized. Use your best judgment.
"""

class LLMHandler:
    """
    Handles interactions with an LLM (e.g., OpenAI GPT models) to generate solutions.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-3.5-turbo"):
        """
        Initializes the LLMHandler.

        Args:
            api_key: The API key for the LLM service (e.g., OpenAI API key).
                     If None, it will attempt to use the OPENAI_API_KEY environment variable.
            model_name: The name of the LLM model to use.
        """
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            logger.error("OpenAI API key is required. Not provided and not found in OPENAI_API_KEY env var.")
            raise ValueError("OpenAI API key is required. Not provided and not found in OPENAI_API_KEY env var.")

        try:
            self.client = OpenAI(api_key=api_key)
            self.model_name = model_name
            logger.info(f"LLMHandler initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ConnectionError(f"Failed to initialize OpenAI client: {e}") from e

    def _format_repo_files_context(self, repo_files_context: Dict[str, str]) -> str:
        """
        Formats the repository files context into a string for the prompt.

        Args:
            repo_files_context: A dictionary where keys are file paths and values are their content.

        Returns:
            A string representation of the repository files context.
        """
        if not repo_files_context:
            return "No files provided for context."

        formatted_str = ""
        for file_path, content in repo_files_context.items():
            formatted_str += f"File: {file_path}\nContent:\n```\n{content}\n```\n\n"
        return formatted_str.strip()

    def generate_solution(
        self,
        issue_title: str,
        issue_body: str,
        repo_files_context: Dict[str, str],
        custom_prompt_template: Optional[str] = None,
        max_tokens: int = 2048, # Max tokens for the generated response
        temperature: float = 0.2 # Lower temperature for more deterministic output
    ) -> Optional[str]:
        """
        Generates a potential solution for a given issue using the LLM.

        Args:
            issue_title: The title of the GitHub issue.
            issue_body: The body/description of the GitHub issue.
            repo_files_context: A dictionary of relevant file paths and their content.
            custom_prompt_template: An optional custom prompt template to use.
            max_tokens: The maximum number of tokens to generate in the response.
            temperature: The sampling temperature for the LLM.

        Returns:
            A string containing the LLM's proposed solution (explanation and code changes),
            or None if an error occurs or the response is unusable.
        """
        if not issue_title or not issue_body:
            logger.error("Issue title and body are required to generate a solution.")
            return None

        formatted_repo_files_context = self._format_repo_files_context(repo_files_context)

        prompt_template_to_use = custom_prompt_template or DEFAULT_PROMPT_TEMPLATE

        try:
            full_prompt = prompt_template_to_use.format(
                issue_title=issue_title,
                issue_body=issue_body,
                formatted_repo_files_context=formatted_repo_files_context
            )
        except KeyError as e:
            logger.error(f"Missing key in prompt template: {e}. Ensure all placeholders like {{issue_title}}, {{issue_body}}, {{formatted_repo_files_context}} are present.")
            return None

        logger.info(f"Sending prompt to LLM (model: {self.model_name}). Prompt summary: Issue '{issue_title}', Context files: {len(repo_files_context)}")
        # For debugging, you might want to log the full_prompt, but be cautious with sensitive data and length.
        # logger.debug(f"Full prompt:\n{full_prompt}")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert software developer."}, # System message can be part of the main prompt too
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                n=1, # Number of completions to generate
                stop=None # Potentially add stop sequences if needed
            )

            if response.choices and response.choices[0].message:
                solution_text = response.choices[0].message.content.strip()
                logger.info(f"Successfully received solution from LLM for issue '{issue_title}'.")
                # logger.debug(f"LLM Raw Response:\n{solution_text}")

                # Basic validation of the response structure (presence of "File:")
                if "File:" not in solution_text and "explanation:" not in solution_text.lower(): # crude check
                    logger.warning(f"LLM response for issue '{issue_title}' might not be in the expected format. It lacks 'File:' or 'explanation:'.")

                return solution_text
            else:
                logger.warning(f"LLM response for issue '{issue_title}' was empty or malformed. Choices: {response.choices}")
                return None

        except AuthenticationError as e:
            logger.error(f"OpenAI API Authentication Error: {e}. Check your API key.")
            raise # Re-raise for handling by the caller, as this is critical
        except RateLimitError as e:
            logger.error(f"OpenAI API Rate Limit Exceeded: {e}. Please check your usage and limits.")
            return None # Or implement retry logic
        except APIError as e: # General API errors (e.g., server-side issues, model overload)
            logger.error(f"OpenAI API Error for issue '{issue_title}': {e}")
            return None
        except Exception as e: # Other unexpected errors
            logger.error(f"An unexpected error occurred while interacting with LLM for issue '{issue_title}': {e}")
            return None

# Example Usage (for testing purposes)
if __name__ == '__main__':
    from dotenv import load_dotenv

    # Load .env from the parent directory of this file's directory
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Attempting to load .env from: {dotenv_path}")


    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables. Please set it in .env file in the project root.")
        print("OPENAI_API_KEY not found. Set it in .env in the project root (e.g., ../.env).")
        sys.exit(1)

    print("\n--- LLMHandler Test ---")
    try:
        # Initialize handler (will use OPENAI_API_KEY from env if api_key=None)
        llm_handler = LLMHandler(model_name="gpt-3.5-turbo") # Or specify api_key explicitly

        # Example issue details
        test_issue_title = "Fix button alignment on login page"
        test_issue_body = """
        The login button on the /login page is misaligned on mobile devices.
        It appears too far to the right and overflows the container.
        This only happens on screen widths below 600px.
        The relevant CSS file is styles/main.css.
        """

        # Example repository file context
        test_repo_files_context = {
            "styles/main.css": """
            .container {
                width: 100%;
                padding: 10px;
            }

            .button {
                padding: 10px 15px;
                background-color: #007bff;
                color: white;
                border: none;
                cursor: pointer;
            }

            /* Login page specific styles */
            .login-page .button {
                display: block;
                margin: 10px 0;
            }
            """,
            "html/login.html": """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login</title>
                <link rel="stylesheet" href="styles/main.css">
            </head>
            <body>
                <div class="container login-page">
                    <h2>Login</h2>
                    <form>
                        <input type="text" placeholder="Username">
                        <input type="password" placeholder="Password">
                        <button class="button" type="submit">Login</button>
                    </form>
                </div>
            </body>
            </html>
            """
        }

        print(f"\nGenerating solution for: '{test_issue_title}'...")
        solution = llm_handler.generate_solution(
            issue_title=test_issue_title,
            issue_body=test_issue_body,
            repo_files_context=test_repo_files_context
        )

        if solution:
            print("\n--- Generated Solution ---")
            print(solution)
            print("--- End of Solution ---")

            # Test parsing (very basic example)
            if "---" in solution and "File:" in solution:
                print("\nSolution seems to contain the expected file change markers.")
            else:
                print("\nWarning: Solution might not be in the expected format for parsing.")
        else:
            print("\nFailed to generate a solution.")

        # Test with missing context
        print("\nGenerating solution with empty context...")
        solution_no_context = llm_handler.generate_solution(
            issue_title="Add a title to the main page",
            issue_body="The main page index.html is missing a <title> tag in the <head>.",
            repo_files_context={}
        )
        if solution_no_context:
            print("\n--- Generated Solution (No Context) ---")
            print(solution_no_context)
            print("--- End of Solution ---")
        else:
            print("\nFailed to generate solution with empty context.")


    except ValueError as e:
        print(f"Configuration Error: {e}")
    except ConnectionError as e:
        print(f"Connection Error: {e}")
    except APIError as e: # Catching re-raised AuthenticationError here too
        print(f"API Error during test: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")
        logger.exception("Unexpected error in LLMHandler example usage.")

    print("\n--- LLMHandler tests finished ---")

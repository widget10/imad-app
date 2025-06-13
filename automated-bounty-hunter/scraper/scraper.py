import json
from typing import List, Dict, Any, Optional

# Assuming logger_config.py is in the parent directory and configured
import sys
sys.path.append("..") # Adds the parent directory to the Python path
from logger_config import get_logger

logger = get_logger(__name__)

class ScrapedIssue:
    """
    A simple class to represent a scraped issue, providing attribute access.
    Not strictly necessary but can be nice for type hinting and structure.
    """
    def __init__(self, id: str, title: str, github_repo_url: str, issue_number: int,
                 bounty_amount: Optional[float] = 0, platform_source: Optional[str] = None,
                 description_override: Optional[str] = None, relevant_files: Optional[List[str]] = None,
                 **kwargs: Any): # Allows for extra fields
        self.id = id
        self.title = title
        self.github_repo_url = github_repo_url
        self.issue_number = issue_number
        self.bounty_amount = bounty_amount
        self.platform_source = platform_source
        self.description_override = description_override # For issues where GH body might be insufficient
        self.relevant_files = relevant_files if relevant_files is not None else [] # Files to fetch for context
        self.other_data: Dict[str, Any] = kwargs # Store any other data

    def __repr__(self) -> str:
        return f"ScrapedIssue(id='{self.id}', title='{self.title}', repo='{self.github_repo_url}', issue_num={self.issue_number})"

    @property
    def repo_owner_name(self) -> Optional[tuple[str, str]]:
        """
        Parses the GitHub repository URL to extract owner and repository name.
        Example: "https://github.com/owner/repo" -> ("owner", "repo")
        """
        if not self.github_repo_url or not self.github_repo_url.startswith("https://github.com/"):
            logger.warning(f"Invalid GitHub repo URL format for issue {self.id}: {self.github_repo_url}")
            return None
        try:
            parts = self.github_repo_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo_name = parts[1].replace(".git", "") # Remove .git if present
                return owner, repo_name
            else:
                logger.warning(f"Could not parse owner/repo from URL for issue {self.id}: {self.github_repo_url}")
                return None
        except Exception as e:
            logger.error(f"Error parsing repo URL {self.github_repo_url} for issue {self.id}: {e}")
            return None


def load_issues_from_file(file_path: str) -> List[ScrapedIssue]:
    """
    Loads a list of issues from a JSON file.

    Each issue object in the JSON file is expected to contain at least:
    - "id": A unique identifier (string or integer).
    - "title": The title of the issue.
    - "github_repo_url": The full URL to the GitHub repository.
    - "issue_number": The issue number within that repository.

    Optional fields include:
    - "bounty_amount": The bounty amount (numeric).
    - "platform_source": Source of the bounty/issue (e.g., "Gitcoin").
    - "description_override": A string to use as the issue body instead of fetching from GitHub.
    - "relevant_files": A list of file paths string to pre-fetch for LLM context.
    - Any other custom fields.

    Args:
        file_path: The path to the JSON file containing the issues.

    Returns:
        A list of ScrapedIssue objects. Returns an empty list if errors occur.
    """
    logger.info(f"Attempting to load issues from file: {file_path}")
    issues: List[ScrapedIssue] = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_issues_data: List[Dict[str, Any]] = json.load(f)

        if not isinstance(raw_issues_data, list):
            logger.error(f"Invalid format: The JSON file {file_path} does not contain a list of issues.")
            return []

        for i, issue_data in enumerate(raw_issues_data):
            if not isinstance(issue_data, dict):
                logger.warning(f"Skipping item at index {i} in {file_path}: not a valid dictionary.")
                continue

            # Validate required fields
            required_fields = ["id", "title", "github_repo_url", "issue_number"]
            missing_fields = [field for field in required_fields if field not in issue_data]
            if missing_fields:
                logger.warning(f"Skipping issue data at index {i} due to missing required fields: {', '.join(missing_fields)}. Data: {issue_data}")
                continue

            # Ensure correct types for critical fields
            if not isinstance(issue_data["issue_number"], int):
                logger.warning(f"Skipping issue data for ID '{issue_data['id']}' due to invalid type for 'issue_number' (expected int). Data: {issue_data}")
                continue
            if not isinstance(issue_data["github_repo_url"], str):
                 logger.warning(f"Skipping issue data for ID '{issue_data['id']}' due to invalid type for 'github_repo_url' (expected str). Data: {issue_data}")
                 continue


            try:
                issue_obj = ScrapedIssue(
                    id=str(issue_data["id"]), # Ensure ID is string
                    title=issue_data["title"],
                    github_repo_url=issue_data["github_repo_url"],
                    issue_number=issue_data["issue_number"],
                    bounty_amount=issue_data.get("bounty_amount"),
                    platform_source=issue_data.get("platform_source"),
                    description_override=issue_data.get("description_override"),
                    relevant_files=issue_data.get("relevant_files"),
                    **{k: v for k, v in issue_data.items() if k not in required_fields + ["bounty_amount", "platform_source", "description_override", "relevant_files"]} # Pass extra fields
                )

                # Validate owner/repo parsing from URL
                if not issue_obj.repo_owner_name:
                    logger.warning(f"Could not parse owner/repo from URL for issue ID '{issue_obj.id}'. Skipping this issue.")
                    continue # Skip if URL is malformed such that owner/repo can't be extracted

                issues.append(issue_obj)
                logger.debug(f"Successfully loaded and parsed issue: {issue_obj.id}")
            except TypeError as te: # Catch errors from ScrapedIssue constructor (e.g. unexpected kwargs if not handled)
                 logger.warning(f"Skipping issue data for ID '{issue_data.get('id', 'UNKNOWN')}' due to TypeError during object creation: {te}. Data: {issue_data}")
                 continue


        logger.info(f"Successfully loaded {len(issues)} issues from {file_path}.")
        return issues

    except FileNotFoundError:
        logger.error(f"Error: The file {file_path} was not found.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error: Invalid JSON format in {file_path}. Details: {e}")
        return []
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred while loading issues from {file_path}: {e}")
        return []

# Example Usage (for testing purposes)
if __name__ == '__main__':
    # Assuming issues.json is in the parent directory relative to this script's location
    # when run as `python scraper/scraper.py` from the project root.
    # If running `python scraper.py` directly from `scraper/` dir, path would be `../issues.json`

    # Determine path to issues.json relative to this script file
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    example_file_path = os.path.join(project_root, "issues.json")

    print(f"--- Testing load_issues_from_file with: {example_file_path} ---")

    loaded_issues = load_issues_from_file(example_file_path)

    if loaded_issues:
        print(f"\nSuccessfully loaded {len(loaded_issues)} issues:")
        for issue_obj in loaded_issues:
            print(f"  ID: {issue_obj.id}, Title: {issue_obj.title}, Repo: {issue_obj.github_repo_url}, Issue #: {issue_obj.issue_number}")
            owner_name_tuple = issue_obj.repo_owner_name
            if owner_name_tuple:
                print(f"    Owner: {owner_name_tuple[0]}, Repo Name: {owner_name_tuple[1]}")
            else:
                print(f"    Could not parse owner/repo from URL.")
            if issue_obj.bounty_amount:
                print(f"    Bounty: ${issue_obj.bounty_amount}")
            if issue_obj.platform_source:
                print(f"    Source: {issue_obj.platform_source}")
            if issue_obj.description_override:
                print(f"    Description Override (first 50 chars): {issue_obj.description_override[:50]}...")
            if issue_obj.relevant_files:
                print(f"    Relevant Files: {issue_obj.relevant_files}")
            if issue_obj.other_data:
                print(f"    Other Data: {issue_obj.other_data}")
            print("-" * 20)
    else:
        print("\nNo issues loaded or an error occurred.")

    print("\n--- Testing with a non-existent file ---")
    non_existent_file_path = os.path.join(project_root, "non_existent_issues.json")
    loaded_issues_non_existent = load_issues_from_file(non_existent_file_path)
    if not loaded_issues_non_existent:
        print("Correctly handled non-existent file: No issues loaded.")

    print("\n--- Testing with an invalid JSON file ---")
    invalid_json_path = os.path.join(project_root, "temp_invalid_issues.json")
    with open(invalid_json_path, 'w') as f:
        f.write("[{'id': '1', 'title': 'bad json'}]") # Invalid JSON (single quotes)

    loaded_issues_invalid = load_issues_from_file(invalid_json_path)
    if not loaded_issues_invalid:
        print("Correctly handled invalid JSON file: No issues loaded.")
    os.remove(invalid_json_path) # Clean up

    print("\n--- Scraper tests finished ---")

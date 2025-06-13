import base64
from typing import Optional, Dict, Any, Union, List

from github import Github, GithubException, UnknownObjectException
from github.Issue import Issue
from github.File import File
from github.ContentFile import ContentFile
from github.Branch import Branch
from github.PullRequest import PullRequest
from github.GitRef import GitRef

# Assuming logger_config.py is in the parent directory and configured
import sys
sys.path.append("..") # Adds the parent directory to the Python path
from logger_config import get_logger

logger = get_logger(__name__)

class GitHubHandler:
    """
    Handles interactions with the GitHub API using PyGithub.
    """

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """
        Initializes the GitHubHandler.

        Args:
            token: GitHub Personal Access Token (PAT).
            repo_owner: The owner of the repository (e.g., "octocat").
            repo_name: The name of the repository (e.g., "Hello-World").
        """
        if not token:
            logger.error("GitHub token is required.")
            raise ValueError("GitHub token is required.")
        if not repo_owner:
            logger.error("Repository owner is required.")
            raise ValueError("Repository owner is required.")
        if not repo_name:
            logger.error("Repository name is required.")
            raise ValueError("Repository name is required.")

        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.full_repo_name = f"{repo_owner}/{repo_name}"

        try:
            self.github_api = Github(token)
            self.repo = self.github_api.get_repo(self.full_repo_name)
            logger.info(f"Successfully connected to repository: {self.full_repo_name}")
        except GithubException as e:
            logger.error(f"Failed to connect to GitHub or repository {self.full_repo_name}: {e}")
            raise ConnectionError(f"Failed to connect to GitHub or repository {self.full_repo_name}: {e}") from e

    def get_issue_details(self, issue_number: int) -> Optional[Dict[str, Any]]:
        """
        Fetches details for a specific issue.

        Args:
            issue_number: The number of the issue.

        Returns:
            A dictionary with issue details (title, body, labels, state, html_url) or None if not found.
        """
        try:
            issue: Issue = self.repo.get_issue(number=issue_number)
            labels = [label.name for label in issue.labels]
            details = {
                "title": issue.title,
                "body": issue.body,
                "labels": labels,
                "state": issue.state,
                "html_url": issue.html_url,
                "number": issue.number,
            }
            logger.info(f"Fetched details for issue #{issue_number} in {self.full_repo_name}")
            return details
        except UnknownObjectException:
            logger.warning(f"Issue #{issue_number} not found in {self.full_repo_name}.")
            return None
        except GithubException as e:
            logger.error(f"Error fetching issue #{issue_number} from {self.full_repo_name}: {e}")
            return None # Or re-raise a custom exception

    def get_file_content(self, file_path: str, branch_or_sha: str = "main") -> Optional[str]:
        """
        Fetches the content of a file from the repository.

        Args:
            file_path: The path to the file in the repository.
            branch_or_sha: The branch name or commit SHA from which to fetch the file. Defaults to "main".

        Returns:
            The decoded content of the file as a string, or None if the file is not found or an error occurs.
        """
        try:
            logger.debug(f"Attempting to fetch file '{file_path}' from branch/SHA '{branch_or_sha}' in {self.full_repo_name}")
            content_file: ContentFile = self.repo.get_contents(file_path, ref=branch_or_sha)

            if content_file.type == "dir":
                logger.warning(f"Path '{file_path}' on branch '{branch_or_sha}' is a directory, not a file.")
                return None

            if content_file.encoding != 'base64':
                logger.warning(f"File '{file_path}' has unexpected encoding '{content_file.encoding}'. Attempting direct decode.")
                # Try to decode assuming it's utf-8, or handle other encodings as needed
                return content_file.decoded_content.decode('utf-8', errors='replace')


            decoded_content = base64.b64decode(content_file.content).decode('utf-8')
            logger.info(f"Successfully fetched and decoded content of '{file_path}' from branch '{branch_or_sha}'.")
            return decoded_content
        except UnknownObjectException:
            logger.warning(f"File '{file_path}' not found on branch/SHA '{branch_or_sha}' in {self.full_repo_name}.")
            return None
        except GithubException as e:
            logger.error(f"Error fetching file '{file_path}' from {self.full_repo_name} (branch/SHA: {branch_or_sha}): {e}")
            return None
        except Exception as e: # Catch potential decoding errors
            logger.error(f"Error decoding content of file '{file_path}': {e}")
            return None

    def create_branch(self, new_branch_name: str, source_branch_name: str = "main") -> Optional[str]:
        """
        Creates a new branch in the repository.

        Args:
            new_branch_name: The name for the new branch.
            source_branch_name: The name of the source branch from which to create the new branch. Defaults to "main".

        Returns:
            The name of the new branch if successful, otherwise None.
        """
        try:
            source_branch: Branch = self.repo.get_branch(source_branch_name)
            source_sha = source_branch.commit.sha

            # Format for ref is "refs/heads/branch-name"
            ref_path = f"refs/heads/{new_branch_name}"

            self.repo.create_git_ref(ref=ref_path, sha=source_sha)
            logger.info(f"Successfully created branch '{new_branch_name}' from '{source_branch_name}' (SHA: {source_sha}) in {self.full_repo_name}.")
            return new_branch_name
        except GithubException as e:
            # Check if branch already exists (this might be a common case)
            if e.status == 422 and "Reference already exists" in str(e.data.get("message", "")):
                 logger.warning(f"Branch '{new_branch_name}' already exists in {self.full_repo_name}. Error: {e.data.get('message')}")
                 return new_branch_name # Or None, depending on desired behavior
            logger.error(f"Error creating branch '{new_branch_name}' from '{source_branch_name}' in {self.full_repo_name}: {e} - Data: {e.data}")
            return None

    def commit_changes(self, branch_name: str, commit_message: str, file_path: str, new_content: str, current_sha: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Commits changes to a single file in the specified branch.
        Creates the file if it doesn't exist, or updates it if it does.

        Args:
            branch_name: The name of the branch to commit to.
            commit_message: The commit message.
            file_path: The path to the file in the repository.
            new_content: The new content for the file (as a string).
            current_sha: The current SHA of the file if updating. If None, it will be fetched.
                         If creating a new file, this should be None.

        Returns:
            A dictionary with commit details (e.g., 'sha', 'html_url') if successful, otherwise None.
        """
        try:
            # Encode content to bytes, then to string for JSON payload if necessary, or let PyGithub handle it
            if not isinstance(new_content, str):
                logger.error("new_content must be a string.")
                raise ValueError("new_content must be a string.")

            # Check if file exists to decide between create_file and update_file
            try:
                existing_file: ContentFile = self.repo.get_contents(file_path, ref=branch_name)
                sha_to_update = current_sha or existing_file.sha
                logger.info(f"Updating existing file '{file_path}' on branch '{branch_name}'. SHA: {sha_to_update}")
                commit_info = self.repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=new_content,
                    sha=sha_to_update,
                    branch=branch_name
                )
            except UnknownObjectException:
                logger.info(f"Creating new file '{file_path}' on branch '{branch_name}'.")
                if current_sha:
                    logger.warning(f"current_sha ('{current_sha}') provided for a new file '{file_path}'. It will be ignored.")
                commit_info = self.repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=new_content,
                    branch=branch_name
                )

            if commit_info and 'commit' in commit_info:
                commit_data = {
                    "sha": commit_info['commit'].sha,
                    "html_url": commit_info['commit'].html_url
                }
                logger.info(f"Successfully committed changes to '{file_path}' on branch '{branch_name}'. Commit SHA: {commit_data['sha']}")
                return commit_data
            else:
                logger.error(f"Commit failed for '{file_path}' on branch '{branch_name}'. Response: {commit_info}")
                return None

        except GithubException as e:
            logger.error(f"GitHub error during commit to '{file_path}' on branch '{branch_name}': {e} - Data: {e.data}")
            # Specific check for "Branch not found" or invalid SHA
            if e.status == 404 or (e.status == 422 and "invalid" in str(e.data.get("message", "")).lower()):
                logger.error(f"Branch '{branch_name}' or file SHA might be invalid.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during commit: {e}")
            return None

    def create_pull_request(self, title: str, body: str, head_branch: str, base_branch: str = "main") -> Optional[Dict[str, Any]]:
        """
        Creates a pull request.

        Args:
            title: The title of the pull request.
            body: The body/description of the pull request.
            head_branch: The name of the branch where your changes are (source branch).
            base_branch: The name of the branch to merge into (target branch). Defaults to "main".

        Returns:
            A dictionary with PR details (e.g., 'number', 'html_url', 'state') if successful, otherwise None.
        """
        try:
            pr: PullRequest = self.repo.create_pull(
                title=title,
                body=body,
                head=head_branch,  # The branch with your changes
                base=base_branch   # The branch you want to merge into
            )
            pr_details = {
                "number": pr.number,
                "html_url": pr.html_url,
                "state": pr.state,
                "title": pr.title,
                "body": pr.body
            }
            logger.info(f"Successfully created pull request #{pr.number} ('{title}') from '{head_branch}' to '{base_branch}' in {self.full_repo_name}.")
            return pr_details
        except GithubException as e:
            # Common errors:
            # 422: Validation Failed - e.g., PR already exists, no commits between branches, merge conflicts.
            if e.status == 422 and e.data and "errors" in e.data:
                error_messages = [err.get("message") for err in e.data["errors"] if err.get("message")]
                specific_error = "; ".join(filter(None, error_messages))
                if "A pull request already exists" in specific_error:
                    logger.warning(f"Pull request from '{head_branch}' to '{base_branch}' already exists. Error: {specific_error}")
                    # Optionally, try to find and return the existing PR
                else:
                    logger.error(f"Validation error creating pull request from '{head_branch}' to '{base_branch}': {specific_error}. Data: {e.data}")

            else:
                logger.error(f"Error creating pull request from '{head_branch}' to '{base_branch}' in {self.full_repo_name}: {e} - Data: {e.data}")
            return None

# Example Usage (for testing purposes, normally instantiated and used from core logic)
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env')) # Load .env from parent

    github_token = os.getenv("GITHUB_TOKEN")
    # Replace with your test repo details or load from env
    repo_owner_env = os.getenv("GH_REPO_OWNER", "your_username")
    repo_name_env = os.getenv("GH_REPO_NAME", "your_repo_name")

    if not github_token:
        print("GITHUB_TOKEN not found in environment variables. Please set it in .env file.")
        sys.exit(1)

    if repo_owner_env == "your_username" or repo_name_env == "your_repo_name":
        print(f"Please update GH_REPO_OWNER and GH_REPO_NAME in your .env file from 'your_username'/'your_repo_name' to actual values for testing.")
        # You could skip testing if these are not set, or use a public repo for read-only tests
        # sys.exit(1)


    # --- Basic Read Operations ---
    print(f"\n--- Testing with repo: {repo_owner_env}/{repo_name_env} ---")
    try:
        handler = GitHubHandler(token=github_token, repo_owner=repo_owner_env, repo_name=repo_name_env)

        # Test get_issue_details (replace with a valid issue number in your test repo)
        # test_issue_num = 1
        # print(f"\nFetching issue #{test_issue_num}...")
        # issue = handler.get_issue_details(test_issue_num)
        # if issue:
        #     print(f"Issue #{test_issue_num} Title: {issue['title']}")
        #     print(f"Issue Labels: {issue['labels']}")
        # else:
        #     print(f"Issue #{test_issue_num} not found or error occurred.")

        # Test get_file_content (replace with a valid file path in your test repo)
        test_file_path = "README.md" # Or any other file
        print(f"\nFetching file content for '{test_file_path}'...")
        content = handler.get_file_content(test_file_path)
        if content:
            print(f"Content of '{test_file_path}' (first 100 chars):\n{content[:100]}...")
        else:
            print(f"File '{test_file_path}' not found or error.")

        # Test get_file_content for a non-existent file
        non_existent_file = "non_existent_file.txt"
        print(f"\nFetching non-existent file '{non_existent_file}'...")
        content = handler.get_file_content(non_existent_file)
        if content is None:
            print(f"Correctly handled: File '{non_existent_file}' not found.")

        # --- Write Operations (Use with caution, targets a real repo!) ---
        # Uncomment and configure carefully if you want to test these.
        # Ensure the repo is a safe test repository.

        # test_branch_name = "test-sdk-branch"
        # print(f"\nCreating branch '{test_branch_name}'...")
        # created_branch = handler.create_branch(test_branch_name, source_branch_name="main")
        # if created_branch:
        #     print(f"Branch '{created_branch}' created (or already existed).")

        #     # Test commit_changes - Create a new file
        #     new_file_path = f"test_file_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        #     new_file_content = f"Hello from GitHubHandler test at {datetime.now()}"
        #     commit_msg_create = f"Test: Create {new_file_path}"
        #     print(f"\nCommitting new file '{new_file_path}' to branch '{test_branch_name}'...")
        #     commit_details_create = handler.commit_changes(
        #         branch_name=test_branch_name,
        #         commit_message=commit_msg_create,
        #         file_path=new_file_path,
        #         new_content=new_file_content
        #     )
        #     if commit_details_create:
        #         print(f"File '{new_file_path}' created. Commit SHA: {commit_details_create['sha']}")

        #         # Test commit_changes - Update the existing file
        #         updated_content = new_file_content + "\nUpdated content."
        #         commit_msg_update = f"Test: Update {new_file_path}"
        #         print(f"\nUpdating file '{new_file_path}' on branch '{test_branch_name}'...")
        #         # Fetching SHA for update (alternatively, pass commit_details_create['sha_of_the_blob_or_file'])
        #         # For simplicity here, we let the method fetch it.
        #         commit_details_update = handler.commit_changes(
        #             branch_name=test_branch_name,
        #             commit_message=commit_msg_update,
        #             file_path=new_file_path,
        #             new_content=updated_content
        #         )
        #         if commit_details_update:
        #             print(f"File '{new_file_path}' updated. Commit SHA: {commit_details_update['sha']}")


        #         # Test create_pull_request
        #         pr_title = f"Test PR from SDK: {test_branch_name}"
        #         pr_body = "This is an automated test pull request created by the GitHubHandler."
        #         print(f"\nCreating pull request from '{test_branch_name}' to 'main'...")
        #         pr_info = handler.create_pull_request(
        #             title=pr_title,
        #             body=pr_body,
        #             head_branch=test_branch_name,
        #             base_branch="main" # Or your default branch
        #         )
        #         if pr_info:
        #             print(f"Pull request #{pr_info['number']} created: {pr_info['html_url']}")
        #         else:
        #             print(f"Failed to create pull request or it might already exist.")

        #     else:
        #         print(f"Skipping further write tests as branch creation/initial commit failed.")
        # else:
        #     print(f"Branch creation failed, skipping commit and PR tests.")

    except ConnectionError as e:
        print(f"Connection Error: {e}")
    except ValueError as e:
        print(f"Value Error: {e}")
    except Exception as e: # Catch any other unexpected errors during setup or testing
        print(f"An unexpected error occurred: {e}")
        logger.exception("Unexpected error in example usage block.")

    print("\n--- GitHubHandler tests finished ---")

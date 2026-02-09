"""Common methods shared by some of the scripting tools."""

import subprocess
import sys
from shutil import which

import git

DOCKER_COMMAND = "docker" if which("docker") is not None else "podman"


def check_docker_image_exists(image_url: str) -> bool:
    """
    Check if a Docker image exists in the specified registry.

    Args:
        image_url: The full URL of the Docker image including registry and tag

    Returns
    -------
        bool: True if the image exists, False otherwise
    """
    try:
        # Using subprocess to run the docker pull command to check image existence
        # The '--quiet' option minimizes output
        print(f"Attempting to verify container exists: {image_url}.")
        result = subprocess.run(
            [DOCKER_COMMAND, "manifest", "inspect", image_url], capture_output=True, text=True, check=False
        )

        # If the command exited with 0, the image exists
        return result.returncode == 0
    except Exception as e:
        print(f"Warning: Failed to check if Docker image exists: {e}", file=sys.stderr)
        # Continue with the process even if checking fails
        return False


def get_current_commit_sha() -> str:
    """
    Get the current Git commit SHA of the repository.

    Returns
    -------
        str: The current Git commit SHA.

    Raises
    ------
        SystemExit: If not in a Git repository or SHA cannot be determined.
    """
    try:
        repo = git.Repo(search_parent_directories=True)
        if repo.is_dirty():  # Check if repo object is valid by checking dirty status
            pass  # Valid repo
        commit_sha = repo.head.commit.hexsha
        if not commit_sha:
            raise ValueError("Commit SHA is empty.")
        print(f"Using current Git commit SHA for prototype image tag: {commit_sha}")
        return commit_sha
    except git.InvalidGitRepositoryError:
        print("Error: Not inside a Git repository. Cannot determine commit SHA.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error getting current Git commit SHA: {e}", file=sys.stderr)
        sys.exit(1)


def check_uncommitted_changes() -> None:
    """
    Checks for uncommitted changes in the current Git repository.

    If changes are found, warns the user and asks for confirmation to proceed.
    """
    try:
        repo = git.Repo(search_parent_directories=True)
        if repo.is_dirty(untracked_files=True):
            print("\nWarning: There are uncommitted changes in your working directory.", file=sys.stderr)
            print("Changes will not be present in the deployed prototype image unless committed.", file=sys.stderr)
            print("The image will be tagged with the LATEST COMMITTED SHA or version.", file=sys.stderr)

            user_input = input("Do you wish to continue with the deployment? (yes/no): ").strip().lower()
            if user_input not in ["y", "yes"]:
                print("Aborted by user due to uncommitted changes.", file=sys.stderr)
                sys.exit(1)
            print("Continuing deployment despite uncommitted changes...")
        else:
            print("No uncommitted changes detected in the current repository.")
    except git.InvalidGitRepositoryError:
        print("Warning: Could not check for uncommitted changes (not a Git repository). Proceeding...", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Error checking for uncommitted changes: {e}. Proceeding...", file=sys.stderr)

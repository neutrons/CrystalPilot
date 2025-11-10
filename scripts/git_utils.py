"""Git repository utilities for project setup."""

import sys
from pathlib import Path

import git


def init_repository() -> None:
    """Initialize a git repository, make the initial commit, and prepare for push.

    This function will:
    - Initialize a git repository if one doesn't exist.
    - Set the default branch to 'main'.
    - Add or update the 'origin' remote to point to the GitLab repository:
      https://code.ornl.gov/ndip/tool-sources/single-crystal-diffraction/crystalpilot
    - Stage all files.
    - Create an initial commit if no commits exist.

    It will ask for confirmation before proceeding and will NOT push the changes.
    """
    try:
        # Determine repository path
        # We need to organize the groups under tool sources and provide them an option of location
        remote_url = "https://code.ornl.gov/ndip/tool-sources/single-crystal-diffraction/"
        remote_url += "crystalpilot"

        # --- Confirmation Step ---
        print("\n--- Git Repository Setup Plan ---")
        if not Path(".git").exists():
            print("- Initialize a new Git repository in the current directory.")
        else:
            print("- Use existing Git repository.")

        # Check current branch name before potential modification
        try:
            current_branch = git.Repo(".").active_branch.name
            if current_branch != "main":
                print(f"- Rename current branch '{current_branch}' to 'main'.")
        except git.InvalidGitRepositoryError:
            # Repo doesn't exist yet, will be created with main implicitly or explicitly
            print("- Set default branch to 'main'.")
        except TypeError:  # Handle detached HEAD state
            print("- Set HEAD to 'main' branch.")

        try:
            git.Repo(".").remote("origin")
            print(f"- Update 'origin' remote URL to: {remote_url}")
        except (ValueError, git.InvalidGitRepositoryError):
            print(f"- Add 'origin' remote with URL: {remote_url}")

        print("- Stage all files for commit.")
        try:
            _ = git.Repo(".").head.commit
            print("- Repository already has commits, skipping initial commit.")
            commit_action = "No initial commit needed."
        except (ValueError, git.InvalidGitRepositoryError):
            print("- Create initial commit with message: 'Initial commit from NOVA Application Template'")
            commit_action = "Create initial commit."

        print("-" * 30)
        confirm = input("Proceed with the above Git actions? (yes/no): ").lower()
        if confirm not in ["yes", "y"]:
            print("Operation cancelled by user.")
            sys.exit(0)

        # --- Execute Actions ---
        print("\nExecuting Git actions...")

        # Initialize git repository if not already initialized
        if not Path(".git").exists():
            print("Initializing git repository...")
            repo = git.Repo.init(".")
            # Explicitly set the initial branch name to main if initializing
            repo.git.checkout("-b", "main")
        else:
            repo = git.Repo(".")

        # Ensure we're using 'main' as the default branch
        if repo.active_branch.name != "main":
            # Handle detached head state before renaming
            if repo.head.is_detached:
                print("HEAD is detached, checking out main...")
                try:
                    repo.git.checkout("main")
                except git.GitCommandError:
                    print("Branch 'main' doesn't exist, creating and checking out...")
                    repo.git.checkout("-b", "main")
            else:
                print(f"Renaming branch '{repo.active_branch.name}' to 'main'...")
                repo.active_branch.rename("main")

        # Setup remote
        try:
            origin = repo.remote("origin")
            if origin.url != remote_url:
                print(f"Setting remote URL: {remote_url}")
                repo.git.remote("set-url", "origin", remote_url)
            else:
                print("Remote 'origin' URL already set correctly.")
        except ValueError:
            print(f"Adding remote: {remote_url}")
            repo.create_remote("origin", remote_url)

        # Add all files
        print("Adding files to repository...")
        repo.git.add(".")

        # Make initial commit if needed
        if commit_action == "Create initial commit.":
            print("Making initial commit...")
            repo.git.commit("-m", "Initial commit from NOVA Application Template")
        else:
            print("Skipping initial commit as repository already has commits.")

        # --- Post-Action Instructions ---
        print("\nRepository setup complete (changes NOT pushed).")
        print("Please review the changes:")
        print("  git status")
        print("  git diff --staged")
        print("\nIf everything looks correct, push the changes manually:")
        print("  git push --set-upstream origin main")

    except git.GitCommandError as e:
        print(f"Git error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing repository: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    init_repository()

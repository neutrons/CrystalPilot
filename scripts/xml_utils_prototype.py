"""Utility for pushing PROTOTYPE tool XML to Galaxy tools repository."""

import os
import sys
import tempfile
from pathlib import Path

import git

from .utils import check_docker_image_exists, check_uncommitted_changes, get_current_commit_sha


def push_tool_xml_prototype() -> None:
    """Push the PROTOTYPE tool XML file to the Galaxy tools XML repository.

    This function will:
    - Check for uncommitted changes in the current repository.
    - Determine the current Git commit SHA for the prototype image tag.
    - Check for the source XML file (`xml/tool.xml`).
    - Determine the project version (from pyproject.toml or default to 'latest').
    - Clone the Galaxy tools repository (`https://code.ornl.gov/ndip/galaxy-tools.git`) into a temporary directory.
    - Check out the 'prototype' branch.
    - Construct the destination path for the XML file.
    - Replace placeholders in the XML content (version, container details).
    - Check if the corresponding Docker image exists (with a prompt to continue if not found).
    - Write the modified XML to the temporary clone.
    - Check if there are changes to commit.
    - **Ask for confirmation before committing and pushing.**
    - If confirmed and changes exist, add, commit, and push the XML file to the 'prototype' branch.
    """
    try:
        # Check for uncommitted changes first
        check_uncommitted_changes()

        # Get current commit SHA for prototype image tag
        prototype_image_tag = get_current_commit_sha()

        xml_source = Path("xml/tool.xml")
        if not xml_source.exists():
            print(f"Error: Tool XML file not found at {xml_source}", file=sys.stderr)
            sys.exit(1)

        # Get current project version for container tag
        with open("pyproject.toml", "r") as f:
            for line in f:
                if line.startswith("version = "):
                    version = line.split("=")[1].strip().strip("\"'")
                    break

        # Temporary directory for Galaxy tools repo
        with tempfile.TemporaryDirectory() as temp_dir:
            # Clone Galaxy tools repository
            galaxy_tools_repo = "https://code.ornl.gov/ndip/galaxy-tools.git"
            print(f"Cloning Galaxy tools repository: {galaxy_tools_repo}")

            try:
                repo = git.Repo.clone_from(galaxy_tools_repo, temp_dir)
            except git.GitCommandError as e:
                print(f"Error cloning repository: {e}", file=sys.stderr)
                sys.exit(1)

            repo.git.checkout("prototype")
            # Destination path within the tools repo
            dest_dir = os.path.join(temp_dir, "tools", "neutrons", "single-crystal-diffraction")
            xml_filename = "crystalpilot.xml"

            # Create destination directory if it doesn't exist
            os.makedirs(dest_dir, exist_ok=True)

            # XML destination in the Galaxy tools repo
            xml_dest = os.path.join(dest_dir, xml_filename)

            # Read the source XML
            with open(xml_source, "r") as src_file:
                xml_content = src_file.read()

            # Replace placeholders with actual values
            container_registry = "savannah.ornl.gov"
            container_path = "ndip/tool-sources/single-crystal-diffraction/crystalpilot/prototypes"

            # Construct the full Docker image URL
            docker_image = f"{container_registry}/{container_path}:{prototype_image_tag}"

            # Check if the Docker image exists
            image_exists = check_docker_image_exists(docker_image)
            if not image_exists:
                print(f"Warning: Docker image {docker_image} could not be verified.", file=sys.stderr)
                print("You should build and push the Docker image before pushing the XML.", file=sys.stderr)

                user_input = input("Continue anyway? (y/n): ").strip().lower()
                if user_input != "y":
                    print("Aborted by user.", file=sys.stderr)
                    sys.exit(1)
                print("Continuing without Docker image verification...", file=sys.stderr)

            xml_content = xml_content.replace("@TOOL_VERSION@", version)
            xml_content = xml_content.replace("@CONTAINER_REGISTRY@", container_registry)
            xml_content = xml_content.replace("@CONTAINER_PATH@", container_path)
            xml_content = xml_content.replace("@CONTAINER_TAG@", prototype_image_tag)

            # Write the modified XML to the destination
            with open(xml_dest, "w") as dest_file:
                dest_file.write(xml_content)

            # Check for changes
            has_changes = False
            if repo.is_dirty(untracked_files=True) or xml_dest not in [item.a_path for item in repo.index.diff(None)]:
                has_changes = True

            if not has_changes:
                print("No changes detected in the XML file within the Galaxy tools repo clone.")
            else:
                # --- Confirmation Step ---
                print("\n--- Galaxy Tools XML Push Plan ---")
                print(f"- Repository: {galaxy_tools_repo}")
                print("- Branch: prototype")
                print(f"- File to add/update: {xml_dest.replace(temp_dir, 'galaxy-tools')}")  # Show relative path
                commit_msg = f"Add/update tool XML for CrystalPilot (v{version})"
                print(f"- Commit message: '{commit_msg}'")
                print("- Action: Add, commit, and push the changes.")
                print("-" * 30)

                confirm = input("Proceed with pushing the XML to Galaxy tools? (yes/no): ").lower()
                if confirm not in ["yes", "y"]:
                    print("Operation cancelled by user.")
                    # No sys.exit here, just finish the function without pushing
                else:
                    # --- Execute Actions ---
                    print("\nExecuting Galaxy tools push...")
                    # Add the XML file
                    repo.git.add(xml_dest)

                    # Commit changes
                    print(f"Committing changes with message: '{commit_msg}'")
                    repo.git.commit("-m", commit_msg)

                    # Push changes to prototype branch
                    print("Pushing XML to Galaxy tools repository (prototype branch)...")
                    repo.git.push("--set-upstream", "origin", "prototype")
                    print("Tool XML successfully pushed to Galaxy tools repository (prototype branch)!")

    except git.GitCommandError as e:
        print(f"Git error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    push_tool_xml_prototype()

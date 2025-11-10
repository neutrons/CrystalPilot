"""Utility for deploying production tool XML to the Galaxy tools repository."""

import os
import sys
import tempfile
from pathlib import Path

import git
import gitlab

from .utils import check_docker_image_exists, check_uncommitted_changes, get_current_commit_sha

GITLAB_URL = os.getenv("GITLAB_URL", "https://code.ornl.gov")
GITLAB_PRIVATE_TOKEN = os.getenv("GITLAB_PRIVATE_TOKEN")
if GITLAB_PRIVATE_TOKEN is None:
    raise ValueError("Environment variable GITLAB_PRIVATE_TOKEN must be set.")

PROJECT_NAME_RAW = "CrystalPilot"
PROJECT_SLUG = "crystalpilot"
TOOL_CI_PATH = "ndip/tool-sources/single-crystal-diffraction/" + PROJECT_SLUG
GITLAB_PROJECT_PATH_GALAXY_TOOLS = "ndip/galaxy-tools"


def trigger_production_build(commit_sha: str) -> str:
    """
    Triggers a production build pipeline on GitLab for the current branch at the given commit SHA.

    Returns the web URL of the created pipeline.
    """
    gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_PRIVATE_TOKEN)
    project = gl.projects.get(TOOL_CI_PATH)
    pipeline_id = project.commits.get(commit_sha).last_pipeline["id"]
    pipeline = project.pipelines.get(pipeline_id)
    jobs = pipeline.jobs.list()

    job_found = False
    for job in jobs:
        if job.name == "build-prod-image":
            j = project.jobs.get(job.id)
            j.play()
            job_found = True
            break

    if job_found is False:
        raise RuntimeError("Production image build was not found.")

    print(f"Successfully started production build job: {pipeline.web_url}")
    return pipeline.web_url


def deploy_production_xml() -> None:
    """Deploy the PRODUCTION tool XML file to the Galaxy tools XML repository.

    This function orchestrates the production deployment process:
    1.  Checks for uncommitted changes in the current tool repository.
    2.  Verifies the existence of the production Docker image (versioned by pyproject.toml).
        - If the image exists, warns the user and asks for confirmation to proceed.
        - If the image does NOT exist, triggers a GitLab CI pipeline to build it.
          The pipeline URL is captured for inclusion in the Merge Request.
    3.  Clones the Galaxy tools repository.
    4.  Checks out the 'dev' branch.
    5.  Creates a new feature branch (e.g., feature/tool-name-vX.Y.Z).
    6.  Prepares the tool XML (replaces placeholders with version, container details).
    7.  Writes the modified XML to the feature branch in the cloned Galaxy tools repo.
    8.  Commits and pushes the feature branch.
    9.  Creates a Merge Request from the feature branch to 'dev' in the Galaxy tools repository.
        - The MR description includes the link to the build pipeline if one was triggered.
    10. Prompts the user to review the MR and assign a reviewer.
    """
    try:
        pipeline_url = None
        check_uncommitted_changes()

        # Get current project version for container tag
        try:
            with open("pyproject.toml", "r") as f:
                for line in f:
                    if line.startswith("version = "):
                        version = line.split("=")[1].strip().strip("\"'")
                        break
        except Exception:
            version = "latest"

        # Construct the full Docker image URL
        container_registry = "savannah.ornl.gov"
        container_path = "ndip/tool-sources/single-crystal-diffraction/crystalpilot"
        docker_image = f"{container_registry}/{container_path}:{version}"

        # Check if the Docker image exists
        image_exists = check_docker_image_exists(docker_image)
        if image_exists:
            print(f"Warning: Production Docker image {docker_image} already exists.", file=sys.stderr)
            print("You may have forgot to update the version in pyproject.toml.", file=sys.stderr)
            print("It is HIGHLY RECOMMENDED to update the version for a new deployment.", file=sys.stderr)
            user_input_existing = input("Do you want to proceed with this existing image? (yes/no): ").strip().lower()
            if user_input_existing not in ["yes", "y"]:
                print("Aborted. Update version in pyproject.toml or verify the image name/tag.", file=sys.stderr)
                sys.exit(1)
            print(f"Continuing with existing image {docker_image}...", file=sys.stderr)
        else:
            print(f"Information: Production Docker image {docker_image} was not found.", file=sys.stderr)
            current_commit_sha = get_current_commit_sha()
            print(f"Attempting to start a production build pipeline for commit {current_commit_sha}", file=sys.stderr)
            try:
                pipeline_url = trigger_production_build(current_commit_sha)
                print(f"Production build pipeline started: {pipeline_url}", file=sys.stderr)
                print("Monitor the pipeline. The XML will be pushed once the image build is started.", file=sys.stderr)
            except Exception as e:
                print("Failed to start production build pipeline.", file=sys.stderr)
                print(e)
                user_input_fail = (
                    input(
                        """There was an issue starting the build. Continue with XML push anyway?
                        This may lead to a non-functional tool if the image is missing) (yes/no): """
                    )
                    .strip()
                    .lower()
                )
                if user_input_fail not in ["yes", "y"]:
                    print("Aborted by user due to build initiation failure.", file=sys.stderr)
                    sys.exit(1)
                print("Continuing XML push despite build issue. The image may not be available.", file=sys.stderr)

        # XML source file in the current project
        xml_source = Path("xml/tool.xml")
        if not xml_source.exists():
            print(f"Error: Tool XML file not found at {xml_source}", file=sys.stderr)
            sys.exit(1)

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

            # Checkout dev branch
            print("Checking out 'dev' branch in Galaxy tools repository...")
            repo.git.checkout("dev")
            repo.git.pull("origin", "dev")  # Ensure dev is up-to-date

            # Create a new branch from dev
            project_name_slug = "crystalpilot"
            new_branch_name = f"feature/{project_name_slug}-v{version}"
            print(f"Creating new branch '{new_branch_name}' from 'dev'...")
            try:
                repo.git.checkout("-b", new_branch_name)
            except git.GitCommandError as e:
                if "already exists" in str(e):
                    print(f"Branch '{new_branch_name}' already exists. Checking it out...")
                    repo.git.checkout(new_branch_name)
                else:
                    raise

            # Destination path within the tools repo
            dest_dir = os.path.join(temp_dir, "tools", "neutrons")
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
            container_path = "ndip/tool-sources/single-crystal-diffraction/crystalpilot"

            xml_content = xml_content.replace("@TOOL_VERSION@", version)
            xml_content = xml_content.replace("@CONTAINER_REGISTRY@", container_registry)
            xml_content = xml_content.replace("@CONTAINER_PATH@", container_path)
            xml_content = xml_content.replace("@CONTAINER_TAG@", version)

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
                print(f"- Target Repository: {galaxy_tools_repo}")
                print("- Target Base Branch: dev")
                print(f"- New Source Branch: {new_branch_name}")
                print(f"- File to add/update: {xml_dest.replace(temp_dir, 'galaxy-tools')}")
                commit_msg = f"Add/update tool XML for {project_name_slug} v{version}"
                print(f"- Commit message: '{commit_msg}'")
                mr_title = f"Add/update tool XML for {project_name_slug} v{version}"
                print(f"- Merge Request Title: '{mr_title}'")
                mr_description = f"This MR adds/updates the Galaxy tool XML for {project_name_slug} version {version}."
                if pipeline_url:
                    mr_description += f"\n\nProduction build pipeline: {pipeline_url}"
                print(f"- Merge Request Description:\n{mr_description}")
                print("- Action: Add, commit, push new branch, and create Merge Request to 'dev'.")
                print("-" * 30)

                confirm = input(f"Proceed with pushing '{new_branch_name}' and creating MR? (yes/no): ").lower()
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

                    # Push changes to the new feature branch
                    print(f"Pushing XML to Galaxy tools repository (branch '{new_branch_name}')...")
                    repo.git.push("--set-upstream", "origin", new_branch_name)
                    print(f"Tool XML successfully pushed to branch '{new_branch_name}' in Galaxy tools repository!")

                    # Create Merge Request
                    print(f"Creating Merge Request from '{new_branch_name}' to 'dev'...")
                    try:
                        gl_galaxy = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_PRIVATE_TOKEN)
                        # Use the project path for galaxy tools to get the project object
                        galaxy_project = gl_galaxy.projects.get(GITLAB_PROJECT_PATH_GALAXY_TOOLS)
                        mr = galaxy_project.mergerequests.create(
                            {
                                "source_branch": new_branch_name,
                                "target_branch": "dev",
                                "title": mr_title,
                                "description": mr_description,
                                "remove_source_branch": True,
                            }
                        )
                        print(f"Successfully created Merge Request: {mr.web_url}")
                        print("Please review the Merge Request and assign a reviewer.")
                    except Exception as e_mr:
                        print(f"Error creating Merge Request: {e_mr}", file=sys.stderr)
                        print(f"Please create the MR manually from '{new_branch_name}' to 'dev'.", file=sys.stderr)
                        if pipeline_url:
                            print(f"Please include pipeline URL in the description: {pipeline_url}", file=sys.stderr)

    except git.GitCommandError as e:
        print(f"Git error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    deploy_production_xml()

import os
import sys
import argparse
from huggingface_hub import HfApi

def deploy():
    parser = argparse.ArgumentParser(description="Deploy SLA-Guard to Hugging Face Spaces")
    parser.add_argument("--username", type=str, default="Saeed0296", help="Your Hugging Face username")
    parser.add_argument("--token", type=str, help="Your Hugging Face Access Token with WRITE permissions")
    args = parser.parse_args()

    username = args.username
    token = args.token

    if not token:
        print("Error: Hugging Face Access Token is required. Use --token flag.")
        sys.exit(1)

    project_dir = "/Users/saeedanwar/Desktop/saeed/project/sla_guard"
    repo_id = f"{username}/sla-guard"
    
    print(f"Connecting to Hugging Face to check/create repository: {repo_id}...")
    api = HfApi()

    try:
        # Create Space repo if not exists
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=False,
            exist_ok=True,
            token=token
        )
        print(f"Repository {repo_id} ready on Hugging Face Spaces.")
    except Exception as e:
        print(f"Error checking/creating repository: {e}")
        sys.exit(1)

    print("Uploading folder contents to Hugging Face Spaces...")
    try:
        # Upload folder, excluding local cache files and git configs
        api.upload_folder(
            folder_path=project_dir,
            repo_id=repo_id,
            repo_type="space",
            token=token,
            ignore_patterns=[".git", ".DS_Store", "venv", "jupyter_env", "__pycache__"]
        )
        print("\n" + "="*80)
        print("UPLOAD COMPLETED SUCCESSFULLY!")
        print(f"Your application is now building. You can view the status and access the dashboard at:")
        print(f"👉 https://huggingface.co/spaces/{repo_id}")
        print("="*80)
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    deploy()

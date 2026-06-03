import os
import boto3
from botocore.exceptions import NoCredentialsError

def upload_multiple_files_to_s3(file_mapping, bucket_name):
    """
    Uploads multiple local files to their respective S3 destinations.
    
    :param file_mapping: A dictionary where key = local file path, value = S3 target key
    :param bucket_name: Name of the target S3 bucket
    """
    # Initialize the S3 client once
    s3_client = boto3.client('s3')
    
    print(f"Starting batch upload of {len(file_mapping)} files to bucket '{bucket_name}'...\n")
    
    # Loop through each file in our mapping
    for local_path, s3_key in file_mapping.items():
        try:
            # Check if the local file actually exists before trying to upload
            if not os.path.exists(local_path):
                print(f"❌ Error: Local file '{local_path}' not found. Skipping...")
                continue
                
            print(f"Uploading {local_path} ──► s3://{bucket_name}/{s3_key}...")
            
            # Upload the file
            s3_client.upload_file(local_path, bucket_name, s3_key)
            print("file uploaded")
            
        except NoCredentialsError:
            print("❌ Error: AWS credentials not found. Run 'aws configure' first.")
            return False
        except Exception as e:
            print(f"❌ Failed to upload {local_path}. Error: {e}")
            
    print("\n🏁 Batch upload complete!")
    return True

# --- CONFIGURATION ---
TARGET_BUCKET = 'walmart-project-330420072894-us-east-2-an'

# Map your local files to their distinct S3 folder destinations
# Format: 'local_filename.csv': 's3_folder/sub_folder/s3_filename.csv'
WALMART_FILES_TO_UPLOAD = {
    'department.csv': 'department_data/department.csv',
    'stores.csv':      'store_data/stores.csv',
    'fact.csv':  'sales_data/fact.csv'
}

# Run the batch execution
if __name__ == "__main__":
    upload_multiple_files_to_s3(WALMART_FILES_TO_UPLOAD, TARGET_BUCKET)

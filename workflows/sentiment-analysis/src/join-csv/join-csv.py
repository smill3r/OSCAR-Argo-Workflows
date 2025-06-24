import csv
import os
import sys
import json
from minio import Minio
from minio.error import S3Error

# Function to merge multiple CSV files into a single file
def join_csv(file_paths, output_file):
    # Tracks if the header has already been written
    header_written = False

    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)

        for file_path in file_paths:
            try:
                # Open each CSV file and read its content
                with open(file_path, newline='', encoding='utf-8') as infile:
                    reader = csv.reader(infile)
                    # Read the header
                    header = next(reader)

                    # Write the header only once
                    if not header_written:
                        writer.writerow(header)
                        header_written = True

                    # Write the rows from the current file to the output file
                    for row in reader:
                        writer.writerow(row)
            except FileNotFoundError:
                # Warn if a local file is not found
                print(f"[WARN] Local file not found: {file_path}. It will be skipped.", file=sys.stderr)

# Main function to handle configuration, file download, merging, and upload
def main():
    # Ensure the script is called with the correct number of arguments
    if len(sys.argv) != 2:
        print("Usage: python join_csv.py <config_json>", file=sys.stderr)
        sys.exit(1)

    # Load configuration from the provided JSON file
    config_path = sys.argv[1]
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)

    # List of CSV files to merge
    file_list = config["file_list"]
    # Output path for the merged file
    output_path = config["output_path"]

    # MinIO configuration
    endpoint = os.getenv("server_host", None)
    access_key = os.getenv("access_key", None)
    secret_key = os.getenv("secret_key", None)
    secure = os.getenv("secure", "false").lower() == "true"

    # Ensure MinIO credentials are provided
    if not endpoint or not access_key or not secret_key:
        raise ValueError("Missing secret values for MinIO configuration")

    # Initialize the MinIO client
    minio_client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure
    )

    # List to store paths of downloaded files
    local_files = []
    for file_path in file_list:
        # Extract the file name
        local_file = os.path.basename(file_path)
         # Split bucket and object name
        bucket_name, object_name = file_path.split("/", 1)

        try:
            # Download the file from MinIO
            minio_client.fget_object(bucket_name, object_name, local_file)
            local_files.append(local_file)
        except S3Error as e:
            # Warn if a file could not be downloaded
            print(f"[WARN] Could not download {file_path}: {e.code}. It will be skipped.", file=sys.stderr)

    # Abort if no files were successfully downloaded
    if not local_files:
        print("[ERROR] No files were successfully downloaded. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Merge the downloaded files
    merged_file = config["result_file_name"]
    join_csv(local_files, merged_file)

    # Upload the merged file back to MinIO
    bucket_name, object_prefix = output_path.split("/", 1)
    remote_path = f"{object_prefix}/{merged_file}"
    minio_client.fput_object(bucket_name, remote_path, merged_file)

    # Print a success message with the output file path
    print(json.dumps({
        "message": "Merged file uploaded to MinIO",
        "output_file": f"{bucket_name}/{remote_path}"
    }))

# Entry point of the script
if __name__ == "__main__":
    main()
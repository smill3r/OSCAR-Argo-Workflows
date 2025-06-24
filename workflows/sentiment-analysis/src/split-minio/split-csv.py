import csv
import os
import sys
import json
from minio import Minio

# Number of records per file, configurable from the JSON file
RECORDS_PER_FILE = 100

# Function to split a CSV file into multiple smaller files
def split_csv(local_input_path, output_dir):
    original_file_name = os.path.splitext(os.path.basename(local_input_path))[0]
    output_folder = os.path.join(output_dir, original_file_name)
    os.makedirs(output_folder, exist_ok=True)
    output_files = []

    with open(local_input_path, newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        # Get the header of the original file
        header = next(reader)

        chunk = []
        file_count = 1

        # Iterate over the rows of the original file
        for i, row in enumerate(reader, start=1):
            chunk.append(row)
            # When the limit of records per file is reached
            if len(chunk) == RECORDS_PER_FILE:
                output_file = write_chunk(header, chunk, output_folder, original_file_name, file_count)
                output_files.append(output_file)
                chunk = []
                file_count += 1

        # If there are rows left unwritten after the last iteration
        if chunk:
            output_file = write_chunk(header, chunk, output_folder, original_file_name, file_count)
            output_files.append(output_file)

    # Return the list of generated files
    return output_files

# Function to write a CSV file with a header and a set of rows
def write_chunk(header, rows, output_folder, original_file_name, index):
    filename = f"{original_file_name}-{index}.csv"
    filepath = os.path.join(output_folder, filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(rows)

    return filepath

# Main function that handles configuration, download, splitting, and uploading of files
def main():
    if len(sys.argv) != 2:
        print("Usage: python split_csv.py <config_json>", file=sys.stderr)
        sys.exit(1)

    # Load configuration from a JSON file
    config_path = sys.argv[1]
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)

    # Path of the original CSV file in MinIO
    input_path = config["input_path"]
    # Output path for the split files
    output_path = config["output_path"]
    # Number of records per file
    records_per_file = config["records_per_file"]

    # MinIO configuration
    endpoint = os.getenv("server_host", None)
    access_key = os.getenv("access_key", None)
    secret_key = os.getenv("secret_key", None)
    secure = os.getenv("secure", "false").lower() == "true"

    if not endpoint or not access_key or not secret_key:
        raise ValueError("Missing secret values for minio configuration")

    global RECORDS_PER_FILE
    RECORDS_PER_FILE = records_per_file

    # Initialize the MinIO client with the provided credentials
    minio_client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure
    )

    # Download the original CSV file from MinIO
    local_input_path = os.path.basename(input_path)
    bucket_name, object_name = input_path.split("/", 1)
    minio_client.fget_object(bucket_name, object_name, local_input_path)

    # Split the CSV file into multiple smaller files
    output_files = split_csv(local_input_path, output_path)

    uploaded_files = []

    bucket_name, object_prefix = output_path.split("/", 1)

    # Upload the generated files to MinIO
    for output_file in output_files:
        filename = os.path.basename(output_file)
        remote_path = f"{object_prefix}/{filename}"

        minio_client.fput_object(bucket_name, remote_path, output_file)
        uploaded_files.append(f"{bucket_name}/{remote_path}")

    print(json.dumps({
        "message": "Files generated and uploaded to MinIO",
        "output_files": uploaded_files
    }))

if __name__ == "__main__":
    main()
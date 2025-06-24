import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import argparse
import os
from pathlib import Path
from time import time
import json
from minio import Minio
import requests
import traceback

# Load the pre-trained RoBERTa model for sentiment analysis
def load_model():
    model_name = "cardiffnlp/twitter-roberta-base-sentiment"
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    return model

# Perform sentiment analysis on the comments in the DataFrame
def analyze_sentiment(df, text_column, model):
    print(f"Analyzing sentiment for {len(df)} comments...")

    tokenizer = AutoTokenizer.from_pretrained("cardiffnlp/twitter-roberta-base-sentiment")
    sentiments = []
    scores = []
    labels = ["NEGATIVE", "NEUTRAL", "POSITIVE"]

    for text in df[text_column]:
        if not isinstance(text, str) or not text.strip():
            sentiments.append("NEUTRAL")
            scores.append(0.0)
            continue

        inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")

        with torch.no_grad():
            outputs = model(**inputs)

        probabilities = torch.softmax(outputs.logits, dim=1)[0]
        pred_label = torch.argmax(probabilities).item()

        if pred_label == 0:
            score = -probabilities[0].item()
        elif pred_label == 1:
            score = 0.0
        else:
            score = probabilities[2].item()

        sentiments.append(labels[pred_label])
        scores.append(score)

    df['sentiment'] = sentiments
    df['sentiment_score'] = scores
    return df

# Send notification
def notify(config, success=True, message=""):
    notify_cfg = config.get("notify", False)
    if not notify_cfg:
        return

    token = os.getenv("argo_token", None)
    endpoint = notify_cfg.get("success_endpoint") if success else notify_cfg.get("error_endpoint")
    data = notify_cfg.get("data", {})

    if not token or not endpoint or not data:
        print("Error: Notification not configured correctly.")
        return

    # You can add result information
    if not success:
        data["message"] = message

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.put(endpoint, json=data, headers=headers, verify=False)
        if response.status_code == 200:
            print("Notification sent successfully.")
        else:
            print(f"Error sending notification: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error trying to send notification: {e}")

# Main function
def main():
    parser = argparse.ArgumentParser(description="RoBERTa Sentiment Analysis")
    parser.add_argument("config_path", help="Path to the configuration file")
    parser.add_argument("output_path", help="Path to the output directory")
    args = parser.parse_args()

    config_path = Path(args.config_path)

    try:
        if not config_path.exists():
            raise FileNotFoundError(f"Input path not found: {args.config_path}")

        with open(config_path, 'r') as config_file:
            config = json.load(config_file)

        input_path = config["input_path"]
        analysis_column = config.get("analysis_column", "comment")

        # MinIO configuration
        endpoint = os.getenv("server_host", None)
        access_key = os.getenv("access_key", None)
        secret_key = os.getenv("secret_key", None)
        secure = os.getenv("secure", "false").lower() == "true"

        minio_client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )

        file_name = os.path.basename(input_path)
        local_input_path = file_name
        bucket_name, object_name = input_path.split("/", 1)
        minio_client.fget_object(bucket_name, object_name, local_input_path)

        print(f"Loading data from {local_input_path}...")
        df = pd.read_csv(local_input_path)

        print("Loading RoBERTa model...")
        start = time()
        model = load_model()
        print(f"Model loaded in {time() - start:.2f}s")

        if analysis_column not in df.columns:
            raise ValueError(f"Column '{analysis_column}' not found. Available columns: {list(df.columns)}")

        print("Analyzing sentiment...")
        df = analyze_sentiment(df, analysis_column, model)

        os.makedirs(args.output_path, exist_ok=True)
        output_file = Path(args.output_path) / file_name
        print(f"Saving results to {output_file}...")
        df.to_csv(output_file, index=False)
        print("Analysis completed!")

        if config.get("notify", False):
            notify(config, success=True, message="Analysis completed successfully")

    except Exception as e:
        error_msg = str(e)
        print(f"An error occurred: {error_msg}")
        if 'config' in locals():
            notify(config, success=False, message=error_msg)

if __name__ == "__main__":
    main()
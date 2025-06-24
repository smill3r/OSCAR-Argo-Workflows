import praw
import pandas as pd
from datetime import datetime
import json
import os
import sys

# Leer argumentos de entrada
input_path = sys.argv[1]
output_dir = sys.argv[2]

# Leer configuración desde el JSON de entrada
with open(input_path, "r") as f:
    config = json.load(f)

input_filename = os.path.splitext(os.path.basename(input_path))[0]

client_id = os.getenv("reddit_client_id", None)
client_secret = os.getenv("reddit_client_secret", None)
user_agent = os.getenv("reddit_user_agent", "reddit_data_collector")

if not client_id or not client_secret:
    raise ValueError("Por favor, establece las variables de entorno 'reddit_client_id' y 'reddit_client_secret'.")

subreddits = config["subreddits"]
keywords = config["keywords"]
limit = config.get("limit", 10)
max_comments_per_post = config.get("max_comments_per_post", 100)

# Configurar conexión con Reddit
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    user_agent=user_agent
)

data = []

# Buscar comentarios
for subreddit in subreddits:
    for keyword in keywords:
        # Limita cuántos posts devuelve la búsqueda por keyword en ese subreddit.
        posts = reddit.subreddit(subreddit).search(keyword, limit=limit)
        for post in posts:
            # Solo se conservan los comentarios ya cargados por defecto (los más relevantes o primeros)
            post.comments.replace_more(limit=0)
            for comment in post.comments:
                data.append({
                    "subreddit": subreddit,
                    "keyword": keyword,
                    "post_title": post.title,
                    "comment": comment.body,
                    "comment_score": comment.score,
                    "created_utc": datetime.fromtimestamp(comment.created_utc),
                    "num_comments": post.num_comments,
                    "url": post.url
                })

# Guardar resultados en CSV en la carpeta temporal de salida
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, f"{input_filename}.csv")
df = pd.DataFrame(data)
df.to_csv(output_path, index=False)
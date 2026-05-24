from dotenv import load_dotenv
import requests
import os


load_dotenv()
YC_API_KEY = os.getenv('YC_API_KEY')
YC_FOLDER_ID = os.getenv("YC_FOLDER_ID", "b1gdhar0cvv1mgn23gpg")
HEADERS = {
    "Authorization": f"Api-Key {YC_API_KEY}",
    "Content-Type": "application/json",
    "x-folder-id": YC_FOLDER_ID,
}


def embed_courses(course_text, *, model_type: str = "doc"):
    model_name = "text-search-query" if model_type == "query" else "text-search-doc"
    req = {
      "modelUri": f"emb://{YC_FOLDER_ID}/{model_name}/latest",
      "text": course_text,
    }
    response = requests.post(os.getenv("YC_URL"), json=req, headers=HEADERS)
    if response.status_code != 200:
        raise RuntimeError(f"Yandex embedding API error {response.status_code}: {response.text}")
    return response.json()['embedding']

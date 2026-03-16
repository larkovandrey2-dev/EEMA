from dotenv import load_dotenv
import requests
import os


load_dotenv()
YC_API_KEY = os.getenv('YC_API_KEY')
HEADERS = {
    "Authorization": f"Bearer {YC_API_KEY}",
    "Content-Type": "application/json",
    "x-folder-id": "b1gdhar0cvv1mgn23gpg",
}


def embed_courses(course_text):
    req = {
      "modelUri": "emb://b1gdhar0cvv1mgn23gpg/text-search-doc/latest",
      "text": course_text,
    }
    response = requests.post(os.getenv("YC_URL"), json=req, headers=HEADERS)
    return response.json()['embedding']


import os
import json
import time
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import silhouette_score, f1_score
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA


load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
def parse_embedding(emb):
    if isinstance(emb, str):
        return np.array(json.loads(emb), dtype=np.float64)
    elif isinstance(emb, list):
        return np.array(emb, dtype=np.float64)
    return np.zeros(256)


def run_ml_pipeline():
    print("Скачиваем все векторы из БД")

    all_data = []
    page_size = 1000
    current_page = 0

    while True:
        start = current_page * page_size
        end = start + page_size - 1

        response = supabase.table("courses") \
            .select("id, embedding") \
            .not_.is_("embedding", "null") \
            .range(start, end) \
            .execute()

        batch = response.data
        if not batch:
            break

        all_data.extend(batch)
        print(f"Загружено {len(all_data)} строк")

        if len(batch) < page_size:
            break

        current_page += 1

    if not all_data:
        print("Нет курсов с векторами")
        return

    df = pd.DataFrame(all_data)
    print(f"Загружено {len(df)} курсов. Запускаем математику")
    embedding_matrix = np.vstack(df['embedding'].apply(parse_embedding))
    _, s, _ = np.linalg.svd(embedding_matrix)
    pref_sums = [s[0]]
    for i in range(1, len(embedding_matrix[0])):
        pref_sums.append(pref_sums[-1] + s[i])
    pref_sums = np.asarray(pref_sums, dtype=np.float64)
    pref_sums /= pref_sums.max()
    n_comp = len(embedding_matrix[0])
    for i in range(len(embedding_matrix[0]) - 1, 1, -1):
        if pref_sums[i] < 0.96:
            n_comp = i
            break

    print(f"Размерность снижена с {len(embedding_matrix[0])} до {n_comp} компонент")
    pca = PCA(n_components=n_comp)
    new_embeddings = pca.fit_transform(embedding_matrix)
    df_new_embeddings = pd.DataFrame(new_embeddings)
    print("Ищем оптимальное количество кластеров")
    sil_scores = []
    max_clusters_to_check = min(30, len(df))
    for i in range(2, max_clusters_to_check):
        clust = GaussianMixture(n_components=i, random_state=42)
        y_pred = clust.fit_predict(df_new_embeddings)
        sil_scores.append(silhouette_score(df_new_embeddings, y_pred))

    clust_count = sil_scores.index(max(sil_scores)) + 2
    print(f"Оптимальное количество кластеров: {clust_count}")
    clust = GaussianMixture(n_components=clust_count, random_state=42)
    final_clusters = clust.fit_predict(df_new_embeddings)
    df["cluster_id"] = final_clusters
    print(f"Сохраняем {clust_count} кластеров обратно в Supabase")
    updated_count = 0

    for index, row in df.iterrows():
        course_id = row['id']
        c_id = int(row['cluster_id'])

        try:
            supabase.table("courses").update({"cluster_id": c_id}).eq("id", course_id).execute()
            updated_count += 1
            print(f"Сохранено: {updated_count}")
        except Exception as e:
            print(f"Ошибка на курсе {course_id}: {e}")

        time.sleep(0.01)

    print(f"Успешно обновлен cluster_id у {updated_count} курсов.")


if __name__ == "__main__":
    run_ml_pipeline()
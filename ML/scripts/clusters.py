import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
from sklearn.metrics.cluster import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA

def str_to_array_decompose(s):
  return np.array(list(map(float,s[1:-1].split(","))),dtype=np.float64)

def clusterize_data(courses_file: str) -> tuple[pd.DataFrame, GradientBoostingClassifier, np.float64, np.float64]:
  df = pd.read_csv(courses_file)
  df_embeddings = df['embedding'].apply(str_to_array_decompose)
  embedding_matrix = np.vstack(df_embeddings)

  _, s, _ = np.linalg.svd(embedding_matrix)
  pref_sums = [s[0]]
  for i in range(1,len(embedding_matrix[0])):
    pref_sums.append(pref_sums[-1] + s[i])
  pref_sums = np.asarray(pref_sums,dtype=np.float64)
  pref_sums /= pref_sums.max()

  n_comp = 0
  for i in range(len(embedding_matrix[0]) - 1, 1, -1):
    if pref_sums[i] < 0.96:
      n_comp = i
      break

  pca = PCA(n_components=n_comp)
  new_embeddings = pca.fit_transform(embedding_matrix)

  df_new_embeddings = pd.DataFrame(new_embeddings, columns=["e" + str(i) for i in range(len(new_embeddings[0]))])

  sil_scores = []
  for i in range(2,100):
    clust = GaussianMixture(n_components=i, random_state=42)
    y_pred = clust.fit_predict(df_new_embeddings)
    sil_scores.append(silhouette_score(df_new_embeddings, y_pred))

  clust_count = sil_scores.index(max(sil_scores)) + 2

  clust = GaussianMixture(n_components=clust_count, random_state=42)
  y_pred = clust.fit_predict(df_new_embeddings)

  gbc = GradientBoostingClassifier()

  df_embeddings = df['embedding'].apply(str_to_array_decompose)
  embedding_matrix = np.vstack(df_embeddings)
  df_embeddings = pd.DataFrame(embedding_matrix, columns=["e" + str(i) for i in range(len(embedding_matrix[0]))])

  X = df_embeddings
  y = y_pred

  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42, shuffle=True)

  gbc.fit(X_train,y_train)

  y_pred_ = gbc.predict(X_test)

  df["cluster"] = pd.Series(y_pred)

  return df, gbc, silhouette_score(df_new_embeddings, y_pred), f1_score(y_test, y_pred_, average="macro")

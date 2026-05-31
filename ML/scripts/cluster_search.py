from sklearn.metrics.pairwise import cosine_distances
import numpy as np
import pandas as pd

def get_fitting_courses(course, df_courses, amount=3):
  cluster: pd.DataFrame = df_courses[df_courses["cluster"] == course['cluster']]
  emb_ = cluster['embedding'].apply(lambda s: np.array(list(map(float,s[1:-1].split(","))),dtype=np.float64))
  emb = np.vstack(emb_)
  clust = pd.DataFrame(cosine_distances([np.array(list(map(float,course["embedding"][1:-1].split(","))),
                                              dtype=np.float64)], emb)[0],cluster.index,columns=["dist"])
  cluster = pd.concat([cluster, clust],axis=1)
  cluster = cluster.sort_values("dist")
  cluster.drop(columns=["dist"], inplace=True)
  return cluster.head(amount+1)[1:]

import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.decomposition import PCA

n_routes, n_intl, dist_sum = {}, {}, {}
for src, dst, d in zip(routes["src_country"], routes["dst_country"], routes["distance_km"]):
    n_routes[src] = n_routes.get(src, 0) + 1
    dist_sum[src] = dist_sum.get(src, 0) + d
    if src != dst:
        n_intl[src] = n_intl.get(src, 0) + 1

countries["n_routes"] = [n_routes.get(c, 0) for c in countries["iso_country"]]
countries["intl_route_share"] = [n_intl.get(c, 0) / n_routes[c] if c in n_routes else 0
                                 for c in countries["iso_country"]]
countries["mean_route_km"] = [dist_sum[c] / n_routes[c] if c in n_routes else 0
                              for c in countries["iso_country"]]

big = countries[countries["population"] >= 1_000_000].copy().reset_index(drop=True)
big["log_routes"] = np.log1p(big["n_routes"])
feats = ["open_per_1000km2", "open_per_million", "sched_per_1000km2", "sched_per_million",
         "share_scheduled", "log_routes", "intl_route_share", "mean_route_km"]
X = big[feats].copy()
for c in ["open_per_1000km2", "open_per_million", "sched_per_1000km2", "sched_per_million"]:
    X[c] = np.log1p(X[c]) 
X = X.fillna(0)
Xs = StandardScaler().fit_transform(X)

ks = list(range(2, 11)); inertias = []
for k in ks:
    m = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xs)
    inertias.append(m.inertia_)
print([round(i, 1) for i in inertias])

plt.figure(figsize=(6, 4))
plt.plot(ks, inertias, marker="o")
plt.title("Elbow plot"); plt.xlabel("Number of clusters (k)"); plt.ylabel("Inertia")
plt.tight_layout(); plt.savefig("k_selection.png", dpi=150); plt.show()


K = 6
km = KMeans(n_clusters=K, n_init=10, random_state=42).fit(Xs)
big["cluster"] = km.labels_

prof = big.groupby("cluster")[["open_per_1000km2", "open_per_million", "sched_per_million",
        "share_scheduled", "n_routes", "intl_route_share", "mean_route_km"]].median().round(2)
prof["countries"] = big.groupby("cluster").size()
print(prof.to_string())
for c in range(K):
    sub = big[big["cluster"] == c].sort_values("population", ascending=False)
    print(c, sub["country"].head(9).tolist())

pcs = PCA(n_components=2).fit_transform(Xs)
plt.figure(figsize=(7, 5.5))
for c in range(K):
    m = big["cluster"] == c
    plt.scatter(pcs[m, 0], pcs[m, 1], label=f"Cluster {c}", alpha=0.8)
for name in ["United States", "Singapore", "Germany", "Canada", "India", "Sudan"]:
    j = big.index[big["country"] == name][0]
    plt.annotate(name, (pcs[j, 0], pcs[j, 1]), fontsize=8)
plt.legend(); plt.title("Countries by aviation profile (PCA view)")
plt.tight_layout(); plt.savefig("clusters_pca.png", dpi=150); plt.show()

for s in [1, 2, 3, 4, 5]:
    other = KMeans(n_clusters=K, n_init=10, random_state=s).fit(Xs).labels_
    print(s, round(adjusted_rand_score(km.labels_, other), 2))

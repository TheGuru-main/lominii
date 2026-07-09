"""PageRank Service (Platform Layer)"""
from collections import defaultdict

def compute_pagerank(graph: dict, damping=0.85, max_iter=100, tol=1.0e-6):
    """Compute PageRank for a graph {url: [outgoing links]}."""
    urls = list(graph.keys())
    n = len(urls)
    if n == 0:
        return {}

    url_to_idx = {url: i for i, url in enumerate(urls)}
    pr = [1.0 / n] * n
    out_degree = {url: len(links) for url, links in graph.items()}

    for _ in range(max_iter):
        new_pr = [0.0] * n
        for i, url in enumerate(urls):
            if out_degree[url] == 0:
                for j in range(n):
                    new_pr[j] += pr[i] / n
            else:
                for link in graph[url]:
                    if link in url_to_idx:
                        j = url_to_idx[link]
                        new_pr[j] += damping * pr[i] / out_degree[url]
                    else:
                        for j in range(n):
                            new_pr[j] += damping * pr[i] / (n * out_degree[url])
        for j in range(n):
            new_pr[j] += (1 - damping) / n
        diff = sum(abs(new_pr[i] - pr[i]) for i in range(n))
        if diff < tol:
            break
        pr = new_pr

    return {urls[i]: pr[i] for i in range(n)}
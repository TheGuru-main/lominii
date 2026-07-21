"""PageRank Service (Platform Layer)
Enhanced while preserving the original algorithm.

Features:
- Classical PageRank
- Personalization support
- Precomputed incoming links
- Precomputed dangling nodes
- Optional weighted-edge support
- Graph metadata for analytics/admin
"""

from collections import defaultdict


def compute_pagerank(
    graph: dict,
    damping=0.85,
    max_iter=100,
    tol=1.0e-6,
    personalization=None,
    return_metadata=False,
):
    """
    Compute PageRank.

    Supported graph formats:

    1. Unweighted (existing)
       {
           "A": ["B", "C"],
           "B": ["C"]
       }

    2. Weighted (new)
       {
           "A": {"B": 5, "C": 1},
           "B": {"C": 3}
       }
    """

    urls = list(graph.keys())
    n = len(urls)

    if n == 0:
        return {} if not return_metadata else {
            "scores": {},
            "metadata": {}
        }

    url_to_idx = {url: i for i, url in enumerate(urls)}

    # -------------------------------------------------
    # Personalization
    # -------------------------------------------------

    if personalization:
        total = sum(personalization.get(u, 0.0) for u in urls)

        if total > 0:
            pr = [
                personalization.get(u, 0.0) / total
                for u in urls
            ]
        else:
            pr = [1.0 / n] * n
    else:
        pr = [1.0 / n] * n

    # -------------------------------------------------
    # Precompute graph
    # -------------------------------------------------

    incoming = defaultdict(list)

    outgoing_weight = {}

    metadata = {}

    dangling_nodes = []

    for url in urls:

        links = graph.get(url, {})

        # -------------------------
        # Old format
        # -------------------------

        if isinstance(links, list):

            outgoing_weight[url] = len(links)

            if len(links) == 0:
                dangling_nodes.append(url)

            for link in links:
                if link in url_to_idx:
                    incoming[link].append((url, 1.0))

        # -------------------------
        # Weighted format
        # -------------------------

        elif isinstance(links, dict):

            total_weight = sum(links.values())

            outgoing_weight[url] = total_weight

            if total_weight == 0:
                dangling_nodes.append(url)

            for link, weight in links.items():
                if link in url_to_idx:
                    incoming[link].append((url, float(weight)))

        else:
            outgoing_weight[url] = 0
            dangling_nodes.append(url)

    # -------------------------------------------------
    # Metadata
    # -------------------------------------------------

    for url in urls:

        links = graph.get(url, {})

        outgoing = len(links) if isinstance(
            links,
            (list, dict)
        ) else 0

        metadata[url] = {
            "incoming": len(incoming[url]),
            "outgoing": outgoing,
            "dangling": url in dangling_nodes,
        }

    # -------------------------------------------------
    # PageRank Iteration
    # -------------------------------------------------

    for _ in range(max_iter):

        new_pr = [(1 - damping) / n] * n

        # Dangling distribution

        dangling_mass = sum(
            pr[url_to_idx[u]]
            for u in dangling_nodes
        )

        dangling_share = damping * dangling_mass / n

        for j in range(n):
            new_pr[j] += dangling_share

        # Incoming contributions

        for target in urls:

            target_idx = url_to_idx[target]

            for source, weight in incoming[target]:

                source_idx = url_to_idx[source]

                total = outgoing_weight[source]

                if total > 0:

                    new_pr[target_idx] += (
                        damping
                        * pr[source_idx]
                        * weight
                        / total
                    )

        diff = sum(
            abs(new_pr[i] - pr[i])
            for i in range(n)
        )

        pr = new_pr

        if diff < tol:
            break

    scores = {
        urls[i]: pr[i]
        for i in range(n)
    }

    if return_metadata:
        return {
            "scores": scores,
            "metadata": metadata,
        }

    return scores
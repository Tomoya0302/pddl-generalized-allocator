from collections import deque

def bfs_component(start, adjacency):
    visited = set([start])
    q = deque([start])
    while q:
        v = q.popleft()
        for u in adjacency.get(v, []):
            if u not in visited:
                visited.add(u)
                q.append(u)
    return visited

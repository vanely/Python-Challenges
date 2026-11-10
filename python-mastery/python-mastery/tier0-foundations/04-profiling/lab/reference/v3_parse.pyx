# cython: language_level=3
"""v3 — the parse+aggregate loop in Cython. Build: python setup.py build_ext --inplace
Then: python v3_cython.py access.log"""
from collections import defaultdict

cpdef dict aggregate(str path):
    cdef dict latencies = {}
    cdef dict users = {}
    cdef str line, status_s, ep, user, lat_s
    cdef int status, lat
    cdef tuple key
    cdef list parts
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.split(" ")
            status = int(parts[1])
            ep = parts[2]
            user = parts[3][5:]
            lat = int(parts[4][11:])
            key = (status, ep)
            if key in latencies:
                (<list>latencies[key]).append(lat)
                (<set>users[key]).add(user)
            else:
                latencies[key] = [lat]
                users[key] = {user}
    return {"latencies": latencies, "users": users}

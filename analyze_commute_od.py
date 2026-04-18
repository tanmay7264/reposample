"""
Commute OD (Origin-Destination) Traffic Analysis - Pendeln
Analyzes commuting flows between zones: volumes, directions, peaks, and top corridors.
"""

import random
import math
from collections import defaultdict

random.seed(42)

# --- Zones (districts) ---
ZONES = {
    "Z01": "Mitte",
    "Z02": "Prenzlauer Berg",
    "Z03": "Friedrichshain",
    "Z04": "Kreuzberg",
    "Z05": "Schöneberg",
    "Z06": "Tempelhof",
    "Z07": "Neukölln",
    "Z08": "Treptow",
    "Z09": "Pankow",
    "Z10": "Weissensee",
}

# Zone centroids (x, y) in km
CENTROIDS = {
    "Z01": (0.0,  0.0),
    "Z02": (1.5,  3.0),
    "Z03": (3.0,  1.0),
    "Z04": (1.0, -2.0),
    "Z05": (-2.0, -1.5),
    "Z06": (-1.0, -5.0),
    "Z07": (2.0, -4.0),
    "Z08": (5.0, -3.0),
    "Z09": (1.0,  6.0),
    "Z10": (4.0,  5.0),
}

# Employment attractiveness (higher = more jobs → more in-commuters)
ATTRACTIVENESS = {
    "Z01": 3.0, "Z02": 1.2, "Z03": 1.5, "Z04": 1.4,
    "Z05": 1.1, "Z06": 0.8, "Z07": 0.9, "Z08": 0.7,
    "Z09": 1.0, "Z10": 0.6,
}

ZONE_IDS = list(ZONES.keys())


def distance(z1: str, z2: str) -> float:
    x1, y1 = CENTROIDS[z1]
    x2, y2 = CENTROIDS[z2]
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def gravity_trips(origin: str, dest: str, base: int = 800) -> int:
    """Gravity model: trips ∝ attractiveness / distance²."""
    if origin == dest:
        return 0
    d = max(distance(origin, dest), 0.5)
    raw = base * ATTRACTIVENESS[dest] / (d ** 1.8)
    noise = random.gauss(1.0, 0.12)
    return max(0, int(raw * noise))


# --- Build OD matrix ---
od_matrix: dict[tuple[str, str], int] = {}
for o in ZONE_IDS:
    for d in ZONE_IDS:
        if o != d:
            od_matrix[(o, d)] = gravity_trips(o, d)

# --- Summary statistics ---
total_trips = sum(od_matrix.values())
num_pairs   = len(od_matrix)

print("=" * 60)
print("   COMMUTE OD TRAFFIC ANALYSIS – PENDELN")
print("=" * 60)
print(f"\nZones analysed : {len(ZONES)}")
print(f"OD pairs       : {num_pairs}")
print(f"Total trips    : {total_trips:,}")
print(f"Avg trips/pair : {total_trips / num_pairs:,.1f}")

# --- Top 10 OD corridors ---
print("\n--- Top 10 OD Corridors ---")
top_pairs = sorted(od_matrix.items(), key=lambda x: x[1], reverse=True)[:10]
print(f"{'Rank':<5} {'Origin':<20} {'Destination':<20} {'Trips':>8}  {'Dist(km)':>9}")
print("-" * 65)
for rank, ((o, d), trips) in enumerate(top_pairs, 1):
    dist = distance(o, d)
    print(f"{rank:<5} {ZONES[o]:<20} {ZONES[d]:<20} {trips:>8,}  {dist:>9.2f}")

# --- Zone-level totals ---
departures: dict[str, int] = defaultdict(int)
arrivals:   dict[str, int] = defaultdict(int)

for (o, d), trips in od_matrix.items():
    departures[o] += trips
    arrivals[d]   += trips

print("\n--- Zone Summary (Departures / Arrivals / Net) ---")
print(f"{'Zone':<20} {'Departures':>12} {'Arrivals':>10} {'Net (Arr-Dep)':>14}")
print("-" * 58)
for zid in ZONE_IDS:
    dep = departures[zid]
    arr = arrivals[zid]
    net = arr - dep
    bar = "▲" if net > 0 else "▼"
    print(f"{ZONES[zid]:<20} {dep:>12,} {arr:>10,} {net:>+13,} {bar}")

# --- Intra-zone share ---
intra = sum(gravity_trips(z, z, 800) for z in ZONE_IDS)  # all zero by design
print(f"\nIntra-zone trips: {intra:,} (internal commutes excluded)")

# --- Distance distribution ---
dist_buckets: dict[str, int] = defaultdict(int)
for (o, d), trips in od_matrix.items():
    d_km = distance(o, d)
    if d_km < 3:
        bucket = "< 3 km (short)"
    elif d_km < 6:
        bucket = "3–6 km (medium)"
    else:
        bucket = "> 6 km (long)"
    dist_buckets[bucket] += trips

print("\n--- Trips by Distance Band ---")
for band, count in sorted(dist_buckets.items()):
    share = 100 * count / total_trips
    bar   = "█" * int(share / 2)
    print(f"  {band:<22} {count:>8,}  ({share:5.1f}%)  {bar}")

# --- Directional balance (symmetry) ---
print("\n--- Directional Balance (top asymmetric pairs) ---")
asymmetry: list[tuple[float, str, str, int, int]] = []
checked: set[frozenset] = set()
for (o, d) in od_matrix:
    key = frozenset([o, d])
    if key in checked:
        continue
    checked.add(key)
    fwd = od_matrix.get((o, d), 0)
    bwd = od_matrix.get((d, o), 0)
    if fwd + bwd == 0:
        continue
    ratio = max(fwd, bwd) / (min(fwd, bwd) + 1)
    asymmetry.append((ratio, o, d, fwd, bwd))

asymmetry.sort(reverse=True)
print(f"{'Pair':<35} {'A→B':>8} {'B→A':>8} {'Ratio':>7}")
print("-" * 60)
for ratio, o, d, fwd, bwd in asymmetry[:8]:
    pair = f"{ZONES[o]} ↔ {ZONES[d]}"
    print(f"{pair:<35} {fwd:>8,} {bwd:>8,} {ratio:>7.2f}x")

# --- Key findings ---
top_origin = max(departures, key=departures.get)
top_dest   = max(arrivals,   key=arrivals.get)
top_od     = top_pairs[0]

print("\n--- Key Findings ---")
print(f"  Strongest origin zone : {ZONES[top_origin]} ({departures[top_origin]:,} departures)")
print(f"  Strongest dest. zone  : {ZONES[top_dest]} ({arrivals[top_dest]:,} arrivals)")
print(f"  Busiest corridor      : {ZONES[top_od[0][0]]} → {ZONES[top_od[0][1]]} ({top_od[1]:,} trips)")
short_pct = 100 * dist_buckets["< 3 km (short)"] / total_trips
print(f"  Short-distance share  : {short_pct:.1f}% of all commutes are < 3 km")
print()
print("Analysis complete.")

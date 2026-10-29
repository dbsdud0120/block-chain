"""파트 1 그래프와 통계표.

실행:  python part1_plot.py
결과:  results/part1_plot.png, results/part1_stats.csv
"""
import csv
import json
import os
import statistics as st
from collections import defaultdict

import matplotlib.pyplot as plt

import sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "results"

with open(os.path.join(OUT, "part1_runs.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
with open(os.path.join(OUT, "part1_summary.json"), encoding="utf-8") as f:
    summary = json.load(f)
r = summary["hash_rate_r"]

groups = defaultdict(list)
for row in rows:
    groups[(row["phase"], float(row["target_exponent"]))].append(row)

stats = []
for (phase, k), g in sorted(groups.items(), key=lambda x: -x[0][1]):
    done = [float(x["seconds"]) for x in g if x["completed"] == "True"]
    att = [int(x["attempts"]) for x in g if x["completed"] == "True"]
    stats.append({
        "phase": phase,
        "target_exponent": round(k, 4),
        "runs": len(g),
        "completed": len(done),
        "incomplete": len(g) - len(done),
        "mean_s": st.mean(done) if done else "",
        "std_s": st.stdev(done) if len(done) > 1 else "",
        "min_s": min(done) if done else "",
        "max_s": max(done) if done else "",
        "mean_attempts": st.mean(att) if att else "",
        "expected_attempts": 2 ** (256 - k),
        "expected_s": 2 ** (256 - k) / r,
    })

with open(os.path.join(OUT, "part1_stats.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(stats[0].keys()))
    w.writeheader()
    w.writerows(stats)

fig, ax = plt.subplots(figsize=(8, 5))

# 개별 시행 (완료)
for phase, color in [("sweep", "tab:blue"), ("tstar", "tab:orange")]:
    xs = [float(x["target_exponent"]) for x in rows if x["phase"] == phase and x["completed"] == "True"]
    ys = [float(x["seconds"]) for x in rows if x["phase"] == phase and x["completed"] == "True"]
    ax.scatter(xs, ys, s=14, alpha=0.4, color=color, label=f"individual runs ({phase})")

# 미완료 시행
xs = [float(x["target_exponent"]) for x in rows if x["completed"] != "True"]
ys = [float(x["seconds"]) for x in rows if x["completed"] != "True"]
if xs:
    ax.scatter(xs, ys, marker="x", color="red", s=40, label="incomplete (timeout)")

# 평균 ± 표준편차
for phase, color in [("sweep", "tab:blue"), ("tstar", "tab:orange")]:
    s = [x for x in stats if x["phase"] == phase and x["mean_s"] != ""]
    ax.errorbar([x["target_exponent"] for x in s], [x["mean_s"] for x in s],
                # 로그 축에서는 mean-std가 음수가 될 수 있어 아래쪽 막대를 mean의 95%로 제한
                yerr=[[min(x["std_s"] or 0, 0.95 * x["mean_s"]) for x in s], [x["std_s"] or 0 for x in s]],
                fmt="o-" if phase == "sweep" else "s",
                color=color, capsize=4, label=f"mean ± std ({phase})")

# 이론 기대 시간 2^(256-k)/r
ks = [x["target_exponent"] for x in stats]
kk = [min(ks) + i * (max(ks) - min(ks)) / 100 for i in range(101)]
ax.plot(kk, [2 ** (256 - k) / r for k in kk], "--", color="gray", label="expected 2^(256-k)/r")

ax.set_yscale("log")
ax.invert_xaxis()
ax.set_xlabel("Target exponent k  (T = 2^k)")
ax.set_ylabel("Mining time (seconds, log scale)")
ax.set_title(f"SHA-256 PoW mining time vs target  (r ≈ {r:,.0f} H/s, n = {summary['trials_per_target']} per target)")
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "part1_plot.png"), dpi=200)

for s in stats:
    print(s)
print(f"저장 완료: {OUT}/part1_plot.png, {OUT}/part1_stats.csv")

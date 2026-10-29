
"""파트 2 그림: 변경 전후 체인 다이어그램, 블록별 채굴 시간.

실행:  python part2_plot.py
결과:  results/part2_diagram.png, results/part2_times.png
"""
import csv
import json
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = sys.argv[1] if len(sys.argv) > 1 else "results"


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


orig = load("chain_original.json")["blocks"]
tamp = load("chain_tampered.json")["blocks"]
reco = load("chain_recovered.json")["blocks"]
val = load("part2_validation.json")
summ = load("part2_summary.json")

# ---------- 그림 1: 체인 다이어그램 ----------
C_OK, C_BAD, C_NEW, C_STALE = "#dbe8f5", "#f4b6b0", "#fbd7a4", "#ececec"
fig, ax = plt.subplots(figsize=(15, 6.2))
ax.set_xlim(-1.6, 10.2)
ax.set_ylim(0.1, 3.3)
ax.axis("off")

rows = [
    (2.6, "Original\n(valid)", orig, val["original"]),
    (1.45, "Tampered\n(block 6 data\nchanged only)", tamp, val["tampered"]),
    (0.3, "Recovered\n(6–10 re-mined)", reco, val["recovered"]),
]
W, H = 0.86, 0.62


def short(h):
    # 앞 6자 + 뒤 6자: 다음 블록의 prev 끝자리와 맞춰 보면 연결을 확인할 수 있다
    return f"{h[:6]}…{h[-6:]}"

for y, label, chain, checks in rows:
    ax.text(-1.5, y + H / 2, label, va="center", ha="left", fontsize=10, fontweight="bold")
    for i, (b, c) in enumerate(zip(chain, checks)):
        x = i
        if label.startswith("Tampered"):
            color = C_BAD if not c["valid"] else (C_STALE if b["index"] > 6 else C_OK)
        elif label.startswith("Recovered") and b["index"] >= 6:
            color = C_NEW
        else:
            color = C_OK
        ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.02", fc=color, ec="#444", lw=1))
        txt = f"#{b['index']}\nhash {short(b['hash'])}\nprev {short(b['prev_hash'])}"
        ax.text(x + W / 2, y + H / 2, txt, ha="center", va="center", fontsize=7, family="monospace")
        if i < 9:
            ax.annotate("", xy=(x + 1, y + H / 2), xytext=(x + W, y + H / 2),
                        arrowprops=dict(arrowstyle="->", color="#444", lw=0.8))

bad = next(c for c in val["tampered"] if not c["valid"])
fails = [k.replace("_ok", "") for k in ["index_ok", "target_ok", "hash_ok", "pow_ok", "link_ok"] if not bad[k]]
ax.text(5 + W / 2, 1.45 - 0.08, f"✗ fails: {', '.join(fails)}\nrecomputed {short(bad['recomputed_hash'])}",
        ha="center", va="top", fontsize=7.5, color="#b02a1f")
ax.text(8 + W / 2, 1.45 - 0.08, "7–10 unchanged (not auto-updated)", ha="center", va="top", fontsize=7.5, color="#555")

handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="#444") for c in (C_OK, C_BAD, C_STALE, C_NEW)]
ax.legend(handles, ["valid / unchanged", "fails validation", "unchanged but built on altered block",
                    "re-mined (new nonce & hash)"],
          loc="upper center", bbox_to_anchor=(0.55, 1.04), ncol=4, fontsize=8.5, frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "part2_diagram.png"), dpi=200)

# ---------- 그림 2: 블록별 채굴 시간 ----------
with open(os.path.join(OUT, "part2_mining_log.csv"), encoding="utf-8") as f:
    log = list(csv.DictReader(f))
o = {int(x["index"]): float(x["seconds"]) for x in log if x["stage"] == "original"}
r = {int(x["index"]): float(x["seconds"]) for x in log if x["stage"] == "recovery"}

fig, ax = plt.subplots(figsize=(9, 4.5))
idx = list(range(1, 11))
ax.bar([i - 0.2 for i in idx], [o[i] for i in idx], width=0.4, label="original", color="#5b8fc9")
ax.bar([i + 0.2 for i in r], [r[i] for i in r], width=0.4, label="recovery (re-mined)", color="#e8963a")
ax.axhline(summ["expected_seconds_per_block"], ls="--", color="gray",
           label=f"expected per block ≈ {summ['expected_seconds_per_block']:.0f} s")
ax.set_xticks(idx)
ax.set_xlabel("Block number")
ax.set_ylabel("Mining time (seconds)")
rec = summ["recovery"]
ax.set_title(f"Per-block mining time at T* = 2^{summ['target_log2']:.2f}   "
             f"(recovery total {rec['mining_seconds']:.0f} s vs expected {rec['expected_seconds']:.0f} s)")
ax.legend(fontsize=8.5)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "part2_times.png"), dpi=200)
print(f"저장 완료: {OUT}/part2_diagram.png, {OUT}/part2_times.png")

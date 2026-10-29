"""파트 2: 고정 목표값 T*로 블록 10개 채굴 → 검증 → 6번 변조 → 6~10번 재채굴 → 재검증.

실행:  python part2_chain.py
입력:  results/part1_summary.json (T*와 해시 속도 r)
결과:  results/chain_original.json        원본 체인
       results/chain_tampered.json        6번 데이터만 변경한 직후 체인 (해시 갱신 전)
       results/chain_tampered_hash_only.json  (보충) 6번 해시만 재계산해 덮어쓴 체인
       results/chain_recovered.json       6~10번을 재채굴한 체인
       results/part2_mining_log.csv       블록별 논스, 해시, 해시 계산 횟수, 시간
       results/part2_comparison.csv       원본과 복구 체인 블록별 비교표
       results/part2_validation.json      단계별 검증 결과
       results/part2_summary.json         요약 (총 시간, 기대값 비교 등)
"""
import argparse
import copy
import csv
import json
import math
import os
import time

from pow_core import ENCODING_DESC, ZERO_HASH, block_hash, mine
from part1_mining import cpu_name

DATA = [f"tx{i}: Alice pays Bob {i * 10} coins" for i in range(1, 11)]
TAMPERED_INDEX = 6
TAMPERED_DATA = "tx6: Alice pays Mallory 6000 coins"

CHECKS = ["index_ok", "target_ok", "hash_ok", "pow_ok", "link_ok"]
CHECK_KO = {"index_ok": "번호", "target_ok": "목표값", "hash_ok": "해시 재계산",
            "pow_ok": "작업증명", "link_ok": "이전 해시 연결"}


def recompute(b: dict) -> str:
    return block_hash(b["index"], b["data"], b["prev_hash"], int(b["target"], 16), b["nonce"])


def verify(chain: list[dict], expected_target: int) -> list[dict]:
    """블록마다 5가지 조건을 검사한 결과를 반환한다.

    index_ok  : 블록 번호가 1, 2, ..., n 순서인가
    target_ok : 블록의 목표값이 고정 목표값 T*와 같은가
    hash_ok   : 저장된 해시 == 블록 내용(해시 필드 제외)으로 재계산한 해시
    pow_ok    : 재계산한 해시 H가 H < T* 를 만족하는가
    link_ok   : prev_hash == 이전 블록의 저장된 해시 (1번은 0 * 64)
    """
    rows = []
    for pos, b in enumerate(chain):
        h = recompute(b)
        expected_prev = ZERO_HASH if pos == 0 else chain[pos - 1]["hash"]
        row = {
            "index": b["index"],
            "index_ok": b["index"] == pos + 1,
            "target_ok": int(b["target"], 16) == expected_target,
            "hash_ok": h == b["hash"],
            "pow_ok": int(h, 16) < expected_target,
            "link_ok": b["prev_hash"] == expected_prev,
            "stored_hash": b["hash"],
            "recomputed_hash": h,
        }
        row["valid"] = all(row[c] for c in CHECKS)
        rows.append(row)
    return rows


def report(name: str, rows: list[dict]) -> bool:
    ok = all(r["valid"] for r in rows)
    print(f"\n[검증] {name}: {'통과' if ok else '실패'}")
    for r in rows:
        if not r["valid"]:
            failed = [CHECK_KO[c] for c in CHECKS if not r[c]]
            print(f"  블록 {r['index']:2}: 실패 → {', '.join(failed)}")
            if not r["hash_ok"]:
                print(f"           저장 해시   {r['stored_hash']}")
                print(f"           재계산 해시 {r['recomputed_hash']}")
    return ok


def save_chain(path: str, label: str, chain: list[dict], target: int) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"label": label, "encoding": ENCODING_DESC,
                   "hash_input_excludes": "hash", "target_hex": f"{target:064x}",
                   "blocks": chain}, f, ensure_ascii=False, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/part1_summary.json")
    ap.add_argument("--out", default="results")
    ap.add_argument("--target-log2", type=float, default=None,
                    help="테스트용으로만 사용: T*대신 2^x를 쓴다 (제출용 실행에서는 쓰지 말 것)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    with open(args.summary, encoding="utf-8") as f:
        p1 = json.load(f)
    T = int(p1["t_star_int"]) if args.target_log2 is None else int(2 ** args.target_log2)
    r = p1["hash_rate_r"]
    expected_block_s = (2 ** 256 / T) / r
    if cpu_name() != p1["hardware"]["cpu"]:
        print(f"경고: 파트 1과 CPU가 다릅니다 ({p1['hardware']['cpu']} → {cpu_name()})")
    print(f"T* = 2^{math.log2(T):.4f}  (블록당 기대 시간 ≈ {expected_block_s:.1f}s)")

    log_rows = []

    def mine_block(stage: str, b: dict) -> None:
        res = mine(b["index"], b["data"], b["prev_hash"], T)
        b["nonce"], b["hash"] = res["nonce"], res["hash"]
        log_rows.append({"stage": stage, "index": b["index"], "data": b["data"],
                         "prev_hash": b["prev_hash"], "nonce": res["nonce"], "hash": res["hash"],
                         "attempts": res["attempts"], "seconds": f"{res['seconds']:.6f}"})
        print(f"[{stage:8}] 블록 {b['index']:2}  nonce={res['nonce']:>11,}  "
              f"attempts={res['attempts']:>11,}  time={res['seconds']:8.2f}s  hash={res['hash'][:16]}…")

    # 1) 원본 체인 채굴
    chain, prev = [], ZERO_HASH
    t0 = time.perf_counter()
    for i in range(1, 11):
        b = {"index": i, "data": DATA[i - 1], "prev_hash": prev, "target": f"{T:064x}", "nonce": None, "hash": None}
        mine_block("original", b)
        chain.append(b)
        prev = b["hash"]
    original_wall = time.perf_counter() - t0
    save_chain(os.path.join(args.out, "chain_original.json"), "original", chain, T)
    v_original = verify(chain, T)
    assert report("원본 체인", v_original), "원본 체인이 검증에 실패했습니다."

    # 2) 6번 블록 데이터만 변경 (해시 갱신 전 검증)
    tampered = copy.deepcopy(chain)
    tampered[TAMPERED_INDEX - 1]["data"] = TAMPERED_DATA
    save_chain(os.path.join(args.out, "chain_tampered.json"), "tampered (data only, before re-hash)", tampered, T)
    v_tampered = verify(tampered, T)
    report("변조 직후 체인 (6번 데이터만 변경)", v_tampered)

    # (보충) 6번 해시만 재계산해 덮어쓰면? → 작업증명과 7번 연결이 깨짐을 보인다
    hash_only = copy.deepcopy(tampered)
    hash_only[TAMPERED_INDEX - 1]["hash"] = recompute(hash_only[TAMPERED_INDEX - 1])
    save_chain(os.path.join(args.out, "chain_tampered_hash_only.json"),
               "supplementary: block 6 hash overwritten without re-mining", hash_only, T)
    v_hash_only = verify(hash_only, T)
    report("(보충) 6번 해시만 덮어쓴 체인", v_hash_only)

    # 3) 6번부터 10번까지 순서대로 재채굴
    recovered = copy.deepcopy(tampered)
    t0 = time.perf_counter()
    for pos in range(TAMPERED_INDEX - 1, 10):
        b = recovered[pos]
        b["prev_hash"] = recovered[pos - 1]["hash"]   # 직전 블록의 (새) 해시를 반영
        mine_block("recovery", b)
    recovery_wall = time.perf_counter() - t0
    save_chain(os.path.join(args.out, "chain_recovered.json"), "recovered (blocks 6-10 re-mined)", recovered, T)
    v_recovered = verify(recovered, T)
    assert report("복구 체인", v_recovered), "복구 체인이 검증에 실패했습니다."
    assert recovered[:TAMPERED_INDEX - 1] == chain[:TAMPERED_INDEX - 1], "1~5번 블록이 바뀌었습니다."
    assert all(int(b["target"], 16) == T for b in recovered)
    print("  1~5번 블록과 목표값이 원본과 동일함을 확인")

    # 4) 기록 저장
    with open(os.path.join(args.out, "part2_mining_log.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
        w.writeheader()
        w.writerows(log_rows)

    orig_log = {x["index"]: x for x in log_rows if x["stage"] == "original"}
    rec_log = {x["index"]: x for x in log_rows if x["stage"] == "recovery"}
    with open(os.path.join(args.out, "part2_comparison.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "original_data", "original_nonce", "original_hash", "original_attempts", "original_seconds",
                    "recovered_data", "recovered_nonce", "recovered_hash", "recovery_attempts", "recovery_seconds", "changed"])
        for o, n in zip(chain, recovered):
            rl = rec_log.get(o["index"])
            w.writerow([o["index"], o["data"], o["nonce"], o["hash"], orig_log[o["index"]]["attempts"],
                        orig_log[o["index"]]["seconds"], n["data"], n["nonce"], n["hash"],
                        rl["attempts"] if rl else "", rl["seconds"] if rl else "", o["hash"] != n["hash"]])

    def strip(rows):
        return [{k: v for k, v in r.items()} for r in rows]

    with open(os.path.join(args.out, "part2_validation.json"), "w", encoding="utf-8") as f:
        json.dump({"checks": CHECK_KO, "original": strip(v_original), "tampered": strip(v_tampered),
                   "tampered_hash_only_supplementary": strip(v_hash_only), "recovered": strip(v_recovered)},
                  f, ensure_ascii=False, indent=2)

    o_att = sum(x["attempts"] for x in orig_log.values())
    o_sec = sum(float(x["seconds"]) for x in orig_log.values())
    r_att = sum(x["attempts"] for x in rec_log.values())
    r_sec = sum(float(x["seconds"]) for x in rec_log.values())
    expected_recovery = 5 * expected_block_s
    summary = {
        "target_hex": f"{T:064x}", "target_log2": math.log2(T),
        "test_override": args.target_log2 is not None,
        "cpu": cpu_name(), "part1_cpu": p1["hardware"]["cpu"],
        "hash_rate_r_part1": r,
        "expected_seconds_per_block": expected_block_s,
        "original": {"blocks": 10, "attempts": o_att, "mining_seconds": o_sec, "wall_seconds": original_wall,
                     "hash_rate": o_att / o_sec, "expected_seconds": 10 * expected_block_s},
        "recovery": {"blocks": 5, "attempts": r_att, "mining_seconds": r_sec, "wall_seconds": recovery_wall,
                     "hash_rate": r_att / r_sec, "expected_seconds": expected_recovery,
                     "ratio_to_expected": r_sec / expected_recovery},
        "tampered_block": TAMPERED_INDEX, "tampered_data": TAMPERED_DATA,
        "valid": {"original": all(x["valid"] for x in v_original),
                  "tampered": all(x["valid"] for x in v_tampered),
                  "tampered_hash_only": all(x["valid"] for x in v_hash_only),
                  "recovered": all(x["valid"] for x in v_recovered)},
    }
    with open(os.path.join(args.out, "part2_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n원본 10블록: {o_att:,}회, {o_sec:.1f}s (기대 {10 * expected_block_s:.0f}s)")
    print(f"복구 5블록 : {r_att:,}회, {r_sec:.1f}s (기대 {expected_recovery:.0f}s, 비율 {r_sec / expected_recovery:.2f})")
    print(f"저장 완료: {args.out}/")


if __name__ == "__main__":
    main()

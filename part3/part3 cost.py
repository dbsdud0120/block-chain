"""파트 3: 비트코인 블록 채굴 기대 전기요금 추정.

실행:  python part3_cost.py
       python part3_cost.py --difficulty 148710000000000 --difficulty-date 2026-10-30   (다른 기준 시점으로 바꿀 때)
결과:  results/part3_inputs.csv   입력값, 단위, 기준 시점, 출처
       results/part3_results.csv  계산 결과
       results/part3_summary.json

근사식 (과제 안내문):
    N  = D * 2^32                 블록당 기대 해시 계산 횟수 (ASIC 기준: SHA-256 2회 = 1회 시도)
    t  = N / h                    채굴기 1대의 기대 채굴 시간 (초)
    C  = P * (t / 3600) * c       블록당 기대 전기요금
    C5 = 5 * C                    고정 난이도에서 연속 블록 5개 재계산 전기요금
포함하지 않은 비용: 냉각(PUE 1.0 가정), 장비 구입·감가상각, 시설·인건비, 풀 수수료, 기본요금·부가세.
블록 보상(3.125 BTC)과 거래 수수료는 수익이므로 비용 C와 별도로 다룬다.
로컬 실험의 해시 속도(SHA-256 1회 기준)는 사용하지 않는다.
"""
import argparse
import csv
import json
import os
from decimal import Decimal, getcontext

getcontext().prec = 40

SECONDS_PER_YEAR = Decimal("31557600")  # 365.25일


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulty", default="140577680051919.59", help="비트코인 난이도 D")
    ap.add_argument("--difficulty-date", default="2026-10-28 (block 973,576; set at block 971,712 on 2026-10-16)")
    ap.add_argument("--difficulty-source", default="CoinWarz Bitcoin Difficulty Chart, https://www.coinwarz.com/mining/bitcoin/difficulty-chart")
    ap.add_argument("--hashrate-ths", default="270", help="ASIC 해시 속도 (TH/s)")
    ap.add_argument("--power-w", default="3645", help="ASIC 소비 전력 (W)")
    ap.add_argument("--asic", default="Bitmain Antminer S21 XP (air-cooled), released 2024-06-17")
    ap.add_argument("--asic-source", default="Hashrate Index, Hardware Overview: Bitmain's Antminer S21 XP, https://hashrateindex.com/blog/hardware-overview-bitmains-antminer-s21-xp/")
    ap.add_argument("--price-krw-kwh", default="185.5", help="전기요금 단가 (원/kWh)")
    ap.add_argument("--price-date", default="2026 Q3-Q4 (annual average industrial rate; Q3 and Q4 2026 rates frozen)")
    ap.add_argument("--price-source", default="딜사이트 2026-06 기사 https://dealsite.co.kr/articles/163752 ; 4분기 동결: 머니투데이방송 2026-09-21 https://news.mtn.co.kr/news-detail/2026092111090432619")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # 단위 통일: H/s, kW, 원/kWh
    D = Decimal(args.difficulty)
    h = Decimal(args.hashrate_ths) * Decimal(10) ** 12
    P = Decimal(args.power_w) / 1000
    c = Decimal(args.price_krw_kwh)

    N = D * Decimal(2) ** 32
    t = N / h
    energy_kwh = P * t / 3600
    C = energy_kwh * c
    C5 = 5 * C
    j_per_th = Decimal(args.power_w) / Decimal(args.hashrate_ths)

    inputs = [
        ["D", "Bitcoin difficulty", f"{D}", "(dimensionless)", args.difficulty_date, args.difficulty_source],
        ["h", "ASIC hash rate", f"{h:.4E}", "H/s", args.asic, args.asic_source],
        ["P", "ASIC power", f"{P}", "kW", args.asic, args.asic_source],
        ["c", "Electricity price", f"{c}", "KRW/kWh", args.price_date, args.price_source],
    ]
    results = [
        ["N", "Expected hashes per block", "D * 2^32", f"{N:.6E}", "hashes"],
        ["t", "Expected mining time (1 ASIC)", "N / h", f"{t:.6E}", "s"],
        ["t_years", "Expected mining time (1 ASIC)", "t / (365.25*86400)", f"{t / SECONDS_PER_YEAR:.2f}", "years"],
        ["E", "Expected energy per block", "P * t / 3600", f"{energy_kwh:.6E}", "kWh"],
        ["C", "Expected electricity cost per block", "P * (t/3600) * c", f"{C:.6E}", "KRW"],
        ["C5", "Electricity cost for 5 blocks (fixed D)", "5 * C", f"{C5:.6E}", "KRW"],
        ["check", "Energy via efficiency", "N * (P/h) / 3.6e6", f"{N * (Decimal(args.power_w) / h) / Decimal('3.6e6'):.6E}", "kWh"],
    ]

    with open(os.path.join(args.out, "part3_inputs.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "name", "value", "unit", "reference_date_or_model", "source"])
        w.writerows(inputs)
    with open(os.path.join(args.out, "part3_results.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "name", "formula", "value", "unit"])
        w.writerows(results)

    summary = {
        "currency": "KRW",
        "inputs": {"D": str(D), "h_Hps": str(h), "P_kW": str(P), "c_KRW_per_kWh": str(c),
                   "efficiency_J_per_TH": str(j_per_th)},
        "results": {"N": f"{N:.6E}", "t_seconds": f"{t:.6E}", "t_years": f"{t / SECONDS_PER_YEAR:.2f}",
                    "energy_kWh_per_block": f"{energy_kwh:.6E}", "C_KRW": f"{C:.0f}", "C5_KRW": f"{C5:.0f}"},
        "excluded_costs": ["cooling (PUE 1.0 assumed)", "hardware purchase and depreciation",
                           "facility and labor", "pool fees", "base charge and VAT"],
        "revenue_note": "Block subsidy 3.125 BTC + transaction fees are revenue, not offset against C.",
        "scope_note": "5C is only the electricity to compute 5 replacement blocks at fixed difficulty; "
                      "replacing history requires a competing chain with more cumulative work than the honest chain.",
        "sources": {"difficulty": args.difficulty_source, "asic": args.asic_source, "electricity": args.price_source},
    }
    with open(os.path.join(args.out, "part3_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("입력값")
    print(f"  D = {D}  ({args.difficulty_date})")
    print(f"  h = {h:.3E} H/s, P = {P} kW  ({args.asic}, {j_per_th} J/TH)")
    print(f"  c = {c} 원/kWh  ({args.price_date})")
    print("\n결과")
    print(f"  N  = {N:.4E} 회")
    print(f"  t  = {t:.4E} 초 ≈ {t / SECONDS_PER_YEAR:.1f}년 (채굴기 1대)")
    print(f"  E  = {energy_kwh:,.0f} kWh/블록")
    print(f"  C  = {C:,.0f} 원  (약 {C / Decimal(10) ** 8:.2f}억 원)")
    print(f"  C5 = {C5:,.0f} 원  (약 {C5 / Decimal(10) ** 8:.2f}억 원)")
    print(f"\n저장 완료: {args.out}/part3_inputs.csv, part3_results.csv, part3_summary.json")


if __name__ == "__main__":
    main()

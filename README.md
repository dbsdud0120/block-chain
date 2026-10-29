# 작업증명과 블록체인 기록 변경 비용

SHA-256 기반 작업증명(PoW)을 직접 구현해 목표값별 채굴 시간을 측정하고(파트 1), 블록 10개 체인을 만들어 변조·복구 실험을 하고(파트 2), 비트코인 블록 채굴의 기대 전기요금을 추정한다(파트 3).

채굴 루프, 체인 생성, 검증기는 직접 구현했고, 해시 계산에는 Python 표준 라이브러리 `hashlib.sha256`만 사용했다.

---

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| CPU | Intel(R) Core(TM) Ultra 5 125H (논리 프로세서 18개) |
| RAM | (직접 기입) |
| OS | Windows 11 (10.0.26200) |
| Python | CPython 3.12.10 |
| 실행 방식 | 단일 프로세스, 단일 스레드 |
| 전원 | 어댑터 연결, Windows 전원 모드 "최고 성능" |

파트 1의 T* 보정 실험과 파트 2는 같은 노트북, 같은 블록 인코딩으로 실행했다.

## 2. 필요한 라이브러리

- 표준 라이브러리: `hashlib`, `time`, `csv`, `json`, `decimal`, `argparse`, `math`, `statistics`, `copy`, `platform`
- 외부 라이브러리: `matplotlib` (그래프 생성용)

```bash
pip install matplotlib
```

## 3. 블록 인코딩 (결정적)

모든 해시 입력은 다음 문자열을 UTF-8로 인코딩한 바이트이다. 파트 1과 파트 2가 같은 함수(`pow_core.py`)를 사용한다.

```
{index}|{data}|{prev_hash}|{target:064x}|{nonce}
```

| 필드 | 형식 |
|---|---|
| `index` | 10진 정수 (파트 1 보정 실험은 0, 파트 2는 1~10) |
| `data` | 문자열. 구분자 `\|`는 포함할 수 없다 |
| `prev_hash` | 소문자 16진수 64자. 1번 블록은 `"0" * 64` |
| `target` | 목표값 T를 앞을 0으로 채운 소문자 16진수 64자 |
| `nonce` | 10진 정수, 0부터 1씩 증가 |

- 블록에 저장되는 `hash` 필드 자체는 해시 입력에서 제외한다.
- SHA-256을 **1회** 적용하고, 결과 32바이트를 big-endian 부호 없는 256비트 정수 H로 해석한다.
- **성공 조건: H < T**
- 파트 1의 실험 식별자는 `data` 필드에 넣는다: `p1-k{지수}-run{번호}`, `p1-tstar-run{번호}`

## 4. 파일 구성

```
pow_core.py        블록 인코딩, 해시 계산, 채굴 루프 (공통 모듈)
part1_mining.py    파트 1: 목표값별 채굴 실험, 해시 속도 r 추정, T* 설정 및 보정 실험
part1_plot.py      파트 1: 그래프와 통계표
part2_chain.py     파트 2: 10블록 체인 생성, 검증기, 6번 변조, 6~10번 재채굴, 재검증
part2_plot.py      파트 2: 변경 전후 체인 다이어그램, 블록별 채굴 시간 그래프
part3_cost.py      파트 3: 비트코인 블록 채굴 기대 전기요금 계산
results/           실행 결과 (아래 6절)
```

## 5. 실행 방법

아래 순서대로 실행한다. 파트 2는 파트 1이 만든 `results/part1_summary.json`에서 T*를 읽는다.

```bash
python part1_mining.py     # 약 3~5분
python part1_plot.py
python part2_chain.py      # 약 10~15분 (원본 10블록 + 복구 5블록)
python part2_plot.py
python part3_cost.py
```

주요 옵션:

| 스크립트 | 옵션 | 설명 |
|---|---|---|
| `part1_mining.py` | `--trials 5` | 목표값당 독립 실험 횟수 |
| | `--expected-limit 60` | 다음 목표값의 예상 시간이 이 값(초)을 넘으면 T* 설정으로 넘어감 |
| | `--timeout 300` | 시행당 최대 시간(초). 초과 시 미완료로 기록하고 제외하지 않음 |
| `part2_chain.py` | `--target-log2 x` | **테스트 전용.** T* 대신 2^x 사용. 제출 결과에는 사용하지 않음 |
| `part3_cost.py` | `--difficulty`, `--hashrate-ths`, `--power-w`, `--price-krw-kwh` | 다른 기준 시점이나 장비로 다시 계산 |
| `*_plot.py` | 첫 인자 | 결과 폴더 경로 (기본 `results`) |

### 목표값 설정 방법

1. T = 2^252, 2^248, 2^244, … 순서로 각 5회 실험한다.
2. 다음 지수 k로 넘어가기 전에, 지금까지의 총 해시 횟수 / 총 시간으로 r을 구하고 예상 시간 2^(256−k) / r을 계산한다.
3. 예상 시간이 60초를 넘으면 중단하고 **T\* = ⌊2^256 / round(60·r)⌋** (양의 정수)로 설정한다.
4. T*에서 5회 보정 실험을 한다.

### 재현성

해시 입력이 결정적이므로 같은 목표값과 같은 데이터로 실행하면 논스, 해시, 해시 계산 횟수는 항상 같다. 실행마다 달라지는 것은 소요 시간뿐이다. 단, T*는 측정한 r에 따라 정해지므로 다른 컴퓨터에서 파트 1을 다시 실행하면 T*가 달라질 수 있다. 제출한 체인을 그대로 재현하려면 제출한 `results/part1_summary.json`을 둔 채 `part2_chain.py`만 실행하면 된다.

## 6. 결과 파일 (`results/`)

| 파일 | 내용 |
|---|---|
| `part1_runs.csv` | 파트 1 모든 시행의 원시 기록 (목표값, 데이터, 논스, 해시, 해시 계산 횟수, 시간, 완료 여부). 미완료 시행 포함 |
| `part1_summary.json` | 실행 환경, r, T*(정수·16진수·log₂), 중단 근거 |
| `part1_stats.csv`, `part1_plot.png` | 목표값별 평균·표준편차·최소·최대, 그래프 |
| `chain_original.json` | 원본 체인 |
| `chain_tampered.json` | 6번 블록 데이터만 변경한 직후 체인 (해시 갱신 전) |
| `chain_tampered_hash_only.json` | (보충) 6번 해시만 재계산해 덮어쓴 체인 |
| `chain_recovered.json` | 6~10번을 재채굴한 복구 체인 |
| `part2_mining_log.csv` | 원본과 복구 단계의 블록별 논스, 해시, 해시 계산 횟수, 시간 |
| `part2_comparison.csv` | 원본과 복구 체인의 블록별 비교 |
| `part2_validation.json` | 단계별·블록별 검증 결과 |
| `part2_summary.json` | 총 해시 횟수, 총 시간, 기대값 대비 비율 |
| `part2_diagram.png`, `part2_times.png` | 변경 전후 다이어그램, 블록별 채굴 시간 |
| `part3_inputs.csv`, `part3_results.csv`, `part3_summary.json` | 비트코인 비용 계산 입력값(출처 포함)과 결과 |

### 검증기가 확인하는 조건

1. 블록 번호가 1, 2, …, 10 순서인가
2. 블록의 목표값이 고정 목표값 T*와 같은가
3. 저장된 해시가 블록 내용(해시 필드 제외)으로 재계산한 해시와 같은가
4. 재계산한 해시 H가 H < T*를 만족하는가 (작업증명)
5. `prev_hash`가 이전 블록의 저장된 해시와 같은가 (1번은 `"0" * 64`)

## 7. 결과 요약

**파트 1**

- r ≈ 756,811 H/s (76,863,586회 / 101.56초)
- 2^228의 예상 시간 354.7초 > 60초 → T* ≈ 2^230.56 (`0000005e95b4de95…`), 기대 시도 약 4,541만 회
- T*에서 5회 모두 완료, 평균 23.4초 (표준편차 31.2초, 범위 3.9~78.4초)

**파트 2**

| | 원본 (10블록) | 복구 (6~10번) |
|---|---|---|
| 해시 계산 횟수 | 362,094,597 | 193,196,637 |
| 채굴 시간 | 372.4초 | 201.4초 (기대 약 300초) |
| 검증 | 통과 | 통과 |

변조 직후 체인은 6번 블록에서 해시 재계산 불일치와 작업증명 실패로 검증에 실패했다.

**파트 3** (D = 140.58T, 2026-10-28 기준 / Antminer S21 XP / 한국 산업용 185.5원/kWh)

- 블록당 기대 전기요금 C ≈ 4.20억 원
- 블록 5개 재계산 C₅ ≈ 21.0억 원

## 8. 외부 자료 및 AI 도구 활용

**외부 자료**

- 비트코인 난이도: CoinWarz, Bitcoin Difficulty Chart (2026-10-28 조회), https://www.coinwarz.com/mining/bitcoin/difficulty-chart
- 난이도 조정 내역: PrimeXBT, "Bitcoin Mining Difficulty Rises 5.92% to 140.58 Trillion" (2026-10-16)
- ASIC 사양: Hashrate Index, "Hardware Overview: Bitmain's Antminer S21 XP", https://hashrateindex.com/blog/hardware-overview-bitmains-antminer-s21-xp/
- 전기요금: 딜사이트 (2026-06), https://dealsite.co.kr/articles/163752 ; 머니투데이방송 (2026-09-21), https://news.mtn.co.kr/news-detail/2026092111090432619

**AI 도구 활용**

Claude (Anthropic)를 사용해 다음 작업을 도움받았다: 과제 진행 계획 수립, 코드 초안 작성(채굴 루프, 체인 생성, 검증기, 그래프, 비용 계산), 실험 결과 해석, 파트 3 자료 조사. 모든 실험은 본인 노트북에서 직접 실행했고, 결과와 코드를 검토했다.

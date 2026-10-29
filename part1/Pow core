"""작업증명 공통 모듈 (파트 1 보정 실험과 파트 2 체인에서 동일하게 사용).

블록 인코딩 (결정적):
    "{index}|{data}|{prev_hash}|{target:064x}|{nonce}"  -> UTF-8 바이트
    - index     : 10진 정수
    - data      : 문자열 ('|' 포함 금지)
    - prev_hash : 소문자 16진수 64자 (1번 블록은 '0' * 64)
    - target    : 64자리 소문자 16진수 (앞을 0으로 채움)
    - nonce     : 10진 정수, 0부터 1씩 증가
    - 저장되는 블록 해시 자체는 입력에 포함하지 않는다.
해시: SHA-256 1회 적용, 결과 32바이트를 big-endian 부호 없는 256비트 정수 H로 해석.
성공 조건: H < T
"""
import hashlib
import time

ZERO_HASH = "0" * 64
ENCODING_DESC = '"{index}|{data}|{prev_hash}|{target:064x}|{nonce}" (UTF-8), SHA-256 x1, big-endian, success if H < T'


def _check(data: str, prev_hash: str, target: int) -> None:
    if "|" in data:
        raise ValueError("data에는 '|' 문자를 넣을 수 없습니다 (인코딩 구분자).")
    if len(prev_hash) != 64:
        raise ValueError("prev_hash는 16진수 64자여야 합니다.")
    if not (0 < target < 2 ** 256):
        raise ValueError("target은 0 < T < 2^256 범위의 정수여야 합니다.")


def encode_prefix(index: int, data: str, prev_hash: str, target: int) -> bytes:
    """논스를 제외한 앞부분. 채굴 루프에서 매번 다시 만들지 않도록 미리 계산한다."""
    _check(data, prev_hash, target)
    return f"{index}|{data}|{prev_hash}|{target:064x}|".encode("utf-8")


def encode_block(index: int, data: str, prev_hash: str, target: int, nonce: int) -> bytes:
    return encode_prefix(index, data, prev_hash, target) + str(nonce).encode("utf-8")


def block_hash(index: int, data: str, prev_hash: str, target: int, nonce: int) -> str:
    return hashlib.sha256(encode_block(index, data, prev_hash, target, nonce)).hexdigest()


def mine(index: int, data: str, prev_hash: str, target: int,
         timeout: float | None = None, check_every: int = 1 << 16) -> dict:
    """논스를 0부터 증가시키며 H < target 이 될 때까지 SHA-256을 계산한다.

    반환값: success, nonce, hash, attempts(해시 계산 횟수), seconds
    timeout(초)을 넘기면 success=False 로 반환한다 (미완료 실험).
    """
    prefix = encode_prefix(index, data, prev_hash, target)
    sha256 = hashlib.sha256
    nonce = 0
    start = time.perf_counter()
    deadline = start + timeout if timeout else None
    mask = check_every - 1

    while True:
        digest = sha256(prefix + str(nonce).encode()).digest()
        if int.from_bytes(digest, "big") < target:
            return {
                "success": True,
                "nonce": nonce,
                "hash": digest.hex(),
                "attempts": nonce + 1,
                "seconds": time.perf_counter() - start,
            }
        nonce += 1
        if deadline is not None and (nonce & mask) == 0 and time.perf_counter() > deadline:
            return {
                "success": False,
                "nonce": None,
                "hash": None,
                "attempts": nonce,
                "seconds": time.perf_counter() - start,
            }

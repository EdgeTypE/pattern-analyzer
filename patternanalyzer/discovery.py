"""Beam-search based discovery helpers for Pattern Analyzer.

Provides a focused implementation used by Engine.discover to search transform
chains (base64 decode, repeating-key-XOR, single-byte XOR) and score candidates
using Index of Coincidence, printable-ratio and a simple English-frequency
heuristic. Designed to be self-contained and imported by patternanalyzer.engine.
"""
from __future__ import annotations

import base64
import math
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple, Optional

from .plugin_api import BytesView


# --- Utilities -----------------------------------------------------------------


ENGLISH_FREQ = {
    "a": 0.08167, "b": 0.01492, "c": 0.02782, "d": 0.04253, "e": 0.12702,
    "f": 0.02228, "g": 0.02015, "h": 0.06094, "i": 0.06966, "j": 0.00153,
    "k": 0.00772, "l": 0.04025, "m": 0.02406, "n": 0.06749, "o": 0.07507,
    "p": 0.01929, "q": 0.00095, "r": 0.05987, "s": 0.06327, "t": 0.09056,
    "u": 0.02758, "v": 0.00978, "w": 0.02360, "x": 0.00150, "y": 0.01974,
    "z": 0.00074, " ": 0.13000
}


def to_bytes(bv: BytesView) -> bytes:
    try:
        return bv.to_bytes()
    except Exception:
        return bytes(bv.data)


def shannon_entropy(bts: bytes) -> float:
    if not bts:
        return 0.0
    freqs = Counter(bts)
    ent = 0.0
    ln = len(bts)
    for v in freqs.values():
        p = v / ln
        ent -= p * math.log2(p)
    return ent


def printable_ratio(bts: bytes) -> float:
    if not bts:
        return 0.0
    good = 0
    for c in bts:
        if 32 <= c <= 126 or c in (9, 10, 13):
            good += 1
    return good / len(bts)


def index_of_coincidence(bts: bytes) -> float:
    n = len(bts)
    if n <= 1:
        return 0.0
    freqs = Counter(bts)
    s = 0
    for v in freqs.values():
        s += v * (v - 1)
    return s / (n * (n - 1))


def english_chi_squared_score(bts: bytes) -> float:
    """Compute a chi-squared style score against English letter+space frequencies.

    Lower is better (0 = perfect match). Non-letter bytes are counted as mismatch.
    """
    if not bts:
        return float("inf")
    cts = Counter()
    total = 0
    for b in bts:
        ch = chr(b).lower() if 0x20 <= b <= 0x7E else None
        if ch and (ch.isalpha() or ch == " "):
            cts[ch] += 1
        else:
            # count as a mismatch by leaving it out but increasing total
            pass
        total += 1
    if total == 0:
        return float("inf")
    chi = 0.0
    for ch, exp in ENGLISH_FREQ.items():
        obs = cts.get(ch, 0)
        expected = exp * total
        # avoid division by zero for extremely small expected
        if expected > 0:
            chi += ((obs - expected) ** 2) / expected
    # normalize by total to make score comparable across lengths
    return chi / total


# --- Kasiski / key-length heuristics ------------------------------------------


def kasiski_candidates(bts: bytes, max_keylen: int = 40) -> List[int]:
    """Simple Kasiski-like examination: find repeated 3..5 byte sequences and
    return common gcds of distances as candidate key lengths.
    """
    if len(bts) < 10:
        return []
    ngram_lens = (3, 4, 5)
    distances = []
    for n in ngram_lens:
        seen = {}
        for i in range(len(bts) - n + 1):
            ng = bts[i : i + n]
            if ng in seen:
                # record distance to previous occurrence(s)
                for j in seen[ng]:
                    distances.append(i - j)
                seen[ng].append(i)
            else:
                seen[ng] = [i]
    # compute gcds frequency
    gcd_counts = Counter()
    from math import gcd

    for d in distances:
        for k in range(2, min(max_keylen, d) + 1):
            if d % k == 0:
                gcd_counts[k] += 1
    if not gcd_counts:
        return []
    # return top 6 candidates sorted by count then by small keylen
    items = sorted(gcd_counts.items(), key=lambda x: (-x[1], x[0]))
    return [k for k, _ in items[:6]]


def ioc_keylen_candidates(bts: bytes, max_keylen: int = 40, topn: int = 6) -> List[int]:
    """Use average IoC across interleaved buckets to rank key length candidates.
    Returns topn key lengths with highest average IoC.
    """
    if len(bts) < 10:
        return []
    scores = []
    for k in range(1, min(max_keylen, len(bts) // 2) + 1):
        buckets = [bytearray() for _ in range(k)]
        for i, b in enumerate(bts):
            buckets[i % k].append(b)
        avg_ioc = 0.0
        for bucket in buckets:
            avg_ioc += index_of_coincidence(bytes(bucket))
        avg_ioc /= k
        scores.append((k, avg_ioc))
    scores.sort(key=lambda x: x[1], reverse=True)
    return [k for k, _ in scores[:topn]]


# --- Repeating-key XOR key estimation -----------------------------------------


def estimate_repeating_xor_key(bts: bytes, keylen: int) -> Tuple[bytes, float]:
    """Estimate repeating-key-XOR key of given length by treating each bucket as
    single-byte XOR and selecting the byte which yields best English match.
    Returns (key_bytes, aggregated_score) where higher aggregated_score is better.
    """
    key = bytearray(keylen)
    bucket_scores = []
    for i in range(keylen):
        bucket = bytes(bts[i::keylen])
        best_score = None
        best_k = 0
        # For speed, we can restrict to 0..255 but score quickly; it's acceptable here.
        for k in range(256):
            dec = bytes([b ^ k for b in bucket])
            # scoring: printable ratio + normalized negative chi (lower chi better)
            pr = printable_ratio(dec)
            chi = english_chi_squared_score(dec)
            # Convert chi to a positive reward (smaller chi => larger reward)
            reward = pr * 1.0 + (1.0 / (1.0 + chi)) * 1.0
            if best_score is None or reward > best_score:
                best_score = reward
                best_k = k
        key[i] = best_k
        # record normalized bucket quality (best_score)
        bucket_scores.append(best_score or 0.0)
    # aggregated score: mean of bucket scores
    agg = sum(bucket_scores) / len(bucket_scores) if bucket_scores else 0.0
    return bytes(key), agg


# --- Transforms applied during beam search -----------------------------------


def try_base64_decode(bts: bytes) -> Optional[bytes]:
    """Attempt to base64-decode the input. Returns decoded bytes or None."""
    # Trim whitespace/newlines and require reasonable length
    txt = bts.strip()
    if len(txt) < 8:
        return None
    # quick character-set check (base64 charset)
    try:
        txt_str = txt.decode("ascii")
    except Exception:
        return None
    # remove common whitespace
    cand = "".join(txt_str.split())
    # valid base64 chars
    import re

    if not re.fullmatch(r"[A-Za-z0-9+/=]+", cand):
        return None
    try:
        dec = base64.b64decode(cand, validate=True)
        if dec:
            return dec
    except Exception:
        return None
    return None


def apply_single_byte_xor_candidates(bts: bytes, top_n: int = 8) -> List[Tuple[int, bytes, float]]:
    """Return top_n single-byte-xor key candidates sorted by heuristic score."""
    scored = []
    for k in range(256):
        dec = bytes([c ^ k for c in bts])
        score = (printable_ratio(dec) * 1.5) - (shannon_entropy(dec) / 8.0) - (english_chi_squared_score(dec) * 0.01)
        scored.append((k, dec, score))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_n]


# --- Beam search core ---------------------------------------------------------


def _score_plaintext_candidate(bts: bytes) -> float:
    """Aggregate heuristic score for a candidate plaintext (higher is better)."""
    if not bts:
        return -999.0
    pr = printable_ratio(bts)
    ent = shannon_entropy(bts)
    ioc = index_of_coincidence(bts)
    chi = english_chi_squared_score(bts)
    # Normalize IoC around English expected ~0.065
    ioc_score = max(0.0, (ioc - 0.03))  # favor above noise baseline
    # Combine heuristics with tuned weights
    score = (pr * 2.0) + (ioc_score * 5.0) - (ent / 8.0) - (chi * 0.1)
    return score


def beam_search_discover(data: BytesView, config: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry: perform a shallow beam search over transform chains.

    Config options (optional):
      - discover_beam_width (int): max beam width (default 10)
      - discover_max_depth (int): max transform chain length (default 3)
      - discover_top_k (int): how many final candidates to return (default 5)
      - discover_max_keylen (int): max key length to try for repeating-xor (default 40)
    """
    raw = to_bytes(data)
    beam_width = int(config.get("discover_beam_width", 10))
    max_depth = int(config.get("discover_max_depth", 3))
    top_k = int(config.get("discover_top_k", 5))
    max_keylen = int(config.get("discover_max_keylen", 40))
    preview_len = int(config.get("discover_preview_len", 200))

    # Beam nodes: tuple (score, chain, bytes, metadata)
    # chain: list of transform dicts {"name":..., "params": {...}}
    BeamNode = Tuple[float, List[Dict[str, Any]], bytes, Dict[str, Any]]

    # Initial node
    init_score = _score_plaintext_candidate(raw)
    beam: List[BeamNode] = [(init_score, [], raw, {"method": "raw"})]

    final_candidates: List[BeamNode] = []

    for depth in range(1, max_depth + 1):
        next_beam: List[BeamNode] = []
        for score, chain, bts, meta in beam:
            # 1) Try base64 decode (if applicable)
            dec = try_base64_decode(bts)
            if dec is not None:
                ch = chain + [{"name": "base64_decode", "params": {}}]
                sc = _score_plaintext_candidate(dec)
                nm = {"method": "base64_decode"}
                next_beam.append((sc, ch, dec, nm))

            # 2) Try repeating-key-XOR candidates:
            #   - compute Kasiski candidates and IoC-based candidates then unique them
            k_candidates = []
            ks1 = kasiski_candidates(bts, max_keylen)
            ks2 = ioc_keylen_candidates(bts, max_keylen)
            for k in ks1 + ks2:
                if 1 <= k <= max_keylen and k not in k_candidates:
                    k_candidates.append(k)
            # Always include small lengths 1..4 as fallback
            for k in range(1, min(5, max_keylen + 1)):
                if k not in k_candidates:
                    k_candidates.append(k)
            # Limit number of lengths to attempt per node
            k_candidates = k_candidates[:6]

            for klen in k_candidates:
                key_bytes, kval = estimate_repeating_xor_key(bts, klen)
                # apply transform
                decoded = bytes([cb ^ key_bytes[i % klen] for i, cb in enumerate(bts)])
                ch = chain + [{"name": "xor_repeating", "params": {"key_hex": key_bytes.hex(), "key_len": klen}}]
                sc = _score_plaintext_candidate(decoded)
                nm = {"method": "xor_repeating", "key_len": klen, "key_score": kval}
                # boost score a bit if key estimation confidence high
                sc += kval * 1.5
                next_beam.append((sc, ch, decoded, nm))

            # 3) Try single-byte XOR top candidates (lightweight)
            single_cands = apply_single_byte_xor_candidates(bts, top_n=6)
            for k, dec_bytes, sscore in single_cands:
                ch = chain + [{"name": "xor_const", "params": {"xor_value": int(k)}}]
                sc = _score_plaintext_candidate(dec_bytes)
                nm = {"method": "xor_const", "key": k}
                next_beam.append((sc, ch, dec_bytes, nm))

        # Merge and prune to beam_width
        if not next_beam:
            break
        next_beam.sort(key=lambda x: x[0], reverse=True)
        beam = next_beam[:beam_width]

        # Collect promising nodes as final candidates (we can also collect at each depth)
        for node in beam:
            final_candidates.append(node)

    # Post-process final_candidates and return top_k unique chains
    # Deduplicate by chain text representation
    seen = set()
    out = []
    final_candidates.sort(key=lambda x: x[0], reverse=True)
    for sc, chain, bts, meta in final_candidates:
        key = tuple((t["name"], tuple(sorted((k, str(v)) for k, v in t.get("params", {}).items()))) for t in chain)
        if key in seen:
            continue
        seen.add(key)
        # prepare preview
        preview = None
        try:
            if printable_ratio(bts) >= 0.6:
                preview = bts.decode("utf-8", errors="replace")[:preview_len]
            else:
                preview = bts[:preview_len].hex()
        except Exception:
            preview = bts[:preview_len].hex()
        # confidence heuristic in [0,1]
        conf = max(0.0, min(1.0, (sc + 5.0) / 15.0))
        entry = {
            "chain": chain,
            "score": float(sc),
            "confidence": float(conf),
            "plaintext_preview": preview,
            "meta": meta,
        }
        # if last transform is xor_repeating, expose key info
        if chain and chain[-1]["name"] == "xor_repeating":
            try:
                keyhex = chain[-1]["params"].get("key_hex")
                entry["repeating_xor"] = {"key_hex": keyhex, "key_len": chain[-1]["params"].get("key_len")}
            except Exception:
                pass
        out.append(entry)
        if len(out) >= top_k:
            break

    # Minimal engine-compatible wrapper
    metainfo = {}
    try:
        import hashlib
        metainfo["input_hash"] = hashlib.sha256(raw).hexdigest()
    except Exception:
        metainfo["input_hash"] = None

    return {"discoveries": out, "meta": metainfo}
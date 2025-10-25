from patternlab.plugin_api import BytesView
from patternlab.plugins.binary_matrix_rank import BinaryMatrixRankTest

def inspect_rows(m=8, num_matrices=1):
    bits_per_matrix = m * m
    total_bytes = (bits_per_matrix * num_matrices) // 8
    pattern = (b'\xAA\x55') * (total_bytes // 2)
    bv = BytesView(pattern)
    bits = bv.bit_view()
    # Build rows for first matrix
    mat_bits = bits[0:bits_per_matrix]
    rows = []
    for r in range(m):
        row_bits = mat_bits[r*m:(r+1)*m]
        val = 0
        for bit in row_bits:
            val = (val << 1) | (1 if bit else 0)
        rows.append((row_bits, val))
    return rows, bv, pattern

def main():
    m = 8
    rows, bv, pattern = inspect_rows(m=m, num_matrices=1)
    print("First matrix rows (bits, int, bin):")
    for i, (rb, val) in enumerate(rows):
        print(f"row {i}: bits={rb} int={val} bin={format(val, '08b')}")
    # Run full plugin to show ranks
    res = BinaryMatrixRankTest().run(BytesView(pattern * 8), {"matrix_dim": m, "min_matrices": 8})
    print("\nFull plugin result p_value:", res.p_value)
    print("ranks:", res.metrics.get("ranks"))

if __name__ == '__main__':
    main()
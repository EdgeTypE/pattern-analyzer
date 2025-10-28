# Test Reference

This document provides a reference for the built-in test and analysis plugins available in Pattern Analyzer.

## Plugin Categories

Plugins are broadly grouped into the following categories:

-   **Statistical Tests**: Classic tests for randomness, many inspired by the NIST SP 800-22 test suite.
-   **Cryptographic Analysis**: Plugins that search for patterns related to cryptographic algorithms.
-   **Structural Analysis**: Plugins that parse and analyze the structure of common file formats.
-   **Machine Learning-Based**: Plugins that use ML models for anomaly detection or classification.
-   **Diagnostic & Information Theory**: Plugins that provide metrics like entropy, complexity, or visualizations without a formal pass/fail result.

---

## Statistical Tests

These plugins produce a `p_value`. A result is typically considered "failed" if the p-value is below the configured significance level (e.g., 0.01) and is rejected by the False Discovery Rate (FDR) correction.

| Plugin Name                         | Description                                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `monobit`                           | Checks the proportion of zeros and ones. A fundamental test for bias.                                   |
| `runs`                              | Counts the number of "runs" (uninterrupted sequences of identical bits) to check for oscillation speed. |
| `block_frequency`                   | Checks the frequency of ones within fixed-size blocks of the data.                                      |
| `frequency_within_block`            | A variant of the block frequency test aligned with the NIST specification.                              |
| `longest_run`                       | Finds the longest run of ones within blocks and checks its distribution.                                |
| `serial`                            | Checks the frequency of all possible overlapping m-bit patterns to find biases.                         |
| `cusum`                             | Cumulative Sums test; detects if the cumulative sum of the random walk strays too far from zero.        |
| `approximate_entropy`               | Measures the predictability and regularity of the sequence.                                             |
| `maurers_universal`                 | A test based on the compressibility of the sequence; less compressible data is more random.             |
| `non_overlapping_template_matching` | Counts non-overlapping occurrences of a specific bit pattern.                                           |
| `overlapping_template_matching`     | Counts overlapping occurrences of a specific bit pattern.                                               |
| `random_excursions`                 | Analyzes the number of visits to various states in a random walk.                                       |
| `random_excursions_variant`         | A variant of the random excursions test.                                                                |
| `binary_matrix_rank`                | Forms binary matrices from the data and checks the distribution of their ranks.                         |
| `nist_dft_spectral`                 | Uses the Discrete Fourier Transform to detect periodic features in the data.                            |
| `diehard_birthday_spacings`         | A test from the Diehard suite that examines the spacing between repeated values.                        |
| `diehard_overlapping_sums`          | A test from the Diehard suite based on the distribution of sums of overlapping words.                   |
| `diehard_3d_spheres`                | A test from the Diehard suite that places points in a 3D cube and checks distribution.                  |
| `testu01_smallcrush`                | An adapter for a subset of the powerful TestU01 SmallCrush battery of tests.                            |

---

## Cryptographic Analysis

| Plugin Name                | Description                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `ecb_detector`             | Detects repeating, fixed-size blocks, a strong indicator of Electronic Codebook (ECB) mode encryption.        |
| `frequency_pattern`        | Performs frequency analysis and uses Index of Coincidence (IoC) to guess repeating-key XOR key lengths.       |
| `known_constants_search`   | Scans the data for known cryptographic constants, such as the AES S-box.                                      |
| `linear_complexity`        | Determines the length of the shortest Linear Feedback Shift Register (LFSR) that can generate the sequence.   |

---

## Structural Analysis

These plugins check if the data conforms to a known file format structure.

| Plugin Name       | Description                                        |
| ----------------- | -------------------------------------------------- |
| `magic_detector`  | Checks the first few bytes for common file "magic numbers" (e.g., PNG, ZIP). |
| `png_structure`   | Parses the chunk structure of a PNG file.          |
| `pdf_structure`   | Performs a lightweight analysis of a PDF file's object structure. |
| `zip_structure`   | Parses local file headers and central directory entries from a ZIP archive. |

---

## Machine Learning-Based

These plugins use trained models or ML heuristics for analysis. They may require the `[ml]` extra dependencies to be installed.

| Plugin Name             | Description                                                                           |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `autoencoder_anomaly`   | Uses an autoencoder model to detect anomalies based on reconstruction error.          |
| `lstm_gru_anomaly`      | Uses a recurrent neural network (LSTM/GRU) to detect anomalies in time-series data.   |
| `classifier_labeler`    | Uses a pre-trained classifier to label the data (e.g., "encrypted", "ransomware").    |

---

## Diagnostic & Information Theory

These plugins provide quantitative metrics or visualizations rather than a formal p-value.

| Plugin Name             | Description                                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------------------------------- |
| `autocorrelation`       | Computes the correlation of the sequence with shifted versions of itself.                                  |
| `dft_spectral_advanced` | A more advanced spectral test that checks if the power spectrum follows an exponential distribution.       |
| `dotplot`               | Creates a 2D self-similarity matrix to visualize repeating patterns.                                       |
| `fft_spectral`          | A diagnostic FFT-based test that reports the Signal-to-Noise Ratio (SNR) of the highest spectral peak.     |
| `hurst_exponent`        | Estimates the Hurst exponent, a measure of long-range dependence or "memory" in the sequence.              |
| `lz_complexity`         | Measures complexity based on the number of phrases in an LZ78-style compression parse.                     |
| `conditional_entropy`   | Calculates the conditional entropy H(Y\|X) between adjacent symbols.                                     |
| `mutual_information`    | Calculates the mutual information I(X;Y) between adjacent symbols.                                       |
| `transfer_entropy`      | A proxy for transfer entropy, equivalent to mutual information for a single stream.                        |
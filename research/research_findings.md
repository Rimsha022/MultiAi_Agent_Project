# Research Findings and Hypothesis Testing

## 1. Experimental Overview

The proposed Multi-Agent AI Cross-Model Validation System was evaluated using 50 benchmark questions across five categories: Science, AI & Technology, Environment & Health, History, and General Knowledge. Three AI models—GPT-OSS, Gemini, and Qwen—were used in the response evaluation and selection process.

## 2. Overall Performance

The system achieved an average final trust score of 9.08/10. Of the 50 evaluated responses, 47 (94%) were classified as high trust, two (4%) as low trust, and one (2%) as moderate trust.

The average response quality score was 9.37/10, verification score was 9.33/10, cross-model consistency score was 8.44/10, and external evidence score was 8.96/10.

## 3. External Evidence Verification

Across the benchmark, 384 factual claims were recorded. Of these, 347 were classified as supported, nine as contradicted, and 23 as having insufficient evidence. These categories account for 379 claims; the remaining five should be investigated to determine their classification.

The observed supported-claim rate was 90.36%. These findings indicate substantial evidence support within the evaluated responses, although the remaining claims demonstrate why external verification is important.

## 4. Category-Wise Performance

Science achieved the highest average trust score at 9.55/10, followed by AI & Technology at 9.42/10, Environment & Health at 9.14/10, History at 9.01/10, and General Knowledge at 8.28/10.

These results suggest that performance varied across the five evaluated categories. General Knowledge had the lowest average score and may benefit from further investigation.

## 5. Model Selection

GPT-OSS was selected for 18 responses, while Gemini and Qwen were each selected for 16 responses. The relatively similar selection frequencies indicate that the system selected different models across the benchmark rather than consistently choosing a single model.

Selection frequency alone does not establish that one model is more accurate than another.

## 6. Hypothesis Testing

Four one-sided statistical tests were conducted at a nominal significance level of 0.05.

- **H1 — Overall Trustworthiness:** The observed mean trust score was 9.08/10. The one-sample t-test returned a statistic of 8.0064 and a displayed p-value of 0.000000. The null hypothesis was rejected.
- **H2 — High-Trust Reliability:** The observed high-trust proportion was 94% (47/50). The exact binomial test returned a p-value of 0.005656. The null hypothesis was rejected.
- **H3 — External Evidence Support:** The observed supported-claim proportion was 90.36% (347/384). The binomial test returned a p-value of 0.001269. The null hypothesis was rejected, subject to the independence assumption discussed below.
- **H4 — Cross-Model Consistency:** The observed mean consistency score was 8.44/10. The one-sample t-test returned a statistic of 5.4892 and a p-value of 0.000001. The null hypothesis was rejected.

The displayed p-values are rounded; a displayed value of 0.000000 does not mean that the true p-value is exactly zero. All four reported p-values are below the Bonferroni-adjusted threshold of 0.0125 for four tests.

## 7. Limitations

The experiment used 50 predefined benchmark questions and did not compare the proposed system against a controlled single-model baseline. Consequently, the results do not establish that multi-agent validation improves accuracy over a single-model approach.

The trust-level thresholds and hypothesis reference values should be justified in the research methodology. The statistical tests also rely on assumptions about independence and score distributions.

The 384 factual claims were grouped within 50 responses, so claims from the same response may not be independent. The binomial test for evidence support should therefore be treated as preliminary until the analysis accounts for this clustering. Five claims also remain unaccounted for in the reported evidence categories.

## 8. Conclusion

The benchmark results demonstrate strong observed trust scores, high-trust classifications, and substantial external evidence support across the evaluated questions. The hypothesis tests provide evidence that the measured outcomes exceed the specified reference thresholds under the tests' assumptions.

Further evaluation using a controlled baseline, independent correctness judgments, and additional benchmark questions is required to establish whether the proposed multi-agent framework provides a measurable improvement in factual accuracy and reliability.

## Per scenario and controller (mean over days; hours are taxi-hours per 3-hour day)

| scenario            | controller     |   days |   charging_loss_h |   loss_sd |   driving_h |   queued_h |   verifying_h |   checks_per_day |   mean_wait_min |   served_pct | attack_alarms   |   alarm_delay_min |   honest_stations_distrusted | Strip_diagnoses   |
|:--------------------|:---------------|-------:|------------------:|----------:|------------:|-----------:|--------------:|-----------------:|----------------:|-------------:|:----------------|------------------:|-----------------------------:|:------------------|
| normal              | TrustAll       |      6 |              3.6  |      0.29 |        3.47 |       0.13 |          0    |              0   |            3.2  |         94.4 | 0/6             |             nan   |                          0   |                   |
| normal              | CUSUM          |      6 |              3.6  |      0.29 |        3.47 |       0.13 |          0    |              0   |            3.2  |         94.4 | 0/6             |             nan   |                          0   |                   |
| normal              | CUSUM+         |      6 |              3.6  |      0.29 |        3.47 |       0.13 |          0    |              0   |            3.2  |         94.4 | 0/6             |             nan   |                          0   |                   |
| normal              | Reasoning      |      6 |              3.68 |      0.41 |        3.56 |       0.11 |          0    |              0   |            3.29 |         94.2 | 0/6             |             nan   |                          0   | NNNNNN            |
| normal              | Reasoning+EVSI |      6 |              3.68 |      0.41 |        3.56 |       0.11 |          0    |              0   |            3.29 |         94.2 | 0/6             |             nan   |                          0   | NNNNNN            |
| congestion          | TrustAll       |      6 |              5.35 |      1.96 |        3.5  |       1.85 |          0    |              0   |            3.28 |         94   | 0/6             |             nan   |                          0   |                   |
| congestion          | CUSUM          |      6 |              5.35 |      1.96 |        3.5  |       1.85 |          0    |              0   |            3.28 |         94   | 0/6             |             nan   |                          0   |                   |
| congestion          | CUSUM+         |      6 |              5.35 |      1.96 |        3.5  |       1.85 |          0    |              0   |            3.28 |         94   | 0/6             |             nan   |                          0   |                   |
| congestion          | Reasoning      |      6 |              5.03 |      2.25 |        3.54 |       1.49 |          0    |              0   |            3.29 |         94.5 | 0/6             |             nan   |                          0   | NNNNNN            |
| congestion          | Reasoning+EVSI |      6 |              4.92 |      2.31 |        3.55 |       1.33 |          0.03 |              0.7 |            3.32 |         94.3 | 0/6             |             nan   |                          0   | NNNNNN            |
| fault               | TrustAll       |      6 |              3.6  |      0.44 |        3.36 |       0.24 |          0    |              0   |            3.22 |         94.5 | 0/6             |             nan   |                          0   |                   |
| fault               | CUSUM          |      6 |              3.52 |      0.43 |        3.37 |       0.15 |          0    |              0   |            3.2  |         94.5 | 2/6             |              51   |                          1   |                   |
| fault               | CUSUM+         |      6 |              3.52 |      0.43 |        3.37 |       0.15 |          0    |              0   |            3.2  |         94.6 | 2/6             |              51   |                          1   |                   |
| fault               | Reasoning      |      6 |              3.81 |      0.48 |        3.61 |       0.21 |          0    |              0   |            3.28 |         94.6 | 1/6             |              14   |                          0.2 | FFFFFF            |
| fault               | Reasoning+EVSI |      6 |              3.88 |      0.43 |        3.58 |       0.28 |          0.03 |              0.5 |            3.27 |         94.8 | 1/6             |              14   |                          0.2 | FFFFFF            |
| attack              | TrustAll       |      6 |             12.39 |      4.24 |        4.75 |       7.64 |          0    |              0   |            4.16 |         91.8 | 0/6             |             nan   |                          0   |                   |
| attack              | CUSUM          |      6 |              3.79 |      0.34 |        3.43 |       0.35 |          0    |              0   |            3.22 |         94.6 | 6/6             |              14.5 |                          3   |                   |
| attack              | CUSUM+         |      6 |              3.78 |      0.34 |        3.43 |       0.35 |          0    |              0   |            3.22 |         94.6 | 6/6             |              14.5 |                          3   |                   |
| attack              | Reasoning      |      6 |              4.15 |      0.61 |        3.7  |       0.45 |          0    |              0   |            3.32 |         94.5 | 6/6             |               9.5 |                          3   | AAAAAA            |
| attack              | Reasoning+EVSI |      6 |              4.07 |      0.59 |        3.65 |       0.39 |          0.03 |              0.5 |            3.33 |         94.4 | 6/6             |               9.5 |                          3   | AAAAAA            |
| local_attack        | TrustAll       |      6 |              3.69 |      0.46 |        3.4  |       0.3  |          0    |              0   |            3.27 |         94.3 | 0/6             |             nan   |                          0   |                   |
| local_attack        | CUSUM          |      6 |              3.62 |      0.47 |        3.41 |       0.21 |          0    |              0   |            3.23 |         94.3 | 6/6             |              47.5 |                          3   |                   |
| local_attack        | CUSUM+         |      6 |              3.61 |      0.48 |        3.4  |       0.21 |          0    |              0   |            3.22 |         94.4 | 6/6             |              47.5 |                          3   |                   |
| local_attack        | Reasoning      |      6 |              3.66 |      0.37 |        3.52 |       0.15 |          0    |              0   |            3.27 |         94.4 | 4/6             |              13.8 |                          0.2 | FFFFFF            |
| local_attack        | Reasoning+EVSI |      6 |              3.66 |      0.37 |        3.52 |       0.15 |          0    |              0   |            3.27 |         94.4 | 4/6             |              13.8 |                          0.2 | FFFFFF            |
| subtle_attack       | TrustAll       |      6 |              3.65 |      0.45 |        3.41 |       0.24 |          0    |              0   |            3.27 |         94.4 | 0/6             |             nan   |                          0   |                   |
| subtle_attack       | CUSUM          |      6 |              3.66 |      0.46 |        3.43 |       0.22 |          0    |              0   |            3.23 |         94.4 | 6/6             |              47.7 |                          3   |                   |
| subtle_attack       | CUSUM+         |      6 |              3.58 |      0.5  |        3.38 |       0.2  |          0    |              0   |            3.23 |         94.4 | 6/6             |              47.7 |                          3   |                   |
| subtle_attack       | Reasoning      |      6 |              3.8  |      0.36 |        3.54 |       0.26 |          0    |              0   |            3.29 |         94.3 | 2/6             |              66   |                          0   | FFNNNN            |
| subtle_attack       | Reasoning+EVSI |      6 |              3.83 |      0.39 |        3.57 |       0.26 |          0.01 |              0.2 |            3.28 |         94.4 | 2/6             |              66   |                          0   | CFFNNN            |
| intermittent_attack | TrustAll       |      6 |              3.66 |      0.29 |        3.51 |       0.16 |          0    |              0   |            3.23 |         94.3 | 0/6             |             nan   |                          0   |                   |
| intermittent_attack | CUSUM          |      6 |              3.66 |      0.29 |        3.51 |       0.16 |          0    |              0   |            3.23 |         94.3 | 0/6             |             nan   |                          0   |                   |
| intermittent_attack | CUSUM+         |      6 |              3.66 |      0.29 |        3.51 |       0.16 |          0    |              0   |            3.23 |         94.3 | 0/6             |             nan   |                          0   |                   |
| intermittent_attack | Reasoning      |      6 |              3.61 |      0.29 |        3.5  |       0.11 |          0    |              0   |            3.27 |         94.3 | 2/6             |              46   |                          0   | FNNNNN            |
| intermittent_attack | Reasoning+EVSI |      6 |              3.72 |      0.42 |        3.57 |       0.15 |          0.01 |              0.2 |            3.26 |         94.3 | 2/6             |              46   |                          0   | NNNNNN            |
| outage              | TrustAll       |      6 |              8.03 |      3.04 |        3.41 |       4.61 |          0    |              0   |            3.44 |         94.1 | 0/6             |             nan   |                          0   |                   |
| outage              | CUSUM          |      6 |              5.58 |      0.95 |        3.38 |       2.2  |          0    |              0   |            3.36 |         94.2 | 5/6             |              21.7 |                          2.5 |                   |
| outage              | CUSUM+         |      6 |              5.5  |      0.97 |        3.38 |       2.12 |          0    |              0   |            3.36 |         94.2 | 5/6             |              21.7 |                          2.5 |                   |
| outage              | Reasoning      |      6 |              4.24 |      0.75 |        3.54 |       0.7  |          0    |              0   |            3.29 |         94.2 | 0/6             |             nan   |                          0.2 | FFFFFF            |
| outage              | Reasoning+EVSI |      6 |              4.26 |      0.75 |        3.57 |       0.68 |          0.02 |              0.3 |            3.28 |         94.2 | 0/6             |             nan   |                          0.2 | FFFFFF            |

## Paired differences in charging loss (same days; negative = first controller loses less)

| scenario            | comparison                 |   days |   mean_diff_h |   ci95_low |   ci95_high |   days_a_better |
|:--------------------|:---------------------------|-------:|--------------:|-----------:|------------:|----------------:|
| normal              | Reasoning - CUSUM          |      6 |          0.07 |      -0.2  |        0.35 |               1 |
| congestion          | Reasoning - CUSUM          |      6 |         -0.32 |      -2.39 |        1.75 |               2 |
| fault               | Reasoning - CUSUM          |      6 |          0.29 |      -0.19 |        0.77 |               2 |
| attack              | Reasoning - CUSUM          |      6 |          0.37 |      -0.22 |        0.96 |               2 |
| local_attack        | Reasoning - CUSUM          |      6 |          0.04 |      -0.28 |        0.36 |               3 |
| subtle_attack       | Reasoning - CUSUM          |      6 |          0.14 |      -0.48 |        0.76 |               3 |
| intermittent_attack | Reasoning - CUSUM          |      6 |         -0.05 |      -0.2  |        0.1  |               2 |
| outage              | Reasoning - CUSUM          |      6 |         -1.34 |      -2.1  |       -0.57 |               6 |
| normal              | Reasoning - CUSUM+         |      6 |          0.07 |      -0.2  |        0.35 |               1 |
| congestion          | Reasoning - CUSUM+         |      6 |         -0.32 |      -2.39 |        1.75 |               2 |
| fault               | Reasoning - CUSUM+         |      6 |          0.3  |      -0.18 |        0.77 |               2 |
| attack              | Reasoning - CUSUM+         |      6 |          0.37 |      -0.22 |        0.96 |               2 |
| local_attack        | Reasoning - CUSUM+         |      6 |          0.06 |      -0.28 |        0.39 |               3 |
| subtle_attack       | Reasoning - CUSUM+         |      6 |          0.22 |      -0.34 |        0.79 |               3 |
| intermittent_attack | Reasoning - CUSUM+         |      6 |         -0.05 |      -0.2  |        0.1  |               2 |
| outage              | Reasoning - CUSUM+         |      6 |         -1.25 |      -1.88 |       -0.63 |               6 |
| normal              | Reasoning+EVSI - Reasoning |      6 |          0    |       0    |        0    |               0 |
| congestion          | Reasoning+EVSI - Reasoning |      6 |         -0.11 |      -0.74 |        0.51 |               1 |
| fault               | Reasoning+EVSI - Reasoning |      6 |          0.07 |      -0.17 |        0.31 |               1 |
| attack              | Reasoning+EVSI - Reasoning |      6 |         -0.09 |      -0.3  |        0.12 |               2 |
| local_attack        | Reasoning+EVSI - Reasoning |      6 |          0    |       0    |        0    |               0 |
| subtle_attack       | Reasoning+EVSI - Reasoning |      6 |          0.04 |      -0.05 |        0.12 |               0 |
| intermittent_attack | Reasoning+EVSI - Reasoning |      6 |          0.11 |      -0.18 |        0.41 |               0 |
| outage              | Reasoning+EVSI - Reasoning |      6 |          0.01 |      -0.02 |        0.05 |               0 |
| normal              | Reasoning - TrustAll       |      6 |          0.07 |      -0.2  |        0.35 |               1 |
| congestion          | Reasoning - TrustAll       |      6 |         -0.32 |      -2.39 |        1.75 |               2 |
| fault               | Reasoning - TrustAll       |      6 |          0.22 |      -0.41 |        0.84 |               2 |
| attack              | Reasoning - TrustAll       |      6 |         -8.24 |     -12.33 |       -4.15 |               6 |
| local_attack        | Reasoning - TrustAll       |      6 |         -0.03 |      -0.48 |        0.42 |               3 |
| subtle_attack       | Reasoning - TrustAll       |      6 |          0.15 |      -0.44 |        0.74 |               3 |
| intermittent_attack | Reasoning - TrustAll       |      6 |         -0.05 |      -0.2  |        0.1  |               2 |
| outage              | Reasoning - TrustAll       |      6 |         -3.78 |      -7.2  |       -0.37 |               6 |

## Verification-cost sweep (loss_vs_no_checks_h: change vs. Reasoning without checks)

| controller          |   verify_min | scenario            |   checks_per_day |   verifying_h |   charging_loss_h |   loss_vs_no_checks_h | days_better_than_no_checks   |
|:--------------------|-------------:|:--------------------|-----------------:|--------------:|------------------:|----------------------:|:-----------------------------|
| Reasoning+EVSI      |          0.5 | fault               |              4.3 |          0.04 |              3.89 |                  0.08 | 2/6                          |
| Reasoning+EVSI      |          0.5 | intermittent_attack |              3.8 |          0.03 |              3.85 |                  0.24 | 1/6                          |
| Reasoning+EVSI      |          0.5 | outage              |              3.8 |          0.03 |              4.04 |                 -0.2  | 3/6                          |
| Reasoning+EVSI      |          0.5 | subtle_attack       |              5.5 |          0.05 |              3.71 |                 -0.09 | 3/6                          |
| Reasoning+EVSI      |          1   | fault               |              2.8 |          0.05 |              3.76 |                 -0.05 | 3/6                          |
| Reasoning+EVSI      |          1   | intermittent_attack |              1.8 |          0.03 |              3.74 |                  0.12 | 0/6                          |
| Reasoning+EVSI      |          1   | outage              |              2.5 |          0.04 |              4.02 |                 -0.22 | 5/6                          |
| Reasoning+EVSI      |          1   | subtle_attack       |              2.8 |          0.05 |              3.84 |                  0.04 | 2/6                          |
| Reasoning+EVSI      |          2   | fault               |              1.2 |          0.04 |              3.82 |                  0.01 | 4/6                          |
| Reasoning+EVSI      |          2   | intermittent_attack |              0.7 |          0.02 |              3.74 |                  0.13 | 0/6                          |
| Reasoning+EVSI      |          2   | outage              |              0.7 |          0.02 |              4.18 |                 -0.06 | 2/6                          |
| Reasoning+EVSI      |          2   | subtle_attack       |              0.8 |          0.03 |              3.9  |                  0.11 | 0/6                          |
| Reasoning+EVSI      |          3   | fault               |              0.5 |          0.03 |              3.88 |                  0.07 | 1/6                          |
| Reasoning+EVSI      |          3   | intermittent_attack |              0.2 |          0.01 |              3.72 |                  0.11 | 0/6                          |
| Reasoning+EVSI      |          3   | outage              |              0.3 |          0.02 |              4.26 |                  0.01 | 0/6                          |
| Reasoning+EVSI      |          3   | subtle_attack       |              0.2 |          0.01 |              3.83 |                  0.04 | 0/6                          |
| Reasoning+EVSI-solo |          0.5 | fault               |              0.7 |          0.01 |              3.78 |                 -0.03 | 2/6                          |
| Reasoning+EVSI-solo |          0.5 | intermittent_attack |              0.3 |          0    |              3.61 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          0.5 | outage              |              0.3 |          0    |              4.22 |                 -0.02 | 2/6                          |
| Reasoning+EVSI-solo |          0.5 | subtle_attack       |              0.5 |          0    |              3.8  |                  0    | 1/6                          |
| Reasoning+EVSI-solo |          1   | fault               |              0   |          0    |              3.81 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          1   | intermittent_attack |              0   |          0    |              3.61 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          1   | outage              |              0   |          0    |              4.24 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          1   | subtle_attack       |              0   |          0    |              3.8  |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          2   | fault               |              0   |          0    |              3.81 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          2   | intermittent_attack |              0   |          0    |              3.61 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          2   | outage              |              0   |          0    |              4.24 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          2   | subtle_attack       |              0   |          0    |              3.8  |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          3   | fault               |              0   |          0    |              3.81 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          3   | intermittent_attack |              0   |          0    |              3.61 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          3   | outage              |              0   |          0    |              4.24 |                  0    | 0/6                          |
| Reasoning+EVSI-solo |          3   | subtle_attack       |              0   |          0    |              3.8  |                  0    | 0/6                          |
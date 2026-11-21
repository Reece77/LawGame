# The v1 balance run (PT-M7)

`make balance` on PT-M7's merge head (seeds 1-10, 132 turns from January 2005, five strategies plus T5's difficulty runs and the T8/T9 variants; 4 workers). One line per run, then every target as `docs/balance-targets.md`'s Measures read it. KNOWN MISS rows are Reece's (2026-11-21), owned by PT-M7b; T6's class reading is accepted as sampling noise; T12's row is printed only (its gate is `make check-timing`: 148 ms).

```text
  strategy       seed       diff      state    lawyers revenue 2015        PEP      09/08       secs
boutique                    1 standard active           5       $7.90M     $2.50M     12.6%      9
boutique                    2 standard active           5       $5.65M     $1.74M    -22.5%      9
boutique                    3 standard active          12      $14.83M     $3.14M     -0.8%      9
boutique                    4 standard dissolved        7       $0.00M    $-0.77M     37.7%      6
boutique                    5 standard active          12      $18.03M     $2.50M     78.1%     10
boutique                    6 standard active           9      $11.75M     $2.00M     33.7%     10
boutique                    7 standard active           7      $10.88M     $2.47M     26.9%      9
boutique                    8 standard active           5      $10.60M     $2.69M     18.7%      9
boutique                    9 standard active           6       $7.64M     $1.61M     39.7%     10
boutique                   10 standard active           6       $8.14M     $1.77M      8.6%      9
do-nothing                  1 standard active           1       $1.34M     $1.07M     -3.9%      9
do-nothing                  2 standard dissolved        2       $0.00M    $-0.86M    -88.9%      5
do-nothing                  3 standard active           2       $3.93M     $1.76M     -3.1%      9
do-nothing                  4 standard active           2       $3.23M     $1.40M    -22.2%      9
do-nothing                  5 standard active           2       $3.45M     $1.51M    -52.5%      8
do-nothing                  6 standard active           2       $3.30M     $1.44M    -15.4%      8
do-nothing                  7 standard active           2       $3.11M     $1.35M    -34.2%      8
do-nothing                  8 standard active           1       $2.29M     $2.08M    -55.0%      7
do-nothing                  9 standard active           2       $3.43M     $1.50M     84.8%      8
do-nothing                 10 standard active           2       $3.26M     $1.41M    -10.0%      8
lateral-rocket              1 standard dissolved        5       $0.00M     $0.94M         -      4
lateral-rocket              2 standard dissolved        5       $0.00M    $-0.29M         -      0
lateral-rocket              3 standard dissolved        6       $0.00M     $1.21M     -1.8%      5
lateral-rocket              4 standard dissolved        5       $0.00M     $0.04M         -      1
lateral-rocket              5 standard dissolved        6       $0.00M     $0.98M         -      4
lateral-rocket              6 standard dissolved        5       $0.00M     $0.85M         -      4
lateral-rocket              7 standard dissolved        6       $0.00M     $0.72M         -      4
lateral-rocket              8 standard active          24      $34.89M     $1.42M      9.5%     10
lateral-rocket              9 standard dissolved        5       $0.00M     $0.32M         -      0
lateral-rocket             10 standard active          23      $35.74M     $1.31M     19.8%     10
lateral-rocket-heeded       1 standard dissolved        5       $0.00M     $0.94M         -      3
lateral-rocket-heeded       2 standard dissolved        5       $0.00M    $-0.29M         -      1
lateral-rocket-heeded       3 standard active           8       $8.35M     $1.36M     -1.8%     10
lateral-rocket-heeded       4 standard dissolved        5       $0.00M     $0.04M         -      1
lateral-rocket-heeded       5 standard dissolved        6       $0.00M     $0.98M         -      4
lateral-rocket-heeded       6 standard dissolved        5       $0.00M     $0.85M         -      4
lateral-rocket-heeded       7 standard active           7       $8.77M     $1.44M    -12.7%      8
lateral-rocket-heeded       8 standard active          24      $34.89M     $1.42M      9.5%     12
lateral-rocket-heeded       9 standard dissolved        5       $0.00M     $0.32M         -      0
lateral-rocket-heeded      10 standard active          23      $35.74M     $1.31M     19.8%     12
pyramid                     1 standard dissolved       15       $0.00M    $-1.65M     -2.1%      7
pyramid                     2 standard dissolved       12       $0.00M    $-0.64M    -18.3%      5
pyramid                     3 standard active           9       $9.60M     $1.54M    -42.7%     13
pyramid                     4 standard active          21      $16.15M     $2.06M    -49.1%     10
pyramid                     5 standard active          21       $8.71M    $-0.76M     14.8%     11
pyramid                     6 standard active          22      $17.99M     $3.82M      4.5%     10
pyramid                     7 standard active          34      $30.84M     $7.58M     53.7%      8
pyramid                     8 standard active          64      $75.29M    $12.46M     19.5%     18
pyramid                     9 standard dissolved        8       $0.00M     $0.02M         -      4
pyramid                    10 standard active          21      $18.86M     $2.69M     -7.7%     11
restructuring               1 standard dissolved       37       $0.00M    $-0.60M     64.2%      7
restructuring               2 standard active          19      $36.40M     $3.32M     40.7%     18
restructuring               3 standard active          51      $69.19M     $4.17M      7.7%     25
restructuring               4 standard active          47      $61.33M     $4.21M     -3.7%     25
restructuring               5 standard active          56      $73.42M     $2.68M      9.7%     32
restructuring               6 standard active          27      $31.35M     $1.84M    -25.4%     19
restructuring               7 standard dissolved       28       $0.00M    $-0.69M      3.7%      9
restructuring               8 standard active          70      $91.13M     $4.41M    -24.8%     32
restructuring               9 standard active          26      $27.26M     $2.41M     -0.9%     21
restructuring              10 standard active          51      $63.33M     $3.22M     -1.2%     30
steady                      1 easy     active          32      $30.97M     $1.47M      0.1%     16
steady                      2 easy     active          80     $111.29M     $4.76M      2.2%     36
steady                      3 easy     active          58      $70.39M     $4.32M    -26.8%     23
steady                      4 easy     active          53      $84.58M     $4.00M    -42.5%     25
steady                      5 easy     active         103     $129.86M     $3.73M      3.8%     45
steady                      6 easy     active          38      $54.36M     $2.70M     19.5%     26
steady                      7 easy     active          61      $81.17M     $4.18M    -27.4%     21
steady                      8 easy     active          68      $81.44M     $4.90M    -38.6%     23
steady                      9 easy     active          50      $69.63M     $4.02M    -12.1%     22
steady                     10 easy     active          74      $94.23M     $3.67M     27.0%     26
steady                      1 hard     active          32      $36.47M     $4.58M      7.1%     16
steady                      2 hard     active          28      $30.29M     $5.10M    -39.9%     16
steady                      3 hard     active          53      $75.38M     $4.15M    -48.3%     21
steady                      4 hard     active          53      $84.58M     $4.00M    -42.5%     27
steady                      5 hard     active          35      $25.56M     $0.82M    -25.5%     26
steady                      6 hard     active          44      $55.15M     $3.84M    -10.1%     25
steady                      7 hard     active          55      $68.95M     $4.22M    -30.9%     23
steady                      8 hard     active          53      $60.39M     $3.70M     -2.8%     20
steady                      9 hard     active          80      $86.71M     $3.97M    -22.1%     26
steady                     10 hard     active          25      $32.67M     $1.86M     -0.5%     22
steady                      1 standard active          32      $37.11M     $4.38M     -8.2%     15
steady                      2 standard active          28      $30.29M     $5.10M    -39.9%     13
steady                      3 standard active          51      $57.11M     $2.78M    -24.2%     20
steady                      4 standard active          53      $84.58M     $4.00M    -42.5%     24
steady                      5 standard active         102     $104.09M     $3.88M     10.0%     36
steady                      6 standard active          44      $55.15M     $3.84M    -10.1%     23
steady                      7 standard active          56      $62.17M     $4.54M    -30.9%     18
steady                      8 standard active          74      $93.18M     $4.14M    -29.7%     26
steady                      9 standard active          80      $86.71M     $3.97M    -22.1%     26
steady                     10 standard active          53      $65.57M     $4.53M     25.1%     20

 ok  T1               do-nothing fails (2009 revenue < $3M in 2005 dollars and falling, or dissolved)          9/10 (7 nominal)  (>= 9/10)
MISS T2               no dominant strategy (best founder's earnings 2005-2015, wins)                        steady 9, pyramid 1  (<= 6/10 each)  KNOWN MISS (PT-M7b)
MISS T3.lawyers       steady lawyers, Dec 2015 (median)                                                                    53.0  (100-250)  KNOWN MISS (PT-M7b)
 ok  T3.revenue       steady revenue 2015 (median)                                                                      $63.87M  ($60M-$150M)
MISS T4.steady        steady PEP 2015 (median)                                                                           $4.07M  ($0.5M-$1.2M)  KNOWN MISS (PT-M7b)
 ok  T4.boutique      boutique PEP 2015 (median)                                                                         $2.24M  ($1.0M-$2.5M)
MISS T4.pyramid       pyramid PEP 2015 (median)                                                                          $1.80M  ($0.7M-$1.6M)  KNOWN MISS (PT-M7b)
 ok  T5.easy          steady dissolves (easy)                                                                              0.0%  (0%-10%)
MISS T5.standard      steady dissolves (standard)                                                                          0.0%  (5%-20%)  KNOWN MISS (PT-M7b)
MISS T5.hard          steady dissolves (hard)                                                                              0.0%  (20%-45%)  KNOWN MISS (PT-M7b)
 ok  T6.attrition     associate attrition a year (median of years and strategies)                                         19.9%  (15%-25%)
FAIL T6.partners      steady: Sept 2006 class made equity partner by Dec 2015                                              7.7%  (8%-15%)
 ok  T7.realisation   median realisation                                                                                  87.4%  (84%-92%)
 ok  T7.collection    median collection                                                                                   96.5%  (93%-98%)
 ok  T7.utilisation   median utilisation                                                                                  84.9%  (75%-90%)
 ok  T7.lockup        median lockup (days)                                                                                  123  (90-150)
MISS T8.corporate     2009 vs 2008, corporate-heavy firms (n=32)                                                          -1.3%  (-30% to -10%)  KNOWN MISS (PT-M7b)
MISS T8.restructuring 2009 vs 2008, restructuring > 20% (n=3)                                                             40.7%  (-5% to +20%)  KNOWN MISS (PT-M7b)
MISS T9.rocket        lateral rocket dissolves by 2015                                                                     8/10  (3-6/10)  KNOWN MISS (PT-M7b)
MISS T9.heeded        the rocket with the CFO's warnings heeded dissolves                                                  6/10  (<= 1/10)  KNOWN MISS (PT-M7b)
MISS T10.ratio        pyramid burnout / steady's (per associate-year)                                                     0.88x  (>= 2x)  KNOWN MISS (PT-M7b)
 ok  T10.steady       steady burnout a year                                                                                0.6%  (<= 5%)
 ok  T11              rivals hold history (worst gap, misses, top-10 kept)                                          5.7%, 0, 10  (±15%, 0, >= 8)
FAIL T12              steady's median turn in 2015 (pure sim, runner's machine)                                          256 ms  (<= 250 ms)

90 runs x 132 turns in 334 s wall clock with 4 jobs
```

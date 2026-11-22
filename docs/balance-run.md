# The v1 balance run (PT-M7, re-read by PT-M7b)

`make balance` (seeds 1-10, 132 turns from January 2005, five strategies plus T5's difficulty runs and the T8/T9 variants; 4 workers). One line per run, then every target as `docs/balance-targets.md`'s Measures read it. PT-M7's run (its readings are in `docs/tasks/PT-M7-balance-and-v1-close.md`'s Decisions) is replaced by PT-M7b's below; T12's row is printed only (its gate is `make check-timing`: 159 ms).

PT-M7b's run (`make balance` on PT-M7b's merge head, after PT-M17; the KNOWN MISS rows are PT-M7b's, for Reece: `docs/tasks/PT-M7b-pressure-and-balance.md`):

```text
strategy       seed       diff      state    lawyers revenue 2015        PEP      09/08       secs
boutique                    1 standard active           6       $9.26M     $2.05M      6.3%     10
boutique                    2 standard active           5       $5.48M     $1.64M    -31.2%     10
boutique                    3 standard active          10      $10.24M     $2.09M     -7.8%     10
boutique                    4 standard dissolved        7       $0.00M    $-0.78M     31.6%      8
boutique                    5 standard active           8      $11.58M     $2.58M     19.9%     11
boutique                    6 standard active           9      $11.58M     $1.96M     17.2%     11
boutique                    7 standard active           7      $10.77M     $2.48M     13.4%     10
boutique                    8 standard active           5      $10.60M     $2.70M      9.8%     10
boutique                    9 standard active           6       $7.60M     $1.59M     24.1%     10
boutique                   10 standard active           6       $8.05M     $1.74M     -2.1%     10
do-nothing                  1 standard active           1       $1.34M     $1.08M    -10.2%     11
do-nothing                  2 standard dissolved        2       $0.00M    $-0.93M    -90.9%      6
do-nothing                  3 standard active           2       $3.88M     $1.73M    -14.0%     10
do-nothing                  4 standard dissolved        2       $0.00M     $0.03M         -      6
do-nothing                  5 standard active           2       $3.38M     $1.48M    -58.6%      9
do-nothing                  6 standard active           2       $3.36M     $1.47M    -47.1%      9
do-nothing                  7 standard active           2       $3.08M     $1.34M    -42.1%      8
do-nothing                  8 standard active           1       $2.33M     $2.12M    -60.8%      9
do-nothing                  9 standard active           2       $3.39M     $1.48M     74.7%      9
do-nothing                 10 standard active           2       $3.25M     $1.41M    -16.2%      9
lateral-rocket              1 standard active          23      $39.47M     $1.50M     18.3%     15
lateral-rocket              2 standard dissolved        5       $0.00M    $-0.16M         -      0
lateral-rocket              3 standard active          17      $29.55M     $1.52M     -4.1%     13
lateral-rocket              4 standard dissolved        5       $0.00M     $0.11M         -      1
lateral-rocket              5 standard active          18      $36.17M     $1.86M     15.9%     14
lateral-rocket              6 standard active          18      $28.17M     $1.34M     -6.0%     14
lateral-rocket              7 standard active          22      $32.87M     $1.46M    -10.6%     11
lateral-rocket              8 standard active          21      $32.18M     $1.29M      5.0%     14
lateral-rocket              9 standard dissolved        5       $0.00M     $0.44M         -      1
lateral-rocket             10 standard active          25      $36.58M     $1.26M      0.8%     15
lateral-rocket-heeded       1 standard active          23      $39.47M     $1.49M     18.3%     13
lateral-rocket-heeded       2 standard dissolved        5       $0.00M    $-0.12M         -      0
lateral-rocket-heeded       3 standard active           4       $6.12M     $1.49M     -6.5%     11
lateral-rocket-heeded       4 standard active           5       $2.72M     $0.45M    -79.0%      9
lateral-rocket-heeded       5 standard active           7      $10.22M     $1.85M     -3.1%     11
lateral-rocket-heeded       6 standard active           7       $4.58M     $0.48M     -6.0%     12
lateral-rocket-heeded       7 standard active           5       $7.48M     $1.28M    -10.6%     12
lateral-rocket-heeded       8 standard active          21      $32.18M     $1.29M      5.0%     14
lateral-rocket-heeded       9 standard active           2      $-0.16M    $-0.87M    -38.8%     10
lateral-rocket-heeded      10 standard active           6       $8.54M     $1.17M      0.8%     13
pyramid                     1 standard active          29      $29.13M     $4.87M    -22.4%     18
pyramid                     2 standard active          51      $51.01M     $3.95M    -22.0%     22
pyramid                     3 standard active          28      $26.98M     $2.43M    -40.1%     16
pyramid                     4 standard active          35      $38.57M     $4.99M    -57.1%     18
pyramid                     5 standard active          15      $13.30M     $1.58M    -26.5%     16
pyramid                     6 standard dissolved       41       $0.00M    $-1.42M      8.9%     13
pyramid                     7 standard dissolved       14       $0.00M    $-1.13M    -61.3%      7
pyramid                     8 standard active          45      $46.88M     $6.57M     31.6%     18
pyramid                     9 standard dissolved       14       $0.00M    $-2.47M    -28.0%     10
pyramid                    10 standard active          20      $17.26M     $3.99M      9.6%     16
restructuring               1 standard dissolved       25       $0.00M     $0.12M     31.1%     10
restructuring               2 standard dissolved       22       $0.00M     $1.70M         -      5
restructuring               3 standard dissolved       32       $0.00M    $-0.09M     41.0%      9
restructuring               4 standard dissolved       18       $0.00M     $0.52M    -49.2%      9
restructuring               5 standard active          55      $70.04M     $3.51M    -20.7%     36
restructuring               6 standard active          60      $73.46M     $4.17M     -5.5%     34
restructuring               7 standard dissolved       18       $0.00M    $-1.09M      9.2%      8
restructuring               8 standard active          24      $22.46M     $1.96M    -12.5%     18
restructuring               9 standard dissolved       44       $0.00M    $-2.77M     38.4%     13
restructuring              10 standard active          55      $69.21M     $4.18M    -11.0%     31
steady                      1 easy     active          55      $70.48M     $4.02M     13.3%     29
steady                      2 easy     active          77      $81.36M     $3.79M    -29.8%     34
steady                      3 easy     dissolved       20       $0.00M    $-0.88M    -63.6%      7
steady                      4 easy     active          73      $87.99M     $3.88M     -4.9%     38
steady                      5 easy     dissolved       20       $0.00M    $-1.44M    -12.6%     20
steady                      6 easy     active          58      $77.68M     $4.12M    -28.8%     30
steady                      7 easy     active          49      $65.95M     $3.68M    -28.7%     30
steady                      8 easy     active          45      $60.91M     $5.36M      4.9%     27
steady                      9 easy     active          28      $30.15M     $4.17M    -19.3%     17
steady                     10 easy     active          38      $36.36M     $1.63M      7.8%     32
steady                      1 hard     active          34      $36.69M     $3.90M    -21.5%     17
steady                      2 hard     dissolved        4       $0.00M    $-0.05M         -      1
steady                      3 hard     active          34      $30.32M     $2.25M    -36.0%     19
steady                      4 hard     dissolved       13       $0.00M     $0.92M         -      3
steady                      5 hard     active          74      $99.65M     $3.91M     13.1%     36
steady                      6 hard     active          58      $67.73M     $3.42M      1.8%     24
steady                      7 hard     active          54      $67.41M     $3.80M      2.3%     30
steady                      8 hard     active          34      $34.51M     $3.18M    -16.9%     19
steady                      9 hard     dissolved        4       $0.00M     $0.22M         -      0
steady                     10 hard     active          36      $34.28M     $3.42M    -41.7%     18
steady                      1 standard active          18      $21.12M     $4.18M    -13.8%     17
steady                      2 standard active          53      $68.92M     $5.31M    -41.5%     23
steady                      3 standard active          73      $84.62M     $3.87M    -20.0%     38
steady                      4 standard active          49      $62.65M     $4.96M    -46.6%     25
steady                      5 standard active          43      $49.95M     $3.47M    -49.1%     27
steady                      6 standard active          53      $51.39M     $2.93M    -43.7%     25
steady                      7 standard dissolved       19       $0.00M    $-3.38M    -47.4%      7
steady                      8 standard active          51      $68.64M     $4.73M      6.9%     26
steady                      9 standard active          52      $69.11M     $4.34M    -28.4%     25
steady                     10 standard active          44      $51.86M     $2.29M     22.4%     29

 ok  T1               do-nothing fails (2009 revenue < $3M in 2005 dollars and falling, or dissolved)          9/10 (7 nominal)  (>= 9/10)
MISS T2               no dominant strategy (best founder's earnings 2005-2015, wins)                       steady 9, boutique 1  (<= 6/10 each)  KNOWN MISS (PT-M7b)
MISS T3.lawyers       steady lawyers, Dec 2015 (median)                                                                    50.0  (100-250)  KNOWN MISS (PT-M7b)
FAIL T3.revenue       steady revenue 2015 (median)                                                                      $57.26M  ($60M-$150M)
MISS T4.steady        steady PEP 2015 (median)                                                                           $4.02M  ($0.5M-$1.2M)  KNOWN MISS (PT-M7b)
 ok  T4.boutique      boutique PEP 2015 (median)                                                                         $2.00M  ($1.0M-$2.5M)
FAIL T4.pyramid       pyramid PEP 2015 (median)                                                                          $3.19M  ($0.7M-$1.6M)
FAIL T5.easy          steady dissolves (easy)                                                                             20.0%  (0%-10%)
 ok  T5.standard      steady dissolves (standard)                                                                         10.0%  (5%-20%)
 ok  T5.hard          steady dissolves (hard)                                                                             30.0%  (20%-45%)
 ok  T6.attrition     associate attrition a year (median of years and strategies)                                         20.5%  (15%-25%)
FAIL T6.partners      steady: Sept 2006 class made equity partner by Dec 2015                                              0.0%  (8%-15%)
 ok  T7.realisation   median realisation                                                                                  84.4%  (84%-92%)
 ok  T7.collection    median collection                                                                                   96.5%  (93%-98%)
 ok  T7.utilisation   median utilisation                                                                                  83.6%  (75%-90%)
 ok  T7.lockup        median lockup (days)                                                                                  126  (90-150)
MISS T8.corporate     2009 vs 2008, corporate-heavy firms (n=38)                                                          -9.0%  (-30% to -10%)  KNOWN MISS (PT-M7b)
MISS T8.restructuring 2009 vs 2008, restructuring > 20% (n=5)                                                             31.1%  (-5% to +20%)  KNOWN MISS (PT-M7b)
 ok  T9.rocket        lateral rocket dissolves by 2015                                                                     3/10  (3-6/10)
 ok  T9.heeded        the rocket with the CFO's warnings heeded dissolves                                                  1/10  (<= 1/10)
 ok  T10.ratio        pyramid burnout / steady's (per associate-year)                                                    10.98x  (>= 2x)
 ok  T10.steady       steady burnout a year                                                                                0.7%  (<= 5%)
 ok  T11              rivals hold history (worst gap, misses, top-10 kept)                                          5.7%, 0, 10  (±15%, 0, >= 8)
FAIL T12              steady's median turn in 2015 (pure sim, runner's machine)                                          283 ms  (<= 250 ms)

90 runs x 132 turns in 368 s wall clock with 4 jobs
```

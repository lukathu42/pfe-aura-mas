# CUHK Avenue Scenario Pack

The repository can generate a 30-identity external evaluation pack from the
official CUHK Avenue dataset. The pack selects all 21 testing clips followed
by 9 normal training clips as negative controls. A testing clip's
`ground_truth` intervals are derived from its official `volLabel` mask; a
training clip has an intentionally empty ground-truth list.

The video archive and ground-truth archive are not vendored. Avenue is
released for academic research, and the official page distributes the media
and labels separately:

- Dataset: <https://www.cse.cuhk.edu.hk/~leojia/projects/detectabnormal/Avenue_Dataset.zip>
- Ground truth: <https://www.cse.cuhk.edu.hk/~leojia/projects/detectabnormal/ground_truth_demo.zip>
- Dataset page: <https://www.cse.cuhk.edu.hk/~leojia/projects/detectabnormal/dataset.html>

The official page describes 16 training and 21 testing clips. The generated
manifests use the existing AURA-MAS replay schema and label Avenue anomalies
as the generic `anomaly` event because Avenue's labels identify abnormal
regions and time ranges, not the project's finer event taxonomy.

## Prepare

Download and extract both official archives into `data/avenue/`, preserving
the `training_videos/`, `testing_videos/`, and
`ground_truth_demo/testing_label_mask/` directories. Check that the archive
contains at least 21 testing and 9 training `.avi` files before generating the
pack.

## Generate

```bash
python -m aura_mas.scenarios.avenue data/avenue \
  --out scenarios \
  --count 30 \
  --fps 25 \
  --source-prefix data/avenue
```

The command writes `avenue_test_01.json` through `avenue_test_21.json` and
`avenue_train_01.json` through `avenue_train_09.json`. It refuses to write
anything when the requested number of distinct clips is unavailable.

## Evaluate

Run a smoke campaign first, then the full matrix only after inspecting the
generated ground-truth windows:

```bash
python -m aura_mas.scripts.run_campaign \
  --scenarios avenue_test_01,avenue_test_02 \
  --reps 0

python -m aura_mas.scripts.run_campaign \
  --scenarios avenue_test_01,avenue_test_02 \
  --reps 0,1,2
```

The second command is a small repeated-run example: replace the two names
with the 30 generated manifest names, or run smaller batches. The campaign runner
does not treat a missing `duration_seconds` as an error; replay uses its
existing timeout default when a codec cannot report the duration.

Do not pool this pack with the existing CAVIAR/AIRTLab/ABODA campaign without
recording the dataset and split in the resulting tables. The 30 manifests are
30 distinct clips, but the training controls and the 21 test clips remain
clustered within one source dataset.

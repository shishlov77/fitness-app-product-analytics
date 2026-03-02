import os
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta

rng = np.random.default_rng(42)

N_REAL  = 50_000
N_BOTS  = 2_500
START   = date(2025, 11, 1)
END     = date(2025, 12, 31)
PERIOD  = (END - START).days + 1

all_dates = [START + timedelta(days=i) for i in range(PERIOD)]

# install date weights — weekends and December/holidays boosted
w = np.ones(PERIOD)
for i, d in enumerate(all_dates):
    if d.weekday() >= 5:                 w[i] *= 1.30
    if d.month == 12:                    w[i] *= 1.40
    if d.month == 12 and d.day >= 20:    w[i] *= 1.50
w /= w.sum()

print("Generating installs...")
n_total = N_REAL + N_BOTS
idx     = rng.choice(PERIOD, size=n_total, p=w)

install_dates = [all_dates[i] for i in idx]
install_timestamps = [
    datetime(d.year, d.month, d.day,
             int(rng.integers(0, 24)), int(rng.integers(0, 60)), int(rng.integers(0, 60)))
    for d in install_dates
]

installs = pd.DataFrame({
    'user_id'           : np.arange(1, n_total + 1),
    'install_date'      : install_dates,
    'install_timestamp' : install_timestamps,
    'platform'          : rng.choice(['iOS', 'Android'], size=n_total, p=[0.42, 0.58]),
    'country'           : rng.choice(
                            ['US','UK','DE','FR','CA','AU','BR','IN','MX','PL'],
                            size=n_total,
                            p=[0.35, 0.12, 0.08, 0.07, 0.06, 0.05, 0.05, 0.05, 0.04, 0.13]),
    'channel'           : rng.choice(
                            ['organic','paid_social','paid_search','referral'],
                            size=n_total, p=[0.45, 0.30, 0.15, 0.10]),
    'app_version'       : rng.choice(
                            ['3.0.1','3.1.0','3.1.2','3.2.0'],
                            size=n_total, p=[0.10, 0.20, 0.45, 0.25]),
    'is_bot'            : [0] * N_REAL + [1] * N_BOTS,
})

os.makedirs('data', exist_ok=True)
installs.to_csv('data/installs.csv', index=False)
print(f'  installs: {len(installs):,}')

# ── onboarding ─────────────────────────────────────────────────────────────────
print("Generating onboarding...")

real = installs[installs['is_bot'] == 0].copy().reset_index(drop=True)

started_mask = rng.random(N_REAL) < 0.72
started_u    = real[started_mask].copy().reset_index(drop=True)
m            = len(started_u)

completed       = (rng.random(m) < 0.70).astype(int)
steps_completed = np.where(completed == 1, 5, rng.integers(1, 5, size=m))
delay_s         = rng.integers(30, 300, size=m)

started_at = [
    ts + timedelta(seconds=int(d))
    for ts, d in zip(started_u['install_timestamp'], delay_s)
]
completed_at = [
    (s + timedelta(seconds=int(rng.integers(180, 480)))) if c == 1 else None
    for s, c in zip(started_at, completed)
]

goals    = ['weight_loss','muscle_gain','endurance','flexibility','general_fitness']
goal_arr = rng.choice(goals, size=m, p=[0.30, 0.25, 0.15, 0.10, 0.20])

onboarding = pd.DataFrame({
    'user_id'         : started_u['user_id'].values,
    'started_at'      : started_at,
    'completed_at'    : completed_at,
    'completed'       : completed,
    'steps_completed' : steps_completed,
    'goal'            : goal_arr,
})

onboarding.to_csv('data/onboarding.csv', index=False)
print(f'  onboarding: {len(onboarding):,}')

# ── events (vectorized probability matrix) ─────────────────────────────────────
print("Generating events (vectorized)...")

ob_done  = set(onboarding[onboarding['completed'] == 1]['user_id'])
ob_flag  = np.isin(real['user_id'].values, list(ob_done))
base_d1  = np.where(ob_flag, 0.35, 0.18)

# retention probability matrix  shape = (N_REAL, 31)
probs         = np.zeros((N_REAL, 31))
probs[:, 0]   = 0.68
probs[:, 1]   = base_d1
for d in range(2, 8):
    probs[:, d] = base_d1 * (0.62 ** (d - 1))
for d in range(8, 31):
    probs[:, d] = base_d1 * (0.62 ** 7) * (0.95 ** (d - 7))

# weekend boost
install_ord = np.array([dt.toordinal() for dt in real['install_date']])
for d in range(31):
    dow = (install_ord + d) % 7
    is_we = (dow == 5) | (dow == 6)
    probs[:, d] = np.where(is_we, np.minimum(probs[:, d] * 1.15, 1.0), probs[:, d])

# mask days beyond END
max_d = np.array([(END - dt).days for dt in real['install_date']])
for d in range(31):
    probs[:, d] = np.where(max_d < d, 0.0, probs[:, d])

draws  = rng.random((N_REAL, 31))
active = draws < probs
u_idx, day_arr = np.where(active)
print(f'  active (user, day) pairs: {len(u_idx):,}')

# peak-hour distribution: morning 6-9, evening 17-21
hour_w = np.array([
    0.5, 0.3, 0.2, 0.2, 0.3, 0.6,
    1.5, 2.5, 3.0, 2.0, 1.5, 1.5,
    1.8, 1.5, 1.3, 1.5, 2.0, 3.5,
    4.5, 4.0, 3.5, 2.5, 1.5, 0.8,
], dtype=float)
hour_w /= hour_w.sum()

WORKOUT_TYPES = ['cardio', 'strength', 'yoga', 'hiit', 'stretching']
WORKOUT_PROBS = [0.30, 0.25, 0.20, 0.15, 0.10]

rows = []
eid  = 1

for ui, day in zip(u_idx, day_arr):
    row      = real.iloc[ui]
    uid      = int(row['user_id'])
    inst_d   = row['install_date']
    plat     = row['platform']
    cur_date = inst_d + timedelta(days=int(day))

    hour   = int(rng.choice(24, p=hour_w))
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    sess_ts = datetime(cur_date.year, cur_date.month, cur_date.day, hour, minute, second)
    sess_id = eid * 10

    rows.append((eid, uid, sess_ts, 'session_start', plat, None, sess_id))
    eid += 1

    # session init error: 6% on day 0, 2% on return days
    err_p = 0.06 if day == 0 else 0.02
    if rng.random() < err_p:
        err_ts = sess_ts + timedelta(seconds=int(rng.integers(1, 8)))
        rows.append((eid, uid, err_ts, 'session_init_error', plat, None, sess_id))
        eid += 1
        continue

    # workout flow
    wo_p = 0.55 if day == 0 else 0.62
    if rng.random() < wo_p:
        wt    = str(rng.choice(WORKOUT_TYPES, p=WORKOUT_PROBS))
        wo_ts = sess_ts + timedelta(minutes=int(rng.integers(2, 12)))
        rows.append((eid, uid, wo_ts, 'workout_start', plat, wt, sess_id))
        eid += 1

        cmp_p = 0.73 if day == 0 else 0.79
        if rng.random() < cmp_p:
            dur = int(rng.integers(15, 65))
            rows.append((eid, uid, wo_ts + timedelta(minutes=dur), 'workout_complete', plat, wt, sess_id))
            eid += 1

events_df = pd.DataFrame(
    rows,
    columns=['event_id','user_id','event_timestamp','event_type','platform','workout_type','session_id']
)

events_df.to_csv('data/events.csv', index=False)
print(f'  events: {len(events_df):,}')
print("Done.")

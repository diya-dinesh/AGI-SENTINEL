"""
Statistical Signal Detection Module

This module implements pharmacovigilance signal detection algorithms using statistical
methods to identify unusual patterns in adverse event reporting. It provides the core
analytical capabilities for the AGI-Sentinel system.

KEY FEATURES:
- Weekly aggregation of adverse event counts
- Baseline statistical modeling (mean, standard deviation)
- Dual-threshold signal detection (z-score + relative increase)
- Handling of sparse data and edge cases
- Configurable sensitivity parameters

SIGNAL DETECTION ALGORITHM:
The module uses a baseline comparison approach to detect safety signals:

1. **Data Preparation**:
   - Normalize receive dates to weekly periods
   - Explode semicolon-separated reactions into individual rows
   - Group by week and reaction to compute counts

2. **Baseline Calculation**:
   - Use all weeks except the most recent as baseline period
   - Compute mean and standard deviation of baseline counts
   - Handle zero/low variance cases with minimum std = 1.0

3. **Signal Detection** (dual-threshold approach):
   A signal is flagged if it meets ANY of these criteria:
   
   a) **Z-Score Threshold** (default: 2.0):
      z = (current_count - baseline_mean) / baseline_std
      Flags statistically significant deviations from baseline
   
   b) **Relative Increase Threshold** (default: 1.5x):
      relative = current_count / baseline_mean
      Flags clinically significant increases over baseline
   
   c) **Volume-Only Heuristic** (for sparse data):
      If baseline_mean < 0.5 AND current_count >= 3
      Catches emerging signals in low-volume drugs

4. **Edge Case Handling**:
   - Single week of data: Use volume threshold (count >= 3)
   - Zero baseline: Use relative threshold with small epsilon
   - Low variance: Apply minimum std to avoid false positives

STATISTICAL FORMULAS:
- Z-score: z = (x - μ) / σ
  where x = current count, μ = baseline mean, σ = baseline std
  
- Relative increase: r = x / μ
  where x = current count, μ = baseline mean
  
- Baseline period: All weeks except most recent
  (ensures we're comparing current week against historical pattern)

CONFIGURATION:
- min_weeks: Minimum weeks required for analysis (default: 2)
- z_threshold: Z-score cutoff for significance (default: 2.0)
- relative_threshold: Relative increase cutoff (default: 1.5)

INTEGRATION:
- Used by AnalyzerAgent for signal detection
- Configured via config.py (thresholds, minimum weeks)
- Returns structured signal dictionaries for downstream processing
"""

import pandas as pd
import numpy as np
import datetime
from typing import List, Dict, Any

def normalize_receivedate(s):
    try:
        return pd.to_datetime(s, errors='coerce')
    except Exception:
        return pd.NaT

def load_reports(db_path, drug_name):
    """
    Thin wrapper around db.load_reports
    """
    from tools.db import load_reports as db_load
    return db_load(db_path, drug_name)

def compute_weekly_counts(df):
    df = df.copy()
    if 'receivedate' in df.columns:
        df['receivedate'] = pd.to_datetime(df['receivedate'], errors='coerce')
    else:
        df['receivedate'] = pd.NaT

    # Split semicolon-joined reactions into individual rows
    if 'reaction' in df.columns:
        df['reaction'] = df['reaction'].fillna("").astype(str)
        # Use a temp column to avoid duplicate 'reaction' columns after explode/rename
        df['reaction_temp'] = df['reaction'].apply(lambda s: ([r.strip() for r in s.split(';') if r.strip()] or ['UNKNOWN']))
        df = df.explode('reaction_temp')
        # Drop original concatenated column, then rename temp to 'reaction'
        df = df.drop(columns=['reaction'])
        df = df.rename(columns={'reaction_temp': 'reaction'})
        df['reaction'] = df['reaction'].fillna('UNKNOWN')
    else:
        df['reaction'] = 'UNKNOWN'

    df['week'] = df['receivedate'].dt.to_period('W').apply(lambda r: r.start_time)
    counts = df.groupby(['week', 'reaction']).size().reset_index(name='count')
    return counts

def detect_spikes(df, min_weeks=2, z_threshold=2.0, relative_threshold=1.5):
    """
    Very simple spike detector:
    - for each reaction, compute baseline (all weeks except most recent)
    - detect if last week's count exceeds mean + z_threshold*std OR relative > relative_threshold
    Returns list of signal dicts.
    """
    results = []
    if df.empty:
        return results
    counts = compute_weekly_counts(df)

    # Fallback: if we only have a single week of data, surface high-volume reactions
    unique_weeks = counts['week'].nunique()
    if unique_weeks < 2:
        totals = counts.groupby('reaction')['count'].sum().sort_values(ascending=False)
        # Heuristic threshold for sparse data
        volume_threshold = 3
        for reaction, total in totals.items():
            if total >= volume_threshold:
                last_week = counts['week'].max()
                results.append({
                    "reaction": reaction,
                    "current_count": int(total),
                    "baseline_mean": 0.0,
                    "zscore": None,
                    "relative": None,
                    "week": str(last_week),
                    "reason": "volume_only"
                })
        return results

    for reaction, grp in counts.groupby('reaction'):
        grp = grp.sort_values('week')
        if len(grp) < min_weeks:
            continue
        baseline = grp['count'].iloc[:-1]
        if baseline.empty:
            continue
        mean = baseline.mean()
        std_raw = baseline.std(ddof=0)
        std = std_raw if std_raw > 0 else 1.0
        current = grp['count'].iloc[-1]
        zscore = (current - mean) / std if std else 0.0
        relative = (current / (mean + 1e-9)) if mean else float('inf')

        # Small-sample heuristic: elevate when baseline is near-zero but current has >= 3
        small_sample_flag = (mean < 0.5 and current >= 3)

        if (zscore >= z_threshold) or (relative >= relative_threshold) or small_sample_flag:
            last_week = grp['week'].iloc[-1]
            reasons = []
            if zscore >= z_threshold:
                reasons.append("zscore")
            if relative >= relative_threshold:
                reasons.append("relative")
            if small_sample_flag and not reasons:
                reasons.append("volume_only")
            results.append({
                "reaction": reaction,
                "current_count": int(current),
                "baseline_mean": float(mean),
                "zscore": float(zscore),
                "relative": float(relative),
                "week": str(last_week),
                "reason": "+".join(reasons) if reasons else None
            })
    return results

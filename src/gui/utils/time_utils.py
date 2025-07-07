# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 12:56:55 2025

@author: Benja
"""

from datetime import datetime, timedelta

def _get_dst_dates(year: int):
    """Calculate DST transition dates (Spring Forward and Fall Back) for America/Chicago."""
    # DST starts: Second Sunday of March (2 AM → 3 AM)
    march = datetime(year, 3, 1)
    spring_forward = march + timedelta(days=(6 - march.weekday()) + 7)  # Second Sunday

    # DST ends: First Sunday of November (2 AM → 1 AM)
    november = datetime(year, 11, 1)
    fall_back = november + timedelta(days=(6 - november.weekday()))  # First Sunday

    return spring_forward, fall_back

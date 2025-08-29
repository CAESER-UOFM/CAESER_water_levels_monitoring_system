#!/usr/bin/env python3
"""
Vented Transducer Utilities

Utilities for detecting vented transducers and determining compensation requirements.
Vented transducers already compensate for atmospheric pressure internally and should
NOT receive additional barometric compensation to avoid data corruption.
"""

import re
from pathlib import Path
from typing import Dict, Optional, Union


def is_vented_transducer(instrument_type: str = None, file_path: Path = None, metadata: Dict = None) -> bool:
    """
    Check if transducer is vented (atmospheric pressure compensated) based on instrument type
    
    Vented transducers (L5_LVENT, etc.) don't need barometric compensation because they
    already measure relative to atmospheric pressure.
    
    Args:
        instrument_type: Direct instrument type string (e.g., "L5_LVENT")
        file_path: Path to XLE file to read instrument type from
        metadata: Metadata dict containing 'instrument_type' key
        
    Returns:
        True if transducer is vented (no compensation needed), False otherwise
    """
    try:
        # Priority order: direct parameter > metadata > file reading
        if not instrument_type:
            if metadata and 'instrument_type' in metadata:
                instrument_type = metadata['instrument_type']
            elif file_path and file_path.exists():
                # Read XLE file to get instrument type
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for <Instrument_type> in the XML
                    match = re.search(r'<Instrument_type>(.*?)</Instrument_type>', content)
                    if match:
                        instrument_type = match.group(1).strip()
        
        # Check if this is a vented transducer model
        if instrument_type:
            vented_types = [
                'L5_LVENT',      # Levelogger 5 LT Vented
                'L4_LVENT',      # Levelogger 4 LT Vented  
                'L3_LVENT',      # Levelogger 3 LT Vented
                'LVENT',         # Generic vented designation
                'VENTED',        # Alternative vented designation
            ]
            
            instrument_upper = instrument_type.upper()
            return any(vented_type in instrument_upper for vented_type in vented_types)
        
        return False
        
    except Exception as e:
        print(f"   ⚠️  Could not check vented status: {e}")
        # If we can't determine, assume it's not vented (safer to attempt compensation)
        return False


def get_compensation_flag(instrument_type: str = None, file_path: Path = None, metadata: Dict = None) -> str:
    """
    Get compensation flag for transducer based on vented status
    
    Returns:
        'vented': Transducer is vented, skip compensation
        'requires_compensation': Transducer needs barometric compensation
    """
    if is_vented_transducer(instrument_type, file_path, metadata):
        return 'vented'
    else:
        return 'requires_compensation'


def should_apply_compensation(instrument_type: str = None, file_path: Path = None, metadata: Dict = None) -> bool:
    """
    Simple boolean check if compensation should be applied
    
    Returns:
        False: Skip compensation (vented transducer)
        True: Apply compensation (non-vented transducer)
    """
    return not is_vented_transducer(instrument_type, file_path, metadata)


# Export commonly used functions
__all__ = [
    'is_vented_transducer',
    'get_compensation_flag', 
    'should_apply_compensation'
]
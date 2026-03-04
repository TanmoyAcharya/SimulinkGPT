"""
Simulink Model Parser Module

This module provides functionality to parse Simulink (.slx) models
and extract structural information for analysis.
"""

from .parser import SimulinkParser
from .models import SimulinkBlock, SimulinkSignal, SimulinkModel

__all__ = ["SimulinkParser", "SimulinkBlock", "SimulinkSignal", "SimulinkModel"]

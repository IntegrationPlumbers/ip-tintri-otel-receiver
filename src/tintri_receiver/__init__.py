"""Tintri OpenTelemetry Receiver.

A Python-based OpenTelemetry Collector Receiver for monitoring Tintri storage infrastructure.
"""

__version__ = "1.0.0"
__author__ = "Engineering Team"

from tintri_receiver.receiver import TintriReceiver
from tintri_receiver.config import TintriReceiverConfig

__all__ = ["TintriReceiver", "TintriReceiverConfig"]

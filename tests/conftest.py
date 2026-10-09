"""Keep UI tests independent of telemetry and machine-specific usage profiling."""

from streamlit import config

config.set_option("browser.gatherUsageStats", False)

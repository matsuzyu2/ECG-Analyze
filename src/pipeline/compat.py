from __future__ import annotations

import numpy as np

# NeuroKit2 on newer NumPy may miss np.trapz; provide a fallback.
if not hasattr(np, "trapz") and hasattr(np, "trapezoid"):
    np.trapz = np.trapezoid  # type: ignore[attr-defined]

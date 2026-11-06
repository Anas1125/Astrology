"""Start the explicitly local, loopback-only AstroAI development server."""
from __future__ import annotations

import os
import uvicorn

# The isolated local switch never changes the public feature/license flags.
os.environ["APP_ENV"] = "development"
os.environ["ASTROLOGY_CALCULATIONS_ENABLED"] = "false"
os.environ["SWISSEPH_LICENSE_CONFIRMED"] = "false"
os.environ["ASTROLOGY_LOCAL_AGPL_DEVELOPMENT_ENABLED"] = "true"


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)

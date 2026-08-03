# WorldMonitor 05 — Model Routing

The implemented WorldMonitor refresh path performs no AI or model request. It never selects a
provider, holds a provider key, accesses Ollama/cloud model endpoints, or triggers model
load/unload. Any future AI enrichment must cross Builder's authenticated router as a separately
approved capability; it is not silently available today.

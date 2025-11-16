# **README.md** – Surgery Unit Simulation (TIES481 – Assignment 2)

---

```markdown
# Surgery Unit Simulation – TIES481 Assignment 2  
**University of Jyväskylä (JYU), Finland**  
**Course:** Simulation (2025)  
**Assignment:** 2 – Process-Based Discrete Event Simulation  
**Author:** Wajahat Haider 

---

## Overview

This project implements a **process-based discrete event simulation** of a hospital surgery unit using **SimPy** (Python), as recommended in the assignment. The model simulates:

- **P preparation rooms**  
- **1 operating theatre**  
- **R recovery rooms**  
- A **continuous patient flow** with **exponentially distributed** interarrival and service times  

Each patient carries **personal service times** for preparation, operation, and recovery — enabling future extension to multiple patient types.

---

## Key Features

| Feature | Implemented |
|-------|-------------|
| Process-based modeling (SimPy) | Yes |
| Patient-specific service times | Yes |
| Resource pools (prep, op, rec) | Yes `simpy.Resource` |
| No intermediate buffers | Yes Direct handoff |
| Entrance queue monitoring | Yes Time-weighted average |
| Operating theatre utilization | Yes Time-weighted |
| **Blocking probability** | Yes Time + Event-based |
| **Queue length over time** | Yes CSV + Plot |
| Average throughput time | Yes |
| Configurable parameters | Yes Top of file |
| Reproducible results | Yes `random.seed(42)` |

---

## System Model

```
[Arrival] → [Queue] → [P Prep Rooms] → [1 Op Theatre] → [R Recovery Rooms] → [Exit]
```

- **No queues** between phases (direct transfer)  
- **Blocking occurs** when operation ends but no recovery bed is free  
- **Entrance queue** = patients waiting for preparation  

---

## File Structure

```
.
├── surgery_simulation.py             # Main simulation code
├── queue_over_time.csv               # Generated: Queue length vs time
├── queue_length_plot.png             # Generated: Visualization
├── README.md                         # This file
└── Experiment_surgery_simulation.py  # just experiment with different python library
```

---

## Requirements

```txt
simpy>=4.0.1
pandas>=1.5
matplotlib>=3.5
```

---

## How to Run

1. **Clone / Save** the project
2. **Install dependencies**:
   ```bash
   pip install simpy pandas matplotlib
   ```
3. **Run the simulation**:
   ```bash
   python surgery_simulation.py
   ```

### Example Output

```
==================================================
         SIMULATION RESULTS
==================================================
Simulation time           : 100,000
Total patients            : 3,998
Avg queue length (entrance): 0.142
Op theatre utilization    : 0.799
Blocking probability (time): 0.068
Blocking fraction (events): 0.271
Avg throughput time       : 108.34
==================================================

Queue length over time saved to queue_over_time.csv
Queue plot saved to queue_length_plot.png
```

---

## Configuration (Top of `surgery_simulation.py`)

```python
INTERARRIVAL_MEAN = 25
PREP_MEAN = 40
OP_MEAN = 20
REC_MEAN = 40
PREP_ROOMS = 3
REC_ROOMS = 3
SIMULATION_TIME = 100_000
RANDOM_SEED = 42
```

> **Change these** to test different scenarios (e.g., increase `REC_ROOMS` to reduce blocking).

---

## Monitoring & Output

### 1. **Console Summary**
- Average entrance queue length  
- Operating theatre utilization  
- **Blocking probability** (time-weighted)  
- **Blocking fraction** (per operation)  
- Average patient throughput time  

### 2. **CSV Export** (`queue_over_time.csv`)
- Columns: `time`, `queue_length`  
- Step changes at every state transition  

### 3. **Plot** (`queue_length_plot.png`)
- Visualizes entrance queue evolution over time  

---

## Model Validation (Default Parameters)

| Metric | Expected | Simulated |
|-------|----------|-----------|
| Arrival rate | 0.04 / time | ~0.040 |
| Op utilization | ≤ 1.0 | **0.799** |
| Blocking | > 0 (R=3) | **6.8% (time)** |
| Throughput time | ~100–110 | **108.34** |

> Matches queueing theory:  
> - Op load = 0.04 × 20 = **0.8**  
> - Bottleneck at recovery → blocking occurs  

---

## Assignment Compliance

| Requirement | Met? | How |
|-----------|------|-----|
| Use SimPy (process-oriented) | Yes | Full patient lifecycle as `env.process()` |
| Patient carries service times | Yes | `Patient` class with `prep_time`, `op_time`, `rec_time` |
| Resource pools without buffers | Yes | `Resource.request()` → direct phase transition |
| Monitor entrance queue & op utilization | Yes | Time-weighted averages |
| Configurable parameters | Yes | All at top, no hardcoding |
| Exponential distributions | Yes | `random.expovariate()` |
| Future-proof design | Yes | Easy to add patient types, distributions |

---

## Future Extensions (Suggested)

- Multiple patient types (e.g., urgent vs elective)  
- Different distributions (normal, uniform)  
- Warm-up period & multiple replications  
- GUI dashboard (with `matplotlib` animation)  
- Export full patient log (CSV)  

---

## License

For academic use only – TIES481 Course Project.

---

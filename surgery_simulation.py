import simpy
import random
import pandas as pd
import matplotlib.pyplot as plt
from collections import deque

# ================================
# CONFIGURATION
# ================================ppy
INTERARRIVAL_MEAN = 25
PREP_MEAN = 40
OP_MEAN = 20
REC_MEAN = 40
PREP_ROOMS = 3
REC_ROOMS = 3
SIMULATION_TIME = 100_000
RANDOM_SEED = 42
OUTPUT_CSV = "queue_over_time.csv"
OUTPUT_PLOT = "queue_length_plot.png"

# ================================
# MONITORING CLASS
# ================================
class Monitor:
    def __init__(self, env):
        self.env = env
        self.queue_history = []      # (time, length)
        self.op_busy_history = []    # (time, 1 if busy, 0 if idle)
        self.op_blocked_history = [] # (time, 1 if blocked, 0 otherwise)
        self.throughput_times = []
        self.blocked_count = 0
        self.op_ended_count = 0
        self.last_time = 0
        self.last_queue_len = 0
        self.last_op_busy = 0
        self.last_op_blocked = 0
        self.action = env.process(self.run())

    def update(self, queue_len, op_busy, op_blocked):
        now = self.env.now
        if now > self.last_time:
            # Record previous state
            self.queue_history.append((self.last_time, self.last_queue_len))
            self.op_busy_history.append((self.last_time, self.last_op_busy))
            self.op_blocked_history.append((self.last_time, self.last_op_blocked))
        self.last_queue_len = queue_len
        self.last_op_busy = op_busy
        self.last_op_blocked = op_blocked
        self.last_time = now

    def record_operation_end(self):
        self.op_ended_count += 1
        if self.last_op_blocked:
            self.blocked_count += 1

    def record_throughput(self, time):
        self.throughput_times.append(time)

    def run(self):
        while True:
            yield self.env.timeout(1.0)

    def finalize(self):
        now = self.env.now
        if now > self.last_time:
            self.queue_history.append((self.last_time, self.last_queue_len))
            self.op_busy_history.append((self.last_time, self.last_op_busy))
            self.op_blocked_history.append((self.last_time, self.last_op_blocked))

        def time_weighted_avg(data):
            total = 0.0
            for i in range(1, len(data)):
                t0, v0 = data[i-1]
                t1, v1 = data[i]
                total += v0 * (t1 - t0)
            return total / now if now > 0 else 0

        avg_queue = time_weighted_avg(self.queue_history)
        op_util = time_weighted_avg(self.op_busy_history)
        blocking_prob = time_weighted_avg(self.op_blocked_history)
        avg_throughput = sum(self.throughput_times) / len(self.throughput_times) if self.throughput_times else 0

        return {
            'avg_queue_length': avg_queue,
            'op_utilization': op_util,
            'blocking_probability': blocking_prob,
            'avg_throughput_time': avg_throughput,
            'total_patients': len(self.throughput_times),
            'blocking_fraction_events': self.blocked_count / self.op_ended_count if self.op_ended_count > 0 else 0
        }

    def export_queue_csv(self):
        df = pd.DataFrame(self.queue_history, columns=['time', 'queue_length'])
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"Queue length over time saved to {OUTPUT_CSV}")

    def plot_queue(self):
        df = pd.DataFrame(self.queue_history, columns=['time', 'queue_length'])
        plt.figure(figsize=(10, 6))
        plt.step(df['time'], df['queue_length'], where='post', label='Entrance Queue Length')
        plt.xlabel('Simulation Time')
        plt.ylabel('Queue Length')
        plt.title('Entrance Queue Length Over Time')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOT)
        plt.close()
        print(f"Queue plot saved to {OUTPUT_PLOT}")


# ================================
# PATIENT CLASS
# ================================
class Patient:
    def __init__(self, id, prep_time, op_time, rec_time, arrival_time):
        self.id = id
        self.prep_time = prep_time
        self.op_time = op_time
        self.rec_time = rec_time
        self.arrival_time = arrival_time
        self.end_time = None


# ================================
# PATIENT PROCESS
# ================================
def patient_process(env, patient, prep_pool, op_unit, rec_pool, monitor, arrival_queue):
    # ARRIVAL
    arrival_queue.append(patient)
    monitor.update(len(arrival_queue), op_unit.count > 0, 0)

    # PREPARATION
    with prep_pool.request() as req:
        yield req
        arrival_queue.remove(patient)
        monitor.update(len(arrival_queue), op_unit.count > 0, 0)
        yield env.timeout(patient.prep_time)

    # OPERATION
    with op_unit.request() as req:
        yield req
        monitor.update(len(arrival_queue), 1, 0)
        yield env.timeout(patient.op_time)
        monitor.record_operation_end()  # Check if blocked after op

    # RECOVERY (blocking happens here if no room)
    with rec_pool.request() as req:
        # If no recovery room, this yield waits → op is blocked
        monitor.update(len(arrival_queue), 1, 1)  # op blocked
        yield req
        monitor.update(len(arrival_queue), 1, 0)  # op unblocked
        yield env.timeout(patient.rec_time)

    # DEPARTURE
    patient.end_time = env.now
    throughput = patient.end_time - patient.arrival_time
    monitor.record_throughput(throughput)
    monitor.update(len(arrival_queue), op_unit.count > 0, 0)


# ================================
# GENERATOR
# ================================
def patient_generator(env, prep_pool, op_unit, rec_pool, monitor):
    patient_id = 0
    arrival_queue = []

    while True:
        yield env.timeout(random.expovariate(1.0 / INTERARRIVAL_MEAN))

        prep_t = random.expovariate(1.0 / PREP_MEAN)
        op_t = random.expovariate(1.0 / OP_MEAN)
        rec_t = random.expovariate(1.0 / REC_MEAN)

        patient = Patient(patient_id, prep_t, op_t, rec_t, env.now)
        patient_id += 1

        env.process(patient_process(env, patient, prep_pool, op_unit, rec_pool, monitor, arrival_queue))


# ================================
# MAIN
# ================================
def run_simulation():
    random.seed(RANDOM_SEED)
    env = simpy.Environment()

    prep_pool = simpy.Resource(env, capacity=PREP_ROOMS)
    op_unit = simpy.Resource(env, capacity=1)
    rec_pool = simpy.Resource(env, capacity=REC_ROOMS)

    monitor = Monitor(env)
    env.process(patient_generator(env, prep_pool, op_unit, rec_pool, monitor))

    print("Running simulation...")
    env.run(until=SIMULATION_TIME)

    results = monitor.finalize()
    monitor.export_queue_csv()
    monitor.plot_queue()

    print("\n" + "="*50)
    print("         SIMULATION RESULTS")
    print("="*50)
    print(f"Simulation time           : {SIMULATION_TIME:,}")
    print(f"Total patients            : {results['total_patients']:,}")
    print(f"Avg queue length (entrance): {results['avg_queue_length']:.3f}")
    print(f"Op theatre utilization    : {results['op_utilization']:.3f}")
    print(f"Blocking probability (time): {results['blocking_probability']:.3f}")
    print(f"Blocking fraction (events): {results['blocking_fraction_events']:.3f}")
    print(f"Avg throughput time       : {results['avg_throughput_time']:.2f}")
    print("="*50)

    return results


if __name__ == "__main__":

    run_simulation()

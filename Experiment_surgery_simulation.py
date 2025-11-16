import heapq
import random
from collections import deque

class Patient:
    def __init__(self, id, arrival_time, prep_time, op_time, rec_time):
        self.id = id
        self.arrival_time = arrival_time
        self.prep_time = prep_time
        self.op_time = op_time
        self.rec_time = rec_time
        self.status = 'arrived'

def simulate(interarrival_mean=25, prep_mean=40, op_mean=20, rec_mean=40, prep_capacity=3, rec_capacity=3, max_patients=1000):
    random.seed(42)  # For reproducibility
    
    events = []  # Priority queue: (time, counter, event_type, data)
    event_counter = 0
    patients = {}  # id -> Patient
    patient_id = 0
    current_time = 0
    last_time = 0
    
    arrival_queue = deque()  # Patients waiting for prep (entrance queue)
    operation_queue = deque()  # Patients waiting for op
    
    prep_free = prep_capacity
    rec_free = rec_capacity
    op_status = 'idle'  # 'idle', 'busy', 'waiting'
    op_patient = None  # Current patient in op (or waiting to move to rec)
    
    # Stats
    throughput_times = []
    queue_area = 0.0  # For avg arrival queue length
    busy_time = 0.0   # Op busy time
    blocked_time = 0.0  # Op waiting time (blocked)
    terminated_patients = 0
    
    # Schedule first arrival
    next_arrival = random.expovariate(1 / interarrival_mean)
    heapq.heappush(events, (next_arrival, event_counter, 'Arrival', None))
    event_counter += 1
    
    while events:
        time, _, event_type, data = heapq.heappop(events)
        current_time = time
        
        # Update stats before processing event (using state from previous time)
        delta = current_time - last_time
        queue_area += len(arrival_queue) * delta
        if op_status == 'busy':
            busy_time += delta
        elif op_status == 'waiting':
            blocked_time += delta
        last_time = current_time
        
        if event_type == 'Arrival':
            patient_id += 1
            prep_t = random.expovariate(1 / prep_mean)
            op_t = random.expovariate(1 / op_mean)
            rec_t = random.expovariate(1 / rec_mean)
            pat = Patient(patient_id, current_time, prep_t, op_t, rec_t)
            patients[patient_id] = pat
            arrival_queue.append(patient_id)
            pat.status = 'waiting_prep'
            
            # Schedule next arrival if not reached max
            if patient_id < max_patients:
                next_arr = random.expovariate(1 / interarrival_mean)
                heapq.heappush(events, (current_time + next_arr, event_counter, 'Arrival', None))
                event_counter += 1
            
            # Try to start preparation (immediate)
            heapq.heappush(events, (current_time, event_counter, 'StartPreparation', None))
            event_counter += 1
        
        elif event_type == 'StartPreparation':
            if arrival_queue and prep_free > 0:
                pid = arrival_queue.popleft()
                pat = patients[pid]
                pat.status = 'in_prep'
                prep_free -= 1
                heapq.heappush(events, (current_time + pat.prep_time, event_counter, 'EndPreparation', pid))
                event_counter += 1
        
        elif event_type == 'EndPreparation':
            pid = data
            pat = patients[pid]
            pat.status = 'prepared'
            operation_queue.append(pid)
            prep_free += 1
            
            # Try to start another prep if queue not empty
            heapq.heappush(events, (current_time, event_counter, 'StartPreparation', None))
            event_counter += 1
            
            # Try to start operation
            heapq.heappush(events, (current_time, event_counter, 'StartOperation', None))
            event_counter += 1
        
        elif event_type == 'StartOperation':
            if operation_queue and op_status == 'idle':
                pid = operation_queue.popleft()
                pat = patients[pid]
                pat.status = 'in_op'
                op_status = 'busy'
                op_patient = pid
                heapq.heappush(events, (current_time + pat.op_time, event_counter, 'EndOperation', pid))
                event_counter += 1
        
        elif event_type == 'EndOperation':
            pid = data
            pat = patients[pid]
            pat.status = 'operated'
            op_status = 'waiting'  # Blocked until recovery available
            
            # Try to start recovery
            heapq.heappush(events, (current_time, event_counter, 'StartRecovery', None))
            event_counter += 1
        
        elif event_type == 'StartRecovery':
            if rec_free > 0 and op_status == 'waiting':
                pid = op_patient
                pat = patients[pid]
                pat.status = 'in_rec'
                rec_free -= 1
                op_status = 'idle'
                op_patient = None
                heapq.heappush(events, (current_time + pat.rec_time, event_counter, 'EndRecovery', pid))
                event_counter += 1
                
                # Try to start next operation
                heapq.heappush(events, (current_time, event_counter, 'StartOperation', None))
                event_counter += 1
        
        elif event_type == 'EndRecovery':
            pid = data
            pat = patients[pid]
            pat.status = 'recovered'
            rec_free += 1
            
            # Try to start recovery if op is waiting
            heapq.heappush(events, (current_time, event_counter, 'StartRecovery', None))
            event_counter += 1
            
            # Terminate patient
            heapq.heappush(events, (current_time, event_counter, 'PatientTerminator', pid))
            event_counter += 1
        
        elif event_type == 'PatientTerminator':
            pid = data
            pat = patients[pid]
            throughput = current_time - pat.arrival_time
            throughput_times.append(throughput)
            terminated_patients += 1
            del patients[pid]
    
    # Final stats (no need for update, as last delta was before last event)
    total_time = current_time
    avg_queue_length = queue_area / total_time if total_time > 0 else 0
    op_utilization = busy_time / total_time if total_time > 0 else 0
    op_blocking_fraction = blocked_time / total_time if total_time > 0 else 0
    avg_throughput_time = sum(throughput_times) / len(throughput_times) if throughput_times else 0
    
    return {
        'avg_queue_length': avg_queue_length,
        'op_utilization': op_utilization,
        'op_blocking_fraction': op_blocking_fraction,
        'avg_throughput_time': avg_throughput_time,
        'total_patients_processed': terminated_patients,
        'total_sim_time': total_time
    }

# Run the simulation with default parameters
results = simulate()
print("Simulation Results:")
print(f"Average queue length at entrance: {results['avg_queue_length']:.2f}")
print(f"Operating theatre utilization: {results['op_utilization']:.2f}")
print(f"Operating theatre blocking fraction: {results['op_blocking_fraction']:.2f} (for reference)")
print(f"Average throughput time: {results['avg_throughput_time']:.2f}")
print(f"Total patients processed: {results['total_patients_processed']}")
print(f"Total simulation time: {results['total_sim_time']:.2f}")
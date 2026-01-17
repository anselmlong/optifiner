#!/usr/bin/env python3
"""Evaluator for the Job Shop Scheduling Problem.

This script evaluates a scheduler on multiple test instances of varying difficulty.
The Job Shop Scheduling Problem (JSSP) is NP-hard - there's no known polynomial-time
algorithm to find optimal solutions for large instances.

The evaluator is OUTSIDE the codebase directory, so it cannot be modified by the agent.
The agent must improve the scheduler in codebase/scheduler.py.

Output format: JSON with a "score" field.
"""

import json
import sys
import random
import time
from dataclasses import dataclass
from typing import Any

# Fixed seed for reproducible test instances
random.seed(12345)

# Add codebase to path so we can import the scheduler
sys.path.insert(0, "codebase")


@dataclass
class Operation:
    """A single operation in a job."""
    job_id: int
    op_index: int  # Index within the job
    machine: int
    duration: int


@dataclass
class Job:
    """A job consisting of a sequence of operations."""
    job_id: int
    operations: list[Operation]


@dataclass
class Instance:
    """A Job Shop Scheduling instance."""
    name: str
    num_jobs: int
    num_machines: int
    jobs: list[Job]
    
    def get_lower_bound(self) -> int:
        """Calculate a lower bound on the makespan.
        
        The lower bound is the maximum of:
        1. The longest job (sum of all its operation durations)
        2. The highest machine load (sum of durations on the busiest machine)
        """
        # Longest job
        max_job_length = max(
            sum(op.duration for op in job.operations)
            for job in self.jobs
        )
        
        # Busiest machine
        machine_loads = [0] * self.num_machines
        for job in self.jobs:
            for op in job.operations:
                machine_loads[op.machine] += op.duration
        max_machine_load = max(machine_loads)
        
        return max(max_job_length, max_machine_load)


@dataclass
class ScheduledOp:
    """A scheduled operation with its start time."""
    job_id: int
    op_index: int
    machine: int
    start_time: int
    duration: int
    
    @property
    def end_time(self) -> int:
        return self.start_time + self.duration


def generate_instance(name: str, num_jobs: int, num_machines: int, 
                      min_duration: int = 1, max_duration: int = 20,
                      ops_per_job: int | None = None) -> Instance:
    """Generate a random Job Shop instance.
    
    Each job visits each machine exactly once (classic JSSP formulation).
    """
    if ops_per_job is None:
        ops_per_job = num_machines
    
    jobs = []
    for j in range(num_jobs):
        # Random permutation of machines
        machines = list(range(num_machines))
        random.shuffle(machines)
        machines = machines[:ops_per_job]
        
        operations = [
            Operation(
                job_id=j,
                op_index=i,
                machine=machines[i],
                duration=random.randint(min_duration, max_duration)
            )
            for i in range(ops_per_job)
        ]
        jobs.append(Job(job_id=j, operations=operations))
    
    return Instance(name=name, num_jobs=num_jobs, num_machines=num_machines, jobs=jobs)


def generate_test_instances() -> list[Instance]:
    """Generate a diverse set of test instances with varying difficulty."""
    instances = []
    
    # Easy instances (5x5)
    for i in range(3):
        random.seed(100 + i)
        instances.append(generate_instance(f"easy_{i}", num_jobs=5, num_machines=5))
    
    # Medium instances (10x5, 8x8)
    for i in range(4):
        random.seed(200 + i)
        if i < 2:
            instances.append(generate_instance(f"medium_{i}", num_jobs=10, num_machines=5))
        else:
            instances.append(generate_instance(f"medium_{i}", num_jobs=8, num_machines=8))
    
    # Hard instances (15x10, 20x10)
    for i in range(4):
        random.seed(300 + i)
        if i < 2:
            instances.append(generate_instance(f"hard_{i}", num_jobs=15, num_machines=10))
        else:
            instances.append(generate_instance(f"hard_{i}", num_jobs=20, num_machines=10))
    
    # Very hard instances (30x15, 50x15)
    for i in range(4):
        random.seed(400 + i)
        if i < 2:
            instances.append(generate_instance(f"veryhard_{i}", num_jobs=30, num_machines=15))
        else:
            instances.append(generate_instance(f"veryhard_{i}", num_jobs=50, num_machines=15))
    
    return instances


def validate_schedule(instance: Instance, schedule: list[ScheduledOp]) -> tuple[bool, str]:
    """Validate a schedule for correctness.
    
    Checks:
    1. All operations are scheduled exactly once
    2. Job precedence constraints are satisfied
    3. No two operations on the same machine overlap
    """
    # Check all operations are present
    expected_ops = set()
    for job in instance.jobs:
        for op in job.operations:
            expected_ops.add((op.job_id, op.op_index))
    
    scheduled_ops = set()
    for sop in schedule:
        scheduled_ops.add((sop.job_id, sop.op_index))
    
    if expected_ops != scheduled_ops:
        missing = expected_ops - scheduled_ops
        extra = scheduled_ops - expected_ops
        return False, f"Missing ops: {missing}, Extra ops: {extra}"
    
    # Build lookup for scheduled operations
    sched_lookup: dict[tuple[int, int], ScheduledOp] = {}
    for sop in schedule:
        sched_lookup[(sop.job_id, sop.op_index)] = sop
    
    # Check job precedence
    for job in instance.jobs:
        for i in range(1, len(job.operations)):
            prev_op = sched_lookup[(job.job_id, i - 1)]
            curr_op = sched_lookup[(job.job_id, i)]
            if curr_op.start_time < prev_op.end_time:
                return False, f"Job {job.job_id}: op {i} starts at {curr_op.start_time} before op {i-1} ends at {prev_op.end_time}"
    
    # Check machine conflicts
    machine_schedules: dict[int, list[ScheduledOp]] = {}
    for sop in schedule:
        if sop.machine not in machine_schedules:
            machine_schedules[sop.machine] = []
        machine_schedules[sop.machine].append(sop)
    
    for machine, ops in machine_schedules.items():
        ops.sort(key=lambda x: x.start_time)
        for i in range(1, len(ops)):
            if ops[i].start_time < ops[i-1].end_time:
                return False, f"Machine {machine}: overlap between job {ops[i-1].job_id} (ends {ops[i-1].end_time}) and job {ops[i].job_id} (starts {ops[i].start_time})"
    
    return True, "Valid"


def calculate_makespan(schedule: list[ScheduledOp]) -> int:
    """Calculate the makespan (total completion time) of a schedule."""
    if not schedule:
        return 0
    return max(sop.end_time for sop in schedule)


def instance_to_dict(instance: Instance) -> dict[str, Any]:
    """Convert instance to a dictionary format for the scheduler."""
    return {
        "name": instance.name,
        "num_jobs": instance.num_jobs,
        "num_machines": instance.num_machines,
        "jobs": [
            {
                "job_id": job.job_id,
                "operations": [
                    {
                        "job_id": op.job_id,
                        "op_index": op.op_index,
                        "machine": op.machine,
                        "duration": op.duration
                    }
                    for op in job.operations
                ]
            }
            for job in instance.jobs
        ]
    }


def schedule_to_objects(schedule: list[dict]) -> list[ScheduledOp]:
    """Convert scheduler output to ScheduledOp objects."""
    return [
        ScheduledOp(
            job_id=s["job_id"],
            op_index=s["op_index"],
            machine=s["machine"],
            start_time=s["start_time"],
            duration=s["duration"]
        )
        for s in schedule
    ]


def evaluate_instance(scheduler_func, instance: Instance, timeout: float = 30.0) -> dict:
    """Evaluate the scheduler on a single instance."""
    instance_dict = instance_to_dict(instance)
    lower_bound = instance.get_lower_bound()
    
    start_time = time.time()
    try:
        schedule_raw = scheduler_func(instance_dict)
        elapsed = time.time() - start_time
        
        if elapsed > timeout:
            return {
                "name": instance.name,
                "valid": False,
                "error": f"Timeout: {elapsed:.2f}s > {timeout}s",
                "score": 0
            }
        
        schedule = schedule_to_objects(schedule_raw)
        valid, msg = validate_schedule(instance, schedule)
        
        if not valid:
            return {
                "name": instance.name,
                "valid": False,
                "error": msg,
                "score": 0
            }
        
        makespan = calculate_makespan(schedule)
        
        # Score: ratio of lower_bound to makespan (1.0 is optimal, lower is worse)
        # We scale to 0-100 range and penalize heavily for being far from optimal
        ratio = lower_bound / makespan if makespan > 0 else 0
        # Score formula: rewards being close to optimal
        # ratio = 1.0 -> score = 100
        # ratio = 0.5 -> score = ~25
        # ratio = 0.3 -> score = ~9
        instance_score = 100 * (ratio ** 2)
        
        return {
            "name": instance.name,
            "valid": True,
            "makespan": makespan,
            "lower_bound": lower_bound,
            "ratio": ratio,
            "elapsed": elapsed,
            "score": instance_score
        }
        
    except Exception as e:
        return {
            "name": instance.name,
            "valid": False,
            "error": str(e),
            "score": 0
        }


def main():
    """Run the benchmark and output the score."""
    try:
        # Import the scheduler
        from scheduler import schedule
        
        # Generate test instances
        instances = generate_test_instances()
        
        results = []
        total_score = 0
        
        for instance in instances:
            result = evaluate_instance(schedule, instance)
            results.append(result)
            total_score += result["score"]
        
        # Average score across all instances
        avg_score = total_score / len(instances) if instances else 0
        
        # Count valid schedules
        valid_count = sum(1 for r in results if r.get("valid", False))
        
        # Calculate category averages
        categories = {"easy": [], "medium": [], "hard": [], "veryhard": []}
        for r in results:
            for cat in categories:
                if r["name"].startswith(cat):
                    categories[cat].append(r["score"])
        
        category_scores = {
            cat: sum(scores) / len(scores) if scores else 0 
            for cat, scores in categories.items()
        }
        
        output = {
            "score": avg_score,
            "passed": valid_count == len(instances),
            "metrics": {
                "total_instances": len(instances),
                "valid_schedules": valid_count,
                "average_score": avg_score,
                "category_scores": category_scores,
            },
            "details": results
        }
        
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        import traceback
        output = {
            "score": 0,
            "passed": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

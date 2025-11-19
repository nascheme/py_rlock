"""
Standalone stress test for recursive lock (RLock) implementation.
Can be run directly from command line for debugging and performance testing.

Usage:
    python -m py_locks.stress_rlock -t 8 -d 10
"""

import argparse
import random
import threading
import time
from dataclasses import dataclass

from . import RLock


@dataclass
class ThreadStats:
    """Statistics for a single thread"""

    thread_id: int
    locks_performed: int = 0
    recursive_locks_performed: int = 0
    errors_detected: int = 0


def busy_wait_microseconds(microseconds):
    """Busy wait for specified microseconds"""
    start = time.perf_counter()
    target = start + (microseconds / 1_000_000)
    while time.perf_counter() < target:
        pass


def do_busy_work(rng, avg_microseconds=30):
    """Do busy work with random duration around the average.

    Args:
        rng: Random number generator instance
        avg_microseconds: Average duration in microseconds (default: 30)
                         Actual duration will be 0.8 to 1.2 times this value
    """
    duration = avg_microseconds * (0.8 + rng.random() * 0.4)
    busy_wait_microseconds(duration)


def lock_operation(rlock, shared_counter, stats, rng):
    """Perform a simple lock operation"""
    # Do some work before acquiring lock
    do_busy_work(rng, avg_microseconds=10)

    rlock.lock()

    # Non-atomic read-modify-write
    old_value = shared_counter[0]

    # Short work while holding lock
    do_busy_work(rng, avg_microseconds=2)

    # Non-atomic write
    shared_counter[0] = old_value + 1

    rlock.unlock()

    # Do some work after releasing lock
    do_busy_work(rng, avg_microseconds=10)

    stats.locks_performed += 1


def recursive_lock_operation(rlock, shared_counter, stats, rng):
    """Perform a recursive lock operation"""
    # Do some work before acquiring lock
    do_busy_work(rng, avg_microseconds=10)

    # Acquire lock recursively (2-4 levels deep)
    depth = rng.randint(2, 4)

    for _ in range(depth):
        rlock.lock()

    # Non-atomic read-modify-write
    old_value = shared_counter[0]

    # Short work while holding lock
    do_busy_work(rng, avg_microseconds=2)

    # Non-atomic write
    shared_counter[0] = old_value + 1

    # Release all locks
    for _ in range(depth):
        rlock.unlock()

    # Do some work after releasing lock
    do_busy_work(rng, avg_microseconds=10)

    stats.recursive_locks_performed += 1


def worker_thread(rlock, shared_counter, stats, stop_flag):
    """Worker thread function - runs until stop_flag is set"""
    # Create per-thread random instance to avoid global state contention
    rng = random.Random()

    while not stop_flag.is_set():
        # Randomly choose operation
        # 50% unlocked work, 30% simple lock, 20% recursive lock
        op = rng.randint(1, 100)

        if op <= 50:
            do_busy_work(rng)
        elif op <= 80:
            lock_operation(rlock, shared_counter, stats, rng)
        else:
            recursive_lock_operation(rlock, shared_counter, stats, rng)


def run_stress_test(threads=8, duration=10):
    """Run the stress test and return success status"""
    print("=== RLock Stress Test ===")
    print("Configuration:")
    print(f"  Threads: {threads}")
    print(f"  Duration: {duration} seconds\n")

    # Create the rlock
    rlock = RLock()

    # Shared counter (using list for mutability)
    shared_counter = [0]

    # Create stop flag
    stop_flag = threading.Event()

    # Create statistics objects for each thread
    stats_list = [ThreadStats(i) for i in range(threads)]

    # Create and start threads
    print("Starting threads...")
    thread_list = []
    start_time = time.time()

    for i in range(threads):
        t = threading.Thread(
            target=worker_thread,
            args=(rlock, shared_counter, stats_list[i], stop_flag),
        )
        t.start()
        thread_list.append(t)

    print(f"Started {threads} threads")
    print("\nRunning test...")

    # Sleep for test duration
    time.sleep(duration)

    # Signal threads to stop
    stop_flag.set()

    # Wait for all threads to complete
    for t in thread_list:
        t.join()

    end_time = time.time()
    actual_duration = end_time - start_time

    print(f"\nTest completed in {actual_duration:.2f} seconds\n")

    # Collect statistics
    total_locks = sum(s.locks_performed for s in stats_list)
    total_recursive = sum(s.recursive_locks_performed for s in stats_list)
    total_errors = sum(s.errors_detected for s in stats_list)
    total_ops = total_locks + total_recursive

    expected_counter = total_locks + total_recursive
    final_counter = shared_counter[0]

    # Print results
    print("=== Results ===")
    print(f"Total operations: {total_ops}")
    print("\nOperation breakdown:")
    if total_ops > 0:
        print(
            f"  Simple locks:    {total_locks} ({100.0 * total_locks / total_ops:.1f}%)"
        )
        print(
            f"  Recursive locks: {total_recursive} ({100.0 * total_recursive / total_ops:.1f}%)"
        )

    print("\nPer-thread statistics:")
    for s in stats_list:
        total = s.locks_performed + s.recursive_locks_performed
        print(
            f"  Thread {s.thread_id}: {total} ops "
            f"({s.locks_performed} simple, {s.recursive_locks_performed} recursive, "
            f"{s.errors_detected} errors)"
        )

    print("\nVerification:")

    if total_errors > 0:
        print(f"  ✗ Errors detected: {total_errors}")
    else:
        print("  ✓ No errors detected")

    if final_counter == expected_counter:
        print("  ✓ Final counter matches expected")
        print(f"      Actual:   {final_counter}")
        print(f"      Expected: {expected_counter}")
    else:
        print("  ✗ Final counter MISMATCH!")
        print(f"      Actual:   {final_counter}")
        print(f"      Expected: {expected_counter}")
        print(f"      Lost updates: {expected_counter - final_counter}")

    print()
    if total_errors == 0 and final_counter == expected_counter:
        print("RESULT: PASS")
        return True
    else:
        print("RESULT: FAIL")
        return False


def main():
    """Main entry point for command line execution"""
    parser = argparse.ArgumentParser(
        description="Run stress test for recursive lock (RLock) implementation"
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=8,
        help="Number of worker threads (default: 8)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=10,
        help="Test duration in seconds (default: 10)",
    )

    args = parser.parse_args()

    success = run_stress_test(threads=args.threads, duration=args.duration)
    import sys

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

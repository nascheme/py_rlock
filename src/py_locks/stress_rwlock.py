"""
Standalone stress test for reader-writer lock (RWLock) implementation.
Can be run directly from command line for debugging and performance testing.

Usage:
    python -m py_locks.stress_rwlock -t 8 -d 10
    python -m py_locks.stress_rwlock -t 8 -d 10 -u  # With upgrade testing
"""

import argparse
import random
import threading
import time
from dataclasses import dataclass

from . import RWLock


@dataclass
class ThreadStats:
    """Statistics for a single thread"""

    thread_id: int
    reads_performed: int = 0
    writes_performed: int = 0
    recursive_performed: int = 0
    errors_detected: int = 0


@dataclass
class UpgradeThreadStats:
    """Statistics for upgrade test mode"""

    thread_id: int
    reads_performed: int = 0
    writes_performed: int = 0
    upgrades_attempted: int = 0
    upgrades_succeeded: int = 0
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


def reader_operation(rwlock, shared_counter, stats, rng):
    """Perform a read operation"""
    # Do some work before acquiring lock
    do_busy_work(rng)

    rwlock.lock_read()

    # Read the value
    value1 = shared_counter[0]

    # Short work while holding lock
    do_busy_work(rng, avg_microseconds=1.5)

    # Read again - should be the same
    value2 = shared_counter[0]

    rwlock.unlock_read()

    # Do some work after releasing lock
    do_busy_work(rng)

    stats.reads_performed += 1

    # Verify consistency
    if value1 != value2:
        stats.errors_detected += 1
        print(
            f"ERROR: Thread {stats.thread_id} detected inconsistent read: {value1} != {value2}"
        )


def writer_operation(rwlock, shared_counter, stats, rng):
    """Perform a write operation"""
    # Do some work before acquiring lock
    do_busy_work(rng)

    rwlock.lock_write()

    # Non-atomic read-modify-write
    old_value = shared_counter[0]

    # Short work while holding write lock
    do_busy_work(rng, avg_microseconds=1.5)

    # Non-atomic write
    shared_counter[0] = old_value + 1

    rwlock.unlock_write()

    # Do some work after releasing lock
    do_busy_work(rng)

    stats.writes_performed += 1


def recursive_operation(rwlock, shared_counter, stats, rng):
    """Perform a recursive lock operation"""
    # Do some work before acquiring lock
    do_busy_work(rng)

    rwlock.lock_write()
    rwlock.lock_write()  # Recursive

    # Non-atomic increment
    shared_counter[0] += 1

    rwlock.unlock_write()
    rwlock.unlock_write()

    # Do some work after releasing lock
    do_busy_work(rng)

    stats.recursive_performed += 1


# ============ Upgrade Test Mode Operations ============


def upgrade_reader_operation(rwlock, shared_counter, stats, rng):
    """Perform a read operation with possible upgrade"""
    # Spend most time without lock (90-95% of time)
    do_busy_work(rng)

    rwlock.lock_read()

    # Read the value
    value1 = shared_counter[0]

    # Short work while holding lock
    do_busy_work(rng, avg_microseconds=1.5)

    # Read again - should be the same
    value2 = shared_counter[0]

    # Try to upgrade with lower probability (2% chance)
    if rng.randint(1, 100) <= 2:
        stats.upgrades_attempted += 1
        if rwlock.try_upgrade():
            stats.upgrades_succeeded += 1
            # Successfully upgraded to write lock
            # Increment counter
            shared_counter[0] += 1

            # Short work as writer
            do_busy_work(rng, avg_microseconds=1.5)

            # Release write lock and reacquire read lock
            rwlock.unlock_write()
            rwlock.lock_read()

    rwlock.unlock_read()

    # Spend most time without lock (90-95% of time)
    do_busy_work(rng)

    stats.reads_performed += 1

    # Verify consistency
    if value1 != value2:
        stats.errors_detected += 1
        print(
            f"ERROR: Thread {stats.thread_id} detected inconsistent read: {value1} != {value2}"
        )


def upgrade_writer_operation(rwlock, shared_counter, stats, rng):
    """Perform a write operation (low contention mode)"""
    # Spend most time without lock
    do_busy_work(rng)

    rwlock.lock_write()

    # Non-atomic read-modify-write
    old_value = shared_counter[0]

    # Short work while holding write lock
    do_busy_work(rng, avg_microseconds=1.5)

    # Non-atomic write
    shared_counter[0] = old_value + 1

    rwlock.unlock_write()

    do_busy_work(rng)

    stats.writes_performed += 1


def upgrade_worker_thread(rwlock, shared_counter, stats, stop_flag):
    """Worker thread for upgrade test mode - low contention"""
    # Create per-thread random instance to avoid global state contention
    rng = random.Random()

    while not stop_flag.is_set():
        # Randomly choose operation
        # 94% reads (with possible upgrade), 6% writes
        op = rng.randint(1, 100)

        if op <= 94:
            upgrade_reader_operation(rwlock, shared_counter, stats, rng)
        else:
            upgrade_writer_operation(rwlock, shared_counter, stats, rng)


# ============ Standard Stress Test ============


def worker_thread(rwlock, shared_counter, stats, stop_flag):
    """Worker thread function - runs until stop_flag is set"""
    # Create per-thread random instance to avoid global state contention
    rng = random.Random()

    while not stop_flag.is_set():
        # Randomly choose operation
        # 50% unlocked work, 48% reads, 2% writes (includes recursive)
        op = rng.randint(1, 100)

        if op <= 50:
            do_busy_work(rng)
        elif op <= 98:
            reader_operation(rwlock, shared_counter, stats, rng)
        elif op <= 99:
            writer_operation(rwlock, shared_counter, stats, rng)
        else:
            recursive_operation(rwlock, shared_counter, stats, rng)


def run_stress_test(threads=8, duration=10):
    """Run the stress test and return success status"""
    print("=== RWLock Stress Test ===")
    print("Configuration:")
    print(f"  Threads: {threads}")
    print(f"  Duration: {duration} seconds\n")

    # Create the rwlock
    rwlock = RWLock()

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
            args=(rwlock, shared_counter, stats_list[i], stop_flag),
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
    total_reads = sum(s.reads_performed for s in stats_list)
    total_writes = sum(s.writes_performed for s in stats_list)
    total_recursive = sum(s.recursive_performed for s in stats_list)
    total_errors = sum(s.errors_detected for s in stats_list)
    total_ops = total_reads + total_writes + total_recursive

    expected_counter = total_writes + total_recursive
    final_counter = shared_counter[0]

    # Print results
    print("=== Results ===")
    print(f"Total operations: {total_ops}")
    print("\nOperation breakdown:")
    if total_ops > 0:
        print(
            f"  Reads:     {total_reads} ({100.0 * total_reads / total_ops:.1f}%)"
        )
        print(
            f"  Writes:    {total_writes} ({100.0 * total_writes / total_ops:.1f}%)"
        )
        print(
            f"  Recursive: {total_recursive} ({100.0 * total_recursive / total_ops:.1f}%)"
        )

    print("\nPer-thread statistics:")
    for s in stats_list:
        total = s.reads_performed + s.writes_performed + s.recursive_performed
        print(
            f"  Thread {s.thread_id}: {total} ops "
            f"({s.reads_performed} reads, {s.writes_performed} writes, "
            f"{s.recursive_performed} recursive, {s.errors_detected} errors)"
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


def run_upgrade_test(threads=8, duration=10):
    """Run upgrade test with low contention"""
    print("=== RWLock Upgrade Test ===")
    print("Configuration:")
    print(f"  Threads: {threads}")
    print(f"  Duration: {duration} seconds")
    print("  Mode: Low contention (optimized for upgrade success)\n")

    # Create the rwlock
    rwlock = RWLock()

    # Shared counter (using list for mutability)
    shared_counter = [0]

    # Create stop flag
    stop_flag = threading.Event()

    # Create statistics objects for each thread
    stats_list = [UpgradeThreadStats(i) for i in range(threads)]

    # Create and start threads
    print("Starting threads...")
    thread_list = []
    start_time = time.time()

    for i in range(threads):
        t = threading.Thread(
            target=upgrade_worker_thread,
            args=(rwlock, shared_counter, stats_list[i], stop_flag),
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
    total_reads = sum(s.reads_performed for s in stats_list)
    total_writes = sum(s.writes_performed for s in stats_list)
    total_upgrades_attempted = sum(s.upgrades_attempted for s in stats_list)
    total_upgrades_succeeded = sum(s.upgrades_succeeded for s in stats_list)
    total_errors = sum(s.errors_detected for s in stats_list)
    total_ops = total_reads + total_writes

    expected_counter = total_writes + total_upgrades_succeeded
    final_counter = shared_counter[0]

    # Print results
    print("=== Results ===")
    print(f"Total operations: {total_ops}")
    print("\nOperation breakdown:")
    if total_ops > 0:
        print(
            f"  Reads:  {total_reads} ({100.0 * total_reads / total_ops:.1f}%)"
        )
        print(
            f"  Writes: {total_writes} ({100.0 * total_writes / total_ops:.1f}%)"
        )

    print("\nUpgrade statistics:")
    print(f"  Upgrade attempts:  {total_upgrades_attempted}")
    print(f"  Upgrade successes: {total_upgrades_succeeded}")
    if total_upgrades_attempted > 0:
        success_rate = (
            100.0 * total_upgrades_succeeded / total_upgrades_attempted
        )
        print(f"  Success rate:      {success_rate:.1f}%")

    print("\nPer-thread statistics:")
    for s in stats_list:
        total = s.reads_performed + s.writes_performed
        print(
            f"  Thread {s.thread_id}: {total} ops "
            f"({s.reads_performed} reads, {s.writes_performed} writes, "
            f"{s.upgrades_succeeded}/{s.upgrades_attempted} upgrades, "
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

    # Check upgrade success rate
    if total_upgrades_attempted > 0:
        success_rate = (
            100.0 * total_upgrades_succeeded / total_upgrades_attempted
        )
        if success_rate >= 50.0:
            print(
                f"  ✓ Upgrade success rate is good ({success_rate:.1f}% >= 50%)"
            )
        else:
            print(
                f"  ✗ Upgrade success rate is low ({success_rate:.1f}% < 50%)"
            )

    print()
    if (
        total_errors == 0
        and final_counter == expected_counter
        and total_upgrades_attempted > 0
        and (100.0 * total_upgrades_succeeded / total_upgrades_attempted)
        >= 50.0
    ):
        print("RESULT: PASS")
        return True
    else:
        print("RESULT: FAIL")
        return False


def main():
    """Main entry point for command line execution"""
    parser = argparse.ArgumentParser(
        description="Run stress test for reader-writer lock implementation"
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
    parser.add_argument(
        "-u",
        "--upgrade",
        action="store_true",
        help="Run upgrade test mode (low contention, optimized for upgrade success)",
    )

    args = parser.parse_args()

    if args.upgrade:
        success = run_upgrade_test(
            threads=args.threads, duration=args.duration
        )
    else:
        success = run_stress_test(
            threads=args.threads, duration=args.duration
        )

    import sys

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# GlobalThreadManager

This package solves the problem of asynchronous thread execution in Python.

Allows concurrent execution in a non-concurrent context (you can submit synchronous functions for asynchronous execution). 

Submit your synchronous functions for concurrent execution without having to run an event loop

## Features

- Execute multiple tasks concurrently with controlled parallelism
- Limit the number of simultaneous workers
- Optional delay between task submissions
- Manages existence of event loop

## Usage

```python
from global_thread_manager import GlobalThreadManager, Task
from typing import List, Any

# Get the singleton instance
manager: GlobalThreadManager = GlobalThreadManager()

# Sample function
def my_function(first_print = "Waiting", second_print = "Done"):
    print(first_print)
    time.sleep(2)
    print(second_print)

# Create tasks
tasks: List[Task] = [
    manager.create_task(function=my_function, args=("I am Waiting..."), kwargs={"second_print": "I am Done."}),
    manager.create_task(function=my_function)
]

# Execute tasks with a maximum of 3 concurrent workers
results: List[Any] = manager.submit_tasks_to_event_loop(tasks=tasks, max_workers=3)

# Execute tasks with delay between submissions
results: List[Any] = manager.submit_tasks_to_event_loop_with_delay(
    tasks=tasks,
    max_workers=3,
    delay_seconds=0.5
)

# Asynchronous execution (fire and forget). Must be run in an async environment.
manager.submit_tasks_to_event_loop(
    tasks=tasks,
    max_workers=3,
    await_completion=False
)
```

## Requirements

- Python 3.10+
- No external dependencies beyond the Python standard library

## Thread Safety

All operations are thread-safe, making this class suitable for use in multi-threaded applications.

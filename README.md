# GlobalThreadManager

This package solves the problem of asynchronous thread execution in python. 

The GlobalThreadManager uses asyncio to concurrently and efficiently execute I/O-bound tasks. Asyncio avoids Python's GIL.

## Features

- Execute multiple tasks concurrently with controlled parallelism
- Limit the number of simultaneous workers
- Optional delay between task submissions
- Singleton pattern ensures consistent task management across your application
- Comprehensive error handling for task execution

## Usage

```python
from global_thread_manager import GlobalThreadManager, Task

# Get the singleton instance
manager = GlobalThreadManager()

# Create tasks
tasks = []
tasks.append(manager.create_task(function=my_function, args=(arg1, arg2), kwargs={'key': 'value'}))
tasks.append(manager.create_task(function=another_function))

# Execute tasks with a maximum of 3 concurrent workers
results = manager.submit_tasks_to_event_loop(tasks=tasks, max_workers=3)

# Execute tasks with delay between submissions
results = manager.submit_tasks_to_event_loop_with_delay(
    tasks=tasks, 
    max_workers=3,
    delay_seconds=0.5
)

# Asynchronous execution (fire and forget)
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

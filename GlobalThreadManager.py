import asyncio
import gc
import threading
from typing import Callable, Tuple, Dict, List, Any, Optional, Union


class Task:
    """A task to be run in a background thread."""

    def __init__(self, function: Callable[..., Any], args: Tuple[Any, ...] = tuple(),
                 kwargs: Dict[str, Any] | None = None):
        # Check types
        if kwargs is None:
            kwargs = dict()

        if not callable(function):
            raise ValueError(f"Function {function} is not callable.")
        if not isinstance(args, tuple):
            raise ValueError(f"Arguments {args} should be a tuple.")
        if not isinstance(kwargs, dict):
            raise ValueError(f"Keyword arguments {kwargs} should be a dictionary.")

        self.function = function
        self.args = args
        self.kwargs = kwargs


class GlobalThreadManager:
    """
    Singleton class to manage all thread-based tasks in the application.

    All tasks are executed concurrently using asyncio underneath.

    Example Usage:
        manager = GlobalThreadManager()
        tasks = []

        for function in functions:
            task = manager.create_task(function=function, args=(my_first_arg), kwargs={'my_second_arg': my_second_arg})
            tasks.append(task)

        results = manager.submit_tasks_to_event_loop(
            tasks=tasks, max_workers=5
        )
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock: # Singleton
            if cls._instance is None:
                cls._instance = super(GlobalThreadManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def reset(cls):
        """
        Resets the program memory by setting the GlobalThreadManager
        instance to None and running the garbage collector.
        """
        if cls._instance is not None:
            cls._instance = None
            gc.collect()
            gc.enable()

    @staticmethod
    def create_task(function: Callable[..., Any],
                    args: Union[Tuple[Any, ...], Any, None] = None,
                    kwargs: Optional[Dict[str, Any]] = None) -> Task:
        """
        Create a task to be run in a thread.

        :param function: The function to be run in the thread.
        :param args: A tuple of positional arguments to pass to the function.
        :param kwargs: A dictionary of keyword arguments to pass to the function.
        :return: A Task object containing the function, args, and kwargs.
        """
        if not callable(function):
            raise ValueError(f"Function {function} is not callable.")

        if args is None:
            args = ()

        if not isinstance(args, tuple):
            args = (args,)

        if kwargs is None:
            kwargs = {}

        if not isinstance(kwargs, dict):
            raise ValueError(f"Keyword arguments {kwargs} should be a dictionary or None.")

        return Task(function=function, args=args, kwargs=kwargs)

    def submit_tasks_to_event_loop(self, tasks: List[Task] | Task,
                                   max_workers: int,
                                   await_completion: bool = True,
                                   print_updates: bool = False,
                                   *args, **kwargs) -> List[Any] | None:
        """
        Submit a list of tasks to be executed concurrently using asyncio underneath.

        This maintains the same API as before but uses asyncio internally:
            1. Creates an asyncio event loop if needed
            2. Runs all tasks concurrently with asyncio.gather
            3. Uses semaphores to limit concurrency to max_workers

        :param tasks: A list of Task objects to be executed
        :param max_workers: Maximum number of concurrent workers for this batch of tasks
        :param await_completion: Whether to wait for task completion
        :param print_updates: Whether to print status updates
        :param args: Kept for backwards compatibility
        :param kwargs: Kept for backwards compatibility
        :return: List of task results
        """
        if not isinstance(tasks, list):
            tasks = [tasks]

        if await_completion:
            results = self._run_async_tasks(tasks, max_workers, print_updates)

            if print_updates:
                print(f"Completed {len(results)} tasks")

            return results

        else:
            # Just submit tasks and continue without waiting
            asyncio.create_task(self._execute_tasks_async(tasks, max_workers, print_updates))

    def submit_tasks_to_event_loop_with_delay(self, tasks: List[Task],
                                              max_workers: int,
                                              delay_seconds: float = 1.0,
                                              await_completion: bool = True,
                                              print_updates: bool = False) -> List[Any] | None:
        """
        Submit a list of tasks to be executed concurrently with a delay between submissions.

        This method introduces a specified delay between task submissions while
        maintaining the concurrency limit using asyncio semaphores.

        :param tasks: A list of Task objects to be executed
        :param max_workers: Maximum number of concurrent workers
        :param delay_seconds: Delay in seconds between submitting each task
        :param await_completion: Whether to wait for task completion
        :param print_updates: Whether to print status updates
        :return: List of task results if await_completion is True, otherwise None
        """
        if delay_seconds < 0:
            raise ValueError("Delay seconds must be non-negative")

        if len(tasks) == 0:
            return [] if await_completion else None

        if await_completion:
            # Run tasks with delay and wait for completion
            loop = self.safely_get_event_loop()
            results = loop.run_until_complete(
                self._execute_tasks_async_with_delay(tasks, max_workers, delay_seconds, print_updates)
            )

            if print_updates:
                print(f"Completed {len(results)} tasks with {delay_seconds}s delay between submissions")

            return results
        else:
            # Submit tasks with delay without waiting for completion
            asyncio.create_task(self._execute_tasks_async_with_delay(
                tasks, max_workers, delay_seconds, print_updates
            ))
            return None

    def _run_async_tasks(self, tasks, max_workers, print_updates):
        """
        Run tasks using asyncio and return results.

        This creates an event loop if needed and runs the tasks concurrently.
        """
        loop = self.safely_get_event_loop()
        # Run the tasks
        return loop.run_until_complete(
            self._execute_tasks_async(tasks, max_workers, print_updates)
        )

    async def _execute_tasks_async(self, tasks, max_workers, print_updates):
        """
        Execute tasks concurrently using asyncio.

        This limits concurrency using a semaphore and runs each task in
        a separate thread using run_in_executor.
        """
        semaphore = asyncio.Semaphore(max_workers)
        async_tasks = []

        # Create an async task for each input task
        for task in tasks:
            coro = self._run_task_with_semaphore(
                semaphore,
                task.function,
                task.args,
                task.kwargs,
                print_updates
            )
            async_tasks.append(asyncio.create_task(coro))

        # Run all tasks and gather results
        results = await asyncio.gather(*async_tasks, return_exceptions=True)

        # Filter out exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Task error: {result}")
                processed_results.append(result)
            else:
                processed_results.append(result)

        return processed_results

    async def _run_task_with_semaphore(self, semaphore, function, args, kwargs, print_updates):
        """
        Run a single task with semaphore control for concurrency limiting.
        """
        async with semaphore:
            if print_updates:
                print(f"Starting task {function.__name__}")

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,  # Use default executor
                self._run_function,
                function,
                args,
                kwargs
            )

            if print_updates:
                print(f"Completed task {function.__name__}")

            return result

    @staticmethod
    def _run_function(function, args, kwargs):
        """
        Run a function with the given args and kwargs.
        This isolates the function call to handle exceptions.
        """
        try:
            return function(*args, **kwargs)
        except Exception as e:
            print(f"Error in function {function.__name__}: {e}")
            raise  # Re-raise to be caught by asyncio.gather

    async def _execute_tasks_async_with_delay(self, tasks, max_workers, delay_seconds, print_updates):
        """
        Execute tasks concurrently using asyncio with a delay between task submissions.

        This limits concurrency using a semaphore and runs each task in
        a separate thread using run_in_executor, adding a delay between submissions.

        :param tasks: List of Task objects to execute
        :param max_workers: Maximum number of concurrent workers
        :param delay_seconds: Delay in seconds between task submissions
        :param print_updates: Whether to print status updates
        :return: List of task results
        """
        semaphore = asyncio.Semaphore(max_workers)
        async_tasks = []

        # Create an async task for each input task with delay
        for i, task in enumerate(tasks):
            # Add delay between task submissions (skip delay for the first task)
            if i > 0 and delay_seconds > 0:
                if print_updates:
                    print(f"Waiting {delay_seconds} seconds before submitting next task...")
                await asyncio.sleep(delay_seconds)

            coro = self._run_task_with_semaphore(
                semaphore,
                task.function,
                task.args,
                task.kwargs,
                print_updates
            )
            async_tasks.append(asyncio.create_task(coro))

        # Run all tasks and gather results
        results = await asyncio.gather(*async_tasks, return_exceptions=True)

        # Filter out exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Task error: {result}")
                processed_results.append(result)
            else:
                processed_results.append(result)

        return processed_results

    @staticmethod
    def safely_get_event_loop() -> asyncio.AbstractEventLoop:
        """
        Get the current event loop if it exists, or create a new one if needed.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

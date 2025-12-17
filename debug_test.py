#!/usr/bin/env python3
"""
debug_test.py - A utility for debugging and testing Python code.

This script provides a set of debugging and testing utilities to help developers
identify issues in their code. It includes functions for logging, timing, and
validating code behavior.
"""

import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

class DebugTest:
    """
    A class to provide debugging and testing utilities.
    """

    def __init__(self, name: str = "DebugTest"):
        """
        Initialize the DebugTest instance.

        Args:
            name (str): The name of the debug test instance.
        """
        self.name = name
        self.start_time = None
        self.end_time = None

    def log_info(self, message: str) -> None:
        """
        Log an informational message.

        Args:
            message (str): The message to log.
        """
        logger.info(f"{self.name}: {message}")

    def log_error(self, message: str) -> None:
        """
        Log an error message.

        Args:
            message (str): The message to log.
        """
        logger.error(f"{self.name}: {message}")

    def log_exception(self, message: str) -> None:
        """
        Log an exception with traceback.

        Args:
            message (str): The message to log.
        """
        logger.error(f"{self.name}: {message}", exc_info=True)

    def start_timer(self) -> None:
        """
        Start the timer for performance measurement.
        """
        self.start_time = time.time()
        self.log_info("Timer started.")

    def stop_timer(self) -> float:
        """
        Stop the timer and return the elapsed time.

        Returns:
            float: The elapsed time in seconds.
        """
        if self.start_time is None:
            self.log_error("Timer was not started.")
            return 0.0

        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time
        self.log_info(f"Timer stopped. Elapsed time: {elapsed_time:.4f} seconds.")
        return elapsed_time

    def time_function(
        self, func: Callable, *args: Any, **kwargs: Any
    ) -> Tuple[Any, float]:
        """
        Time the execution of a function.

        Args:
            func (Callable): The function to time.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Tuple[Any, float]: The result of the function and the elapsed time.
        """
        self.start_timer()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            self.log_exception(f"Function {func.__name__} raised an exception.")
            raise e
        finally:
            elapsed_time = self.stop_timer()
        return result, elapsed_time

    def validate_output(
        self,
        func: Callable,
        expected_output: Any,
        *args: Any,
        **kwargs: Any
    ) -> bool:
        """
        Validate the output of a function against expected output.

        Args:
            func (Callable): The function to validate.
            expected_output (Any): The expected output.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            bool: True if the output matches the expected output, False otherwise.
        """
        try:
            result = func(*args, **kwargs)
            if result == expected_output:
                self.log_info(
                    f"Function {func.__name__} output matches expected output."
                )
                return True
            else:
                self.log_error(
                    f"Function {func.__name__} output does not match expected output. "
                    f"Expected: {expected_output}, Got: {result}"
                )
                return False
        except Exception as e:
            self.log_exception(
                f"Function {func.__name__} raised an exception during validation."
            )
            return False

    def run_tests(
        self, test_cases: List[Dict[str, Union[Callable, Any, Tuple]]]
    ) -> Dict[str, Union[bool, str]]:
        """
        Run a series of test cases and return the results.

        Args:
            test_cases (List[Dict]): A list of test cases. Each test case should be a
                dictionary with the following keys:
                - 'func': The function to test.
                - 'args': A tuple of positional arguments to pass to the function.
                - 'kwargs': A dictionary of keyword arguments to pass to the function.
                - 'expected': The expected output of the function.

        Returns:
            Dict: A dictionary with the results of the tests. The keys are the function
                names, and the values are dictionaries with the following keys:
                - 'passed': Whether the test passed.
                - 'message': A message describing the result.
        """
        results = {}
        for test_case in test_cases:
            func = test_case['func']
            args = test_case.get('args', ())
            kwargs = test_case.get('kwargs', {})
            expected = test_case['expected']

            try:
                result = func(*args, **kwargs)
                if result == expected:
                    results[func.__name__] = {
                        'passed': True,
                        'message': 'Test passed.'
                    }
                    self.log_info(f"Test for {func.__name__} passed.")
                else:
                    results[func.__name__] = {
                        'passed': False,
                        'message': f"Expected {expected}, got {result}."
                    }
                    self.log_error(f"Test for {func.__name__} failed.")
            except Exception as e:
                results[func.__name__] = {
                    'passed': False,
                    'message': f"Exception raised: {str(e)}"
                }
                self.log_exception(f"Test for {func.__name__} raised an exception.")
        return results

def example_function(x: int, y: int) -> int:
    """
    An example function for demonstration purposes.

    Args:
        x (int): The first integer.
        y (int): The second integer.

    Returns:
        int: The sum of x and y.
    """
    return x + y

def example_function_with_error(x: int, y: int) -> int:
    """
    An example function that raises an error for demonstration purposes.

    Args:
        x (int): The first integer.
        y (int): The second integer.

    Returns:
        int: The sum of x and y.

    Raises:
        ValueError: If x or y is negative.
    """
    if x < 0 or y < 0:
        raise ValueError("x and y must be non-negative.")
    return x + y

def main():
    """
    The main function to demonstrate the usage of the DebugTest class.
    """
    debug_test = DebugTest("ExampleDebugTest")

    # Example 1: Timing a function
    debug_test.log_info("Example 1: Timing a function")
    result, elapsed_time = debug_test.time_function(example_function, 3, 5)
    debug_test.log_info(f"Result: {result}, Elapsed time: {elapsed_time:.4f} seconds")

    # Example 2: Validating output
    debug_test.log_info("Example 2: Validating output")
    is_valid = debug_test.validate_output(example_function, 8, 3, 5)
    debug_test.log_info(f"Validation result: {is_valid}")

    # Example 3: Running multiple tests
    debug_test.log_info("Example 3: Running multiple tests")
    test_cases = [
        {
            'func': example_function,
            'args': (3, 5),
            'expected': 8
        },
        {
            'func': example_function,
            'args': (0, 0),
            'expected': 0
        },
        {
            'func': example_function_with_error,
            'args': (3, 5),
            'expected': 8
        },
        {
            'func': example_function_with_error,
            'args': (-1, 5),
            'expected': 4
        }
    ]
    test_results = debug_test.run_tests(test_cases)
    debug_test.log_info("Test results:")
    for func_name, result in test_results.items():
        debug_test.log_info(f"{func_name}: {result['message']}")

if __name__ == "__main__":
    main()
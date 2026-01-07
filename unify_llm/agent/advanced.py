"""Advanced workflow features including parallel execution and error handling."""

from typing import Any, Dict, List, Optional
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from unify_llm.agent.workflow import WorkflowNode, NodeType
from unify_llm.agent.executor import ExecutionResult

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """Executes multiple agents in parallel.

    Example:
        ```python
        from unify_llm.agent.advanced import ParallelExecutor

        parallel = ParallelExecutor(max_workers=3)

        # Execute multiple agents concurrently
        results = parallel.execute_parallel(
            agents=[agent1, agent2, agent3],
            executors=[exec1, exec2, exec3],
            inputs=["task 1", "task 2", "task 3"]
        )
        ```
    """

    def __init__(self, max_workers: int = 5):
        """Initialize parallel executor.

        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers

    def execute_parallel(
        self,
        agents: List[Any],
        executors: List[Any],
        inputs: List[str],
        **kwargs
    ) -> List[ExecutionResult]:
        """Execute multiple agents in parallel.

        Args:
            agents: List of agents to execute
            executors: List of executors (one per agent)
            inputs: List of inputs (one per agent)
            **kwargs: Additional parameters for execution

        Returns:
            List of execution results
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_idx = {
                executor.submit(exec_obj.run, input_text, **kwargs): idx
                for idx, (exec_obj, input_text) in enumerate(zip(executors, inputs))
            }

            # Collect results as they complete
            result_dict = {}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    result_dict[idx] = result
                except Exception as e:
                    logger.error(f"Error executing agent {idx}: {e}")
                    result_dict[idx] = ExecutionResult(
                        success=False,
                        error=str(e),
                        iterations=0,
                        tool_calls=[]
                    )

            # Return results in original order
            results = [result_dict[i] for i in range(len(agents))]

        return results

    async def aexecute_parallel(
        self,
        agents: List[Any],
        executors: List[Any],
        inputs: List[str],
        **kwargs
    ) -> List[ExecutionResult]:
        """Execute multiple agents in parallel asynchronously.

        Args:
            agents: List of agents to execute
            executors: List of executors (one per agent)
            inputs: List of inputs (one per agent)
            **kwargs: Additional parameters for execution

        Returns:
            List of execution results
        """
        tasks = [
            exec_obj.arun(input_text, **kwargs)
            for exec_obj, input_text in zip(executors, inputs)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to ExecutionResult
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(ExecutionResult(
                    success=False,
                    error=str(result),
                    iterations=0,
                    tool_calls=[]
                ))
            else:
                processed_results.append(result)

        return processed_results


class ErrorHandler:
    """Handles errors and implements retry logic for agents.

    Example:
        ```python
        from unify_llm.agent.advanced import ErrorHandler

        handler = ErrorHandler(max_retries=3, backoff_factor=2.0)

        result = handler.execute_with_retry(
            executor=executor,
            user_input="Task input",
            on_error=lambda e: print(f"Error: {e}")
        )
        ```
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        retry_on_errors: Optional[List[str]] = None
    ):
        """Initialize error handler.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff factor
            retry_on_errors: List of error types to retry on
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on_errors = retry_on_errors or ["timeout", "rate_limit", "api_error"]

    def should_retry(self, error: str) -> bool:
        """Determine if an error should trigger a retry.

        Args:
            error: Error message

        Returns:
            True if should retry
        """
        error_lower = error.lower()
        return any(retry_error in error_lower for retry_error in self.retry_on_errors)

    def execute_with_retry(
        self,
        executor: Any,
        user_input: str,
        on_error: Optional[callable] = None,
        **kwargs
    ) -> ExecutionResult:
        """Execute agent with retry logic.

        Args:
            executor: Agent executor
            user_input: User input
            on_error: Callback function called on each error
            **kwargs: Additional parameters

        Returns:
            Execution result
        """
        import time

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = executor.run(user_input, **kwargs)

                if result.success:
                    return result

                # Check if we should retry on this error
                if not self.should_retry(result.error or ""):
                    return result

                last_error = result.error

                if on_error:
                    on_error(f"Attempt {attempt + 1} failed: {result.error}")

                # Wait before retry (exponential backoff)
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            except Exception as e:
                last_error = str(e)

                if on_error:
                    on_error(f"Attempt {attempt + 1} exception: {e}")

                if attempt < self.max_retries:
                    wait_time = self.backoff_factor ** attempt
                    time.sleep(wait_time)

        # All retries exhausted
        return ExecutionResult(
            success=False,
            error=f"Max retries exceeded. Last error: {last_error}",
            iterations=0,
            tool_calls=[]
        )


class AgentChain:
    """Chains multiple agents in sequence with data transformation.

    Example:
        ```python
        from unify_llm.agent.advanced import AgentChain

        chain = AgentChain()

        # Add agents to chain
        chain.add_agent(researcher, researcher_executor)
        chain.add_agent(analyst, analyst_executor,
                       transform=lambda prev: f"Analyze: {prev}")
        chain.add_agent(writer, writer_executor,
                       transform=lambda prev: f"Write about: {prev}")

        # Execute chain
        result = chain.execute("Research AI trends")
        ```
    """

    def __init__(self):
        """Initialize agent chain."""
        self._chain: List[Dict[str, Any]] = []

    def add_agent(
        self,
        agent: Any,
        executor: Any,
        transform: Optional[callable] = None,
        name: Optional[str] = None
    ) -> "AgentChain":
        """Add an agent to the chain.

        Args:
            agent: Agent to add
            executor: Agent executor
            transform: Optional function to transform previous output
            name: Optional name for this step

        Returns:
            Self for chaining
        """
        self._chain.append({
            "agent": agent,
            "executor": executor,
            "transform": transform,
            "name": name or f"step_{len(self._chain) + 1}"
        })
        return self

    def execute(self, initial_input: str, **kwargs) -> Dict[str, Any]:
        """Execute the agent chain.

        Args:
            initial_input: Initial input to the chain
            **kwargs: Additional parameters

        Returns:
            Dictionary with results from each step
        """
        results = {}
        current_input = initial_input

        for step in self._chain:
            agent = step["agent"]
            executor = step["executor"]
            transform = step["transform"]
            name = step["name"]

            logger.info(f"Executing chain step: {name}")

            # Apply transformation if provided
            if transform:
                current_input = transform(current_input)

            # Execute agent
            result = executor.run(current_input, **kwargs)

            results[name] = {
                "input": current_input,
                "result": result,
                "success": result.success
            }

            # If failed, stop chain
            if not result.success:
                logger.error(f"Chain failed at step {name}: {result.error}")
                break

            # Use output as input for next step
            current_input = result.output

        return {
            "success": all(r["success"] for r in results.values()),
            "final_output": current_input,
            "steps": results
        }

    async def aexecute(self, initial_input: str, **kwargs) -> Dict[str, Any]:
        """Execute the agent chain asynchronously.

        Args:
            initial_input: Initial input to the chain
            **kwargs: Additional parameters

        Returns:
            Dictionary with results from each step
        """
        results = {}
        current_input = initial_input

        for step in self._chain:
            agent = step["agent"]
            executor = step["executor"]
            transform = step["transform"]
            name = step["name"]

            logger.info(f"Executing chain step: {name}")

            # Apply transformation if provided
            if transform:
                current_input = transform(current_input)

            # Execute agent
            result = await executor.arun(current_input, **kwargs)

            results[name] = {
                "input": current_input,
                "result": result,
                "success": result.success
            }

            # If failed, stop chain
            if not result.success:
                logger.error(f"Chain failed at step {name}: {result.error}")
                break

            # Use output as input for next step
            current_input = result.output

        return {
            "success": all(r["success"] for r in results.values()),
            "final_output": current_input,
            "steps": results
        }

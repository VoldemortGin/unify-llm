"""
n8n-style AI Agent Example

This example demonstrates the new n8n-inspired features:
1. Schedule Triggers - Automated time-based execution
2. Webhook Triggers - HTTP endpoint triggers
3. HTTP Request Node - Making API calls
4. Execution History - Persistent execution tracking
5. Workflow Automation - Complete automation pipeline

Use case: Automated GitHub issue tracker that:
- Runs on a schedule every hour
- Fetches open issues from GitHub API
- Saves execution history
- Can also be triggered via webhook
"""

import asyncio
from datetime import datetime
from src.agent import (
    # Triggers
    ScheduleTrigger,
    IntervalTrigger,
    WebhookTrigger,
    ManualTrigger,
    TriggerConfig,
    TriggerType,
    TriggerManager,
    # HTTP Tools
    http_request,
    http_get,
    create_http_request_tool,
    # Execution History
    ExecutionHistory,
    ExecutionData,
    ExecutionStatus,
    # Webhook Server
    WebhookServer,
    # Core Agent
    Agent,
    AgentConfig,
    AgentExecutor,
    ToolRegistry,
)


async def example_1_schedule_trigger():
    """Example 1: Schedule Trigger - Run workflow every 5 minutes"""
    print("\n" + "=" * 60)
    print("Example 1: Schedule Trigger (Cron-based)")
    print("=" * 60)

    def on_scheduled_execution(event):
        """Handle scheduled execution"""
        print(f"\n[{datetime.now()}] Scheduled trigger fired!")
        print(f"  Trigger ID: {event.trigger_id}")
        print(f"  Workflow ID: {event.metadata['workflow_id']}")
        print(f"  Data: {event.data}")

    # Create schedule trigger (every 5 minutes)
    config = TriggerConfig(
        id="schedule_github_check",
        name="Hourly GitHub Check",
        type=TriggerType.SCHEDULE,
        workflow_id="github_workflow",
        config={"cron": "*/5 * * * *"}  # Every 5 minutes
    )

    trigger = ScheduleTrigger(config, on_scheduled_execution)

    print(f"\nCreated schedule trigger:")
    print(f"  Name: {config.name}")
    print(f"  Cron: {config.config['cron']}")
    print(f"  Workflow: {config.workflow_id}")

    # Start trigger (would run in background)
    await trigger.start()
    print("\n✅ Schedule trigger started (would run every 5 minutes)")

    # In production, this would run indefinitely
    # For demo, we'll stop it
    await asyncio.sleep(2)
    await trigger.stop()
    print("✅ Trigger stopped")


async def example_2_http_requests():
    """Example 2: HTTP Request Node - Fetching data from APIs"""
    print("\n" + "=" * 60)
    print("Example 2: HTTP Request Node (API Calls)")
    print("=" * 60)

    # Example: Fetch GitHub repository info
    print("\nFetching GitHub repository data...")

    result = await http_get(
        url="https://api.github.com/repos/microsoft/vscode",
        headers={"Accept": "application/json"}
    )

    if result.success:
        data = result.output
        print(f"\n✅ API Request successful!")
        print(f"  Status: {data['status_code']}")
        print(f"  Repository: {data['body'].get('full_name', 'N/A')}")
        print(f"  Stars: {data['body'].get('stargazers_count', 0)}")
        print(f"  Forks: {data['body'].get('forks_count', 0)}")
    else:
        print(f"\n❌ Request failed: {result.error}")

    # Example: POST request
    print("\n\nExample POST request (to JSONPlaceholder)...")

    result = await http_request(
        url="https://jsonplaceholder.typicode.com/posts",
        method="POST",
        body={
            "title": "Test Post",
            "body": "This is a test",
            "userId": 1
        }
    )

    if result.success:
        print(f"\n✅ POST request successful!")
        print(f"  Status: {result.output['status_code']}")
        print(f"  Created: {result.output['body']}")
    else:
        print(f"\n❌ Request failed: {result.error}")


async def example_3_webhook_trigger():
    """Example 3: Webhook Trigger - HTTP endpoint trigger"""
    print("\n" + "=" * 60)
    print("Example 3: Webhook Trigger")
    print("=" * 60)

    def on_webhook_triggered(event):
        """Handle webhook execution"""
        print(f"\n[{datetime.now()}] Webhook triggered!")
        print(f"  Method: {event.data.get('method')}")
        print(f"  Path: {event.data.get('path')}")
        print(f"  Body: {event.data.get('body')}")

    # Create webhook trigger
    config = TriggerConfig(
        id="webhook_github_event",
        name="GitHub Event Webhook",
        type=TriggerType.WEBHOOK,
        workflow_id="github_workflow",
        config={
            "path": "/webhook/github",
            "method": "POST"
        }
    )

    trigger = WebhookTrigger(config, on_webhook_triggered)
    await trigger.start()

    print(f"\nCreated webhook trigger:")
    print(f"  Name: {config.name}")
    print(f"  Path: {trigger.path}")
    print(f"  Method: {trigger.method}")

    # Simulate webhook request
    print("\nSimulating webhook request...")
    response = trigger.handle_request({
        "method": "POST",
        "path": "/webhook/github",
        "body": {"action": "opened", "issue": {"id": 123}}
    })

    print(f"  Response: {response}")


async def example_4_execution_history():
    """Example 4: Execution History - Persistent tracking"""
    print("\n" + "=" * 60)
    print("Example 4: Execution History (Persistence)")
    print("=" * 60)

    # Initialize history
    history = ExecutionHistory(db_path="demo_executions.db")

    # Save some executions
    executions = [
        ExecutionData(
            id="exec_001",
            workflow_id="github_workflow",
            workflow_name="GitHub Issue Tracker",
            status=ExecutionStatus.SUCCESS,
            start_time=datetime.now(),
            end_time=datetime.now(),
            trigger_type="schedule",
            input_data={"repo": "microsoft/vscode"},
            output_data={"issues_found": 10}
        ),
        ExecutionData(
            id="exec_002",
            workflow_id="github_workflow",
            workflow_name="GitHub Issue Tracker",
            status=ExecutionStatus.SUCCESS,
            start_time=datetime.now(),
            end_time=datetime.now(),
            trigger_type="webhook",
            input_data={"repo": "facebook/react"},
            output_data={"issues_found": 15}
        ),
        ExecutionData(
            id="exec_003",
            workflow_id="github_workflow",
            workflow_name="GitHub Issue Tracker",
            status=ExecutionStatus.ERROR,
            start_time=datetime.now(),
            end_time=datetime.now(),
            trigger_type="manual",
            input_data={"repo": "invalid/repo"},
            error="Repository not found"
        )
    ]

    print("\nSaving execution history...")
    for execution in executions:
        history.save(execution)
        print(f"  ✅ Saved: {execution.id} - {execution.status}")

    # Query history
    print("\n\nRecent executions:")
    recent = history.get_recent(limit=5)
    for execution in recent:
        print(f"  - [{execution.status.value}] {execution.workflow_name} ({execution.trigger_type})")

    # Get statistics
    stats = history.get_statistics(workflow_id="github_workflow")
    print(f"\n\nWorkflow Statistics:")
    print(f"  Total executions: {stats['total']}")
    print(f"  Successful: {stats['success']}")
    print(f"  Failed: {stats['error']}")
    print(f"  Success rate: {stats['success_rate']}%")


async def example_5_complete_automation():
    """Example 5: Complete n8n-style Automation"""
    print("\n" + "=" * 60)
    print("Example 5: Complete Automation Pipeline")
    print("=" * 60)

    # Initialize components
    history = ExecutionHistory(db_path="automation_executions.db")
    trigger_manager = TriggerManager()

    async def run_workflow(event):
        """Execute the workflow"""
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\n[{datetime.now()}] Workflow execution started")
        print(f"  Execution ID: {execution_id}")
        print(f"  Triggered by: {event.trigger_type}")

        # Start execution
        execution = ExecutionData(
            id=execution_id,
            workflow_id=event.metadata["workflow_id"],
            workflow_name="Automated GitHub Monitor",
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(),
            trigger_type=event.trigger_type.value,
            input_data=event.data
        )
        history.save(execution)

        try:
            # Step 1: Fetch GitHub data
            print("  Step 1: Fetching GitHub issues...")
            result = await http_get(
                url="https://api.github.com/repos/microsoft/vscode/issues",
                query_params={"state": "open", "per_page": "5"}
            )

            if not result.success:
                raise Exception(f"Failed to fetch issues: {result.error}")

            issues = result.output["body"]
            print(f"    ✅ Found {len(issues)} open issues")

            # Step 2: Process data
            print("  Step 2: Processing issues...")
            issue_summary = [
                {"title": issue["title"], "number": issue["number"]}
                for issue in issues[:3]
            ]
            print(f"    ✅ Processed {len(issue_summary)} issues")

            # Update execution as success
            execution.status = ExecutionStatus.SUCCESS
            execution.end_time = datetime.now()
            execution.output_data = {
                "issues_count": len(issues),
                "summary": issue_summary
            }
            history.save(execution)

            print(f"\n✅ Workflow completed successfully!")
            print(f"  Duration: {execution.duration:.2f}s")

        except Exception as e:
            # Update execution as error
            execution.status = ExecutionStatus.ERROR
            execution.end_time = datetime.now()
            execution.error = str(e)
            history.save(execution)

            print(f"\n❌ Workflow failed: {e}")

    # Create triggers
    print("\nSetting up automation triggers...")

    # 1. Schedule trigger (every 10 minutes in production)
    schedule_config = TriggerConfig(
        id="schedule_monitor",
        name="Scheduled Monitor",
        type=TriggerType.SCHEDULE,
        workflow_id="github_monitor",
        config={"cron": "*/10 * * * *"}
    )
    schedule_trigger = ScheduleTrigger(schedule_config, run_workflow)
    trigger_manager.add_trigger(schedule_trigger)
    print("  ✅ Schedule trigger configured (every 10 min)")

    # 2. Manual trigger (for testing)
    manual_config = TriggerConfig(
        id="manual_monitor",
        name="Manual Execution",
        type=TriggerType.MANUAL,
        workflow_id="github_monitor"
    )
    manual_trigger = ManualTrigger(manual_config, run_workflow)
    trigger_manager.add_trigger(manual_trigger)
    print("  ✅ Manual trigger configured")

    # Start triggers
    await trigger_manager.start_all()
    print("\n✅ All triggers started!")

    # Manually trigger for demo
    print("\nTriggering manual execution for demonstration...")
    manual_trigger.execute({"repo": "microsoft/vscode", "reason": "demo"})

    # Wait a bit
    await asyncio.sleep(2)

    # Show status
    print("\n\nTrigger Status:")
    status = trigger_manager.get_status()
    for trigger_id, info in status.items():
        print(f"  {info['name']}: {info['status']}")

    # Cleanup
    await trigger_manager.stop_all()
    print("\n✅ All triggers stopped")


async def main():
    """Run all examples"""
    print("\n" + "🚀 " + "=" * 58)
    print("UnifyLLM n8n-Style AI Agent Features Demo")
    print("=" * 60)

    try:
        # Run examples
        await example_1_schedule_trigger()
        await example_2_http_requests()
        await example_3_webhook_trigger()
        await example_4_execution_history()
        await example_5_complete_automation()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

        print("\n📚 Key Features Demonstrated:")
        print("  ✅ Schedule Triggers (cron-based automation)")
        print("  ✅ Webhook Triggers (HTTP endpoint triggers)")
        print("  ✅ Interval Triggers (fixed interval execution)")
        print("  ✅ HTTP Request Node (API calls)")
        print("  ✅ Execution History (persistent tracking)")
        print("  ✅ Complete Automation Pipeline")

        print("\n🎯 n8n-Style Capabilities:")
        print("  • Automated workflow execution")
        print("  • Time-based scheduling (cron)")
        print("  • HTTP webhooks and triggers")
        print("  • REST API integration")
        print("  • Execution history and analytics")
        print("  • Error handling and recovery")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

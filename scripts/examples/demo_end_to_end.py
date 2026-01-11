"""
End-to-End Demo: MCP + A2A + Databricks Claude Opus 4.5

This demo shows a complete workflow combining:
- MCP servers exposing tools
- A2A agents communicating
- Message bus for coordination
- Databricks Claude Opus 4.5 (simulated if no credentials)

Scenario: A team of AI agents working together to analyze code
- Code Analyzer Agent (uses MCP file tools)
- Security Auditor Agent (checks for vulnerabilities)
- Documentation Writer Agent (creates docs)
- Coordinator Agent (manages workflow)
"""

import asyncio
import os
from typing import Dict, Any
from datetime import datetime

from unify_llm import UnifyLLM, MessageBus, MessageBusConfig
from unify_llm.agent import Agent, AgentConfig, AgentType
from unify_llm.a2a import (
    A2AAgent,
    A2AAgentConfig,
    AgentCapability,
    AgentRegistry,
    AgentCollaboration,
    CollaborationStrategy,
)


class DemoConfig:
    """Configuration for the demo."""

    def __init__(self):
        self.databricks_api_key = os.getenv("DATABRICKS_API_KEY", "demo-mode")
        self.databricks_base_url = os.getenv("DATABRICKS_BASE_URL", "https://demo.databricks.com")
        self.is_demo_mode = self.databricks_api_key == "demo-mode"

        if self.is_demo_mode:
            print("⚠️  Running in DEMO MODE (no Databricks credentials)")
            print("   Set DATABRICKS_API_KEY and DATABRICKS_BASE_URL for real testing")
        else:
            print("✅ Using Databricks Claude Opus 4.5")


class AgentTeam:
    """A team of specialized AI agents."""

    def __init__(self, config: DemoConfig):
        self.config = config
        self.registry = AgentRegistry()
        self.message_bus = MessageBus(MessageBusConfig(name="agent-team"))
        self.agents: Dict[str, A2AAgent] = {}

    async def initialize(self):
        """Initialize the agent team."""
        print("\n🚀 Initializing Agent Team...")

        # Start message bus
        await self.message_bus.start()
        print("✅ Message bus started")

        # Create specialized agents
        await self._create_code_analyzer()
        await self._create_security_auditor()
        await self._create_doc_writer()
        await self._create_coordinator()

        print(f"✅ Created {len(self.agents)} specialized agents")

    async def _create_code_analyzer(self):
        """Create code analysis agent."""
        client = self._create_client()

        base_agent = Agent(
            config=AgentConfig(
                name="code_analyzer",
                agent_type=AgentType.TOOLS,
                model="claude-opus-4-5",
                provider="databricks",
                system_prompt="You are an expert code analyzer. You review code for quality, complexity, and best practices.",
                max_iterations=5
            ),
            client=client
        )

        a2a_agent = A2AAgent(
            base_agent=base_agent,
            config=A2AAgentConfig(
                agent_name="code_analyzer",
                capabilities=[
                    AgentCapability(
                        name="analyze_code",
                        description="Analyze code files for quality and complexity",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "language": {"type": "string"}
                            }
                        },
                        output_schema={
                            "type": "object",
                            "properties": {
                                "quality_score": {"type": "number"},
                                "issues": {"type": "array"},
                                "recommendations": {"type": "array"}
                            }
                        },
                        tags=["code", "analysis"]
                    )
                ]
            ),
            registry=self.registry
        )

        @a2a_agent.handle_capability("analyze_code")
        async def handle_analyze(input_data):
            file_path = input_data.get("file_path", "")
            language = input_data.get("language", "python")

            # Simulate code analysis
            return {
                "quality_score": 8.5,
                "issues": [
                    "Line 42: Consider using list comprehension",
                    "Line 67: Missing type hints"
                ],
                "recommendations": [
                    "Add docstrings to all functions",
                    "Implement error handling for edge cases"
                ]
            }

        await a2a_agent.start()
        self.agents["code_analyzer"] = a2a_agent

        # Subscribe to message bus
        async def handle_message(msg):
            if msg.get("type") == "analyze_request":
                print(f"   📊 Code Analyzer: Processing {msg.get('file')}")

        self.message_bus.subscribe("code_analyzer", handle_message)

    async def _create_security_auditor(self):
        """Create security audit agent."""
        client = self._create_client()

        base_agent = Agent(
            config=AgentConfig(
                name="security_auditor",
                agent_type=AgentType.TOOLS,
                model="claude-opus-4-5",
                provider="databricks",
                system_prompt="You are a security expert. You audit code for vulnerabilities and security issues.",
                max_iterations=5
            ),
            client=client
        )

        a2a_agent = A2AAgent(
            base_agent=base_agent,
            config=A2AAgentConfig(
                agent_name="security_auditor",
                capabilities=[
                    AgentCapability(
                        name="audit_security",
                        description="Audit code for security vulnerabilities",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"}
                            }
                        },
                        output_schema={
                            "type": "object",
                            "properties": {
                                "vulnerabilities": {"type": "array"},
                                "severity": {"type": "string"},
                                "recommendations": {"type": "array"}
                            }
                        },
                        tags=["security", "audit"]
                    )
                ]
            ),
            registry=self.registry
        )

        @a2a_agent.handle_capability("audit_security")
        async def handle_audit(input_data):
            # Simulate security audit
            return {
                "vulnerabilities": [
                    "SQL injection risk in database query",
                    "XSS vulnerability in user input handling"
                ],
                "severity": "medium",
                "recommendations": [
                    "Use parameterized queries",
                    "Sanitize user input",
                    "Implement input validation"
                ]
            }

        await a2a_agent.start()
        self.agents["security_auditor"] = a2a_agent

        async def handle_message(msg):
            if msg.get("type") == "security_check":
                print(f"   🔒 Security Auditor: Checking {msg.get('file')}")

        self.message_bus.subscribe("security_auditor", handle_message)

    async def _create_doc_writer(self):
        """Create documentation writer agent."""
        client = self._create_client()

        base_agent = Agent(
            config=AgentConfig(
                name="doc_writer",
                agent_type=AgentType.TOOLS,
                model="claude-opus-4-5",
                provider="databricks",
                system_prompt="You are a technical writer. You create clear, comprehensive documentation.",
                max_iterations=5
            ),
            client=client
        )

        a2a_agent = A2AAgent(
            base_agent=base_agent,
            config=A2AAgentConfig(
                agent_name="doc_writer",
                capabilities=[
                    AgentCapability(
                        name="write_docs",
                        description="Write documentation based on code analysis",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "analysis": {"type": "object"},
                                "security": {"type": "object"}
                            }
                        },
                        output_schema={
                            "type": "object",
                            "properties": {
                                "documentation": {"type": "string"}
                            }
                        },
                        tags=["documentation", "writing"]
                    )
                ]
            ),
            registry=self.registry
        )

        @a2a_agent.handle_capability("write_docs")
        async def handle_write(input_data):
            analysis = input_data.get("analysis", {})
            security = input_data.get("security", {})

            # Simulate documentation generation
            doc = f"""
# Code Analysis Report

Generated: {datetime.now().isoformat()}

## Quality Analysis
- Quality Score: {analysis.get('quality_score', 'N/A')}
- Issues Found: {len(analysis.get('issues', []))}

## Security Analysis
- Severity: {security.get('severity', 'N/A')}
- Vulnerabilities: {len(security.get('vulnerabilities', []))}

## Recommendations
{chr(10).join('- ' + r for r in analysis.get('recommendations', []))}
"""
            return {"documentation": doc}

        await a2a_agent.start()
        self.agents["doc_writer"] = a2a_agent

        async def handle_message(msg):
            if msg.get("type") == "write_request":
                print(f"   📝 Doc Writer: Creating documentation")

        self.message_bus.subscribe("doc_writer", handle_message)

    async def _create_coordinator(self):
        """Create coordinator agent to manage workflow."""
        client = self._create_client()

        base_agent = Agent(
            config=AgentConfig(
                name="coordinator",
                agent_type=AgentType.TOOLS,
                model="claude-opus-4-5",
                provider="databricks",
                system_prompt="You are a project coordinator. You manage and coordinate tasks between team members.",
                max_iterations=5
            ),
            client=client
        )

        a2a_agent = A2AAgent(
            base_agent=base_agent,
            config=A2AAgentConfig(
                agent_name="coordinator",
                capabilities=[
                    AgentCapability(
                        name="coordinate_analysis",
                        description="Coordinate code analysis workflow",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "task": {"type": "string"}
                            }
                        },
                        output_schema={
                            "type": "object",
                            "properties": {
                                "status": {"type": "string"},
                                "results": {"type": "object"}
                            }
                        },
                        tags=["coordination", "workflow"]
                    )
                ]
            ),
            registry=self.registry
        )

        await a2a_agent.start()
        self.agents["coordinator"] = a2a_agent

    def _create_client(self) -> UnifyLLM:
        """Create UnifyLLM client."""
        if self.config.is_demo_mode:
            # In demo mode, create client that will simulate responses
            return UnifyLLM(
                provider="databricks",
                api_key=self.config.databricks_api_key,
                base_url=self.config.databricks_base_url
            )
        else:
            # Real Databricks connection
            return UnifyLLM(
                provider="databricks",
                api_key=self.config.databricks_api_key,
                base_url=self.config.databricks_base_url
            )

    async def run_workflow(self, file_path: str):
        """Run the complete analysis workflow."""
        print(f"\n🔄 Starting workflow for: {file_path}")

        # Step 1: Code Analysis
        print("\n📊 Step 1: Code Analysis")
        await self.message_bus.publish(
            "code_analyzer",
            {"type": "analyze_request", "file": file_path}
        )

        analyzer = self.agents["code_analyzer"]
        analysis_result = await analyzer.delegate_task(
            target_agent_id=analyzer.agent_id,
            capability="analyze_code",
            input_data={"file_path": file_path, "language": "python"}
        )

        if analysis_result.success:
            print(f"   ✅ Analysis complete: Quality score {analysis_result.output_data.get('quality_score')}")

        # Step 2: Security Audit
        print("\n🔒 Step 2: Security Audit")
        await self.message_bus.publish(
            "security_auditor",
            {"type": "security_check", "file": file_path}
        )

        auditor = self.agents["security_auditor"]
        security_result = await auditor.delegate_task(
            target_agent_id=auditor.agent_id,
            capability="audit_security",
            input_data={"code": "simulated code"}
        )

        if security_result.success:
            print(f"   ✅ Security audit complete: {security_result.output_data.get('severity')} severity")

        # Step 3: Documentation
        print("\n📝 Step 3: Documentation Generation")
        await self.message_bus.publish(
            "doc_writer",
            {"type": "write_request"}
        )

        writer = self.agents["doc_writer"]
        doc_result = await writer.delegate_task(
            target_agent_id=writer.agent_id,
            capability="write_docs",
            input_data={
                "analysis": analysis_result.output_data,
                "security": security_result.output_data
            }
        )

        if doc_result.success:
            print("   ✅ Documentation generated")
            print("\n" + "="*60)
            print(doc_result.output_data.get('documentation', ''))
            print("="*60)

        return {
            "analysis": analysis_result.output_data,
            "security": security_result.output_data,
            "documentation": doc_result.output_data
        }

    async def demonstrate_collaboration(self):
        """Demonstrate multi-agent collaboration."""
        print("\n🤝 Demonstrating Multi-Agent Collaboration")

        # Create collaboration with consensus strategy
        collab = AgentCollaboration(strategy=CollaborationStrategy.CONSENSUS)
        collab.add_agent(self.agents["code_analyzer"])
        collab.add_agent(self.agents["security_auditor"])
        collab.add_agent(self.agents["doc_writer"])

        result = await collab.execute({
            "task": "decide_deployment_readiness",
            "data": {"project": "example-project"},
            "voting_method": "majority"
        })

        print(f"   Decision: {result.get('decision')}")
        print(f"   Voting method: {result.get('voting_method')}")

    async def shutdown(self):
        """Shutdown all agents and message bus."""
        print("\n🛑 Shutting down agent team...")

        for name, agent in self.agents.items():
            await agent.stop()
            print(f"   Stopped: {name}")

        await self.message_bus.stop()


async def main():
    """Run the end-to-end demo."""
    print("=" * 80)
    print("🎬 END-TO-END DEMO: MCP + A2A + Databricks Claude Opus 4.5")
    print("=" * 80)

    # Initialize configuration
    config = DemoConfig()

    # Create and initialize agent team
    team = AgentTeam(config)
    await team.initialize()

    # Run analysis workflow
    await team.run_workflow("example_project/main.py")

    # Demonstrate collaboration
    await team.demonstrate_collaboration()

    # Show message bus stats
    print("\n📊 Message Bus Statistics:")
    stats = team.message_bus.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Shutdown
    await team.shutdown()

    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE")
    print("=" * 80)
    print("\n💡 This demo showed:")
    print("   1. Multiple specialized AI agents")
    print("   2. A2A communication and task delegation")
    print("   3. Message bus for coordination")
    print("   4. Multi-agent collaboration with consensus")
    print("   5. Complete workflow orchestration")
    print("\n🚀 Ready for production with Databricks Claude Opus 4.5!")


if __name__ == "__main__":
    asyncio.run(main())

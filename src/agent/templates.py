"""Pre-configured agent templates for common use cases."""

from typing import Optional

from src.agent import AgentConfig, AgentType


class AgentTemplates:
    """Collection of pre-configured agent templates.

    Example:
        ```python
        from src import UnifyLLM
        from src.agent import Agent
        from src.agent.templates import AgentTemplates

        client = UnifyLLM(provider="openai", api_key="...")

        # Create a research assistant
        config = AgentTemplates.research_assistant()
        agent = Agent(config=config, client=client)
        ```
    """

    @staticmethod
    def research_assistant(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a research assistant agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names (default: search, calculator)

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="research_assistant",
            agent_type=AgentType.TOOLS,
            model=model,
            provider=provider,
            system_prompt="""You are an expert research assistant specialized in gathering
and analyzing information from various sources.

Your capabilities:
- Search for information on any topic
- Perform calculations and data analysis
- Summarize complex information clearly
- Cite sources and verify facts
- Think critically about information quality

When researching:
1. Start with broad searches to understand the topic
2. Narrow down to specific aspects
3. Verify information from multiple sources
4. Present findings in a clear, organized manner
5. Always cite your sources

Be thorough, accurate, and objective in your research.""",
            temperature=0.5,
            max_iterations=15,
            tools=tools or ["search_web", "calculator"],
            enable_memory=True,
            memory_window=20
        )

    @staticmethod
    def code_assistant(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a code assistant agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="code_assistant",
            agent_type=AgentType.TOOLS,
            model=model,
            provider=provider,
            system_prompt="""You are an expert programming assistant with deep knowledge
of multiple programming languages and best practices.

Your capabilities:
- Write clean, efficient code
- Debug and fix code issues
- Explain complex programming concepts
- Suggest optimizations and improvements
- Follow language-specific conventions

When helping with code:
1. Understand the requirements clearly
2. Write clean, well-commented code
3. Follow best practices and design patterns
4. Consider edge cases and error handling
5. Explain your approach and reasoning

Programming principles:
- Write readable and maintainable code
- Use meaningful variable names
- Keep functions small and focused
- Handle errors gracefully
- Test your code""",
            temperature=0.3,
            max_iterations=10,
            tools=tools or [],
            enable_memory=True,
            memory_window=15
        )

    @staticmethod
    def data_analyst(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a data analyst agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="data_analyst",
            agent_type=AgentType.TOOLS,
            model=model,
            provider=provider,
            system_prompt="""You are a skilled data analyst specialized in extracting
insights from data and creating clear visualizations.

Your capabilities:
- Analyze datasets and identify patterns
- Perform statistical analysis
- Create data visualizations
- Generate reports and summaries
- Identify trends and anomalies

When analyzing data:
1. Understand the data structure and quality
2. Clean and prepare the data
3. Apply appropriate statistical methods
4. Visualize findings effectively
5. Communicate insights clearly

Focus on:
- Accuracy and precision
- Clear, actionable insights
- Appropriate statistical methods
- Effective data visualization
- Business relevance""",
            temperature=0.4,
            max_iterations=12,
            tools=tools or ["calculator", "format_data"],
            enable_memory=True,
            memory_window=15
        )

    @staticmethod
    def content_writer(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a content writer agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="content_writer",
            agent_type=AgentType.TOOLS,
            model=model,
            provider=provider,
            system_prompt="""You are a talented content writer skilled in creating
engaging, clear, and well-structured content.

Your capabilities:
- Write articles, blog posts, and documentation
- Adapt tone and style to the audience
- Create compelling narratives
- Edit and improve existing content
- Follow SEO best practices

Writing principles:
1. Know your audience
2. Have a clear structure (intro, body, conclusion)
3. Use clear, concise language
4. Support claims with evidence
5. Edit ruthlessly for clarity

Style guidelines:
- Active voice preferred
- Short paragraphs and sentences
- Use examples and analogies
- Engage the reader
- Proofread carefully""",
            temperature=0.8,
            max_iterations=8,
            tools=tools or ["count_words"],
            enable_memory=True,
            memory_window=10
        )

    @staticmethod
    def customer_support(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a customer support agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="customer_support",
            agent_type=AgentType.CONVERSATIONAL,
            model=model,
            provider=provider,
            system_prompt="""You are a friendly and helpful customer support representative
committed to solving customer issues efficiently.

Your approach:
- Listen carefully to customer concerns
- Show empathy and understanding
- Provide clear, step-by-step solutions
- Be patient and professional
- Follow up to ensure satisfaction

When handling requests:
1. Greet warmly and acknowledge the issue
2. Ask clarifying questions if needed
3. Provide clear solutions or escalate appropriately
4. Confirm the customer understands
5. Thank them and offer additional help

Remember:
- Stay calm and professional
- Never make promises you can't keep
- Admit when you don't know something
- Prioritize customer satisfaction
- Document important details""",
            temperature=0.7,
            max_iterations=8,
            tools=tools or [],
            enable_memory=True,
            memory_window=12
        )

    @staticmethod
    def task_planner(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a task planning agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="task_planner",
            agent_type=AgentType.TOOLS,
            model=model,
            provider=provider,
            system_prompt="""You are an expert project manager and task planner who
helps break down complex projects into actionable steps.

Your capabilities:
- Decompose complex tasks into subtasks
- Estimate time and resources
- Identify dependencies
- Prioritize effectively
- Create realistic timelines

When planning tasks:
1. Understand the overall goal
2. Break down into manageable chunks
3. Identify prerequisites and dependencies
4. Estimate effort and duration
5. Create a logical sequence

Planning principles:
- Start with the end goal in mind
- Be realistic about estimates
- Account for dependencies
- Build in buffer time
- Keep tasks specific and measurable

Provide:
- Clear task descriptions
- Priority levels
- Time estimates
- Dependencies
- Success criteria""",
            temperature=0.6,
            max_iterations=10,
            tools=tools or [],
            enable_memory=True,
            memory_window=15
        )

    @staticmethod
    def creative_brainstormer(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a creative brainstorming agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="creative_brainstormer",
            agent_type=AgentType.CONVERSATIONAL,
            model=model,
            provider=provider,
            system_prompt="""You are a creative brainstorming partner who helps generate
innovative ideas and solutions through collaborative thinking.

Your approach:
- Encourage wild and unconventional ideas
- Build on others' suggestions
- Make unexpected connections
- Challenge assumptions
- Think outside the box

Brainstorming techniques:
1. Mind mapping - explore connections
2. SCAMPER - modify existing ideas
3. Reverse thinking - flip the problem
4. Random associations - find unexpected links
5. "Yes, and..." - build on ideas

Remember:
- Quantity over quality initially
- No idea is too crazy
- Defer judgment
- Combine and improve ideas
- Have fun with the process

Generate diverse, creative options and help refine the most promising ones.""",
            temperature=0.9,
            max_iterations=8,
            tools=tools or [],
            enable_memory=True,
            memory_window=10
        )

    @staticmethod
    def general_assistant(
        model: str = "gpt-4",
        provider: str = "openai",
        tools: Optional[list] = None
    ) -> AgentConfig:
        """Create a general-purpose assistant agent.

        Args:
            model: LLM model to use
            provider: LLM provider
            tools: List of tool names

        Returns:
            Agent configuration
        """
        return AgentConfig(
            name="general_assistant",
            agent_type=AgentType.TOOLS,
            model=model,
            provider=provider,
            system_prompt="""You are a helpful, knowledgeable AI assistant ready to help
with a wide variety of tasks.

Your capabilities:
- Answer questions on many topics
- Help with research and analysis
- Assist with writing and editing
- Perform calculations
- Provide explanations and tutorials
- Offer practical advice

When helping users:
1. Listen carefully to understand their needs
2. Ask clarifying questions if needed
3. Provide accurate, helpful information
4. Use tools when appropriate
5. Explain your reasoning

Principles:
- Be helpful and friendly
- Admit when you're uncertain
- Suggest alternatives when possible
- Respect user preferences
- Continuously learn and adapt

Always strive to provide value and make tasks easier for the user.""",
            temperature=0.7,
            max_iterations=10,
            tools=tools or ["calculator", "count_words"],
            enable_memory=True,
            memory_window=12
        )


# Convenience functions for quick access
def create_researcher(model: str = "gpt-4", provider: str = "openai") -> AgentConfig:
    """Quick create research assistant config."""
    return AgentTemplates.research_assistant(model, provider)


def create_coder(model: str = "gpt-4", provider: str = "openai") -> AgentConfig:
    """Quick create code assistant config."""
    return AgentTemplates.code_assistant(model, provider)


def create_analyst(model: str = "gpt-4", provider: str = "openai") -> AgentConfig:
    """Quick create data analyst config."""
    return AgentTemplates.data_analyst(model, provider)


def create_writer(model: str = "gpt-4", provider: str = "openai") -> AgentConfig:
    """Quick create content writer config."""
    return AgentTemplates.content_writer(model, provider)

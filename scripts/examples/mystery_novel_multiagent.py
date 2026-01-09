#!/usr/bin/env python3
"""
悬疑小说多Agent写作系统

这个示例展示了如何使用Databricks模型和A2A协议构建一个多Agent协作系统来写悬疑小说。

Agent角色:
1. FrameworkArchitect (框架设计者): 提出小说框架
2. CriticAgent (评论者): 与框架设计者讨论框架合理性
3. WriterAgent (写作者): 按照框架写小说

协作流程:
1. FrameworkArchitect 提出初始框架
2. CriticAgent 评估框架并提出改进建议
3. 两者讨论直到达成共识
4. WriterAgent 按照框架逐章写作
5. FrameworkArchitect 和 CriticAgent 共同评判每章节

使用的技术:
- A2A协议: Agent之间的任务委托和协作
- ToolRegistry: 直接定义Agent工具
"""

import os
import asyncio
import json
import re
from datetime import datetime

import rootutils

ROOT_DIR = rootutils.setup_root(os.getcwd(), indicator=".project-root", pythonpath=True)

from src.client import UnifyLLM
from src.core.config import settings
from src.agent.base import Agent, AgentConfig, AgentType
from src.agent.executor import AgentExecutor
from src.agent.memory import ConversationMemory, SharedMemory
from src.agent.tools import Tool, ToolParameter, ToolParameterType, ToolRegistry, ToolResult
from src.a2a.protocol import AgentCapability
from src.a2a.agent_comm import A2AAgent, A2AAgentConfig, AgentRegistry
from src.a2a.message_bus import MessageBus, MessageBusConfig


# ============================================================================
# 小说存储类
# ============================================================================


class NovelStorage:
    """小说内容存储"""

    def __init__(self):
        self.title: str = ""
        self.genre: str = "悬疑"
        self.framework: dict = {}
        self.chapters: list[dict] = []
        self.reviews: list[dict] = []
        self.created_at: datetime = datetime.now()

    def set_framework(self, framework: dict) -> None:
        """设置小说框架"""
        self.framework = framework
        self.title = framework.get("title", "未命名悬疑小说")

    def add_chapter(self, chapter_num: int, title: str, content: str) -> None:
        """添加章节"""
        self.chapters.append(
            {
                "chapter_num": chapter_num,
                "title": title,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "reviews": [],
            }
        )

    def add_review(self, chapter_num: int, reviewer: str, score: int, feedback: str) -> None:
        """添加章节评论"""
        for chapter in self.chapters:
            if chapter["chapter_num"] == chapter_num:
                chapter["reviews"].append(
                    {
                        "reviewer": reviewer,
                        "score": score,
                        "feedback": feedback,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                break

    def get_progress(self) -> dict:
        """获取写作进度"""
        total_chapters = self.framework.get("total_chapters", 0)
        completed_chapters = len(self.chapters)
        return {
            "title": self.title,
            "total_chapters": total_chapters,
            "completed_chapters": completed_chapters,
            "progress_percentage": (
                (completed_chapters / total_chapters * 100) if total_chapters > 0 else 0
            ),
            "average_score": self._calculate_average_score(),
        }

    def _calculate_average_score(self) -> float:
        """计算平均评分"""
        all_scores = []
        for chapter in self.chapters:
            for review in chapter.get("reviews", []):
                all_scores.append(review["score"])
        return sum(all_scores) / len(all_scores) if all_scores else 0.0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "title": self.title,
            "genre": self.genre,
            "framework": self.framework,
            "chapters": self.chapters,
            "progress": self.get_progress(),
        }

    def save_to_file(self, output_dir: str = "output/novels") -> str:
        """保存小说到文件"""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        safe_title = re.sub(r'[\\/*?:"<>|]', "", self.title) or "untitled"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存JSON格式
        json_file = output_path / f"{safe_title}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

        # 保存Markdown格式
        md_file = output_path / f"{safe_title}_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# {self.title}\n\n")
            f.write(f"**类型**: {self.genre}\n\n")
            f.write(f"**故事梗概**: {self.framework.get('synopsis', '')}\n\n")
            f.write(f"**主要人物**: {', '.join(self.framework.get('characters', []))}\n\n")
            f.write(f"**核心悬念**: {self.framework.get('mystery_core', '')}\n\n")
            f.write("---\n\n")

            for chapter in self.chapters:
                f.write(f"## 第{chapter['chapter_num']}章 {chapter['title']}\n\n")
                content = self._clean_content(chapter["content"])
                f.write(f"{content}\n\n")

                if chapter.get("reviews"):
                    f.write("### 评审意见\n\n")
                    for review in chapter["reviews"]:
                        f.write(
                            f"- **{review['reviewer']}** (评分: {review['score']}/10): {review['feedback'][:200]}...\n"
                        )
                    f.write("\n")

            f.write("---\n\n")
            progress = self.get_progress()
            f.write(
                f"*完成进度: {progress['completed_chapters']}/{progress['total_chapters']} 章*\n"
            )
            f.write(f"*平均评分: {progress['average_score']:.1f}/10*\n")

        print(f"  小说已保存到: {md_file}")
        return str(md_file)

    def _clean_content(self, content: str) -> str:
        """清理内容中的JSON标记"""
        content = re.sub(r"```json\s*", "", str(content))
        content = re.sub(r"```\s*", "", content)
        if '"content"' in content:
            match = re.search(r'"content"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', content)
            if match:
                content = match.group(1).replace("\\n", "\n")
        return content


# ============================================================================
# Agent工具定义 (直接使用ToolRegistry，不用MCP)
# ============================================================================


def create_framework_tools(storage: NovelStorage) -> ToolRegistry:
    """为框架设计者创建工具"""
    registry = ToolRegistry()

    def submit_framework(
        title: str,
        total_chapters: int,
        synopsis: str,
        characters: str,
        mystery_core: str,
        chapter_outlines: str,
    ) -> ToolResult:
        """提交小说框架"""
        framework = {
            "title": title,
            "total_chapters": total_chapters,
            "synopsis": synopsis,
            "characters": [c.strip() for c in characters.split(",")],
            "mystery_core": mystery_core,
            "chapter_outlines": [c.strip() for c in chapter_outlines.split("|")],
        }
        storage.set_framework(framework)
        return ToolResult(
            success=True,
            output=f"框架《{title}》已提交，共{total_chapters}章",
            metadata={"framework": framework},
        )

    registry.register(
        Tool(
            name="submit_framework",
            description="提交悬疑小说框架设计",
            parameters={
                "title": ToolParameter(
                    type=ToolParameterType.STRING, description="小说标题", required=True
                ),
                "total_chapters": ToolParameter(
                    type=ToolParameterType.INTEGER, description="总章节数", required=True
                ),
                "synopsis": ToolParameter(
                    type=ToolParameterType.STRING, description="故事梗概", required=True
                ),
                "characters": ToolParameter(
                    type=ToolParameterType.STRING, description="主要人物，逗号分隔", required=True
                ),
                "mystery_core": ToolParameter(
                    type=ToolParameterType.STRING, description="核心悬念", required=True
                ),
                "chapter_outlines": ToolParameter(
                    type=ToolParameterType.STRING, description="章节大纲，用|分隔", required=True
                ),
            },
            function=submit_framework,
        )
    )

    return registry


def create_writer_tools(storage: NovelStorage) -> ToolRegistry:
    """为写作者创建工具"""
    registry = ToolRegistry()

    def write_chapter(chapter_num: int, title: str, content: str) -> ToolResult:
        """写一个章节"""
        storage.add_chapter(chapter_num, title, content)
        return ToolResult(
            success=True,
            output=f"第{chapter_num}章《{title}》已完成，共{len(content)}字",
            metadata={"chapter_num": chapter_num, "word_count": len(content)},
        )

    def get_framework() -> ToolResult:
        """获取当前框架"""
        return ToolResult(
            success=True, output=str(storage.framework), metadata={"framework": storage.framework}
        )

    registry.register(
        Tool(
            name="write_chapter",
            description="写一个章节",
            parameters={
                "chapter_num": ToolParameter(
                    type=ToolParameterType.INTEGER, description="章节编号", required=True
                ),
                "title": ToolParameter(
                    type=ToolParameterType.STRING, description="章节标题", required=True
                ),
                "content": ToolParameter(
                    type=ToolParameterType.STRING, description="章节内容", required=True
                ),
            },
            function=write_chapter,
        )
    )

    registry.register(
        Tool(
            name="get_framework", description="获取小说框架", parameters={}, function=get_framework
        )
    )

    return registry


def create_critic_tools(storage: NovelStorage) -> ToolRegistry:
    """为评论者创建工具"""
    registry = ToolRegistry()

    def submit_review(chapter_num: int, score: int, feedback: str) -> ToolResult:
        """提交章节评论"""
        storage.add_review(chapter_num, "CriticAgent", score, feedback)
        return ToolResult(
            success=True,
            output=f"对第{chapter_num}章的评论已提交，评分: {score}/10",
            metadata={"score": score},
        )

    def view_chapter(chapter_num: int) -> ToolResult:
        """查看指定章节"""
        for chapter in storage.chapters:
            if chapter["chapter_num"] == chapter_num:
                return ToolResult(
                    success=True,
                    output=f"第{chapter_num}章《{chapter['title']}》:\n{chapter['content']}",
                    metadata={"chapter": chapter},
                )
        return ToolResult(success=False, output=f"未找到第{chapter_num}章", error="章节不存在")

    registry.register(
        Tool(
            name="submit_review",
            description="提交对章节的评论和评分",
            parameters={
                "chapter_num": ToolParameter(
                    type=ToolParameterType.INTEGER, description="章节编号", required=True
                ),
                "score": ToolParameter(
                    type=ToolParameterType.INTEGER, description="评分(1-10)", required=True
                ),
                "feedback": ToolParameter(
                    type=ToolParameterType.STRING, description="评论内容", required=True
                ),
            },
            function=submit_review,
        )
    )

    registry.register(
        Tool(
            name="view_chapter",
            description="查看指定章节内容",
            parameters={
                "chapter_num": ToolParameter(
                    type=ToolParameterType.INTEGER, description="章节编号", required=True
                ),
            },
            function=view_chapter,
        )
    )

    return registry


# ============================================================================
# Agents创建
# ============================================================================


def create_llm_client() -> UnifyLLM:
    """创建Databricks LLM客户端"""
    return UnifyLLM(
        provider="databricks",
        api_key=settings.DATABRICKS_API_KEY,
        base_url=settings.DATABRICKS_BASE_URL,
    )


def create_framework_architect(
    client: UnifyLLM, storage: NovelStorage
) -> tuple[Agent, AgentExecutor]:
    """创建框架设计者Agent"""
    config = AgentConfig(
        name="FrameworkArchitect",
        agent_type=AgentType.CONVERSATIONAL,
        model=settings.DATABRICKS_MODEL,
        provider="databricks",
        system_prompt="""你是一位资深的悬疑小说框架设计师。你的任务是设计引人入胜的悬疑小说框架。

你需要考虑以下要素：
1. 引人入胜的开篇设计
2. 复杂但合理的人物关系
3. 层层推进的悬念设计
4. 出人意料又在情理之中的结局
5. 伏笔和线索的巧妙安排

当被要求设计框架时，请严格按照以下JSON格式返回：
```json
{
  "title": "小说标题",
  "total_chapters": 数字,
  "synopsis": "故事梗概",
  "characters": ["人物1", "人物2"],
  "mystery_core": "核心悬念",
  "chapter_outlines": ["第一章大纲", "第二章大纲", "第三章大纲"]
}
```""",
        temperature=0.8,
        max_iterations=3,
        tools=[],
    )

    agent = Agent(config=config, client=client)
    tools = create_framework_tools(storage)
    memory = ConversationMemory(window_size=20)
    executor = AgentExecutor(agent, tools, memory, verbose=True)

    return agent, executor


def create_critic_agent(client: UnifyLLM, storage: NovelStorage) -> tuple[Agent, AgentExecutor]:
    """创建评论者Agent"""
    config = AgentConfig(
        name="CriticAgent",
        agent_type=AgentType.CONVERSATIONAL,
        model=settings.DATABRICKS_MODEL,
        provider="databricks",
        system_prompt="""你是一位严谨的悬疑小说评论家和编辑。你的任务是：

1. 评估小说框架的合理性
   - 悬念设计是否吸引人
   - 人物动机是否合理
   - 情节是否有逻辑漏洞
   - 伏笔安排是否巧妙

2. 评审每个章节的质量
   - 文笔是否流畅
   - 悬念推进是否恰当
   - 人物塑造是否立体
   - 是否与整体框架一致

评分标准：
- 1-3分：需要重写
- 4-6分：需要修改
- 7-8分：良好
- 9-10分：优秀

当被要求评审时，请按以下JSON格式返回：
```json
{
  "score": 评分数字,
  "feedback": "详细评论",
  "suggestions": ["建议1", "建议2"]
}
```""",
        temperature=0.6,
        max_iterations=3,
        tools=[],
    )

    agent = Agent(config=config, client=client)
    tools = create_critic_tools(storage)
    memory = ConversationMemory(window_size=20)
    executor = AgentExecutor(agent, tools, memory, verbose=True)

    return agent, executor


def create_writer_agent(client: UnifyLLM, storage: NovelStorage) -> tuple[Agent, AgentExecutor]:
    """创建写作者Agent"""
    config = AgentConfig(
        name="WriterAgent",
        agent_type=AgentType.CONVERSATIONAL,
        model=settings.DATABRICKS_MODEL,
        provider="databricks",
        system_prompt="""你是一位才华横溢的悬疑小说作家。你的任务是根据框架设计写出引人入胜的小说章节。

写作要求：
1. 文笔优美，描写生动
2. 善于营造悬疑氛围
3. 人物对话自然生动
4. 情节推进紧凑有力
5. 适当埋下伏笔

每个章节应该：
- 有明确的开头、发展和结尾
- 推进主线悬念
- 展现人物性格
- 留下适当悬念引导下一章

当被要求写章节时，请按以下JSON格式返回：
```json
{
  "chapter_title": "章节标题",
  "content": "章节正文内容（至少500字）"
}
```""",
        temperature=0.9,
        max_iterations=3,
        tools=[],
    )

    agent = Agent(config=config, client=client)
    tools = create_writer_tools(storage)
    memory = ConversationMemory(window_size=20)
    executor = AgentExecutor(agent, tools, memory, verbose=True)

    return agent, executor


# ============================================================================
# A2A协作系统
# ============================================================================


async def setup_a2a_system(
    framework_agent: Agent, critic_agent: Agent, writer_agent: Agent, registry: AgentRegistry
) -> tuple[A2AAgent, A2AAgent, A2AAgent]:
    """设置A2A协作系统"""

    # 框架设计者的A2A配置
    framework_a2a_config = A2AAgentConfig(
        agent_name="FrameworkArchitect",
        capabilities=[
            AgentCapability(
                name="design_framework",
                description="设计悬疑小说框架",
                input_schema={"type": "object", "properties": {"theme": {"type": "string"}}},
                output_schema={"type": "object"},
                tags=["framework", "design", "mystery"],
            ),
            AgentCapability(
                name="review_chapter",
                description="从框架角度评审章节",
                input_schema={"type": "object", "properties": {"chapter_num": {"type": "integer"}}},
                output_schema={"type": "object"},
                tags=["review", "framework"],
            ),
        ],
        heartbeat_interval=30,
        discovery_enabled=True,
    )

    # 评论者的A2A配置
    critic_a2a_config = A2AAgentConfig(
        agent_name="CriticAgent",
        capabilities=[
            AgentCapability(
                name="evaluate_framework",
                description="评估小说框架的合理性",
                input_schema={"type": "object", "properties": {"framework": {"type": "object"}}},
                output_schema={
                    "type": "object",
                    "properties": {"approved": {"type": "boolean"}, "feedback": {"type": "string"}},
                },
                tags=["evaluate", "framework"],
            ),
            AgentCapability(
                name="review_chapter",
                description="评审章节质量",
                input_schema={"type": "object", "properties": {"chapter_num": {"type": "integer"}}},
                output_schema={
                    "type": "object",
                    "properties": {"score": {"type": "integer"}, "feedback": {"type": "string"}},
                },
                tags=["review", "chapter"],
            ),
        ],
        heartbeat_interval=30,
        discovery_enabled=True,
    )

    # 写作者的A2A配置
    writer_a2a_config = A2AAgentConfig(
        agent_name="WriterAgent",
        capabilities=[
            AgentCapability(
                name="write_chapter",
                description="根据框架写作章节",
                input_schema={
                    "type": "object",
                    "properties": {
                        "chapter_num": {"type": "integer"},
                        "outline": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
                },
                tags=["write", "chapter"],
            )
        ],
        heartbeat_interval=30,
        discovery_enabled=True,
    )

    # 创建A2A代理
    framework_a2a = A2AAgent(framework_agent, framework_a2a_config, registry)
    critic_a2a = A2AAgent(critic_agent, critic_a2a_config, registry)
    writer_a2a = A2AAgent(writer_agent, writer_a2a_config, registry)

    return framework_a2a, critic_a2a, writer_a2a


# ============================================================================
# 协作工作流
# ============================================================================


class MysteryNovelWorkflow:
    """悬疑小说多Agent协作工作流"""

    def __init__(
        self,
        storage: NovelStorage,
        framework_executor: AgentExecutor,
        critic_executor: AgentExecutor,
        writer_executor: AgentExecutor,
        framework_a2a: A2AAgent,
        critic_a2a: A2AAgent,
        writer_a2a: A2AAgent,
        message_bus: MessageBus,
    ):
        self.storage = storage
        self.framework_executor = framework_executor
        self.critic_executor = critic_executor
        self.writer_executor = writer_executor
        self.framework_a2a = framework_a2a
        self.critic_a2a = critic_a2a
        self.writer_a2a = writer_a2a
        self.message_bus = message_bus
        self.shared_memory = SharedMemory()

    async def run(self, theme: str = "密室杀人案", chapters_to_write: int = 2) -> dict:
        """运行完整的小说创作流程"""
        print("\n" + "=" * 60)
        print("悬疑小说多Agent创作系统启动")
        print("=" * 60)

        # 阶段1: 框架设计
        print("\n[阶段1] 框架设计")
        print("-" * 40)
        framework = await self._design_framework(theme)

        # 阶段2: 框架评审和讨论
        print("\n[阶段2] 框架评审与讨论")
        print("-" * 40)
        await self._discuss_framework(framework)

        # 阶段3: 章节写作和评审
        print("\n[阶段3] 章节写作与评审")
        print("-" * 40)
        chapters = await self._write_and_review_chapters(chapters_to_write)

        # 汇总结果
        result = {
            "title": self.storage.title,
            "framework": self.storage.framework,
            "chapters": chapters,
            "progress": self.storage.get_progress(),
        }

        print("\n" + "=" * 60)
        print("创作完成!")
        print(f"小说标题: {result['title']}")
        print(
            f"完成章节: {result['progress']['completed_chapters']}/{result['progress']['total_chapters']}"
        )
        print(f"平均评分: {result['progress']['average_score']:.1f}/10")
        print("=" * 60)

        # 保存小说到文件
        if self.storage.chapters:
            self.storage.save_to_file()

        return result

    async def _design_framework(self, theme: str) -> dict:
        """框架设计阶段"""
        print(f"  主题: {theme}")
        print("  FrameworkArchitect 正在设计框架...")

        prompt = f"""请为以下主题设计一个悬疑小说框架：

主题: {theme}

要求:
1. 设计3章的故事结构
2. 创建2-3个主要人物
3. 设计一个核心悬念
4. 确保结局出人意料但合理

请严格按照JSON格式返回框架设计。"""

        result = await self.framework_executor.arun(prompt)

        if result.success and result.output:
            framework = self._parse_json_from_text(result.output)
            if framework:
                self.storage.set_framework(framework)
                print("  框架设计完成")
                print(f"    标题: {self.storage.title}")
                print(f"    章节数: {self.storage.framework.get('total_chapters', 0)}")
                self.shared_memory.set("initial_framework", self.storage.framework)
            else:
                print("  无法解析框架JSON，使用默认框架")
                self._set_default_framework(theme)
        else:
            print(f"  框架设计失败: {result.error}")
            self._set_default_framework(theme)

        return self.storage.framework

    def _parse_json_from_text(self, text: str) -> dict | None:
        """从文本中解析JSON"""
        # 尝试找到JSON块
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试直接解析
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

        return None

    def _set_default_framework(self, theme: str) -> None:
        """设置默认框架"""
        default = {
            "title": f"关于{theme}的悬疑故事",
            "total_chapters": 3,
            "synopsis": f"一个关于{theme}的悬疑故事",
            "characters": ["主角", "嫌疑人", "侦探"],
            "mystery_core": "真相隐藏在表象之下",
            "chapter_outlines": ["开端：发现谜团", "发展：追寻真相", "结局：揭晓答案"],
        }
        self.storage.set_framework(default)

    async def _discuss_framework(self, framework: dict) -> dict:
        """框架讨论阶段 - 使用A2A协作"""
        print("  CriticAgent 正在评估框架...")

        # 通过A2A消息总线发送评估请求
        if self.framework_a2a and self.critic_a2a:
            await self.message_bus.publish(
                target_id=self.critic_a2a.agent_id,
                message={"type": "evaluate_framework_request", "framework": framework},
                sender_id=self.framework_a2a.agent_id,
            )

        # 评论者评估框架
        critic_prompt = f"""请评估以下悬疑小说框架的合理性:

框架内容:
{framework}

请从以下方面进行评估:
1. 悬念设计是否吸引人？
2. 人物动机是否合理？
3. 情节是否有逻辑漏洞？
4. 结构是否完整？

给出你的评估意见和改进建议。"""

        critic_result = await self.critic_executor.arun(critic_prompt)

        if critic_result.success:
            print("  框架评估完成")
            feedback = critic_result.output
            self.shared_memory.set("framework_feedback", feedback)

            # 如果有重要改进建议，让框架设计者修改
            if "需要修改" in feedback or "建议" in feedback:
                print("  FrameworkArchitect 正在根据反馈修改框架...")
                revision_prompt = f"""评论者对你的框架给出了以下反馈:

{feedback}

请根据反馈修改你的框架设计，然后使用submit_framework工具提交修改后的版本。"""
                await self.framework_executor.arun(revision_prompt)
                print("  框架修改完成")

        return self.storage.framework

    async def _write_and_review_chapters(self, num_chapters: int) -> list:
        """章节写作和评审阶段"""
        chapters = []
        outlines = self.storage.framework.get("chapter_outlines", [])

        for i in range(1, min(num_chapters + 1, len(outlines) + 1)):
            print(f"\n  写作第{i}章...")

            outline = outlines[i - 1] if i <= len(outlines) else f"第{i}章"

            # 写作者写章节
            write_prompt = f"""请根据以下框架写第{i}章。

小说框架:
- 标题: {self.storage.framework.get('title')}
- 核心悬念: {self.storage.framework.get('mystery_core')}
- 人物: {', '.join(self.storage.framework.get('characters', []))}

本章大纲: {outline}

要求:
1. 按照大纲展开情节
2. 营造悬疑氛围
3. 章节内容至少300字

请按JSON格式返回章节内容。"""

            write_result = await self.writer_executor.arun(write_prompt)

            if write_result.success and write_result.output:
                chapter_data = self._parse_json_from_text(write_result.output)
                if chapter_data:
                    title = chapter_data.get("chapter_title", f"第{i}章")
                    content = chapter_data.get("content", write_result.output)
                else:
                    title = f"第{i}章"
                    content = self.storage._clean_content(write_result.output)

                self.storage.add_chapter(i, title, content)
                print(f"  第{i}章《{title}》写作完成")

                # 评审章节
                print(f"  评审第{i}章...")
                await self._review_chapter(i, title, content)

                # 从存储中获取评分
                score = None
                for ch in self.storage.chapters:
                    if ch["chapter_num"] == i and ch.get("reviews"):
                        score = ch["reviews"][-1].get("score")
                        break

                chapters.append(
                    {
                        "chapter_num": i,
                        "title": title,
                        "content": content[:500] + "..." if len(content) > 500 else content,
                        "score": score,
                    }
                )

        return chapters

    async def _review_chapter(self, chapter_num: int, title: str, content: str) -> None:
        """评审单个章节"""
        review_prompt = f"""请评审以下章节的质量。

章节标题: {title}
章节内容:
{content[:1000]}...

评审标准:
1. 文笔流畅度（2分）
2. 悬念推进（2分）
3. 人物塑造（2分）
4. 框架一致性（2分）
5. 整体吸引力（2分）

请按JSON格式返回评审结果。"""

        critic_result = await self.critic_executor.arun(review_prompt)

        if critic_result.success:
            review_data = self._parse_json_from_text(critic_result.output)
            if review_data:
                score = review_data.get("score", 7)
                feedback = review_data.get("feedback", critic_result.output)
            else:
                score = 7
                feedback = critic_result.output

            self.storage.add_review(chapter_num, "CriticAgent", score, feedback)
            print(f"  第{chapter_num}章评审完成，评分: {score}/10")


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数"""
    import sys

    if "--demo" in sys.argv:
        return await run_demo_mode()

    # 检查配置
    if not settings.DATABRICKS_API_KEY or not settings.DATABRICKS_BASE_URL:
        print("未正确设置Databricks配置")
        print("请在.env文件中设置:")
        print("  DATABRICKS_API_KEY=your_api_key")
        print("  DATABRICKS_BASE_URL=your_base_url")
        print("  DATABRICKS_MODEL=databricks-claude-opus-4-5")
        print("\n或使用 --demo 参数运行演示模式")
        return await run_demo_mode()

    print("初始化系统...")
    print(f"  模型: {settings.DATABRICKS_MODEL}")

    # 初始化存储
    storage = NovelStorage()

    # 创建LLM客户端
    client = create_llm_client()
    print("  Databricks客户端已创建")

    # 创建Agents
    framework_agent, framework_executor = create_framework_architect(client, storage)
    critic_agent, critic_executor = create_critic_agent(client, storage)
    writer_agent, writer_executor = create_writer_agent(client, storage)
    print("  Agents已创建")

    # 创建A2A注册表和消息总线
    registry = AgentRegistry()
    message_bus = MessageBus(MessageBusConfig(name="novel-bus"))
    await message_bus.start()
    print("  消息总线已启动")

    # 设置A2A系统
    framework_a2a, critic_a2a, writer_a2a = await setup_a2a_system(
        framework_agent, critic_agent, writer_agent, registry
    )

    # 启动A2A代理
    await framework_a2a.start()
    await critic_a2a.start()
    await writer_a2a.start()
    print("  A2A代理已启动")

    # 创建工作流
    workflow = MysteryNovelWorkflow(
        storage=storage,
        framework_executor=framework_executor,
        critic_executor=critic_executor,
        writer_executor=writer_executor,
        framework_a2a=framework_a2a,
        critic_a2a=critic_a2a,
        writer_a2a=writer_a2a,
        message_bus=message_bus,
    )

    # 运行工作流
    try:
        result = await workflow.run(theme="古老图书馆中的密室杀人案", chapters_to_write=2)

        # 输出预览
        print("\n" + "=" * 60)
        print("小说内容预览")
        print("=" * 60)

        if result["chapters"]:
            for chapter in result["chapters"]:
                print(f"\n【第{chapter['chapter_num']}章 - {chapter.get('title', '未知')}】")
                print(f"评分: {chapter.get('score', 'N/A')}/10")
                content = storage._clean_content(chapter.get("content", ""))
                print(f"内容预览:\n{content[:300]}...")

    finally:
        # 清理资源
        await framework_a2a.stop()
        await critic_a2a.stop()
        await writer_a2a.stop()
        await message_bus.stop()
        print("\n资源已清理")


async def run_demo_mode():
    """演示模式"""
    print("\n" + "=" * 60)
    print("悬疑小说多Agent创作系统 - 演示模式")
    print("=" * 60)

    print(
        """
架构概览:

┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Framework     │   │    Critic     │   │    Writer     │
│ Architect     │<->│    Agent      │   │    Agent      │
│ (A2A Agent)   │   │ (A2A Agent)   │   │ (A2A Agent)   │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │ Message Bus │
                    │  (A2A通信)  │
                    └─────────────┘

工作流程:
1. FrameworkArchitect 设计小说框架
2. CriticAgent 评估框架合理性，提出改进建议
3. 两者通过A2A协议讨论直到达成共识
4. WriterAgent 根据框架逐章写作
5. FrameworkArchitect + CriticAgent 共同评判每章质量

使用的技术:
- Databricks Provider: 连接Databricks托管的LLM
- A2A Protocol: Agent间任务委托和协作
- ToolRegistry: 直接定义Agent工具（简化，不用MCP）
- AgentExecutor: 执行Agent任务循环
- MessageBus: Agent间消息通信
- SharedMemory: 多Agent共享数据

要运行真实版本，请设置环境变量:
   export DATABRICKS_API_KEY=your_api_key
   export DATABRICKS_BASE_URL=your_base_url
   export DATABRICKS_MODEL=databricks-meta-llama-3-1-70b-instruct
"""
    )


if __name__ == "__main__":
    asyncio.run(main())

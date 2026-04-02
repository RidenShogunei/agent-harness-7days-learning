#写一个todo list
import os
import subprocess
from anthropic import Anthropic
from dotenv import load_dotenv
from pathlib import Path

import re
import yaml

load_dotenv(override=True)

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.

Skills available:
<loading skills...>"""
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."

#现在可以操作bash，读写文件，编辑文件
# 工具处理函数
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "todo":       lambda **kw: TODO.update(kw["items"]),
    # Parent-only tool: delegate work in a fresh context.
    # The model should provide `prompt`, but we defensively handle missing input.
    "task":       lambda **kw: run_subagent(kw.get("prompt") or "Error: task requires 'prompt'."),
    # Skill tool: return the full skill body wrapped for the model.
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}


CHILD_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "todo", "description": "Update task list. Track progress on multi-step tasks.",
     "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["id", "text", "status"]}}}, "required": ["items"]}},
 {"name": "load_skill", "description": "Load specialized knowledge by name.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string", "description": "Skill name to load"}}, "required": ["name"]}},
]


# todo manager: 结构化状态，LLM写入
class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        if len(items) > 20:
            raise ValueError("Max 20 todos allowed")

        validated = []
        in_progress_count = 0
        for i, row in enumerate(items):
            text = str(row.get("text", "")).strip()
            status = str(row.get("status", "pending")).lower()
            item_id = str(row.get("id", str(i + 1)))
            if not text:
                raise ValueError(f"Item {item_id}: text required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {item_id}: invalid status '{status}'")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")
        self.items = validated
        return self.render()
    #渲染todo列表
    def render(self) -> str:
        if not self.items:
            return "No todos."
        lines = []
        for item in self.items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item["status"]]
            lines.append(f"{marker} #{item['id']}: {item['text']}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)

class SkillLoader:
    def __init__(self,skills_dir: Path):
        # 技能根目录：从这里递归寻找 `SKILL.md`
        self.skills_dir = skills_dir

        # 已加载技能的内存缓存：
        #   key   -> 技能名
        #   value -> {"meta": ..., "body": ..., "path": ...}
        self.skills = {}

        # 注意：这里调用的是 load_all()。
        # 如果文件里实际实现方法叫 `_load_all`，需要把方法名对齐（可在后续再检查/修复）。
        self._load_all()
    
    def _load_all(self):
        # 从技能目录加载所有技能文件
        if not self.skills_dir.exists():
            return

        # 递归查找所有 `SKILL.md`，并按路径顺序排序，保证加载顺序稳定
        for f in sorted(self.skills_dir.rglob("SKILL.md")):
            text = f.read_text()

            # 拆分：把 YAML frontmatter 和正文分离
            meta, body = self._parse_frontmatter(text)

            # 技能名优先从 meta.name 取；meta 没写则用父目录名当默认技能名
            name = meta.get("name", f.parent.name)

            # 缓存解析结果，供后续 tool_result/系统提示使用
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}

    def _parse_frontmatter(self, text: str) -> tuple:
        """Parse YAML frontmatter between --- delimiters."""
        # 期望文件格式类似：
        # ---
        # <yaml...>
        # ---
        # <正文...>
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)

        # 如果没有 frontmatter，就把整个文件当正文
        if not match:
            return {}, text

        # 尝试解析 YAML 元数据（meta）
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            # YAML 写错时降级：meta 为空，但尽量保留正文
            meta = {}

        # group(2) 是正文部分；去掉首尾空白，方便拼接到系统提示/结果里
        return meta, match.group(2).strip()

    def get_descriptions(self) -> str:
        """Layer 1: short descriptions for the system prompt."""
        # 给系统提示（system prompt）用的“技能清单”，只保留简短描述
        if not self.skills:
            return "(no skills available)"

        lines = []
        for name, skill in self.skills.items():
            # 技能元数据里的 description（没有就用默认文案）
            desc = skill["meta"].get("description", "No description")

            # tags 可选：用于模型更好地理解/分类技能
            tags = skill["meta"].get("tags", "")

            # 组装每行：`- 技能名: 描述 [tags]`
            line = f"  - {name}: {desc}"
            if tags:
                line += f" [{tags}]"
            lines.append(line)

        # 多行字符串返回，便于直接拼到 SYSTEM 文本里
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """Layer 2: full skill body returned in tool_result."""
        # 给模型返回“完整技能内容”的 tool_result 格式
        skill = self.skills.get(name)

        # 找不到技能时：返回错误，并列出可选技能名，便于模型纠错/重试
        if not skill:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"

        # 用一个简单的 XML-ish 包装，让模型更容易从输出中定位该技能正文边界
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"

SKILL_LOADER = SkillLoader(SKILLS_DIR)

# 现在技能已加载完成，可以把“技能清单”写入系统提示（system prompt）
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.

Skills available:
{SKILL_LOADER.get_descriptions()}"""

TODO = TodoManager()

# -- Subagent: fresh context, filtered tools, summary-only return --
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]  # fresh context
    for _ in range(30):  # safety limit
        response = client.messages.create(
            model=MODEL, system=SUBAGENT_SYSTEM, messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        sub_messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)[:50000]})
        sub_messages.append({"role": "user", "content": results})
    # Only the final text returns to the parent -- child context is discarded
    return "".join(b.text for b in response.content if hasattr(b, "text")) or "(no summary)"


# -- Parent tools: base tools + task dispatcher --
PARENT_TOOLS = CHILD_TOOLS + [
    {"name": "task", "description": "Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
     "input_schema": {"type": "object", "properties": {"prompt": {"type": "string"}, "description": {"type": "string", "description": "Short description of the task"}}, "required": ["prompt"]}},
]

# Parent loop uses this toolset (base tools + `task` dispatcher).
TOOLS = PARENT_TOOLS


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path: str, limit: int = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command."
    try:
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

#loop开始
def agent_loop(messages: list) -> str:
    rounds_since_todo = 0
    while True:
        print(f"进入agent_loop")
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        print(f"response.content: {response.content}")
        if response.stop_reason != "tool_use":
            return
        #执行每个工具调用，收集结果
        results = []
        used_todo = False
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block.name}:")
                print(str(output)[:200])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
                if block.name == "todo":
                    used_todo = True
        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            results.append({"type": "text", "text": "<reminder>Update your todos.</reminder>"})
        messages.append({"role": "user", "content": results})

if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms05 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()

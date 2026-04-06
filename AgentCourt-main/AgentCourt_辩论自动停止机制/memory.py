import json
import os
from typing import Any, Dict, Optional, List


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """从LLM输出中提取JSON对象"""
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


class CourtMemoryManager:
    """
    庭审专用记忆管理器

    架构设计：
    - 短期记忆：当前任务 + 上一轮对话总结（用于本轮发言）
    - 长期记忆：过程层（每轮对话的摘要，持续追加）

    提示词拼接顺序：当前阶段 + 角色信息 + 过程层 + 短期记忆

    注意：案件原始描述（indictmentDesc / defendant_defense 等）
    不通过 build_memory_prompt 输出，而是在 Agent 初始化时通过
    Config.xxx_case_info 模板嵌入 role_prompt，避免重复冗余。
    """

    def __init__(self, case_info: Dict[str, Any], simulation_id: str, output_folder: Optional[str] = None):
        self.case_info = case_info
        self.simulation_id = simulation_id
        self.output_folder = output_folder

        # 当前阶段描述（由 CourtFlow 设置）
        self.current_phase: str = ""

        # ========== 短期记忆 ==========
        self.short_term_memory: Dict[str, Any] = {
            "current_task": "",           # 当前任务
            "previous_round_summary": "", # 上一轮对话总结
        }

        # ========== 长期记忆 ==========
        self.long_term_memory: Dict[str, Any] = {

            # === 基础层（庭审开始即写入）===
            "case_info": {},     # 案件基本信息：案由、地区、原被告、诉讼请求、答辩意见概要
            "role_info": {},     # 角色信息：各方当事人及代理人身份

            # === 过程层（每轮对话结束后追加）===
            "round_summaries": [],  # 每轮对话总结列表
        }

    # ------------------------------------------------------------------
    # 阶段和任务管理
    # ------------------------------------------------------------------

    def set_phase(self, phase: str):
        """设置当前阶段描述"""
        self.current_phase = phase

    def set_current_task(self, task: str):
        """设置当前任务（短期记忆）"""
        self.short_term_memory["current_task"] = task

    # ------------------------------------------------------------------
    # 基础层初始化（在 flow() 开头调用一次）
    # ------------------------------------------------------------------

    def init_case_info(self, judge_info: Dict, left_lawyer_info: Dict, right_lawyer_info: Dict):
        """庭审开始前，初始化案件基础信息和角色信息"""
        ci = self.case_info
        self.long_term_memory["case_info"] = {
            "case_name": ci.get("name", ""),
            "province": ci.get("province", ""),
            "city": ci.get("city", ""),
            "case_type": ci.get("thirdType", ""),          # 案由三级分类
            "description": ci.get("description", ""),
            "indictmentDesc": ci.get("indictmentDesc", ""),     # 起诉状描述（诉称）
            "indictmentProof": ci.get("indictmentProof", ""), # 原告证据描述
            "defendant_defense": ci.get("pleadingsDesc", ""),   # 答辩状描述（辩称）
            "defendant_evidence": ci.get("pleadingsProof", ""),  # 被告证据描述
        }
        self.long_term_memory["role_info"] = {
            "原告律师": {**left_lawyer_info},
            "被告律师": {**right_lawyer_info},
            "法官": {**judge_info},
        }
        self.save()

    # ------------------------------------------------------------------
    # 记忆更新：每轮对话结束后
    # ------------------------------------------------------------------

    def update_round_summary(self, round_number: int, content: str, speaker: str = ""):
        """
        每轮对话结束后，提取并记录本轮对话的核心内容到长期记忆的过程层
        """
        try:
            from api import run_api

            prompt = f"""你是庭审记忆分析师。请提炼本轮对话的核心内容摘要。

【当前轮次】第 {round_number} 轮
【发言角色】{speaker}
【对话内容】
{content[:8000]}

任务：
1. 提炼本轮对话的核心要点（关键事实、争议、法律观点等）
2. 用简洁的一两句话概括
3. 只输出JSON，不要解释

输出JSON格式：
{{"summary": "本轮核心内容摘要", "key_points": ["要点1", "要点2"]}}
"""
            raw = run_api(prompt)
            parsed = _extract_first_json_object(raw)
            if not parsed:
                # 降级处理：直接使用前200字
                summary_text = content[:200] if content else ""
                parsed = {"summary": summary_text, "key_points": []}

            self.long_term_memory["round_summaries"].append({
                "round": round_number,
                "summary": parsed.get("summary", ""),
                "key_points": parsed.get("key_points", []),
                "speaker": speaker,
                "phase": self.current_phase,
            })

            # 追加到过程层后，更新短期记忆的"上一轮总结"
            self.short_term_memory["previous_round_summary"] = parsed.get("summary", "")

            self.save()
        except Exception as e:
            print(f"轮次总结提取失败: {e}")
            # 降级处理
            if content:
                self.short_term_memory["previous_round_summary"] = content[:200]
                self.long_term_memory["round_summaries"].append({
                    "round": round_number,
                    "summary": content[:200],
                    "key_points": [],
                    "speaker": speaker,
                    "phase": self.current_phase,
                })

    def update_summary(self):
        """
        辩论结束后提炼摘要（兼容旧接口）
        """
        # 如果有上一轮总结，直接追加到过程层
        prev_summary = self.short_term_memory.get("previous_round_summary", "")
        if prev_summary:
            current_round = len(self.long_term_memory["round_summaries"]) + 1
            self.long_term_memory["round_summaries"].append({
                "round": current_round,
                "summary": prev_summary,
                "key_points": [],
                "speaker": "辩论总结",
                "phase": self.current_phase,
            })

    # ------------------------------------------------------------------
    # 构建提示词（Agent 调用）
    # ------------------------------------------------------------------

    def build_memory_prompt(self) -> str:
        """
        构建完整的记忆提示词，供 Agent.speech / Agent.ask 使用。

        拼接顺序：当前阶段 + 角色信息 + 长期记忆（过程层）+ 短期记忆

        设计原则：
        - 案件原始描述（indictmentDesc / defendant_defense 等）不写入此处，
          已在 Agent 初始化时通过 Config.xxx_case_info 模板嵌入 role_prompt。
        - 过程层只保留每轮摘要，不重复案件基础信息。
        """
        lm = self.long_term_memory
        stm = self.short_term_memory

        # === 当前阶段 ===
        phase_block = f"【当前阶段】{self.current_phase}\n" if self.current_phase else ""

        # === 角色信息 ===
        role_info = lm.get("role_info", {})
        role_block = ""
        if role_info:
            role_lines = [
                f"- {role}：{info.get('name', '')}"
                for role, info in role_info.items()
                if isinstance(info, dict) and info.get('name')
            ]
            if role_lines:
                role_block = "【角色信息】\n" + "\n".join(role_lines) + "\n"

        # === 长期记忆-过程层（最近10轮对话摘要）===
        process_block = ""
        round_summaries = lm.get("round_summaries", [])
        if round_summaries:
            lines = []
            for item in round_summaries[-10:]:
                phase = item.get("phase", "")
                summary = item.get("summary", "")
                round_num = item.get("round", "")
                key_points = item.get("key_points", [])
                line = f"第{round_num}轮（{phase}）：{summary}"
                if key_points:
                    line += " | 要点：" + "；".join(key_points[:3])
                lines.append(line)
            process_block = "【长期记忆-过程层（各轮对话总结）】\n" + "\n".join(lines) + "\n"

        # === 短期记忆 ===
        short_block = ""
        if stm.get("previous_round_summary"):
            short_block += f"【短期记忆-上一轮总结】{stm['previous_round_summary']}\n"
        if stm.get("current_task"):
            short_block += f"【短期记忆-当前任务】{stm['current_task']}\n"

        return (phase_block + role_block + process_block + short_block).strip()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def save(self):
        """保存记忆到文件"""
        if not self.output_folder:
            return
        os.makedirs(self.output_folder, exist_ok=True)
        save_path = os.path.join(self.output_folder, f"memory_{self.simulation_id}.json")
        data = {
            "simulation_id": self.simulation_id,
            "short_term_memory": self.short_term_memory,
            "long_term_memory": self.long_term_memory,
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        """从文件加载记忆"""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.short_term_memory = data.get("short_term_memory", self.short_term_memory)
        self.long_term_memory = data.get("long_term_memory", self.long_term_memory)

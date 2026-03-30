import json
import os
import re
from typing import Any, Dict, Optional, List

from api import run_api
from config import Config


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort JSON extractor:
    - find the first '{' and the last '}' and parse it
    - returns None if parsing fails
    """
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


class MemoryManager:
    """
    记忆管理器（本案模拟内长期记忆 + 每次请求的短期工作记忆）。

    - 短期记忆：由最近历史“直接摘录+规则格式化”，不做昂贵LLM抽取
    - 长期记忆：每轮自由辩论结束后调用LLM做结构化更新（会写入本地文件）
    """

    def __init__(self, case_info: Dict[str, Any], simulation_id: str, output_folder: Optional[str] = None):
        self.case_info = case_info
        self.simulation_id = simulation_id
        self.output_folder = output_folder

        self.long_memory: Dict[str, Any] = {
            "facts": {
                # 每条尽量原子化，后续用于“短提示注入”
                "claims": [],
                "last_round_summary": "",
            },
            "social": {
                # 观测者->被观测者
                "cognition": {},
                "trust": {},
                "trust2": {},
                "behavior_bias": {},
            },
            "meta": {
                "case_name": case_info.get("name", ""),
                "updated_rounds": 0,
            },
        }

    def build_history_text(
        self,
        history_text: str,
        task: str,
        actor_role_key: str,
        obj_role_key: Optional[str] = None,
        round_counter: Optional[int] = None,
    ) -> str:
        """
        将“短期记忆+长期记忆”拼到 history_text 前面。
        注意：不修改 history_text 本体，避免污染后续日志。
        """
        short_block = self._build_short_memory(history_text, task, actor_role_key, obj_role_key)
        long_block = self._format_long_memory(actor_role_key, obj_role_key)

        # 保护长度：避免 prompt 爆炸
        memory_prefix = f"{short_block}\n{long_block}\n"
        max_prefix_chars = 2000
        if len(memory_prefix) > max_prefix_chars:
            memory_prefix = memory_prefix[:max_prefix_chars] + "\n...(已截断)"

        # 注意：AgentTemplate.txt 内部已经有“这是历史对话内容：{history}”，
        # 因此这里不再重复输出该字段名，避免 prompt 冗余。
        return f"{memory_prefix}\n{history_text}"

    def _build_short_memory(
        self,
        history_text: str,
        task: str,
        actor_role_key: str,
        obj_role_key: Optional[str],
    ) -> str:
        # 从 history_text 里直接取最近若干行，充当“当前局面”
        lines = [ln for ln in history_text.splitlines() if ln.strip()]
        tail = "\n".join(lines[-8:]) if lines else ""

        # “我需要做什么”：直接复述当前task（足够稳定、成本低）
        # “希望对方做什么”：在 ask 场景下，对方应当回应/补充/承认或反驳
        obj_desc = obj_role_key if obj_role_key else "对方"
        return (
            "【短期记忆：工作记忆】\n"
            f"当前局面（最近发言摘录）：\n{tail if tail else '（尚无历史发言）'}\n"
            f"你的任务：{task}\n"
            f"希望对方做什么：围绕你提出的观点/证据/认定进行回应（承认或反驳，并补充必要事实或证据）。\n"
            f"发言主体：{actor_role_key}；对话对象：{obj_desc}\n"
        )

    def _format_long_memory(self, actor_role_key: str, obj_role_key: Optional[str]) -> str:
        facts_claims: List[Dict[str, Any]] = self.long_memory.get("facts", {}).get("claims", []) or []

        if not facts_claims:
            facts_str = "事实记忆：暂无（等待自由辩论轮次更新）。"
        else:
            # 只展示前 N 条，控制长度
            show_n = min(len(facts_claims), 7)
            fact_lines = []
            for i in range(show_n):
                c = facts_claims[i] or {}
                claim_type = c.get("claim_type", "")
                claim_text = c.get("claim_text", "")
                support_or_attack = c.get("support_or_attack", "")
                ev_refs = c.get("evidence_refs", []) or []
                ev_part = f"证据片段/编号：{', '.join(map(str, ev_refs))}" if ev_refs else "证据片段/编号：无"
                fact_lines.append(
                    f"- [{claim_type}] {support_or_attack}：{claim_text}；{ev_part}"
                )
            facts_str = (
                "事实记忆（用于不遗忘与检索）：\n"
                + "\n".join(fact_lines)
            )

        social = self.long_memory.get("social", {}) or {}
        trust = social.get("trust", {}) or {}
        trust2 = social.get("trust2", {}) or {}

        # 对象相关的信任：取与 actor/obj 尽量匹配的条目
        def _filter_social(d: Dict[str, Any]) -> List[str]:
            if not d:
                return []
            keys = list(d.keys())
            prefer = []
            if obj_role_key:
                prefer_keys = [f"{actor_role_key}->{obj_role_key}", f"{obj_role_key}->{actor_role_key}"]
                for k in prefer_keys:
                    if k in d:
                        prefer.append(k)
            remain = [k for k in keys if k not in prefer]
            ordered = prefer + remain
            ordered = ordered[:6]
            out = []
            for k in ordered:
                out.append(f"- {k} = {d.get(k)}")
            return out

        trust_lines = _filter_social(trust)
        trust2_lines = _filter_social(trust2)

        if not trust_lines and not trust2_lines:
            social_str = "社会记忆：暂无可用信任/二阶信任更新。"
        else:
            social_str = "社会记忆（认知/信任/二阶信任/偏置的当前状态）：\n"
            if trust_lines:
                social_str += "信任度（trust）：\n" + "\n".join(trust_lines) + "\n"
            if trust2_lines:
                social_str += "二阶信任（trust2）：\n" + "\n".join(trust2_lines) + "\n"

        return f"【长期记忆：本案模拟内】\n{facts_str}\n{social_str}"

    def update_from_free_debate_round(self, history: Dict[str, Any], round_counter: int) -> None:
        """
        每轮自由辩论结束后（即一方与对方的两段发言都已写入history），更新长期记忆。
        """
        dataset = history.get("dataset", []) or []
        if len(dataset) < 2:
            return

        # 自由辩论循环里每轮是一次 Agent.ask()，它会追加两条：自己+对方
        last_entries = dataset[-2:]
        left_turn = last_entries[0]
        right_turn = last_entries[1]

        # 提取最近发言摘录（供LLM理解上下文）
        history_text_lines = history.get("text", "").splitlines()
        tail_text = "\n".join(history_text_lines[-10:]) if history_text_lines else ""

        current_long_memory = self.long_memory

        update_prompt = (
            "你是“庭审长期记忆更新器”。\n"
            "你的任务：基于本轮自由辩论中双方刚刚的两段发言，更新“事实记忆”和“社会记忆”。\n"
            "要求：\n"
            "1) 只输出 JSON，且必须能被 json.loads 解析；不要输出任何额外文本。\n"
            "2) facts.claims：新增或覆盖关键事实主张/争点结论；每条尽量原子化。\n"
            "3) 社会记忆中 trust/trust2 建议输出 0~1 的浮点数；键名采用“观察者->被观察者”的字符串形式。\n"
            "4) 你可以基于推断进行更新，但要尽量保持与发言内容一致。\n"
            "5) 如果信息不足，也允许输出空数组/空对象。\n"
            "输出 JSON 结构：\n"
            "{\n"
            '  "facts": {\n'
            '    "claims": [\n'
            "      {\n"
            '        "claim_type": "诉称/辩称/证据/结论/矛盾点之一",\n'
            '        "claim_text": "该主张的简短原子化文本",\n'
            '        "support_or_attack": "支持/反驳",\n'
            '        "evidence_refs": ["证据片段的简短编号/描述(可为空)"]\n'
            "      }\n"
            "    ],\n"
            '    "last_round_summary": "一句话概括本轮对争点/证据的推进"\n'
            "  },\n"
            '  "social": {\n'
            '    "cognition": { "observer->target": "认知摘要(可为空)" },\n'
            '    "trust": { "observer->target": 0.0 },\n'
            '    "trust2": { "observer->target": 0.0 },\n'
            '    "behavior_bias": { "actor": "行为偏置摘要(可为空)" }\n'
            "  },\n"
            '  "meta": { "updated_rounds": 1 }\n'
            "}\n"
            "\n"
            f"当前长期记忆（将被你更新）：\n{json.dumps(current_long_memory, ensure_ascii=False)}\n"
            "\n"
            f"本轮回合号：{round_counter}\n"
            "\n"
            f"最近发言摘录（tail）：\n{tail_text}\n"
            "\n"
            f"发言1（role={left_turn.get('role')} name={left_turn.get('name')}）：\n{left_turn.get('response','')}\n"
            f"发言2（role={right_turn.get('role')} name={right_turn.get('name')}）：\n{right_turn.get('response','')}\n"
        )

        try:
            raw = run_api(update_prompt)
            parsed = _extract_first_json_object(raw)
            if not parsed:
                return

            # 结构合并：用LLM输出覆盖facts/social/meta（避免难合并）
            new_facts = parsed.get("facts", {}) or {}
            new_social = parsed.get("social", {}) or {}
            new_meta = parsed.get("meta", {}) or {}

            # 只保留 claims 的合理数量，避免prompt越来越长
            claims = new_facts.get("claims", []) or []
            if isinstance(claims, list) and len(claims) > 25:
                claims = claims[:25]

            self.long_memory["facts"]["claims"] = claims
            self.long_memory["facts"]["last_round_summary"] = new_facts.get("last_round_summary", "") or ""
            self.long_memory["social"] = {
                "cognition": new_social.get("cognition", {}) or {},
                "trust": new_social.get("trust", {}) or {},
                "trust2": new_social.get("trust2", {}) or {},
                "behavior_bias": new_social.get("behavior_bias", {}) or {},
            }
            self.long_memory["meta"]["updated_rounds"] = int(
                new_meta.get("updated_rounds", self.long_memory.get("meta", {}).get("updated_rounds", 0)) or 0
            )
        except Exception:
            # 更新失败不应让主流程崩溃
            return

        # 落盘（本案模拟内，便于调试观察）
        if self.output_folder:
            try:
                self.save(os.path.join(self.output_folder, f"memory_{self.simulation_id}.json"))
            except Exception:
                pass

    def save(self, path: str) -> None:
        if not path:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.long_memory, f, ensure_ascii=False, indent=2)


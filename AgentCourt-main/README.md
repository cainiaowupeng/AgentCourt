# AgentCourt - 智能模拟法庭系统

## 项目概述

AgentCourt 是一个基于多智能体（Multi-Agent）的模拟法庭系统，通过大语言模型（LLM）模拟真实的法庭审判流程。系统支持民事案件的自动化审理，包括庭审准备、法庭调查、法庭辩论、最后陈述与宣判等完整环节。

## 项目结构

```
AgentCourt-main/
├── AgentCourt_辩论自动停止机制/          # 核心项目目录
│   ├── main.py                          # 主入口程序，支持批量案件处理
│   ├── CourtFlow.py                     # 庭审流程控制（核心）
│   ├── Agent.py                         # Agent角色定义与对话逻辑
│   ├── config.py                        # 全局配置管理
│   ├── api.py                           # LLM API调用封装
│   ├── memory.py                        # 记忆管理系统
│   ├── data_loader.py                   # 数据加载工具
│   ├── log.py                           # 日志模块
│   ├── prompts/                         # 提示词模板目录
│   │   ├── AgentTemplate.txt            # Agent基础模板
│   │   ├── JudgeSettings.txt            # 法官角色设置
│   │   ├── LawyerSettings.txt           # 律师角色设置
│   │   ├── JudgeCaseInfoTemplate.txt     # 法官案件信息模板
│   │   ├── LeftCaseInfoTemplate.txt      # 原告案件信息模板
│   │   ├── RightCaseInfoTemplate.txt     # 被告案件信息模板
│   │   ├── JudgementTemplate.txt         # 判决书模板
│   │   ├── CheckTemplate.txt             # 检查模板
│   │   └── IntentionCheckTemplate.txt     # 意图检查模板
│   ├── role_setting.json                # 角色设置配置
│   ├── data/                            # 案件数据目录
│   └── output/                          # 输出结果目录
└── README.md                            # 项目说明文档
```

## 核心模块说明

### 1. Agent.py - 角色代理模块

定义了法庭中的六种角色Agent：


| 角色   | 键值                | 功能描述           |
| ---- | ----------------- | -------------- |
| 法官   | `court_judge`     | 主持庭审、归纳争点、宣布判决 |
| 书记员  | `court_clerk`     | 宣布法庭纪律、记录庭审    |
| 原告   | `court_plaintiff` | 陈述身份、宣读起诉状     |
| 原告律师 | `left_lawyer`     | 举证、质证、发表辩论意见   |
| 被告   | `court_defendant` | 陈述身份、发表答辩意见    |
| 被告律师 | `right_lawyer`    | 举证、质证、发表辩论意见   |


**核心方法：**

- `speech()`: 单方发言
- `ask()`: 双方对话交互
- `set_memory_manager()`: 设置记忆管理器

### 2. CourtFlow.py - 庭审流程模块

模拟完整民事庭审流程，包含四个阶段：

#### 阶段一：庭审准备

1. 书记员宣布法庭纪律
2. 法官宣布开庭，核对当事人身份
3. 当事人陈述身份信息
4. 告知诉讼权利义务，询问是否申请回避

#### 阶段二：法庭调查

1. 原告宣读起诉状，明确诉讼请求
2. 被告发表答辩意见
3. 原告举证，被告质证
4. 被告举证，原告质证
5. 双方补充说明
6. 法官宣布调查结束

#### 阶段三：法庭辩论

1. 法官归纳争议焦点
2. 原告发表辩论意见
3. 被告发表辩论意见
4. **自由辩论**（核心环节）
5. 询问是否需要补充辩论意见
6. 宣布辩论结束

#### 阶段四：最后陈述与宣判

1. 原告作最后陈述
2. 被告作最后陈述
3. **法官三次独立宣判**，取多数意见
4. **出具书面判决书**

### 3. config.py - 配置模块

关键配置项：

```python
# API配置
api_model = 'Qwen/Qwen3-8B'           # 默认模型
api_url = 'http://10.176.60.51:6699/v1'  # API地址
temperature = 0.5                      # 生成温度
MAX_TURN = 5                            # 最大辩论轮次

# 辩论停止机制
stop_threshold = 0.8                    # Embedding相似度阈值
embeddingmodel = '/home/fan/...'        # 嵌入模型路径
```

### 4. memory.py - 记忆管理模块

采用**双层记忆架构**，核心目标：避免将原始对话流水账塞入 prompt，转而通过 LLM 提炼的结构化摘要传递上下文。

短期记忆 (short_term_memory)
  current_task — 当前轮次任务
  previous_round_summary — 上一轮对话的LLM提炼摘要

长期记忆 (long_term_memory)
  role_info — 各角色姓名（庭审开始写入）
  round_summaries — 各轮对话的结构化摘要列表

#### 提示词如何拼接

最终 prompt 由 **两个来源** 拼接：

**来源一（一次性）：Agent 初始化时嵌入 role_prompt**
来自 `Config.xxx_case_info` 模板，包含案件原始描述（起诉状、证据等），庭审中不变化。

**来源二（动态）：每次 Agent 调用时生成（build_memory_prompt）**

```
【当前阶段】xxx
【角色信息】原告律师：律师1；被告律师：律师2；法官：法官
【长期记忆-过程层（各轮对话总结）】
  第19轮（法庭辩论-法官归纳争议焦点）：法官宣布进入法庭辩论阶段...
  第20轮（法庭辩论-原告发表辩论意见）：原告律师主张本案不构成重复起诉...
  ...
【短期记忆-上一轮总结】被告律师声明已就争议焦点完成充分辩论，无需补充意见
【短期记忆-当前任务】陈述最后意见
```

**完整 prompt 组装结构：**

```
1. AgentTemplate.txt（固定模板，role/name/self_description 等占位符）
2. {role_settings}（角色设定，来源 role_setting.json）
3. {case_info}（来源：Config.xxx_case_info，案件原始描述，一次性嵌入）
4. 这是当前庭审的记忆上下文：（来源：build_memory_prompt()，实时生成）
5. 这是你这次发言的任务：{task}
6. 这是你的输出要求：{output}
```

#### 每一步记忆如何工作

**Step 1：庭审开始 → 初始化角色信息**

`CourtFlow` 创建 `CourtMemoryManager`，调用 `init_case_info()` 写入各 Agent 姓名。案件原始描述通过 `Agent.__init__` 直接嵌入 `role_prompt`，不写入记忆管理器。

**Step 2：每轮对话结束 → LLM 提炼摘要**

`update_round_summary()` 将本轮对话原文（最多 8000 字）发给 LLM，LLM 返回 `{"summary": "核心摘要", "key_points": ["要点1"]}`，结果追加到 `round_summaries` 并持久化。

**Step 3：Agent 发言前 → 构建结构化上下文**

`Agent.speech()` 调用 `build_memory_prompt()`：读取当前阶段 + role_info + 最近10轮摘要 + 短期记忆，填入 `AgentTemplate.txt` 的 `{history}` 占位符。

**关键设计原则：**
- 案件原始描述**不在** `build_memory_prompt` 中输出，避免重复冗余
- 过程层只保留 LLM 提炼的摘要，不保存原始对话流水账
- 最近 10 轮摘要足够 Agent 理解庭审进展

### 5. api.py - API调用模块

统一封装LLM API调用，支持：

- 流式/非流式输出
- 自动重试机制（默认10次）
- 统一的错误处理

### 6. main.py - 主程序

支持批量案件处理：

- 从指定文件夹读取JSON案件文件
- 批量并发执行（默认每批2个）
- 记录已完成案件，避免重复执行

## 辩论自动停止机制

系统采用双重机制判断辩论是否应停止：

### 1. 标签停止

Agent在无新意见时可回复"无补充辩论意见"

### 2. 相似度停止（默认启用）

使用Sentence-Transformers计算发言embedding相似度：

- 当 `similarity >= stop_threshold (0.8)` 时自动停止
- 避免双方重复相同观点
- 节约计算资源

### 3. 触发条件

- 仅在辩论进行2轮后生效
- 需要双方均无新意见才真正停止

## 使用方法

### 单案件测试

```python
from CourtFlow import flow
import json

with open('test_sample.json', 'r', encoding='utf-8') as f:
    test_sample = json.load(f)

flow(
    judge=test_sample['judge'],
    left_lawyer=test_sample['left_lawyer'],
    right_lawyer=test_sample['right_lawyer'],
    case=test_sample['case'],
    role_data=test_sample['role_data'],
    simulation_id='test_001'
)
```

### 批量处理

```python
from main import run_full_simulation_from_folder

folder_path = './data'  # JSON案件文件目录
run_full_simulation_from_folder(folder_path, batch_size=2)
```

### 命令行参数

```bash
python main.py \
    --api_model Qwen/Qwen3-8B \
    --api_url http://localhost:6699/v1 \
    --temperature 0.5 \
    --MAX_TURN 5 \
    --stop_threshold 0.8
```

## 案件数据格式

案件JSON文件需包含以下字段：

```json
{
    "judge": {"name": "法官姓名"},
    "left_lawyer": {"name": "原告律师姓名"},
    "right_lawyer": {"name": "被告律师姓名"},
    "case": {
        "name": "案件名称",
        "province": "省份",
        "city": "城市",
        "thirdType": "案件类型",
        "description": "案件描述",
        "indictmentDesc": "原告诉称",
        "indictmentProof": "原告证据",
        "pleadingsDesc": "被告辩称",
        "pleadingsProof": "被告证据",
        "plaintiffAware": "原告是否知晓被告证据",
        "defendantAware": "被告是否知晓原告证据"
    },
    "role_data": {"role": "robot"}
}
```

## 输出文件

程序运行后生成以下文件：


| 文件                                      | 说明           |
| --------------------------------------- | ------------ |
| `history_{simulation_id}.json`          | 庭审对话历史（完整记录） |
| `history_{simulation_id}_complete.json` | 最终完整记录       |
| `history_{simulation_id}.txt`           | 庭审对话文本版      |
| `memory_{simulation_id}.json`           | 长期记忆快照       |
| `simulation_log.txt`                    | 运行日志         |


## 技术特点

1. **多Agent协作**：通过角色分工模拟真实庭审场景
2. **智能停止机制**：避免无效辩论，提高效率
3. **记忆管理系统**：保持庭审上下文连贯性
4. **三次宣判机制**：提高判决结果稳定性
5. **批量处理能力**：支持大规模案件并行审理
6. **完整流程覆盖**：从立案到宣判全流程自动化

## 依赖环境

- Python 3.8+
- transformers
- sentence-transformers（可选，用于相似度停止）
- openai（API调用）
- 其他标准库（json, os, re, concurrent.futures等）


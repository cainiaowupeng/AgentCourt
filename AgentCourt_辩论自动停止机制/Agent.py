import time
from transformers import AutoModel, AutoTokenizer
from config import Config
from api import run_api
import re, requests, json
try:
    from sentence_transformers import SentenceTransformer, util, models  # type: ignore  # 新增zzj
except ModuleNotFoundError:
    SentenceTransformer = None  # type: ignore
    util = None  # type: ignore
    models = None  # type: ignore
transformer = models.Transformer(Config.embeddingmodel) if models is not None else None
pooling = (
    models.Pooling(
        1024,  # 或者你模型的实际维度，如768、1024等
        pooling_mode_mean_tokens=True,
        pooling_mode_cls_token=False,
        pooling_mode_max_tokens=False,
    )
    if models is not None
    else None
)
model = (
    SentenceTransformer(
        modules=[transformer, pooling],
        device="cpu",
    )
    if SentenceTransformer is not None and transformer is not None and pooling is not None
    else None
)


def process_court_internal(data):
    """
    模拟服务器端逻辑，处理数据并返回结果。
    """
    print("Processing data locally:", data)
    
    # 示例：对 data 进行处理
    processed_message = f"Processed message: {data.get('message', 'No message provided')}"
    
    # 返回处理后的结果
    return {"success": True, "message": processed_message}

def give_judgement(history, case_info, task, simulation_id):
    # 构造 prompt
    prompt = Config.judgement.format(
        history=history['text'],
        indictmentDesc=case_info["indictmentDesc"],
        indictmentProof=case_info["indictmentProof"],
        pleadingsDesc=case_info['pleadingsDesc'],
        pleadingsProof=case_info['pleadingsProof'],
        task=task,
        output=f'''1.你应该仔细分析以上信息并明确你的任务
2.你的回复应该是Markdown格式
3.你的回复内容会被直接用作输出，你不能在“### RESPONSE”中回复多余的内容
4.你的回复应该是纯文本格式'''
    )
    
    # 调用 API 获取响应
    origin_response = run_api(prompt)
    response = re.findall('### RESPONSE:(.*)', origin_response, re.DOTALL)[0].replace('\n\n', '\n').strip()
    
    # 更新 history
    history['text'] += f'<判决书>: {response}\n'
    history['dataset'].append({
        'role': '判决书',
        'role_desc': '判决书撰写',
        'prompt': prompt,
        'message': origin_response,
        'response': response,
        'human': False
    })
    
    # 本地处理逻辑替代 HTTP 请求
    process_result = process_court_internal({
        'simulation_id': simulation_id,
        'role': 'court_judgement',
        'role_desc': '判决书',
        'message': response
    })
    #print("Local processing result:", process_result)


class Agent(object):
    def __init__(self, case_info, role_name, simulation_id, role_info=None):
        self.simulation_id = simulation_id
        self.role_name = role_name
        self.role_info = role_info
        self.base_prompt = Config.base_prompt
        # 注入型记忆管理器（本案模拟内长期记忆 + 当前请求短期工作记忆）
        # 不影响原有逻辑：如果未设置，将保持原行为。
        self.memory_manager = None
        if role_name == 'judge':
            self.role_key = 'court_judge'
            self.role = '法官'
            self.name = self.role_info['name']
            self.case_info = {
                "name": case_info['name'],
                "province": case_info['province'],
                "city": case_info['city'],
                "thirdType": case_info['thirdType'],
                "description": case_info['description'],
                "indictmentDesc": case_info['indictmentDesc'],
                "indictmentProof": case_info['indictmentProof'],
                "pleadingsDesc": case_info['pleadingsDesc'],
                "pleadingsProof": case_info['pleadingsProof'],
                "plaintiffAware": case_info['plaintiffAware'],
                "defendantAware": case_info['defendantAware']
            }
            self.role_prompt = self.base_prompt.format(
                role=self.role,
                name=self.role_info['name'],
                self_description=Config.judge_prompt.format(
                    name=self.role_info["name"]
                ),
                role_settings=Config.role_settings[role_name],
                case_info=Config.judge_case_info.format(
                    province=self.case_info["province"],
                    city=self.case_info["city"],
                    thirdType=self.case_info["thirdType"],
                    name=self.case_info["name"],
                    description=self.case_info["description"],
                    indictmentDesc=self.case_info["indictmentDesc"],
                    indictmentProof=self.case_info["indictmentProof"],
                    pleadingsDesc=self.case_info['pleadingsDesc'],
                    pleadingsProof=self.case_info['pleadingsProof']
                ),
                history='{history}',
                task='{task}',
                output='{output}',
                example='{example}'
            )
        elif role_name == 'clerk':
            self.role_key = 'court_clerk'
            self.role = '书记员'
            self.name = '书记员1'
            self.case_info = {
                "name": case_info['name'],
                "province": case_info['province'],
                "city": case_info['city'],
                "thirdType": case_info['thirdType'],
                "description": case_info['description'],
                "indictmentDesc": case_info['indictmentDesc'],
                "indictmentProof": case_info['indictmentProof'],
                "pleadingsDesc": case_info['pleadingsDesc'],
                "pleadingsProof": case_info['pleadingsProof'],
                "plaintiffAware": case_info['plaintiffAware'],
                "defendantAware": case_info['defendantAware']
            }
            self.role_prompt = self.base_prompt.format(
                role=self.role,
                name=self.name,
                self_description='你是一个普通的书记员',
                role_settings=Config.role_settings[role_name],
                case_info=Config.judge_case_info.format(
                    province=self.case_info["province"],
                    city=self.case_info["city"],
                    thirdType=self.case_info["thirdType"],
                    name=self.case_info["name"],
                    description=self.case_info["description"],
                    indictmentDesc=self.case_info["indictmentDesc"],
                    indictmentProof=self.case_info["indictmentProof"],
                    pleadingsDesc=self.case_info['pleadingsDesc'],
                    pleadingsProof=self.case_info['pleadingsProof']
                ),
                history='{history}',
                task='{task}',
                output='{output}',
                example='{example}'
            )
        elif role_name == 'left':
            self.role_key = 'court_plaintiff'
            self.role = '原告'
            # self.name = case_info['left']   # 缺少原被告名字
            self.name = '原告'
            self.case_info = {
                "name": case_info['name'],
                "province": case_info['province'],
                "city": case_info['city'],
                "thirdType": case_info['thirdType'],
                "description": case_info['description'],
                "indictmentDesc": case_info['indictmentDesc'],
                "indictmentProof": case_info['indictmentProof'],
                "pleadingsDesc": case_info['pleadingsDesc'],
                "pleadingsProof": case_info['pleadingsProof'],
                "plaintiffAware": case_info['plaintiffAware'],
                "defendantAware": case_info['defendantAware']
            }
            self.plaintiffAware = ''
            if case_info['plaintiffAware']:
                self.plaintiffAware = f"\n这是被告的证据：\n{self.case_info['pleadingsProof']}"
            self.role_prompt = self.base_prompt.format(
                role=self.role,
                name=self.name,
                self_description='你是一个普通民众',
                role_settings=Config.role_settings[role_name],
                case_info=Config.left_case_info.format(
                    indictmentDesc=self.case_info["indictmentDesc"],
                    indictmentProof=self.case_info["indictmentProof"],
                ) + self.plaintiffAware,
                history='{history}',
                task='{task}',
                output='{output}',
                example='{example}'
            )
        elif role_name == 'left_lawyer':
            self.role_key = 'left_lawyer'
            self.role = '原告律师'
            self.name = self.role_info['name']
            self.case_info = {
                "name": case_info['name'],
                "province": case_info['province'],
                "city": case_info['city'],
                "thirdType": case_info['thirdType'],
                "description": case_info['description'],
                "indictmentDesc": case_info['indictmentDesc'],
                "indictmentProof": case_info['indictmentProof'],
                "pleadingsDesc": case_info['pleadingsDesc'],
                "pleadingsProof": case_info['pleadingsProof'],
                "plaintiffAware": case_info['plaintiffAware'],
                "defendantAware": case_info['defendantAware']
            }
            self.plaintiffAware = ''
            if case_info['plaintiffAware']:
                self.plaintiffAware = f"\n这是被告的证据：\n{self.case_info['pleadingsProof']}"
            self.role_prompt = self.base_prompt.format(
                role=self.role,
                name=self.role_info['name'],
                self_description=Config.lawyer_prompt.format(
                    name=self.role_info['name']
                ),
                role_settings=Config.role_settings[role_name],
                case_info=Config.left_case_info.format(
                    indictmentDesc=self.case_info["indictmentDesc"],
                    indictmentProof=self.case_info["indictmentProof"],
                ) + self.plaintiffAware,
                history='{history}',
                task='{task}',
                output='{output}',
                example='{example}'
            )
        elif role_name == 'right':
            self.role_key = 'court_defendant'
            self.role = '被告'
            # self.name = case_info['right']  # 缺少原被告名字
            self.name = '被告'
            self.case_info = {
                "name": case_info['name'],
                "province": case_info['province'],
                "city": case_info['city'],
                "thirdType": case_info['thirdType'],
                "description": case_info['description'],
                "indictmentDesc": case_info['indictmentDesc'],
                "indictmentProof": case_info['indictmentProof'],
                "pleadingsDesc": case_info['pleadingsDesc'],
                "pleadingsProof": case_info['pleadingsProof'],
                "plaintiffAware": case_info['plaintiffAware'],
                "defendantAware": case_info['defendantAware']
            }
            self.defendantAware = ''
            if case_info['defendantAware']:
                self.defendantAware = f"\n这是原告的证据：\n{self.case_info['indictmentProof']}"
            self.role_prompt = self.base_prompt.format(
                role=self.role,
                name=self.name,
                self_description='你是一个普通民众',
                role_settings=Config.role_settings[role_name],
                case_info=Config.right_case_info.format(
                    pleadingsDesc=self.case_info['pleadingsDesc'],
                    pleadingsProof=self.case_info['pleadingsProof']
                ) + self.defendantAware,
                history='{history}',
                task='{task}',
                output='{output}',
                example='{example}'
            )
        elif role_name == 'right_lawyer':
            self.role_key = 'right_lawyer'
            self.role = '被告律师'
            self.name = self.role_info['name']
            self.case_info = {
                "name": case_info['name'],
                "province": case_info['province'],
                "city": case_info['city'],
                "thirdType": case_info['thirdType'],
                "description": case_info['description'],
                "indictmentDesc": case_info['indictmentDesc'],
                "indictmentProof": case_info['indictmentProof'],
                "pleadingsDesc": case_info['pleadingsDesc'],
                "pleadingsProof": case_info['pleadingsProof'],
                "plaintiffAware": case_info['plaintiffAware'],
                "defendantAware": case_info['defendantAware']
            }
            self.defendantAware = ''
            if case_info['defendantAware']:
                self.defendantAware = f"\n这是原告的证据：\n{self.case_info['indictmentProof']}"
            self.role_prompt = self.base_prompt.format(
                role=self.role,
                name=self.role_info['name'],
                self_description=Config.lawyer_prompt.format(
                    name=self.role_info['name']
                ),
                role_settings=Config.role_settings[role_name],
                case_info=Config.right_case_info.format(
                    pleadingsDesc=self.case_info['pleadingsDesc'],
                    pleadingsProof=self.case_info['pleadingsProof']
                ) + self.defendantAware,
                history='{history}',
                task='{task}',
                output='{output}',
                example='{example}'
            )
        else:
            raise ValueError('Unaccepted Agent Role')

    def set_memory_manager(self, memory_manager):
        self.memory_manager = memory_manager

    def _history_with_memory(self, history_text, task, obj_role_key=None, round_counter=None):
        """
        把短期/长期记忆拼到 prompt 所需的 history 字段前面。
        """
        if not self.memory_manager:
            return history_text
        try:
            return self.memory_manager.build_history_text(
                history_text=history_text,
                task=task,
                actor_role_key=self.role_key,
                obj_role_key=obj_role_key,
                round_counter=round_counter,
            )
        except Exception:
            # 记忆注入失败时回退到原始 history，避免影响主流程
            return history_text

    def speech(self, task, history, example=None, stop_event=None, summary=False):
        if not example:
            example = 'XXX'
        output = '''1.你需要根据以上的所有信息进行一次发言
2.你只能做要求你做的内容，你不能擅自采取其他行动
3.你的回复内容会被直接用作输出，你不能讲多余的话
4.你的回复应该是纯文本格式'''
        history_text = self._history_with_memory(
            history_text=history['text'],
            task=task,
            obj_role_key=None,
            round_counter=None,
        )
        prompt = self.role_prompt.format(
            history=history_text,
            task=task,
            output=output,
            example=example
        )
        origin_response = run_api(prompt)
        response = re.findall('### RESPONSE:(.*)', origin_response, re.DOTALL)[0].replace('\n\n', '\n').strip()
        if summary:
            if self.role_key == 'left_lawyer':
                role_desc = '原告诉讼策略总结'
            elif self.role_key == 'right_lawyer':
                role_desc = '被告诉讼策略总结'
            elif self.role_key == 'court_judge':
                role_desc = '法官裁判要点总结'
            history['text'] += f'<{self.role}:{role_desc}>: {response}\n'
            history['dataset'].append({
                'role': self.role,
                'role_desc': role_desc,
                'prompt': prompt,
                'message': origin_response,
                'response': response,
                'human': False
            })
            process_result = process_court_internal({
                'simulation_id': self.simulation_id,
                'role': f"{self.role_key}_summary",
                'role_desc': role_desc,
                'message': response,
            })
            #print("Local processing result:", process_result)
        else:
            history['text'] += f'<{self.role}:{self.name}>: {response}\n'
            history['dataset'].append({
                'role': self.role,
                'name': self.name,
                'task': task,
                'prompt': prompt,
                'message': origin_response,
                'response': response,
                'human': False
            })
            process_result = process_court_internal({
                'simulation_id': self.simulation_id,
                'role': self.role_key,
                'role_desc': self.role,
                'name': self.name,
                'message': response,
                'task': "NA"
            })
        #print("Local processing result:", process_result)
        return response
    def ask(self, task, obj, task_obj, history, example=None, example_obj=None, stop_event=None,round_counter=0):
        plaintiff_no_new = 0  # Default value
        defendant_no_new = 0
        if not example:
            example = 'XXX'
        output = f'''1.你现在的说话对象是<{obj.role}:{obj.name}>
2.你需要根据以上的所有信息向<{obj.role}:{obj.name}>进行一次对话
3.你只能做要求你做的内容，你不能擅自采取其他行动
4.你的回复内容会被直接用作输出，你不能讲多余的话
5.你的回复应该是纯文本格式'''
        history_text_self = self._history_with_memory(
            history_text=history['text'],
            task=task,
            obj_role_key=obj.role_key if obj else None,
            round_counter=round_counter,
        )
        prompt = self.role_prompt.format(
            history=history_text_self,
            task=task,
            output=output,
            example=example
        )
        origin_response = run_api(prompt)
        response = re.findall('### RESPONSE:(.*)', origin_response, re.DOTALL)[0].replace('\n\n', '\n').strip()
        if round_counter >= 2:
            # 如果 embedding 相似度停止模块可用，就用“内容相似度”辅助停止；
            # 否则仅依赖 <stop> tag（保证程序在缺依赖时仍能运行）。
            if model is not None and util is not None:
                left_current_response_encode = model.encode(response)  # zzj新增
                left_history_response_encode = model.encode(history['dataset'][-2]['response'])  # zzj新增
                left_similarty = util.cos_sim(left_current_response_encode, left_history_response_encode)[0][0]  # zzj新增
                if '<stop>' in response or left_similarty >= Config.stop_threshold:  # If <stop> tag is found
                    print(f"Stopping free debate for {self.role_name} as <stop> was found.")
                    plaintiff_no_new = 1
            else:
                if '<stop>' in response:
                    print(f"Stopping free debate for {self.role_name} as <stop> was found.")
                    plaintiff_no_new = 1
        history['text'] += f'<{self.role}:{self.name}>: {response}\n'
        history['dataset'].append({
            'role': self.role,
            'name': self.name,
            'task': task,
            'prompt': prompt,
            'message': origin_response,
            'response': response,
            'human': False
        })
        process_result = process_court_internal({
            'simulation_id': self.simulation_id,
            'role': self.role_key,
            'role_desc': self.role,
            'name': self.name,
            'message': response,
            'task': "NA"
        })
        #print("Local processing result:", process_result)
        
        if not example_obj:
                example_obj = 'XXX'
        if task_obj != '决定是否补充辩论意见':
            output = f'''1.<{self.role}:{self.name}>正在和你对话
2.你需要根据以上的所有信息回答<{self.role}:{self.name}>
3.你只能做要求你做的内容，你不能擅自采取其他行动
4.你的回复内容会被直接用作输出，你不能讲多余的话
5.你的回复应该是纯文本格式'''
            history_text_obj = obj._history_with_memory(
                history_text=history['text'],
                task=task_obj,
                obj_role_key=self.role_key,
                round_counter=round_counter,
            )
            prompt = obj.role_prompt.format(
                    history=history_text_obj,
                    task=task_obj,
                    output=output,
                    example=example_obj
                )
            origin_response = run_api(prompt)
            response = re.findall('### RESPONSE:(.*)', origin_response, re.DOTALL)[0].replace('\n\n', '\n').strip()
            if round_counter >= 2:  # 只有在执行过2轮后才考虑停止
                # 如果 embedding 相似度停止模块可用，就用“内容相似度”辅助停止；
                # 否则仅依赖 <stop> tag（保证程序在缺依赖时仍能运行）。
                if model is not None and util is not None:
                    right_current_response_encode = model.encode(response)  # zzj新增
                    right_history_response_encode = model.encode(history['dataset'][-2]['response'])  # zzj新增
                    right_similarty = util.cos_sim(right_current_response_encode, right_history_response_encode)[0][0]  # zzj新增
                    if '<stop>' in response or right_similarty >= Config.stop_threshold:  # If <stop> tag is found
                        print(f"Stopping free debate for {obj.name} as <stop> was found.")
                        defendant_no_new = 1
                else:
                    if '<stop>' in response:
                        print(f"Stopping free debate for {obj.name} as <stop> was found.")
                        defendant_no_new = 1
                # 增加轮次信息到历史记录
            history['text'] += f'<{obj.role}:{obj.name}>: {response}\n'
            history['dataset'].append({
                    'role': obj.role,
                    'name': obj.name,
                    'task': task_obj,
                    'prompt': prompt,
                    'message': origin_response,
                    'response': response,
                    'human': False
            })
                # 将数据发送到服务器
            process_result = process_court_internal({
                    'simulation_id': obj.simulation_id,
                    'role': obj.role_key,
                    'role_desc': obj.role,
                    'name': obj.name,
                    'message': response,
                    'task': "NA"
                })
            if plaintiff_no_new == 1 and defendant_no_new == 1:
                print(f"原被告双方均无补充辩论意见")
                return 11
            return {'plaintiff_no_new': plaintiff_no_new, 'defendant_no_new': defendant_no_new}
        else:
            output = f'''1.<{self.role}:{self.name}>正在和你对话
2.你需要根据以上的所有信息回答<{self.role}:{self.name}>
3.如果你认为你不需要补充内容，请在你的“### RESPONSE”后增加”### RESULT: “，并在”### RESULT: “后回复”否“
4.如果你认为你还需要补充内容，请在你的“### RESPONSE”后增加”### RESULT: “，并在”### RESULT: “后回复”是“
5.你只能做要求你做的内容，你不能擅自采取其他行动
6.你的回复内容会被直接用作输出，你不能讲多余的话
7.你的回复应该是纯文本格式'''
            history_text_obj = obj._history_with_memory(
                history_text=history['text'],
                task=task_obj,
                obj_role_key=self.role_key,
                round_counter=round_counter,
            )
            prompt = obj.role_prompt.format(
                    history=history_text_obj,
                    task=task_obj,
                    output=output,
                    example=example_obj
                )
            while True:
                try:
                    origin_response = run_api(prompt)
                    response = re.findall('### RESPONSE:(.*)### RESULT', origin_response, re.DOTALL)[0].replace('\n\n', '\n').strip()
                    result = re.findall('### RESULT:(.*)', origin_response, re.DOTALL)[0].strip()
                    if result in ['是', '否']:
                        break
                except:
                    pass
            if response == '':
                    response = '审判长，我方认为无需进一步补充辩论意见，我方已就争议焦点进行了充分的法律依据和事实证据上的阐述。'
            history['text'] += f'<{obj.role}:{obj.name}>: {response}\n'
            history['dataset'].append({
                    'role': obj.role,
                    'name': obj.name,
                    'task': task_obj,
                    'prompt': prompt,
                    'message': origin_response,
                    'response': response,
                    'human': False
            })
                # 替换 HTTP 请求为本地处理逻辑
            process_result = process_court_internal({
                    'simulation_id': obj.simulation_id,
                    'role': obj.role_key,
                    'role_desc': obj.role,
                    'name': obj.name,
                    'message': response,
                    'task': "NA"
                })
            if result == "否":
                return 0
            else:
                return 1

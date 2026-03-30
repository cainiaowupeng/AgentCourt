import argparse, sys, os
from pathlib import Path
from data_loader import load

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]                          # root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))                  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

parser = argparse.ArgumentParser()
parser.add_argument('--api_model', default='Qwen/Qwen3-8B', type=str, help='Api Based Model Name')
parser.add_argument('--api_url', default='http://10.176.60.51:6699/v1', type=str, help='Api Based Model Url')
parser.add_argument('--api_key', default='abc123', type=str, help='Api Based Model Key')
parser.add_argument('--max_tokens', default=10000, type=int, help='Api Config of output_token. ')  #Config.max_tokens 降低（例如 600）再跑一次。
parser.add_argument('--temperature', default=0.5, type=float, help='Api Config of temperature. Range: (0, 2)')
parser.add_argument('--top_p', default=0.5, type=float, help='Api Config of top_p. Range: [0, 1]')
parser.add_argument('--frequency_penalty', default=0.5, type=float, help='Api Config of frequency_penalty. Range: [-2.0, 2.0]')
parser.add_argument('--presence_penalty', default=0.5, type=float, help='Api Config of presence_penalty. Range: [-2.0, 2.0]')
parser.add_argument('--log_dir', default='./logs/', type=str, help='Log Path Dictionary')
parser.add_argument('--prompt_template_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/AgentTemplate.txt', type=str, help='Base Prompt Template')
parser.add_argument('--prompt_judge_settings_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/JudgeSettings.txt', type=str, help='Judge Settings Prompt Template')
parser.add_argument('--prompt_lawyer_settings_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/LawyerSettings.txt', type=str, help='Lawyer Settings Prompt Template')
parser.add_argument('--prompt_judge_case_info_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/JudgeCaseInfoTemplate.txt', type=str, help='Prompt of Judge Cases Info')
parser.add_argument('--prompt_left_case_info_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/LeftCaseInfoTemplate.txt', type=str, help='Prompt of Left Case Info')
parser.add_argument('--prompt_right_case_info_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/RightCaseInfoTemplate.txt', type=str, help='Prompt of Right Case Info')
parser.add_argument('--prompt_judgement_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/JudgementTemplate.txt', type=str, help='Prompt of Judgement')
parser.add_argument('--prompt_check_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/CheckTemplate.txt', type=str, help='Prompt of Check')
parser.add_argument('--prompt_check_intention_path', default='/home/lzj/AgentCourt_辩论自动停止机制/prompts/IntentionCheckTemplate.txt', type=str, help='Prompt of Intention Check')
parser.add_argument('--role_setting_path', default=r'/home/lzj/AgentCourt_辩论自动停止机制/role_setting.json', type=str, help='Role Settings')
parser.add_argument('--sample_path', default='/home/lzj/AgentCourt_辩论自动停止机制/sample.json', type=str, help='Sample Data for test')
parser.add_argument('--MAX_TURN', default=5, type=int, help='Maximum Number of Disputing Turns')
parser.add_argument('--server_host', default='http://localhost:5010', type=str, help='Flask Base Front HOST')
parser.add_argument('--server_back_host', default='http://localhost:5010', type=str, help='Flask Base Back HOST')
parser.add_argument('--server_url_court_internal', default='/court/internal', type=str, help='Flask Base URL of Court Internal')
parser.add_argument('--server_url_human', default='/court/input', type=str, help='Flask Base Back URL of Human Interaction')

# parser.add_argument('--input_path', default='./input.json', type=str, help='Input File Path')
# parser.add_argument('--output_path', default='./output.json', type=str, help='Output File Path')
# parser.add_argument('--experience_path', default='./experience.json', type=str, help='Experience File Path')
# parser.add_argument('--filtration_path', default='./filtration.json', type=str, help='Filtration File Path')
# parser.add_argument('--output_dataset_path', default='./dataset.json', type=str, help='Output Dataset File Path for Supervised Fine-Tuning')
parser.add_argument('--MAX_RETRY', type=int, default=10, help='Maximum Retry Number of API Requests')
# parser.add_argument('--MAX_AUTH', type=int, default=10, help='Maximum Auth Number of Useless Params')
parser.add_argument('--stop_threshold', type=float, default=0.8, help='Threshold of Stop') ##zzj新增
parser.add_argument('--embeddingmodel', type=str, default='/home/fan/zhangzhijie/model/allmodel/BGEm3', help='Embedding Model') ##zzj新增

args = parser.parse_args()


class Config:
    # sample = load(args.sample_path)
    role_settings = load(args.role_setting_path)
    judge_prompt = load(args.prompt_judge_settings_path)
    lawyer_prompt = load(args.prompt_lawyer_settings_path)
    base_prompt = load(args.prompt_template_path)
    judge_case_info = load(args.prompt_judge_case_info_path)
    left_case_info = load(args.prompt_left_case_info_path)
    right_case_info = load(args.prompt_right_case_info_path)
    judgement = load(args.prompt_judgement_path)
    check = load(args.prompt_check_path)
    check_intention = load(args.prompt_check_intention_path)


for k, v in vars(args).items():
    setattr(Config, k, v)

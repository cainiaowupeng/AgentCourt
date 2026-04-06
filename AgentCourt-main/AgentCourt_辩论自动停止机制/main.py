import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from CourtFlow import flow
import uuid  # 用于生成唯一的 ID


def load_completed_cases(folder_path):
    """读取已完成案件的ID"""
    completed_cases_file = os.path.join(folder_path, "completed_cases.txt")  # 存储在 folder_path 下
    if os.path.exists(completed_cases_file):
        with open(completed_cases_file, 'r', encoding='utf-8') as file:
            return set(file.read().splitlines())  # 返回一个集合，包含所有已完成的案件ID
    return set()


def save_completed_case(folder_path, simulation_id):
    """将已完成案件的ID保存到文件"""
    completed_cases_file = os.path.join(folder_path, "completed_cases.txt")  # 存储在 folder_path 下
    with open(completed_cases_file, 'a', encoding='utf-8') as file:
        file.write(f"{simulation_id}\n")


def start_court_simulation_local(judge, left_lawyer, right_lawyer, case, role_data, simulation_id):
    """使用本地逻辑启动模拟法庭并返回 simulation_id"""
    print(f"正在处理案件 {simulation_id} ...")
    try:
        # 模拟启动逻辑，可以根据需要添加更多处理
        print(f"案件 {simulation_id} 启动成功")
        return simulation_id
    except Exception as e:
        print(f"案件 {simulation_id} 启动失败: {str(e)}")
        return None


def run_simulation_for_case(test_sample, completed_cases, folder_path):
    """为单个案件启动模拟法庭并调用 flow"""
    # 使用 "case" 中的 "name" 字段作为 simulation_id
    simulation_id = test_sample['case'].get('name', str(uuid.uuid4()))  # 如果没有 "name"，则生成一个唯一的 ID

    # 检查案件是否已经完成过
    if simulation_id in completed_cases:
        print(f"案件 {simulation_id} 已经完成，跳过...")
        return

    # 启动模拟法庭
    simulation_id = start_court_simulation_local(
        judge=test_sample['judge'],
        left_lawyer=test_sample['left_lawyer'],
        right_lawyer=test_sample['right_lawyer'],
        case=test_sample['case'],
        role_data=test_sample['role_data'],
        simulation_id=simulation_id
    )

    if simulation_id:
        print(f"案件 {simulation_id} 成功启动，正在运行模拟流程...")
        # 运行模拟法庭的整个流程
        flow(
            judge=test_sample['judge'],
            left_lawyer=test_sample['left_lawyer'],
            right_lawyer=test_sample['right_lawyer'],
            case=test_sample['case'],
            role_data=test_sample['role_data'],
            simulation_id=simulation_id
        )
        # 模拟完成后，保存案件ID到已完成文件
        save_completed_case(folder_path, simulation_id)
        print(f"案件 {simulation_id} 完成")
    else:
        print(f"案件 {simulation_id} 启动失败")


def run_full_simulation_from_folder(folder_path, batch_size=2):
    """从指定文件夹读取所有案件的 JSON 文件并批量并发执行"""
    # 加载已完成案件
    completed_cases = load_completed_cases(folder_path)

    # 获取文件夹中所有的 JSON 文件
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    print(f"找到 {len(json_files)} 个案件文件.")

    # 每次批量处理10个案件
    total_files = len(json_files)
    for i in range(0, total_files, batch_size):
        batch_files = json_files[i:i + batch_size]
        print(f"\n正在处理第 {i // batch_size + 1} 组 {len(batch_files)} 个案件...")

        # 创建一个线程池并发执行案件
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = []
            for file_name in batch_files:
                with open(os.path.join(folder_path, file_name), 'r', encoding='utf-8') as file:
                    test_sample = json.loads(file.read())
                    futures.append(executor.submit(run_simulation_for_case, test_sample, completed_cases, folder_path))

            # 等待所有任务完成并输出结果
            for future in as_completed(futures):
                future.result()

        print(f"第 {i // batch_size + 1} 组案件已全部完成.")


if __name__ == "__main__":
    folder_path = r"D:\AgentCourt-main\AgentCourt_辩论自动停止机制\data"  # 替换为你存放案件 JSON 文件的文件夹路径
    run_full_simulation_from_folder(folder_path)

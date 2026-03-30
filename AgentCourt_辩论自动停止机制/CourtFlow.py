from Agent import Agent, give_judgement
from config import Config
from data_loader import output
from memory import MemoryManager
import os
import requests
from collections import Counter
output_folder=r"/Users/linzhijie/Documents/AgentCourt/AgentCourt_辩论自动停止机制/output"


def flow(judge, left_lawyer, right_lawyer, case, role_data, simulation_id, stop_event=None):
    # Initialization
    case_info = case

    # 本案模拟内长期/短期记忆：
    # - 长期记忆仅保留在本次模拟（不跨case）
    # - 每轮自由辩论结束后更新一次长期记忆
    memory_manager = MemoryManager(
        case_info=case_info,
        simulation_id=simulation_id,
        output_folder=output_folder,
    )

    judge_agent = Agent(case_info=case_info, role_name='judge', role_info=judge, simulation_id=simulation_id)
    judge_agent.set_memory_manager(memory_manager)
    if role_data['role'] == 'robot':
        left_lawyer_agent = Agent(case_info=case_info, role_info=left_lawyer,
                                  role_name='left_lawyer', simulation_id=simulation_id)
        right_lawyer_agent = Agent(case_info=case_info, role_info=right_lawyer,
                                   role_name='right_lawyer', simulation_id=simulation_id)
        left_lawyer_agent.set_memory_manager(memory_manager)
        right_lawyer_agent.set_memory_manager(memory_manager)
    

    clerk_agent = Agent(case_info=case_info, role_name='clerk', simulation_id=simulation_id)
    left_agent = Agent(case_info=case_info, role_name='left', simulation_id=simulation_id)
    right_agent = Agent(case_info=case_info, role_name='right', simulation_id=simulation_id)
    clerk_agent.set_memory_manager(memory_manager)
    left_agent.set_memory_manager(memory_manager)
    right_agent.set_memory_manager(memory_manager)

    # init environment
    history = {
        'text': str(),
        'dataset': list()
    }

    # Start Simulation
    # TODO: 可以增加能看到下一个task，增加输出规范性
    # 庭审准备
    # 书记员宣布纪律
    clerk_agent.speech(task='首先宣布法庭纪律，其次交代庭前准备工作情况', history=history, example="现在宣布法庭纪律：\n一、审判人员进入法庭和审判长宣告法院判决时，全体人员应当起立。\n二、在庭审过程中，全体人员应当关闭移动电话、寻呼机或调至振动档。\n三、诉讼参与人应当遵守法庭规则，维护法庭秩序，不得喧哗、吵闹；发言、陈述和辩论，须经审判长许可。\n四、旁听人员必须遵守下列纪律：\n未经审判长许可，不得在庭审过程中录音、录像和摄影。\n不得随意走动和进入审判区。\n不得发言、提问。\n不得鼓掌、喧哗、哄闹和实施其他妨害审判活动的行为。\n旁听人员对法庭的审判活动有意见，可以在休庭后书面向人民法院提出。\n五、进入法庭的人员不得吸烟和随地吐痰。\n六、对于违反法庭纪律的人，审判长可以口头警告、训诫，也可以没收录音、录像和摄影器材，责令退出法庭或者经院长批准予以罚款、拘留。\n七、对哄闹、冲击法庭，侮辱、诽谤、威胁、殴打审判人员等严重扰乱法庭秩序的人，依法追究刑事责任；情节较轻的，予以罚款、拘留。\n法庭纪律宣读完毕，请全体起立，请审判长、审判员入庭。报告审判长，法庭准备工作就绪，可以开庭。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 法官宣布开庭，并核对当事人身份信息和代理人代理权限
    judge_agent.speech(task='宣布开庭，并核对当事人身份信息和代理人代理权限，同时要求原告先陈述', history=history, example="XXX庭公开审理XXX一案。下面核对核对当事人、诉讼代理人等人的身份。首先，由原告陈述自己的身份信息及诉讼代理人信息情况。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 原告陈述个人信息
    left_agent.speech(task='陈述自己的身份信息，如果是自然人，信息包括姓名、性别、出生年月、民族、住所地和身份证号码；如果是法人或组织，自己的身份信息包括法人名称、住所地、统一社会信用代码、法定代表人或负责人及其职务。诉讼代理人只需要名字和所在的律师事务所名称即可。', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 被告陈述个人信息
    right_agent.speech(task='陈述自己的身份信息，如果是自然人，信息包括姓名、性别、出生年月、民族、住所地和身份证号码；如果是法人或组织，自己的身份信息包括法人名称、住所地、统一社会信用代码、法定代表人或负责人及其职务。诉讼代理人只需要名字和所在的律师事务所名称即可。', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 法官询问原告对身份有无异议
    judge_agent.ask(task='询问原告对身份有无异议', obj=left_agent, task_obj='表明对身份没有异议', example='原告对对方到庭的当事人及其委托代理人的身份有无异议？', example_obj='没有。', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 法官询问被告对身份有无异议
    judge_agent.ask(task='询问被告对身份有无异议', obj=right_agent, task_obj='表明对身份没有异议', example='被告对对方到庭的当事人及其委托代理人的身份有无异议？', example_obj='没有。', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 法官告知双方的权力义务，并询问是否申请回避
    judge_agent.speech(task='首先宣布手续合法，准许参加本案诉讼；其次说明本案审判员和书记员；然后告知双方在法庭上享有的诉讼权利与应尽的诉讼义务；最后询问双方当事人是否听清，是否申请回避。', history=history, example='经法庭审查，各方当事人及其委托诉讼代理人诉讼手续合法，准许参加本案诉讼。此案审理适用简易程序，由本院审判员XXX独任审判，书记员XXX任法庭记录。下面告知双方当事人在法庭上享有的诉讼权利与应尽的诉讼义务：\n诉讼权利有:\n（1）申请回避的权利；\n（2）提出新证据的权利：\n（3）进行辩论，请求法庭予以调解的权利；\n（4）原告有放弃，变更，增加诉讼请求的权利，被告有对本诉进行反驳及反诉的权利；\n（5）最后陈述的权利；\n诉讼义务有:\n（1）听从法庭指挥，遵守法庭纪律的义务；\n（2）如实陈述事实的义务；\n（3）依法行使诉讼权利的义务。\n双方当事人是否听清楚了，是否申请回避？', stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 原告表明听清楚了且不申请回避
    left_agent.speech(task='表明听清楚了且不申请回避', history=history, example='听清楚了，不申请。', stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 被告表面听清楚了且不申请回避
    right_agent.speech(task='表明听清楚了且不申请回避', history=history, example='听清楚了，不申请。', stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    
    # 法庭调查
    # 原告宣读起诉书
    judge_agent.ask(task='宣布开始法庭调查，并要求原告明确其诉讼请求、事实和理由', obj=left_agent, task_obj='说明自己的诉讼请求，并阐明事实和理由，不得抄袭起诉状的内容', history=history, example="本庭现在进入法庭调查阶段。请原告宣读起诉状，明确诉讼请求、事实和理由。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}', history)
        return
    # 被告进行答辩
    judge_agent.ask(task='要求被告发表答辩意见', obj=right_agent, task_obj='针对原告的诉讼请求发表答辩意见', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}', history)
        return
    # 原告举证
    judge_agent.ask(task='要求原告进行举证', obj=left_lawyer_agent, task_obj='原告针对自己的诉讼请求进行举证，不得抄袭起诉状的内容，回复中不得包含“结尾敬辞”，并且要求针对诉讼请求、事实和理由进行举证，分条展开，每举出一份证据，详细说明该份证据所要证明的内容或事实是什么。', history=history, example="请原告就起诉状中陈述的事实和理由进行举证。", example_obj="审判长，针对我方所陈述的事实和理由，举证内容如下：XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 被告质证
    judge_agent.ask(task='要求被告进行质证', obj=right_lawyer_agent, task_obj='被告针对原告的举证进行质证，不得抄袭答辩状的内容，回复中不得包含”结尾敬辞“，并且要求针对原告提出的证据，逐个进行质证。质证时，对对方提供的证据的“关联性”、“合法性”和“真实性”发表意见。主要围绕以下几点展开分析：证据与待证事实之间是否存在关联；证据的来源主体是否合法、证据的收集方式是否合法、证据的程序是否合法、证据的种类是否合法以及证据的形式是否合法；证据是否真实，包括原件是否与复印件相符合、证据的内容能否反映案件的真实情况。质证意见表达可以分为以下六种：第一，无异议。也即对该证据的“三性”及证明力大小均无异议；第二，对“关联性”有异议。比如，对该证据的“关联性”有异议。因为该证据与待证事实无关；第三，对“合法性”有异议。比如，对该证据的“合法性”有异议。因为该证据是被告在被非法拘禁期间被迫写的，属于以严重侵害他人合法权益的方式取得的证据，取证方式不合法。还可以说：“该证据的证据主体、取得方式、证据程序、证据形式等不符合法律规定。” 比如说鉴定人员不具有鉴定的资格，就属于鉴定意见主体不合法；第四，对“真实性”有异议。比如，一方提供了证人的书面“情况说明”，但该情况说明阐述的内容与客观事实不符。此时可回答：对该证据的“真实性”有异议。因为该情况说明（书证内容）与客观事实不符，证人虚假陈述；第五，对“真实性”无法确认或无法表态。举例：有一份《合作协议》系对方和其他人签署的，我方不知道协议内容，也不知道协议是真是假。此时可回答：因为我方不是该证据的当事人，也不知道该证据的形成过程，对该证据的真实性无法确认（或无法发表质证意见），由法院认定。', history=history, example='请被告就原告的证据发表质证意见', example_obj="审判长，针对原告律师的举证内容，我方将依法进行质证。XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 被告举证
    judge_agent.ask(task='要求被告进行举证', obj=right_lawyer_agent, task_obj='被告针对自己的答辩意见进行举证，不得抄袭答辩状的内容，回复中不得包含“结尾敬辞”，并且要求针对被告的答辩意见或者待证事实进行举证，分条展开，每举出一份证据，详细说明该份证据所要证明的内容或事实是什么。', history=history, example="针对本案事实，请问被告是否有新的证据需要补充和说明。", example_obj="审判长，针对我方所陈述的事实和理由，举证内容如下：XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 原告质证
    judge_agent.ask(task='要求原告进行质证', obj=left_lawyer_agent, task_obj='原告针对被告的举证进行质证，不得抄袭起诉状的内容，回复中不得包含”结尾敬辞“，并且要求针对被告提出的证据，逐个进行质证。质证时，就是对对方提供的证据的“关联性”、“合法性”和“真实性”发表意见。主要围绕以下几点展开分析：证据与待证事实之间是否存在关联；证据的来源主体是否合法、证据的收集方式是否合法、证据的程序是否合法、证据的种类是否合法以及证据的形式是否合法；证据是否真实，包括原件是否与复印件相符合、证据的内容能否反映案件的真实情况。质证意见表达可以分为以下六种：第一，无异议。也即对该证据的“三性”及证明力大小均无异议；第二，对“关联性”有异议。比如，对该证据的“关联性”有异议。因为该证据与待证事实无关；第三，对“合法性”有异议。比如，对该证据的“合法性”有异议。因为该证据是被告在被非法拘禁期间被迫写的，属于以严重侵害他人合法权益的方式取得的证据，取证方式不合法。还可以说：“该证据的证据主体、取得方式、证据程序、证据形式等不符合法律规定。” 比如说鉴定人员不具有鉴定的资格，就属于鉴定意见主体不合法；第四，对“真实性”有异议。比如，一方提供了证人的书面“情况说明”，但该情况说明阐述的内容与客观事实不符。此时可回答：对该证据的“真实性”有异议。因为该情况说明（书证内容）与客观事实不符，证人虚假陈述；第五，对“真实性”无法确认或无法表态。举例：有一份《合作协议》系对方和其他人签署的，我方不知道协议内容，也不知道协议是真是假。此时可回答：因为我方不是该证据的当事人，也不知道该证据的形成过程，对该证据的真实性无法确认（或无法发表质证意见），由法院认定。', history=history, example='请原告就被告的证据发表质证意见', example_obj="审判长，针对被告律师的举证内容，我方将依法进行质证。XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 原告补充
    judge_agent.ask(task='询问原告是否发问', obj=left_lawyer_agent, task_obj='决定不向被告发问', history=history, example="针对被告提交的证据及其答辩意见？请问原告是否需要进一步发问或补充说明？", example_obj="审判长，我方不需要进一步发问或补充说明。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 被告补充
    judge_agent.ask(task='询问被告是否发问', obj=right_lawyer_agent, task_obj='决定不向原告发问', history=history, example="针对原告提交的证据及其答辩意见？请问被告是否需要进一步发问或补充说明？", example_obj="审判长，我方不需要进一步发问或补充说明。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 法庭调查结束
    judge_agent.speech(task='宣布法庭调查结束，无需评议和休庭，开始进入下一个环节', history=history, example="现在法庭调查阶段结束。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return

    # 法庭辩论
    # 法官归纳争议焦点
    judge_agent.speech(task='总结争议焦点，并宣布法庭辩论开始', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 原告发表意见
    judge_agent.ask(task='直接要求对方发表辩论意见，不需要展开陈述', obj=left_lawyer_agent, task_obj='发表辩论意见，不得与在法庭调查阶段已经发表过的意见相同', history=history, example="请原告围绕本案的争议焦点发表答辩意见。", example_obj="审判长，我方的辩论意见如下：XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 被告发表意见
    judge_agent.ask(task='直接要求对方发表辩论意见，不需要展开陈述', obj=right_lawyer_agent, task_obj='发表辩论意见，不得与在法庭调查阶段已经发表过的意见相同', history=history, example="请被告围绕本案的争议焦点发表辩论意见。", example_obj="审判长，我方的辩论意见如下：XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 自由辩论
    for i in range(Config.MAX_TURN):
        result=left_lawyer_agent.ask(task='若本轮有新意见则发表辩论意见，请确保内容不与在法庭调查阶段已经发表过的意见重复，且不重复援引相同的法律依据或立场观点。辩论的目的是向法庭说明为何应支持我的诉求，而对方的答辩应当被驳回。辩论时可以从以下角度展开：第一，围绕本案的争议焦点发表辩论内容，本案的争议焦点不局限于法官总结的争议焦点，自己也可以思考是否还有其他没有被提到的争议焦点；第二，在围绕争议焦点发表意见时，要判断对方是否隐瞒一些证据或者，存在的虚假陈述内容或者证据，或者对方有哪些陈述矛盾的地方来反驳对方陈述的事实和证据；第三，在驳斥对方陈述的事实和证据时，要顺带提出或主张自己认为的法律事实以及自己的证据为何能够充分支撑自己的诉求；第四，主张本案应从何种角度裁判是合情合理的，引导以下法官的思维；第五，法律条文如何正确理解，判断对方对引述的法律规范的理解是否正确，同时积极援引先行的法律法规、部门规章、司法解释或者类案判决来增强自己的辩论说服力，以支持自己的诉求。若本轮无新意见，必须回复"无补充辩论意见<stop>"。', obj=right_lawyer_agent, task_obj='若本轮有新意见则发表辩论意见，请确保内容不与在法庭调查阶段已经发表过的意见重复，且不重复援引相同的法律依据或立场观点。辩论的目的是向法庭说明为何应支持我的诉求，而对方的答辩应当被驳回。辩论时可以从以下角度展开：第一，围绕本案的争议焦点发表辩论内容，本案的争议焦点不局限于法官总结的争议焦点，自己也可以思考是否还有其他没有被提到的争议焦点；第二，在围绕争议焦点发表意见时，要判断对方是否隐瞒一些证据或者，存在的虚假陈述内容或者证据，或者对方有哪些陈述矛盾的地方来反驳对方陈述的事实和证据；第三，在驳斥对方陈述的事实和证据时，要顺带提出或主张自己认为的法律事实以及自己的证据为何能够充分支撑自己的诉求；第四，主张本案应从何种角度裁判是合情合理的，引导以下法官的思维；第五，法律条文如何正确理解，判断对方对引述的法律规范的理解是否正确，同时积极援引先行的法律法规、部门规章、司法解释或者类案判决来增强自己的辩论说服力，以支持自己的诉求。若本轮无新意见，必须回复"无补充辩论意见<stop>"。', history=history, stop_event=stop_event,round_counter=i)
        # 每轮自由辩论都更新一次长期记忆（本案模拟内）。
        # 由于 Agent.ask() 已经把这一轮双方的两段发言写入 history，这里直接从 history 中取最近两条更新。
        try:
            memory_manager.update_from_free_debate_round(history=history, round_counter=i)
        except Exception:
            # 记忆更新失败不应影响主流程
            pass
        if result==11 :
            break
        if stop_event and stop_event.is_set():
            print(f'Tread {simulation_id} Stopped')
            output(f'{output_folder}/history_{simulation_id}.json', history)
            return
    # 法官询问原告是否需要补充
    flag = judge_agent.ask(task='询问对方是否需要补充辩论意见', obj=left_lawyer_agent, task_obj='决定是否补充辩论意见', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    if flag:
        right_lawyer_agent.speech(task='发表辩论意见', history=history, stop_event=stop_event)
        if stop_event and stop_event.is_set():
            print(f'Tread {simulation_id} Stopped')
            output(f'{output_folder}/history_{simulation_id}.json', history)
            return
            # 法官询问被告是否需要补充
    flag = judge_agent.ask(task='询问对方是否需要补充辩论意见', obj=right_lawyer_agent, task_obj='决定是否补充辩论意见', history=history, stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    if flag:
        left_lawyer_agent.speech(task='发表辩论意见', history=history, stop_event=stop_event)
        if stop_event and stop_event.is_set():
            print(f'Tread {simulation_id} Stopped')
            output(f'{output_folder}/history_{simulation_id}.json', history)
            return

    # 最后陈述与宣判
    # 原告作最后陈述
    judge_agent.ask(task='宣布法庭辩论结束，并要求对方作最后陈述', obj=left_lawyer_agent, task_obj='陈述最后意见', history=history, example="现在法庭辩论阶段结束。请原告作最后陈述。", example_obj="审判长，我方的最后陈述如下：XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 被告作最后陈述
    judge_agent.ask(task='要求对方作最后陈述', obj=right_lawyer_agent, task_obj='陈述最后意见', history=history, example="请被告作最后陈述。", example_obj="审判长，我方的最后陈述是：XXX。", stop_event=stop_event)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # 法庭宣判：同一提示词，独立三次，取众数
    def _extract_verdict(text):
        if '原告胜诉' in text:
            return '原告胜诉'
        if '原告败诉' in text:
            return '原告败诉'
        return '未识别'

    verdicts = []
    base_history_snapshot = {
        'text': history['text'],
        'dataset': list(history['dataset'])
    }
    for idx in range(3):
        temp_history = {
            'text': base_history_snapshot['text'],
            'dataset': list(base_history_snapshot['dataset'])
        }
        response = judge_agent.speech(
            task='首先宣布庭审结束，其次进行评议，发表一下法官的意见，最后依法作出判决。并且要求在法院认为部分包括对双方的证据是如何认定的；对本案的争议焦点是如何认定；对原告方提出的诉求是否支持以及相应的理由。另外，法院应该从中立者的立场，根据原被告提供的证据从关联性、真实性、合法性进行逐个认定。最后，在判决结果中要给出原告胜诉还是败诉，注意必须从原告胜诉或者原告败诉两个选项中选择，不得出现其他模棱两可的回答。',
            history=temp_history,
            stop_event=stop_event,
            example='本案经过法庭调查、举证质证及法庭辩论，本院认为：XXX。本庭现作出如下判决：XXX。本次案件中原告败诉。'
        )
        history['text'] += f'<{judge_agent.role}:{judge_agent.name}-第{idx + 1}次宣判>: {response}\n'
        if temp_history['dataset']:
            history['dataset'].append({**temp_history['dataset'][-1], 'round': idx + 1})
        verdicts.append(_extract_verdict(response))
        if stop_event and stop_event.is_set():
            print(f'Tread {simulation_id} Stopped')
            output(f'{output_folder}/history_{simulation_id}.json', history)
            return

    counted = [v for v in verdicts if v in ['原告胜诉', '原告败诉']]
    final_verdict = Counter(counted).most_common(1)[0][0] if counted else '未识别'
    history['text'] += f'<最终宣判结果>: 三次宣判分别为：{verdicts}，多数意见为：{final_verdict}\n'
    history['dataset'].append({
        'role': '系统',
        'role_desc': '最终宣判统计',
        'verdicts': verdicts,
        'final_verdict': final_verdict
    })
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return

    # 出具判决书
    give_judgement(history=history, case_info=case_info, task='撰写一篇书面判决书。', simulation_id=simulation_id)
    if stop_event and stop_event.is_set():
        print(f'Tread {simulation_id} Stopped')
        output(f'{output_folder}/history_{simulation_id}.json', history)
        return
    # # 法官裁判要点总结
    # judge_agent.speech(history=history, task='撰写法官裁判要点总结。法官裁判要点中主要包含事实认定；争议焦点；法律适用；法律论证；裁判结果。', stop_event=stop_event, summary=True)
    # if stop_event and stop_event.is_set():
    #     print(f'Tread {simulation_id} Stopped')
    #     output(f'{output_folder}/history_{simulation_id}.json', history)
    #     return
    # # # 原告诉讼策略总结
    # left_lawyer_agent.speech(history=history, task='撰写原告方的诉讼策略总结。诉讼应对策略中应该包含从原告律师角度提出的诉讼策略以及从被告律师角度提出的诉讼策略。每一点的内容都应该进行详细描述。要求在诉讼策略中，你应该指出对方的证据漏洞或瑕疵，包括证据的关联性、合法性和真实性。并找出现行法律法规、部门规章、司法解释等相关规定，反驳对方的观点和立场。以及识别相关的司法判例，通过类案判决支持自己的观点和立场，反驳对方的观点和立场。', stop_event=stop_event, summary=True)
    # if stop_event and stop_event.is_set():
    #     print(f'Tread {simulation_id} Stopped')
    #     output(f'{output_folder}/history_{simulation_id}.json', history)
    #     return
    # # 被告方诉讼策略总结
    # right_lawyer_agent.speech(history=history, task='撰写被告方的诉讼策略总结。诉讼应对策略中应该包含从原告律师角度提出的诉讼策略以及从被告律师角度提出的诉讼策略。每一点的内容都应该进行详细描述。要求在诉讼策略中，你应该指出对方的证据漏洞或瑕疵，包括证据的关联性、合法性和真实性。并找出现行法律法规、部门规章、司法解释等相关规定，反驳对方的观点和立场。以及识别相关的司法判例，通过类案判决支持自己的观点和立场，反驳对方的观点和立场。', stop_event=stop_event, summary=True)
    # if stop_event and stop_event.is_set():
    #     print(f'Tread {simulation_id} Stopped')
    #     output(f'{output_folder}/history_{simulation_id}.json', history)
    #     return

    # End Simulation
    # 保存最终长期记忆（本案模拟内）用于观察和调试
    try:
        if memory_manager:
            memory_manager.save(os.path.join(output_folder, f"memory_{simulation_id}.json"))
    except Exception:
        pass
    # 替换 HTTP 回调为本地日志记录
    log_message = f"Simulation {simulation_id} Finished"
    log_file = f"{output_folder}/simulation_log.txt"
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(log_message + '\n')
    print(log_message)
    output(f'{output_folder}/history_{simulation_id}_complete.json', history)
    with open(f'{output_folder}/history_{simulation_id}_complete.txt', 'w', encoding='utf-8') as file:
        file.write(history['text'])


if __name__ == '__main__':
    '''
    left_lawyer -> 原告律师
    right_lawyer -> 被告律师
    '''
    import json
    with open('./test_sample_0830.json', 'r', encoding='utf-8') as file:
        test_sample = json.loads(file.read())
    flow(
        judge=test_sample['judge'],
        left_lawyer=test_sample['left_lawyer'],
        right_lawyer=test_sample['right_lawyer'],
        case=test_sample['case'],
        role_data=test_sample['role_data'],
        simulation_id='simulation_Qwen2.5-14B-Instruct'
    )

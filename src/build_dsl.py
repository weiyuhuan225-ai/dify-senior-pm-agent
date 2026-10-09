from pathlib import Path
import copy,json,uuid,yaml

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
KIT=PROJECT
TEMPLATES=ROOT/'templates'
OUTPUT=PROJECT/'dist'
OUTPUT.mkdir(exist_ok=True)
SEED=yaml.safe_load((TEMPLATES/'app_base.yml').read_text())
REG=json.loads((ROOT/'registry.json').read_text())
RUNTIME=(ROOT/'runtime.py').read_text().replace('REGISTRY = {}','REGISTRY = '+repr(REG))

def uid():return str(uuid.uuid4())
def node(i,title,typ,data=None,x=0,y=0):
    return {'id':i,'type':'custom','data':{'type':typ,'title':title,'desc':'','selected':False,**(data or {})},
            'position':{'x':x,'y':y},'positionAbsolute':{'x':x,'y':y},'sourcePosition':'right',
            'targetPosition':'left','width':242,'height':100,'selected':False}
def edge(a,b,types,handle='source'):
    return {'id':a+'-'+handle+'-'+b,'type':'custom','source':a,'sourceHandle':handle,'target':b,'targetHandle':'target',
            'data':{'sourceType':types[a],'targetType':types[b],'isInIteration':False,'isInLoop':False},'zIndex':0}
def code(i,title,wrapper,inputs,outputs,x=0,y=0,full=True):
    body=(RUNTIME+'\n\n' if full else '')+wrapper
    return node(i,title,'code',{'code_language':'python3','code':body,
        'variables':[{'variable':k,'value_selector':v,'value_type':'string'} for k,v in inputs.items()],
        'outputs':{k:{'type':v,'children':None} for k,v in outputs.items()}},x,y)
def base(name,mode='workflow'):
    d=copy.deepcopy(SEED);d['app'].update(name=name,mode=mode,description='独立的产品经理问答与需求访谈助手：澄清想法、审查需求、生成可追溯的PRD草案。')
    d['dependencies']=[];d['workflow']['conversation_variables']=[]
    d['workflow']['graph']={'nodes':[],'edges':[],'viewport':{'x':20,'y':80,'zoom':0.65}}
    return d
def write(d,name):
    p=OUTPUT/name;p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=100000));print(p)

def tool_dsl(which):
    guide=which=='guide'
    name='PM 问答 · 需求指南' if guide else 'PM 问答 · PRD 成稿'
    d=base(name)
    fields=[('section_id','number','章节编号 1 至 10'),('slot_ids_json','paragraph','字段 key 数组的 JSON 字符串，如 ["user_goals"]')] if guide else [('snapshot_json','paragraph','已审查冻结的会话状态 JSON'),('review_notes_json','paragraph','已披露风险 JSON 数组')]
    start=node('start','输入参数','start',{'variables':[{'variable':k,'label':label,'type':t,'required':True,'max_length':60000,'options':[]} for k,t,label in fields]},80,200)
    result={'guide_json':'string'} if guide else {'markdown':'string','content_hash':'string'}
    wrapper='def main(section_id: float, slot_ids_json: str) -> dict:\n    return tool_guide(section_id,slot_ids_json)' if guide else 'def main(snapshot_json: str, review_notes_json: str) -> dict:\n    return tool_render(snapshot_json,review_notes_json)'
    c=code('code','只读字段指南' if guide else '校验快照并渲染十章',wrapper,{k:['start',k] for k,_,_ in fields},result,400,200)
    end=node('end','输出','end',{'outputs':[{'variable':k,'value_selector':['code',k],'value_type':v} for k,v in result.items()]},730,200)
    nodes=[start,c,end];types={n['id']:n['data']['type'] for n in nodes}
    d['workflow']['graph'].update(nodes=nodes,edges=[edge('start','code',types),edge('code','end',types)])
    write(d,'T01_get_slot_guide.yml' if guide else 'T02_render_prd.yml')

def switch(i,title,source,values,x,y):
    cases=[]
    for v in values:
        cases.append({'id':v,'case_id':v,'logical_operator':'and','conditions':[{'id':uid(),'varType':'string','variable_selector':source,'comparison_operator':'is','value':v}]})
    return node(i,title,'if-else',{'cases':cases},x,y)

def llm(i,title,system,user,schema,x,y):
    data={'context':{'enabled':False,'variable_selector':[]},
          'model':{'provider':'langgenius/deepseek/deepseek','name':'deepseek-flash','mode':'chat','completion_params':{'temperature':0.1,'max_tokens':6000,'thinking':False}},
          'prompt_template':[{'id':uid(),'role':'system','text':system},{'id':uid(),'role':'user','text':user}],
          'vision':{'enabled':False},'structured_output_enabled':True,'structured_output':{'schema':schema},
          'retry_config':{'retry_enabled':True,'max_retries':1,'retry_interval':1000},
          'error_strategy':'default-value','default_value':[{'key':'text','type':'string','value':'{}'},{'key':'structured_output','type':'object','value':'{}'}]}
    return node(i,title,'llm',data,x,y)

def chatflow():
    seed=yaml.safe_load((TEMPLATES/'agent_and_tool.yml').read_text())
    agent=copy.deepcopy(next(n['data'] for n in seed['workflow']['graph']['nodes'] if n['data']['type']=='agent'))
    tool=copy.deepcopy(next(n['data'] for n in seed['workflow']['graph']['nodes'] if n['data']['type']=='tool'))
    d=base('产品经理问答 Agent','advanced-chat');d['dependencies']=[v for v in yaml.safe_load((TEMPLATES/'plugins.yml').read_text())['dependencies'] if 'openai:' not in v['value']['marketplace_plugin_unique_identifier']]
    prior=PROJECT/'dify'/'pm_qa_agent.yml'
    session_id=yaml.safe_load(prior.read_text())['workflow']['conversation_variables'][0]['id'] if prior.exists() else uid()
    w=d['workflow'];w['conversation_variables']=[{'id':session_id,'name':'session_json','description':'21字段唯一事实源，精确版本确认。','selector':['conversation','session_json'],'value':'{}','value_type':'string'}]
    w['features']['opening_statement']='我是你的产品经理问答助手。你可以带着一个想法来，我会陪你理清用户、问题和产品边界；也可以直接问我产品方法。\n\n先聊聊：你想做什么，或者现在卡在哪个问题？\n\n不会回答时可以让我给建议；想先放下某项就说“跳过”。随时可以查看草稿或审查需求，生成前我会请你确认。'
    w['features']['suggested_questions']=['我有个想法，想请你帮我梳理。','MVP 是什么，怎样划定第一版范围？']
    ext=(KIT/'prompts/01_extractor.md').read_text()+'''\n\n实施契约：
非实体字段 value_json 必须编码为字符串。六类实体字段必须编码为对象或对象数组；新增实体的 id 使用 tmp_ 前缀，持久 ID 由程序分配。已有实体必须沿用当前状态的 ID，upsert 只需列改变的字段。禁止用 set 清空整个实体数组。文本字段 set 需要结合旧值保留未被修改的限制。
实体格式：business_goals/user_goals: {id,text}；persona_details:{id,text,context}；user_stories:{id,text,persona_id,goal_ids:[]}；functional_requirements:{id,text,story_ids:[],acceptance_criteria:[]}；success_metrics:{id,name,type,goal_ids:[],definition,baseline,target,timeframe}。未知指标值用 _TBD_，绝不能用0。
只有用户已明确表达的内容可写入 updates；可以忠实压缩文字，不能自行增加画像、目标、故事、指标。若故事缺已知画像引用，先记录功能或概述，暂不制造不明引用；同一轮明确给出的画像/故事可以用 tmp_ID 互相引用。
新实体每个 tmp_ID 全局唯一。本轮不触及的数据不能进入 updates。evidence_quote 必须是本轮原话的连续原样子串。引用的历史事实可用其已有ID，不能拿历史原话充当本轮证据。
一轮内容同时回答多个字段时全部提取。模糊描述“更快”“更好用”可记入概述或待澄清 ambiguities，不把它伪装成可测指标。
同一句话可以命中多个字段，不能因为已放入project_summary就省略具体字段。明确用户对象同时写key_user_types；明确“不做X”同时写non_goals；已说明功能行为同时写functional_requirements（未知story_ids可为空）；明确入口写entry_points。只归入概述会使后续重复追问，禁止这样遗漏。
“不知道/不清楚/我不会回答”表示需要帮助，不是跳过：不写入任何更新，intent=help。只有明确说跳过/待定才可标记字段。与概念解释、方法咨询有关的问题用intent=help，禁止把疑问当成已确认需求。用户如果既问问题又提供事实，可以正常提取其中明确的事实。
用户接受已展示建议时用 accept_proposal 并引用D-ID；不要重新复制模型建议冒充用户原创事实。多个建议且含糊“可以”时返回 ambiguity。
本节点优先提取，不主动提出新建议。无新事实时返回空updates，禁止为了充实结果编造。
字段白名单与说明：\n'''+json.dumps(REG,ensure_ascii=False)
    ext_schema=json.loads((KIT/'schemas/extractor_output.schema.json').read_text())
    ext+='''\n最终输出前逐项检查：business_goals、user_goals、persona_details、user_stories、functional_requirements、success_metrics 的 value_json 绝不能是普通文字。必须是序列化的 JSON 数组。标量字段 entity_id 留空；实体使用 upsert，entity_id 留空并在每个对象内写 id。
例：用户说“主要想省时间，之前大概40分钟，希望10分钟，试用两周”，当前无目标或指标时，updates 应类似：
'''+json.dumps([
{'slot_id':'user_goals','operation':'upsert','entity_id':'','value_json':json.dumps([{'id':'tmp_goal1','text':'节省时间'}],ensure_ascii=False),'evidence_quote':'主要想省时间','source_kind':'user','proposal_id':''},
{'slot_id':'success_metrics','operation':'upsert','entity_id':'','value_json':json.dumps([{'id':'tmp_metric1','name':'任务平均耗时','type':'用户','goal_ids':['tmp_goal1'],'baseline':'用户估计40分钟','target':'10分钟','timeframe':'试用两周','definition':'_TBD_'}],ensure_ascii=False),'evidence_quote':'之前大概40分钟，希望10分钟，试用两周','source_kind':'user','proposal_id':''}],ensure_ascii=False)+'''\n此例只说明编码，不是项目事实。必须用本轮原话取值。实体之间的已知对应关系必须引用临时/既有ID；不要漏掉明确同一主题的目标指标关联。'''
    props=ext_schema['properties']['updates']['items']['properties']
    props['value_json']['description']='JSON.stringify(value) 的结果。user_goals/business_goals/persona_details/user_stories/functional_requirements/success_metrics 必须序列化对象数组，其他字段序列化文字。'
    props['entity_id']['description']='通常留空；仅删除实体时使用已有持久ID。新对象ID在 value_json 内使用 tmp_ 前缀。'
    review_schema={'type':'object','additionalProperties':False,'properties':{'overall':{'type':'string','enum':['PASS','FAIL','UNKNOWN']},'issues':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'id':{'type':'string'},'severity':{'type':'string'},'refs':{'type':'array','items':{'type':'string'}},'finding':{'type':'string'},'suggested_question':{'type':'string'}},'required':['id','severity','refs','finding','suggested_question']}}},'required':['overall','issues']}
    strings=lambda names:{k:'string' for k in names.split()}
    n=[]
    n.append(node('start','N01 用户输入','start',{'variables':[]},40,500))
    n.append(code('begin','N02 命令与确认门禁','def main(session_json: str, query: str) -> dict:\n    return begin(session_json,query)',{'session_json':['conversation','session_json'],'query':['sys','query']},strings('route state_json next_session_json answer_markdown snapshot_json review_notes_json'),350,500))
    n.append(switch('route','N03 输入路由',['begin','route'],['normal','control','generate'],670,500))
    n.append(llm('extract','N04 本轮信息提取',ext,'当前唯一事实源：\n{{#begin.state_json#}}\n本轮用户原话：\n{{#sys.query#}}',ext_schema,980,200))
    n.append(code('merge','N05–06 原子合并与调度','def main(state_json: str, patch_text: str, query: str) -> dict:\n    return merge(state_json,patch_text,query)',{'state_json':['begin','state_json'],'patch_text':['extract','text'],'query':['sys','query']},strings('route state_json next_session_json answer_markdown allowed_slots audit_json context_json'),1290,200))
    n.append(code('command','显式操作 无需信息提取','def main(state_json: str, query: str) -> dict:\n    return merge(state_json,"",query)',{'state_json':['begin','state_json'],'query':['sys','query']},strings('route state_json next_session_json answer_markdown allowed_slots audit_json context_json'),1290,500))
    prepared_groups=[{'groupId':uid(),'group_name':key,'output_type':'string','variables':[[i,key] for i in ['merge','command']]} for key in 'route state_json next_session_json answer_markdown allowed_slots audit_json context_json'.split()]
    n.append(node('prepared','汇合本轮信息','variable-aggregator',{'output_type':'string','variables':[],'advanced_settings':{'group_enabled':True,'groups':prepared_groups}},1600,260))
    n.append(switch('decide','N07 访谈或审查',['prepared','route','output'],['interview','review'],1910,200))
    # Reuse sanitized node shapes. Rebind workflow tools in the target Dify workspace.
    agent.update(title='N08 Senior PM 访谈 Agent',selected=False)
    agent['agent_parameters']['instruction']['value']=(ROOT/'interviewer.md').read_text()
    agent['agent_parameters']['query']={'type':'constant','value':'本轮用户输入：{{#sys.query#}}\n规范状态与允许字段：{{#prepared.context_json.output#}}'}
    agent['agent_parameters']['model']['value'].update(provider='langgenius/deepseek/deepseek',model='deepseek-flash',completion_params={'max_tokens': 3000, 'temperature': 0.3, 'thinking': False})
    agent['agent_parameters']['maximum_iterations']={'type':'constant','value':3}
    agent['error_strategy']='default-value';agent['default_value']=[{'key':'text','type':'string','value':'{}'},{'key':'json','type':'array[object]','value':'[]'}]
    n.append(node('interview',agent.pop('title'),'agent',{k:v for k,v in agent.items() if k not in {'type','selected'}},1930,0))
    n.append(code('reply','N09 校验问题与固定追问降级','def main(state_json: str, agent_text: str, allowed_slots: str) -> dict:\n    return finish_interview(state_json,agent_text,allowed_slots)',{'state_json':['prepared','state_json','output'],'agent_text':['interview','text'],'allowed_slots':['prepared','allowed_slots','output']},strings('next_session_json answer_markdown'),2550,0))
    n.append(llm('semantic','N11 语义一致性审查',(KIT/'prompts/03_semantic_reviewer.md').read_text()+'\n只检查明确事实之间的冲突。TBD/缺失不等于冲突：仅因缺失无法判断时用UNKNOWN，不要写FAIL。已由规则审查列出的TBD无需逐项重复。FAIL必须指出相互矛盾的两条已记录内容。最多列5个最重要问题，refs必须来自输入真实slot或实体ID。','canonical_state_json:\n{{#prepared.state_json.output#}}\nrule_audit_json:\n{{#prepared.audit_json.output#}}',review_schema,2240,350))
    n.append(code('review','N12 十章摘要与风险快照','def main(state_json: str, semantic_text: str) -> dict:\n    return finish_review(state_json,semantic_text)',{'state_json':['prepared','state_json','output'],'semantic_text':['semantic','text']},strings('next_session_json answer_markdown'),2550,350))
    passthrough='def main(state: str, answer: str) -> dict:\n    return {"next_session_json":state,"answer_markdown":answer}'
    n.append(code('merge_error','合并失败 保留原状态',passthrough,{'state':['prepared','next_session_json','output'],'answer':['prepared','answer_markdown','output']},strings('next_session_json answer_markdown'),2240,700,False))
    n.append(code('readonly','N13 只读回复与门禁解释',passthrough,{'state':['begin','next_session_json'],'answer':['begin','answer_markdown']},strings('next_session_json answer_markdown'),1290,960,False))
    tool.update(title='N16 确认后固定模板成稿',selected=False)
    tool['tool_parameters']={k:{'type':'mixed','value':'{{#begin.'+k+'#}}'} for k in ['snapshot_json','review_notes_json']}
    n.append(node('render',tool.pop('title'),'tool',{k:v for k,v in tool.items() if k not in {'type','selected'}},980,700))
    n.append(code('generated','N17 校验并登记当前稿','def main(snapshot_json: str, tool_json: list, tool_text: str) -> dict:\n    return finalize(snapshot_json,tool_json,tool_text)',{'snapshot_json':['begin','snapshot_json'],'tool_json':['render','json'],'tool_text':['render','text']},strings('next_session_json answer_markdown'),1600,780))
    next(x for x in n if x['id']=='generated')['data']['variables'][1]['value_type']='array[object]'
    terminals=['reply','review','merge_error','readonly','generated']
    groups=[{'groupId':uid(),'group_name':key,'output_type':'string','variables':[[i,key] for i in terminals]} for key in ['next_session_json','answer_markdown']]
    n.append(node('aggregate','N20 汇合互斥结果','variable-aggregator',{'output_type':'string','variables':[],'advanced_settings':{'group_enabled':True,'groups':groups}},2570,500))
    n.append(node('save','N21 唯一会话写入','assigner',{'version':'2','items':[{'variable_selector':['conversation','session_json'],'input_type':'variable','operation':'over-write','value':['aggregate','next_session_json','output'],'write_mode':'over-write'}]},2880,500))
    n.append(node('answer','N22 本轮回答','answer',{'answer':'{{#aggregate.answer_markdown.output#}}','variables':[]},3190,500))
    types={x['id']:x['data']['type'] for x in n}
    connections=[('start','begin','source'),('begin','route','source'),('route','extract','normal'),('route','command','control'),('route','render','generate'),('route','readonly','false'),('extract','merge','source'),('merge','prepared','source'),('command','prepared','source'),('prepared','decide','source'),('decide','interview','interview'),('decide','semantic','review'),('decide','merge_error','false'),('interview','reply','source'),('semantic','review','source'),('render','generated','source')]+[(x,'aggregate','source') for x in terminals]+[('aggregate','save','source'),('save','answer','source')]
    w['graph'].update(nodes=n,edges=[edge(a,b,types,h) for a,b,h in connections],viewport={'x':20,'y':50,'zoom':0.35})
    write(d,'PM_QA_Agent.yml')

if __name__=='__main__':
    tool_dsl('guide');tool_dsl('render')
    if (TEMPLATES/'agent_and_tool.yml').exists():chatflow()

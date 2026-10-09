"""PRD Chatflow runtime. Pure Python, embedded in Dify Code nodes.

Source rules: user-supplied core_rules.py, hardened for untrusted model patches.
No filesystem/network/tools access at runtime.
"""
import copy
import hashlib
import json
import re

# REGISTRY is injected at build time.
REGISTRY = {}
HANDLED = {'confirmed', 'tbd', 'na'}
STATUSES = HANDLED | {'missing', 'partial', 'proposed'}
ENTITY_SLOTS = {'business_goals':'G-', 'user_goals':'G-', 'persona_details':'P-',
                'user_stories':'US-', 'functional_requirements':'FR-', 'success_metrics':'M-'}
SECTIONS = ['概述', '目标与边界', '用户与权限', '用户故事', '功能需求',
            '用户体验', '使用叙事', '成功指标', '技术与风险', '建设顺序']
MAX_STATE = 60000
STATUS_LABELS={'missing':'待了解','partial':'待补充','proposed':'待采纳','confirmed':'已记录','tbd':'暂缓','na':'不适用'}
PRIORITY=['project_summary','key_user_types','user_goals','success_metrics','non_goals','persona_details','user_stories','functional_requirements','core_experience','edge_cases','entry_points','role_based_access','ux_highlights','business_goals','data_privacy','integration_points','scalability_performance','potential_challenges','narrative','build_phases','project_title']

def dumps(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def parse_model(text):
    if not isinstance(text, str) or len(text) > 60000:
        raise ValueError('模型输出为空或过长')
    text = text.strip()
    # Some provider adapters prepend reasoning; only the final JSON is data.
    if text.startswith('<think>'):
        end = text.find('</think>')
        if end < 0: raise ValueError('模型未返回完整最终答案')
        text = text[end+8:].strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError('模型输出必须为 JSON 对象')
    return value

def new_session():
    return {'schema_version':'1.0','prd_version':'v1','content_revision':0,
            'turn':0,'stage':'INTERVIEW','cursor':'project_summary',
            'slots':{k:{'value':'','status':'missing','origin':'none','source_turn':0,
                        'evidence_quote':''} for k in REGISTRY},
            'id_counters':{},'proposal_counter':0,'pending_proposals':[],
            'last_question':{},'review':{},'last_artifact':{}}

def load_state(raw):
    if len(raw) > MAX_STATE:
        raise ValueError('会话超过 60000 字符，请拆分项目')
    s = json.loads(raw or '{}')
    if s == {}:
        return new_session()
    if not isinstance(s, dict) or s.get('schema_version') != '1.0':
        raise ValueError('会话版本或类型错误，已保留原状态')
    if set(s.get('slots',{})) != set(REGISTRY):
        raise ValueError('会话字段不完整，不能自动重置')
    if not isinstance(s.get('content_revision'),int) or s['content_revision']<0:
        raise ValueError('修订号无效')
    if s.get('stage') not in {'INTERVIEW','CONFIRM_PENDING','GENERATED'}:
        raise ValueError('会话阶段无效')
    for k,v in s['slots'].items():
        if not isinstance(v,dict) or v.get('status') not in STATUSES:
            raise ValueError(k+'：字段状态损坏')
    for k in ('pending_proposals',):
        if not isinstance(s.get(k),list): raise ValueError(k+'：类型损坏')
    return s

def checked_dump(s):
    raw=dumps(s)
    if len(raw)>MAX_STATE: raise ValueError('会话超过 60000 字符，本轮未写入。请拆分项目。')
    return raw

def digest(s):
    return hashlib.sha256(dumps({'schema_version':s['schema_version'],
        'prd_version':s['prd_version'],'slots':s['slots']}).encode()).hexdigest()

def audit(s):
    fatal,unresolved,warnings,coverage=[],[],[],[]
    by_slot={}; ids=set()
    for k in REGISTRY:
        v=s['slots'][k]; status=v['status']; value=v['value']
        by_slot[k]=[]
        if status not in HANDLED: unresolved.append(k)
        if status=='tbd': warnings.append(REGISTRY[k]['label']+'：TBD')
        if status in {'na','missing'} or (status=='tbd' and not isinstance(value,list)): continue
        if value in ('',None,[]): fatal.append(k+'：已确认内容为空')
        if k not in ENTITY_SLOTS:
            if not isinstance(value,str): fatal.append(k+'：必须为文本')
            continue
        if not isinstance(value,list): fatal.append(k+'：必须为实体数组'); continue
        for e in value:
            if not isinstance(e,dict): fatal.append(k+'：实体类型错误'); continue
            eid=e.get('id','')
            if not isinstance(eid,str) or not re.fullmatch(re.escape(ENTITY_SLOTS[k])+r'[1-9]\d*',eid):
                fatal.append(k+'：实体ID无效'); continue
            if eid in ids: fatal.append(eid+'：重复ID')
            ids.add(eid); by_slot[k].append(e)
            if not e.get('text') and not e.get('name'): fatal.append(eid+'：缺少描述')
    goals=by_slot['business_goals']+by_slot['user_goals']; stories=by_slot['user_stories']
    persona_ids={p['id'] for p in by_slot['persona_details']}; goal_ids={g['id'] for g in goals}
    story_ids={u['id'] for u in stories}
    def refs(e,key,valid):
        val=e.get(key,[])
        if not isinstance(val,list) or not all(isinstance(x,str) for x in val):
            fatal.append(e['id']+'：'+key+'必须为ID数组'); return []
        for x in val:
            if x not in valid: fatal.append(e['id']+'：不存在的引用 '+x)
        return val
    for e in stories:
        if e.get('persona_id') not in persona_ids: fatal.append(e['id']+'：画像引用不存在')
        refs(e,'goal_ids',goal_ids)
    frlinks={e['id']:refs(e,'story_ids',story_ids) for e in by_slot['functional_requirements']}
    mlinks={e['id']:refs(e,'goal_ids',goal_ids) for e in by_slot['success_metrics']}
    for eid,links in list(frlinks.items())+list(mlinks.items()):
        if not links:warnings.append(eid+'：尚未关联'+('用户故事' if eid.startswith('FR-') else '目标'))
    for e in stories+goals:
        links=frlinks if e['id'].startswith('US-') else mlinks
        targets=[i for i,v in links.items() if e['id'] in v]
        coverage.append({'id':e['id'],'targets':targets,'status':'PASS' if targets else 'FAIL'})
        if not targets: warnings.append(e['id']+'：暂缺'+('实现需求' if links is frlinks else '衡量指标'))
    for m in by_slot['success_metrics']:
        for key in ('type','baseline','target','timeframe','definition'):
            if m.get(key) in ('',None,'_TBD_','TBD'): warnings.append(m['id']+'.'+key+'：TBD')
    for k,v in s['slots'].items():
        if re.search(r'估计|大概|预计|假设|未实测',dumps(v.get('value',''))+' '+v.get('evidence_quote','')):
            warnings.append(REGISTRY[k]['label']+'：包含用户估计或未验证假设')
    if s['pending_proposals']: unresolved.append('pending_proposals')
    return {'fatal':fatal,'unresolved':unresolved,'warnings':list(dict.fromkeys(warnings)),
            'coverage':coverage,'can_review':not fatal and not unresolved}

def progress(s):
    counts={x:sum(v['status']==x for v in s['slots'].values()) for x in STATUSES}
    return '修订 r%d · 已记录 %d/21 · 暂缓 %d · 不适用 %d · 待完善 %d'%(
        s['content_revision'],counts['confirmed'],counts['tbd'],counts['na'],
        21-counts['confirmed']-counts['tbd']-counts['na'])

def text_value(value):
    if isinstance(value,str): return value
    if isinstance(value,list):
        return '\n'.join('- '+text_value(x) for x in value)
    if isinstance(value,dict):
        labels={'text':'说明','name':'名称','type':'类型','context':'背景','persona_id':'画像',
                'goal_ids':'目标','story_ids':'故事','baseline':'基线','target':'目标值',
                'timeframe':'期限','definition':'口径','unit':'单位','acceptance_criteria':'验收标准',
                'data_source':'数据来源','evidence':'证据'}
        head=('**'+str(value['id'])+'** ' if 'id' in value and not str(value['id']).startswith('tmp_') else '')
        return head+'；'.join(labels.get(k,k)+'：'+(', '.join(map(str,v)) if isinstance(v,list) and all(isinstance(x,str) for x in v) else text_value(v)) for k,v in value.items() if k!='id')
    return str(value)

def slot_text(s,k):
    v=s['slots'][k]
    if k=='success_metrics' and isinstance(v['value'],list) and v['value']:
        cols=[('id','ID'),('name','指标'),('type','类型'),('goal_ids','对应目标'),('baseline','基线'),('target','目标值'),('timeframe','期限'),('definition','测量口径'),('evidence','依据')]
        rows=['| '+' | '.join(label for _,label in cols)+' |','| '+' | '.join('---' for _ in cols)+' |']
        for e in v['value']:
            rows.append('| '+' | '.join(cell(text_value(e.get(key,'_TBD_'))) for key,_ in cols)+' |')
        return ('已暂缓补齐的指标细节：\n\n' if v['status']=='tbd' else '')+'\n'.join(rows)
    if v['status']=='tbd':
        return '_TBD_'+ ('\n\n已记录的局部信息：'+text_value(v['value']) if v['value'] not in ('',None,'_TBD_') else '')
    if v['status']=='na': return '不适用：'+text_value(v['value'])
    if v['status'] in {'missing','partial','proposed'}:
        return '[待补充/待确认] '+text_value(v['value'])
    return text_value(v['value'])

def cell(value):
    return str(value).replace('|','\\|').replace('\n','；').strip()

def render(s,notes=None,preview=False):
    if not preview:
        a=audit(s)
        if a['fatal'] or a['unresolved']: raise ValueError('渲染被阻断：存在硬错误或未处理字段')
    title=s['slots']['project_title']['value'] or '未命名项目'
    if not isinstance(title,str): title='未命名项目'
    lines=['# '+title+' PRD','',('> 预览，尚未确认生成。' if preview else '> Status: Draft · 需求草案，不代表已验证或可直接上线。'),'',
           'Version: v1 · 内容修订：r'+str(s['content_revision']),'']
    for n,heading in enumerate(SECTIONS,1):
        lines+=['## '+str(n)+' '+heading,'']
        for k,meta in REGISTRY.items():
            if meta['section']==n:
                lines+=['### '+meta['label'],'',slot_text(s,k),'']
    lines+=['---','','## Review Notes','']
    for item in (notes if notes is not None else audit(s)['warnings']): lines.append('- '+str(item))
    if not (notes if notes is not None else audit(s)['warnings']): lines.append('- 未发现程序可识别的待确认风险；仍需真实用户与技术验证。')
    return '\n'.join(lines)

def choose_slots(s):
    pending=s.get('pending_proposals',[])
    if pending: return list(dict.fromkeys(p['slot_id'] for p in pending))[:1]
    unhandled=[k for k in PRIORITY if s['slots'][k]['status'] not in HANDLED]
    if not unhandled: return []
    if unhandled[0]=='user_goals':return ['user_goals']+(['success_metrics'] if 'success_metrics' in unhandled else [])
    return [unhandled[0]]

def decode_value(raw,key,operation='set'):
    if not isinstance(raw,str): raise ValueError('value_json 必须是字符串')
    try: return json.loads(raw)
    except json.JSONDecodeError:
        # Structured-output providers may return a plain scalar string.
        # Only text slots (or explicit skip reasons) allow this safe coercion.
        if (key not in ENTITY_SLOTS or operation in {'mark_tbd','mark_na','remove'}) and raw.strip(): return raw
        raise ValueError(key+'：实体内容必须是有效 JSON 对象或数组')

def put_proposal(s,p):
    if set(p)-{'slot_id','value_json','reason','id'}: raise ValueError('建议含未知字段')
    key=p.get('slot_id'); value=decode_value(p.get('value_json','null'),key)
    if key not in REGISTRY or value in ('',None,[]): raise ValueError('建议字段或内容无效')
    if len(dumps(value))>6000: raise ValueError('建议过长')
    if any(x['slot_id']==key and x['value_json']==dumps(value) for x in s['pending_proposals']): return
    s['proposal_counter']=s.get('proposal_counter',0)+1
    s['pending_proposals'].append({'id':'D-'+str(s['proposal_counter']),'slot_id':key,
                                  'value_json':dumps(value),'reason':str(p.get('reason',''))[:600]})

def numbered_proposals(s):
    return '\n'.join('- **'+p['id']+' · '+REGISTRY[p['slot_id']]['label']+'**：'+text_value(json.loads(p['value_json']))+'\n  理由：'+p.get('reason','供你判断，尚未记录为需求。') for p in s['pending_proposals'])

def next_id(s,prefix):
    n=s.setdefault('id_counters',{}).get(prefix,0)
    for k in ENTITY_SLOTS:
        val=s['slots'][k]['value']
        if isinstance(val,list):
            for e in val:
                if isinstance(e,dict) and re.fullmatch(re.escape(prefix)+r'\d+',str(e.get('id',''))):
                    n=max(n,int(e['id'][len(prefix):]))
    n+=1;s['id_counters'][prefix]=n
    return prefix+str(n)

def evidence_span(quote,query):
    if quote and quote in query:return quote
    # Accept only exact, ordered clauses; restore any omitted clauses from
    # the original message so the stored evidence remains verbatim.
    parts=[p.strip() for p in re.split(r'[，,。；;\n]+',quote) if p.strip()]
    if len(parts)<2 or any(len(p)<3 for p in parts):raise ValueError('证据不能对应原话')
    pos=0;start=None
    clauses=list(re.finditer(r'[^，,。；;\n]+',query))
    for part in parts:
        found=next((m for m in clauses if m.start()>=pos and m.group().strip()==part),None)
        if found is None:raise ValueError('证据不能对应原话')
        at=found.start()
        if start is None:start=at
        pos=found.end()
    if pos-start>len(quote)+300:raise ValueError('证据跨度过长')
    return query[start:pos]

def merge_patch(old,patch,query):
    if set(patch)!={'intent','updates','proposals','ambiguities'}: raise ValueError('提取结果字段不符合协议')
    if not all(isinstance(patch[k],list) for k in ('updates','proposals','ambiguities')): raise ValueError('提取数组格式错误')
    if len(patch['updates'])>30 or len(patch['proposals'])>10: raise ValueError('本轮变更过多')
    s=copy.deepcopy(old); s['turn']=s.get('turn',0)+1
    temp={}; staged=[]
    before=digest(s); old_pending=dumps(s['pending_proposals'])
    for u in patch['updates']:
        required={'slot_id','operation','entity_id','value_json','evidence_quote','source_kind','proposal_id'}
        if not isinstance(u,dict) or set(u)!=required: raise ValueError('变更字段不符合协议')
        if not all(isinstance(v,str) for v in u.values()): raise ValueError('变更协议字段必须为字符串')
        k=u['slot_id']; op=u['operation']; quote=u['evidence_quote']; source=u['source_kind']
        if k not in REGISTRY or op not in {'set','upsert','remove','mark_tbd','mark_na','accept_proposal'}: raise ValueError('未知字段或操作')
        if source not in {'user','accepted_proposal','document'}: raise ValueError('证据类型错误')
        quote=evidence_span(quote,query);u=dict(u,evidence_quote=quote)
        val=decode_value(u['value_json'],k,op); origin='user'
        if source=='document':
            put_proposal(s,{'slot_id':k,'value_json':u['value_json'],'reason':'资料内容待用户确认'}); continue
        if op=='accept_proposal':
            matches=[p for p in s['pending_proposals'] if p['id']==u['proposal_id'] and p['slot_id']==k]
            if len(matches)!=1: raise ValueError('建议ID不存在或不唯一')
            if not re.search(r'接受|采纳|同意|可以|认可|就用|确定|确认',query): raise ValueError('没有明确接受建议的证据')
            if len(s['pending_proposals'])>1 and u['proposal_id'] not in query and not re.search(r'全部|所有',query): raise ValueError('多个建议需明确ID或全部接受')
            val=json.loads(matches[0]['value_json']);s['pending_proposals'].remove(matches[0]);origin='accepted_proposal';op='upsert' if k in ENTITY_SLOTS else 'set'
        elif source=='accepted_proposal': raise ValueError('接受建议必须使用 accept_proposal')
        if op=='mark_tbd' and not re.search(r'跳过|TBD|tbd|待定|暂定|先放一放|先不讨论',query): raise ValueError('你还没有明确选择暂缓这项内容')
        if op=='mark_na' and (not re.search(r'不适用|无需|不需要|没有必要',query) or not isinstance(val,str) or not val.strip()): raise ValueError('不适用需明确原因')
        if op=='remove' and not re.search(r'删除|移除|去掉|取消这|不要这',query): raise ValueError('删除需要明确意图')
        if op in {'mark_tbd','mark_na','remove'}:
            staged.append((k,op,val,u,origin));continue
        if k in ENTITY_SLOTS:
            if isinstance(val,dict): val=[val]
            if not isinstance(val,list) or not val or not all(isinstance(e,dict) for e in val): raise ValueError(k+'：必须提供实体对象数组')
            existing=s['slots'][k]['value']; existing=existing if isinstance(existing,list) else []
            for e in val:
                if k=='success_metrics' and re.search(r'估计|大概|预计|假设|未实测',quote):
                    e['evidence']='含用户估计，未验证；本轮原话：'+quote
                eid=e.get('id') or u['entity_id']
                if eid and str(eid).startswith(('tmp_','tmp-','TEMP')):
                    candidate={a:b for a,b in e.items() if a not in {'id','evidence'}}
                    same=[x for x in existing if {a:b for a,b in x.items() if a not in {'id','evidence'}}==candidate]
                    if len(same)==1:
                        temp[eid]=same[0]['id'];eid=same[0]['id']
                if eid and any(x.get('id')==eid for x in existing): e['id']=eid
                elif not eid or str(eid).startswith(('tmp_','tmp-','TEMP')):
                    new=next_id(s,ENTITY_SLOTS[k])
                    if eid:
                        if eid in temp: raise ValueError('重复临时ID')
                        temp[eid]=new
                    e['id']=new
                else: raise ValueError('新实体请使用 tmp_ 临时ID；不能指定持久ID '+str(eid))
        elif not isinstance(val,str) or not val.strip(): raise ValueError(k+'：必须提供非空文本')
        staged.append((k,op,val,u,origin))
    def resolve(v):
        if isinstance(v,str): return temp.get(v,v)
        if isinstance(v,list): return [resolve(x) for x in v]
        if isinstance(v,dict): return {k:resolve(x) for k,x in v.items()}
        return v
    for k,op,val,u,origin in staged:
        oldv=s['slots'][k]; status='confirmed'
        if op=='mark_tbd':
            val=oldv['value'] if oldv['value'] not in ('',None) else '_TBD_';status='tbd'
        elif op=='mark_na': status='na'
        elif op=='remove':
            if k not in ENTITY_SLOTS or not u['entity_id']: raise ValueError('删除需指定实体ID')
            existing=oldv['value']
            if not isinstance(existing,list) or not any(e['id']==u['entity_id'] for e in existing): raise ValueError('待删除实体不存在')
            val=[e for e in existing if e['id']!=u['entity_id']]
            if not val: val='';status='missing'
        elif k in ENTITY_SLOTS:
            val=resolve(val); existing=copy.deepcopy(oldv['value']) if isinstance(oldv['value'],list) else []
            for e in val:
                match=next((x for x in existing if x['id']==e['id']),None)
                if match is None: existing.append(e)
                else: match.update(e)
            val=existing
            if k=='success_metrics' and any(e.get(key) in ('',None,'_TBD_','TBD') for e in val for key in ('definition','baseline','target','timeframe')):
                status='partial'
        # Preserve exact wrapper on semantic no-op, avoiding phantom revision increments.
        if oldv['value']==val and oldv['status']==status: continue
        s['slots'][k]={'value':val,'status':status,'origin':origin,'source_turn':s['turn'],'evidence_quote':u['evidence_quote']}
        # A direct answer or explicit skip supersedes only proposals for that same slot.
        s['pending_proposals']=[p for p in s['pending_proposals'] if p['slot_id']!=k]
    for p in patch['proposals']: put_proposal(s,p)
    a=audit(s)
    if a['fatal']: raise ValueError('；'.join(a['fatal']))
    if digest(s)!=before:
        s['content_revision']+=1;s['review']={};s['stage']='INTERVIEW'
    elif old_pending!=dumps(s['pending_proposals']): s['review']={};s['stage']='INTERVIEW'
    checked_dump(s)
    return s

def confirm_gate(s,query):
    m=re.fullmatch(r'/确认 r(\d+)( 接受待确认项)?',query.strip())
    if not m: return False,'请使用展示的精确确认口令；包含修改的消息会作为新一轮需求处理。'
    if s['stage']!='CONFIRM_PENDING': return False,'当前未完成审查，请先补齐字段或明确标为待定，再发送 /审查。'
    if int(m.group(1))!=s['content_revision']: return False,'旧修订号不能确认。当前为 r'+str(s['content_revision'])+'，请按最新审查摘要确认。'
    r=s.get('review',{})
    if r.get('content_hash')!=digest(s) or r.get('content_revision')!=s['content_revision']: return False,'内容已变更，必须重新审查。'
    a=audit(s)
    if a['fatal'] or a['unresolved']: return False,'仍有硬错误或未处理字段，不能生成。'
    if r.get('warnings') and not m.group(2): return False,'有已披露的待确认风险，请使用 /确认 r%d 接受待确认项。'%s['content_revision']
    return True,''

def command(q):
    q=q.strip().rstrip('。！!')
    groups={
        'preview':{'/预览','预览','看看当前稿','给我看一下当前稿','查看草稿','预览PRD','看看目前记录了什么'},
        'progress':{'/进度','进度','查看进度','还缺什么','还有哪些没聊到'},
        'review':{'/审查','审查','检查一下需求','审查当前需求','帮我生成PRD','生成PRD','生成 PRD','整理成PRD','整理成 PRD'},
        'help':{'/帮助','使用帮助','怎么使用这个助手'},
        'skip_all':{'/全部待定','其余全部待定','剩下的全部待定'},
        'export':{'/导出','/导出Word','导出Word','导出 Word','导出Markdown','导出 Markdown'}
    }
    return next((kind for kind,words in groups.items() if q in words),'')

def skip_keys(s,q):
    q=q.strip().rstrip('。！!')
    if command(q)=='skip_all':
        return list(dict.fromkeys([k for k in REGISTRY if s['slots'][k]['status'] not in HANDLED]+[p['slot_id'] for p in s['pending_proposals']]))
    m=re.fullmatch(r'(?:不知道[，,\s]*)?(?:/|先|暂时|暂且)?(?:跳过|待定|暂定|先放一放|先不讨论)\s*(.*)',q)
    if not m:return None
    tail=m.group(1).strip()
    if not tail or tail in {'这项','这一项','这个问题','当前问题'}:
        return s.get('last_question',{}).get('slot_ids',[]) or choose_slots(s)
    parts=re.split(r'[、,，和]',tail)
    keys=[]
    for part in parts:
        match=next((k for k,v in REGISTRY.items() if part.strip() in {k,v['label']}),None)
        if match is None:return None
        keys.append(match)
    return list(dict.fromkeys(keys))

def explain_error(exc):
    msg=str(exc)
    if '60000' in msg:return '内容已超过当前会话容量。建议按独立功能拆分项目。'
    if '引用' in msg or 'ID' in msg:return '这次修改涉及关联的目标、故事或功能，请说明要修改或保留哪一项。'
    if '证据' in msg:return '我还无法把这次修改准确对应到你的原话，请换一种说法说明要改什么。'
    return '我没能可靠整理这句话，请再说一下要补充或修改的内容。'

def begin(session_json,query):
    out={'route':'reply','state_json':session_json,'next_session_json':session_json,
         'answer_markdown':'','snapshot_json':'','review_notes_json':'[]'}
    try:
        s=load_state(session_json); raw=checked_dump(s);q=query.strip()
        out.update(state_json=raw,next_session_json=raw)
        kind=command(q)
        if kind=='preview':
            out['answer_markdown']=progress(s)+'\n\n'+render(s,preview=True)
        elif kind=='progress':
            out['answer_markdown']=progress(s)+'\n\n'+'\n'.join('- '+REGISTRY[k]['label']+'：'+STATUS_LABELS[s['slots'][k]['status']] for k in REGISTRY)
            if s['pending_proposals']:out['answer_markdown']+='\n\n待确认建议：\n'+numbered_proposals(s)
        elif re.fullmatch(r'/确认 r\d+( 接受待确认项)?',q):
            ok,reason=confirm_gate(s,q)
            if ok: out.update(route='generate',snapshot_json=raw,review_notes_json=dumps(s['review']['warnings']))
            else: out['answer_markdown']=reason
        elif kind=='export':
            a=s.get('last_artifact',{})
            current=a.get('content_hash')==digest(s) and a.get('content_revision')==s['content_revision'] and bool(a.get('markdown'))
            prefix='当前可复制 Markdown 正文。Word 下载暂未提供。' if 'Word' in q else '这是已确认的当前 Markdown 草案，可直接复制：'
            out['answer_markdown']=(prefix+'\n\n'+a['markdown']) if current else '请先审查并确认当前版本，才能取出最新成稿。你也可以先说“查看草稿”。'
        elif kind=='help':
            out['answer_markdown']='我是产品经理问答 Agent，可以和你一起澄清产品想法，也可以解释产品方法。\n\n直接说你想做什么，或问我一个产品问题。暂时不会回答时，可以说“给我一个建议”；想先放下某项时，说“跳过这一项”。\n\n随时说“查看草稿”“还缺什么”或“审查当前需求”。生成前会展示审查结果，请按给出的版本口令确认。建议只有经你采纳才会记入需求。'
        elif kind=='review' or skip_keys(s,q) is not None or re.fullmatch(r'(?:不采用|拒绝|撤回建议)\s*D-\d+',q):out['route']='control'
        else: out['route']='normal'
    except Exception as exc: out['answer_markdown']='已有记录保持原样。'+explain_error(exc)
    return out

def merge(state_json,patch_text,query):
    out={'route':'reply','state_json':state_json,'next_session_json':state_json,
         'answer_markdown':'','allowed_slots':'[]','audit_json':'{}','context_json':'{}'}
    try:
        old=load_state(state_json)
        q=query.strip()
        keys=skip_keys(old,q);kind=command(q);intent='answer'
        reject=re.fullmatch(r'(?:不采用|拒绝|撤回建议)\s*(D-\d+)',q)
        if kind=='review': s=copy.deepcopy(old); ambiguities=[]
        elif reject:
            s=copy.deepcopy(old);matched=[p for p in s['pending_proposals'] if p['id']==reject.group(1)]
            if not matched:raise ValueError('建议ID不存在')
            s['pending_proposals']=[p for p in s['pending_proposals'] if p['id']!=reject.group(1)];s['review']={};s['stage']='INTERVIEW';ambiguities=[]
        elif keys is not None:
            patch={'intent':'skip','updates':[{'slot_id':k,'operation':'mark_tbd','entity_id':'','value_json':'"_TBD_"','evidence_quote':query,'source_kind':'user','proposal_id':''} for k in keys],'proposals':[],'ambiguities':[]}
            s=merge_patch(old,patch,query);ambiguities=[]
        else:
            patch=parse_model(patch_text);s=merge_patch(old,patch,query);ambiguities=patch['ambiguities'];intent=patch['intent']
        a=audit(s); allowed=choose_slots(s)
        changed=[k for k in REGISTRY if old['slots'][k]!=s['slots'][k]]
        mode='guide' if re.search(r'不知道|不清楚|不会回答|给.{0,5}建议|帮.{0,5}建议',q) and keys is None else ('explain' if intent=='help' and not changed else 'interview')
        if kind=='review' or (a['can_review'] and (changed or not s.get('review')) and mode=='interview'): route='review'
        else: route='interview'
        if not allowed:allowed=['project_summary']
        s['turn_delta']={'changed':changed,'mode':mode}
        raw=checked_dump(s)
        # No past PRD body in model context; canonical facts are the slots.
        context={k:v for k,v in s.items() if k not in {'last_artifact','review','id_counters'}}
        context.update(allowed_slots=allowed,open_issues=ambiguities,rule_warnings=a['warnings'],reply_mode=mode)
        out.update(route=route,state_json=raw,next_session_json=raw,allowed_slots=dumps(allowed),
                   audit_json=dumps(a),context_json=dumps(context))
    except Exception as exc: out['answer_markdown']='已有记录保持原样。'+explain_error(exc)
    return out

def finish_interview(state_json,agent_text,allowed_slots):
    s=load_state(state_json); allowed=json.loads(allowed_slots)
    if not allowed: return {'next_session_json':state_json,'answer_markdown':'请发送 /审查 检查当前内容。'}
    fallback=False;mode=s.get('turn_delta',{}).get('mode','interview')
    try:
        r=parse_model(agent_text)
        if set(r)!={'question','slot_ids','proposals'}: raise ValueError('字段错误')
        question=r['question']; slots=r['slot_ids']
        if not isinstance(question,str) or not (1<=len(question)<=800) or len(re.findall(r'[?？]',question))>3: raise ValueError('问题长度或数量错误')
        if not isinstance(slots,list) or not (0 if mode=='explain' else 1)<=len(slots)<=3 or not all(k in allowed for k in slots): raise ValueError('问题越过允许字段')
        if not isinstance(r['proposals'],list) or len(r['proposals'])>2: raise ValueError('建议数量错误')
        candidate=copy.deepcopy(s)
        for p in r['proposals']:
            if p.get('slot_id') not in slots: raise ValueError('建议越界')
            put_proposal(candidate,p)
        s=candidate
    except Exception:
        fallback=True;slots=allowed[:1];question=REGISTRY[slots[0]]['fallback_question']
        if s['pending_proposals']: question='请确认以下候选建议，明确写出接受的 D-ID，或直接给出你的修改；也可跳过对应字段。'
    if slots and mode!='explain':s['cursor']=slots[0];s['last_question']={'question':question,'slot_ids':slots,'turn':s.get('turn',0)}
    if s['pending_proposals']: s['review']={};s['stage']='INTERVIEW'
    changed=s.get('turn_delta',{}).get('changed',[])
    ack=('已更新：'+'、'.join(REGISTRY[k]['label'] for k in changed[:5])+('等'+str(len(changed))+'项' if len(changed)>5 else '')+'。\n\n') if changed else ''
    answer=ack+question
    if s['pending_proposals']:
        pid=s['pending_proposals'][0]['id']
        answer+='\n\n供你判断的建议（尚未写入需求）：\n'+numbered_proposals(s)+'\n\n可以回复“采纳 '+pid+'”、修改它，或说“不采用 '+pid+'”。'
    if fallback:answer+='\n\n如果暂时不想讨论这项，可以说“跳过这一项”。'
    try: return {'next_session_json':checked_dump(s),'answer_markdown':answer}
    except Exception as exc:return {'next_session_json':state_json,'answer_markdown':'已有记录保持原样。'+explain_error(exc)}

def review_summary(s):
    rows=['| 章节 | 目前内容 |','| --- | --- |']
    for n,heading in enumerate(SECTIONS,1):
        pieces=[]
        for k,meta in REGISTRY.items():
            if meta['section']!=n:continue
            v=s['slots'][k]
            if v['status'] in {'missing','tbd','na'}:text=STATUS_LABELS[v['status']]
            else:text=re.sub(r'\*\*','',text_value(v['value']));text=text[:85]+('…' if len(text)>85 else '')
            pieces.append(meta['label']+'：'+cell(text))
        rows.append('| '+str(n)+' '+heading+' | '+'；'.join(pieces)+' |')
    return '\n'.join(rows)

def finish_review(state_json,semantic_text):
    s=load_state(state_json);a=audit(s);status='UNKNOWN';notes=[]
    try:
        r=parse_model(semantic_text)
        if r.get('overall') not in {'PASS','FAIL','UNKNOWN'} or not isinstance(r.get('issues'),list):raise ValueError('审查格式错误')
        status=r['overall']
        validrefs=set(REGISTRY)
        for k in ENTITY_SLOTS:
            if isinstance(s['slots'][k]['value'],list):validrefs.update(e['id'] for e in s['slots'][k]['value'])
        for item in r['issues']:
            if not isinstance(item,dict) or not isinstance(item.get('refs'),list) or not all(x in validrefs for x in item['refs']):raise ValueError('审查引用不存在')
            finding=str(item.get('finding','')).strip()
            if not finding:raise ValueError('审查缺少依据')
            notes.append('语义审查 '+','.join(item['refs'])+'：'+finding)
    except Exception:status='UNKNOWN';notes=['语义审查不可用或格式无效，请人工核对一致性。']
    warnings=list(dict.fromkeys(a['warnings']+notes+(['语义审查状态：'+status] if status!='PASS' else [])))
    s['review']={'content_revision':s['content_revision'],'content_hash':digest(s),
                 'warnings':warnings,'semantic_status':status,'fatal':a['fatal'],'unresolved':a['unresolved'],'coverage':a['coverage']}
    s['stage']='CONFIRM_PENDING' if a['can_review'] else 'INTERVIEW'
    summary=review_summary(s)
    mapping='\n'.join('- '+x['id']+' → '+(', '.join(x['targets']) or '暂无')+' ['+x['status']+']' for x in a['coverage']) or '暂无可检查的故事或目标实体。'
    status_text={'PASS':'未发现明确冲突','FAIL':'发现需要核对的冲突','UNKNOWN':'信息不足或审查未完成，需人工核对'}[status]
    answer=progress(s)+'\n\n'+summary+'\n\n**对应关系**\n'+mapping+'\n\n**审查意见**\n'+status_text
    if warnings:answer+='\n\n'+'\n'.join('- '+w for w in warnings)
    if a['can_review']:
        cmd='/确认 r'+str(s['content_revision'])+(' 接受待确认项' if warnings else '')
        answer+='\n\n查看全文可说“查看草稿”。确认以上内容与待完善项后，单独发送：\n\n`'+cmd+'`\n\n想修改哪里，直接告诉我；修改后需确认新版本。'
    else:
        labels=[REGISTRY[k]['label'] if k in REGISTRY else '尚未采纳的建议' for k in a['unresolved']]
        answer+='\n\n**还需讨论**：'+'、'.join(labels)+'。\n\n可以继续补充，或明确说“跳过某项”。如需有意保留全部缺口，可说“其余全部待定”，之后再确认草案。'
    return {'next_session_json':checked_dump(s),'answer_markdown':answer}

def tool_guide(section_id,slot_ids_json):
    keys=json.loads(slot_ids_json or '[]')
    if not isinstance(keys,list) or not all(k in REGISTRY for k in keys):raise ValueError('字段白名单错误')
    if not keys:keys=[k for k,v in REGISTRY.items() if v['section']==int(section_id)]
    return {'guide_json':dumps({'notice':'只读方法指南，不代表用户事实。','slots':[dict(slot_id=k,**REGISTRY[k]) for k in keys]})}

def tool_render(snapshot_json,review_notes_json):
    s=load_state(snapshot_json);r=s.get('review',{})
    if s['stage']!='CONFIRM_PENDING' or r.get('content_hash')!=digest(s) or r.get('content_revision')!=s['content_revision']:
        raise ValueError('无有效审查快照')
    notes=json.loads(review_notes_json)
    if notes!=r.get('warnings'): raise ValueError('风险备注与审查快照不一致')
    md=render(s,notes)
    if len(re.findall(r'^## \d+ ',md,re.M))!=10:raise ValueError('十章校验失败')
    if '{{' in md or '}}' in md:raise ValueError('正文含未处理模板占位符，请先修改')
    return {'markdown':md,'content_hash':digest(s)}

def finalize(snapshot_json,tool_json,tool_text):
    s=load_state(snapshot_json)
    try:
        value=tool_json
        if isinstance(value,str):value=json.loads(value)
        if isinstance(value,list):value=next((x for x in value if isinstance(x,dict) and 'markdown' in x),{})
        if not isinstance(value,dict) or not value.get('markdown'):
            value=parse_model(tool_text)
        expected=tool_render(snapshot_json,dumps(s['review']['warnings']))
        if value.get('content_hash')!=expected['content_hash'] or value.get('markdown')!=expected['markdown']:
            raise ValueError('成稿工具结果与冻结快照不一致')
        s['last_artifact']={'content_revision':s['content_revision'],'content_hash':expected['content_hash'],'markdown':expected['markdown']}
        s['stage']='GENERATED'
        return {'next_session_json':checked_dump(s),'answer_markdown':expected['markdown']+'\n\n---\n当前修订已生成，可复制保存。继续修改时，我会保留原稿，并请你确认新版本。'}
    except Exception as exc:
        return {'next_session_json':snapshot_json,'answer_markdown':'这次成稿未完成，已保留需求和审查结果。请稍后用同一确认口令重试。'}

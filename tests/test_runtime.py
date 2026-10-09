import unittest,json,copy,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
import runtime as r
r.REGISTRY=json.loads((PROJECT/'src'/'registry.json').read_text())

def update(k,v,q,op='set',eid='',pid=''):
    return {'slot_id':k,'operation':op,'entity_id':eid,'value_json':r.dumps(v),'evidence_quote':q,'source_kind':'user','proposal_id':pid}
def patch(*updates):return {'intent':'answer','updates':list(updates),'proposals':[],'ambiguities':[]}
def fixture():
    s=r.new_session()
    q='我确认：测试助手，独立插画师，节省时间，填写用途给报价单；估计40分钟，目标10分钟，试用两周。'
    ups=[update('project_title','测试助手',q),update('project_summary','独立插画师的报价助手',q),
         update('user_goals',[{'id':'tmp_g','text':'节省报价时间'}],q),
         update('persona_details',[{'id':'tmp_p','text':'独立插画师'}],q),
         update('user_stories',[{'id':'tmp_u','text':'填写用途得到报价单','persona_id':'tmp_p','goal_ids':['tmp_g']}],q),
         update('functional_requirements',[{'id':'tmp_f','text':'生成报价单','story_ids':['tmp_u']}],q),
         update('success_metrics',[{'id':'tmp_m','name':'报价时间','type':'用户','definition':'从填写到报价单完成','baseline':'用户估计40分钟','target':'10分钟','timeframe':'试用两周','goal_ids':['tmp_g']}],q)]
    s=r.merge_patch(s,patch(*ups),q)
    return r.load_state(r.merge(r.dumps(s),'','/全部待定')['state_json'])

class RuntimeTests(unittest.TestCase):
    def test_provider_reasoning_is_not_a_patch(self):
        out=json.loads((Path(__file__).parent/'fixtures'/'provider_output.json').read_text())
        parsed=r.parse_model(out['text'])
        q='我想做一个给独立插画师用的报价助手，名字叫画价。用户填稿件用途、尺寸和交付时间，助手给报价区间和报价单草稿；第一版只在网页用，不自动发给客户，也不做收款。'
        s=r.merge_patch(r.new_session(),parsed,q)
        self.assertEqual(s['slots']['project_title']['value'],'画价')
        self.assertEqual(len(s['slots']['functional_requirements']['value']),2)
        with self.assertRaises(ValueError):r.parse_model('<think>{"updates":[]}')

    def test_abbreviated_evidence_restores_verbatim_span(self):
        q='我想做报价助手，名字叫画价。用户填写用途和尺寸，助手给报价区间。'
        quote='我想做报价助手，用户填写用途和尺寸，助手给报价区间'
        self.assertEqual(r.evidence_span(quote,q),q[:-1])
        with self.assertRaises(ValueError):r.evidence_span('自动发给客户，自动收款','不自动发给客户，禁止自动收款')
    def test_uncertain_is_guidance_not_skip(self):
        s=r.new_session();s['last_question']={'slot_ids':['business_goals']}
        self.assertIsNone(r.skip_keys(s,'不知道'))
        out=r.merge(r.dumps(s),r.dumps({'intent':'help','updates':[],'proposals':[],'ambiguities':[]}),'不知道')
        n=r.load_state(out['state_json']);self.assertEqual(n['turn_delta']['mode'],'guide');self.assertEqual(n['slots']['business_goals']['status'],'missing')
    def test_skip_mixed_or_question_is_not_shortcut(self):
        s=r.new_session()
        for q in ['要不要跳过？','跳过业务目标，但把目标改成10分钟','跳过这个会有什么影响？']:
            self.assertIsNone(r.skip_keys(s,q))
    def test_early_review_bypasses_extractor(self):
        s=r.new_session();raw=r.dumps(s)
        self.assertEqual(r.begin(raw,'审查当前需求')['route'],'control')
        out=r.merge(raw,'','审查当前需求');self.assertEqual(out['route'],'review')
        end=r.finish_review(out['state_json'],'{"overall":"UNKNOWN","issues":[]}')
        self.assertIn('还需讨论',end['answer_markdown']);self.assertNotIn('/确认 r0',end['answer_markdown'])
    def test_explanation_preserves_last_question(self):
        s=r.new_session();s['last_question']={'question':'已有问题','slot_ids':['project_summary']}
        s['turn_delta']={'mode':'explain','changed':[]}
        out=r.finish_interview(r.dumps(s),r.dumps({'question':'MVP是用于验证核心假设的最小可用产品。','slot_ids':[],'proposals':[]}),r.dumps(['project_summary']))
        n=r.load_state(out['next_session_json']);self.assertEqual(n['last_question'],s['last_question']);self.assertEqual(n['content_revision'],0)
    def test_repeated_new_entity_retains_id(self):
        q='省时间';u=update('user_goals',[{'id':'tmp_one','text':'省时间'}],q,'upsert')
        s=r.merge_patch(r.new_session(),patch(u),q);n=r.merge_patch(s,patch(update('user_goals',[{'id':'tmp_two','text':'省时间'}],q,'upsert')),q)
        self.assertEqual(n['content_revision'],1);self.assertEqual(len(n['slots']['user_goals']['value']),1)
    def test_metric_details_require_handling(self):
        q='用时指标，目标10分钟';s=r.merge_patch(r.new_session(),patch(update('success_metrics',[{'id':'tmp_m','name':'用时','target':'10分钟'}],q,'upsert')),q)
        self.assertEqual(s['slots']['success_metrics']['status'],'partial')
        s['last_question']={'slot_ids':['success_metrics']};n=r.load_state(r.merge(r.dumps(s),'','跳过')['state_json'])
        self.assertEqual(n['slots']['success_metrics']['status'],'tbd');self.assertEqual(n['slots']['success_metrics']['value'][0]['target'],'10分钟')
    def test_rejected_proposal_does_not_become_fact(self):
        s=r.new_session();r.put_proposal(s,{'slot_id':'project_title','value_json':r.dumps('建议名'),'reason':'例子'})
        out=r.merge(r.dumps(s),'','不采用 D-1');n=r.load_state(out['state_json'])
        self.assertEqual(n['pending_proposals'],[]);self.assertEqual(n['slots']['project_title']['value'],'')
    def test_metric_table_is_markdown_safe(self):
        s=fixture();s['slots']['success_metrics']['value'][0]['name']='A|B\nC'
        md=r.render(s);self.assertIn('| ID | 指标 |',md);self.assertIn('A\\|B；C',md)
    def test_natural_skip(self):
        s=r.new_session();s['last_question']={'slot_ids':['business_goals']}
        out=r.merge(r.dumps(s),'{}','不知道，先跳过业务目标。');n=r.load_state(out['state_json'])
        self.assertEqual(n['slots']['business_goals']['status'],'tbd')
        self.assertEqual(n['slots']['project_summary']['status'],'missing')
    def test_estimate_is_disclosed_and_later_ids_work(self):
        s=fixture();self.assertIn('用户估计',r.render(s))
        s=r.merge_patch(s,patch(update('persona_details',{'id':'tmp_other','text':'另一个运营'},'另一个运营','upsert')),'另一个运营')
        self.assertEqual(s['slots']['persona_details']['value'][-1]['id'],'P-2')
    def test_plain_text_provider_compatibility(self):
        u=update('project_title','标题','标题');u['value_json']='标题'
        s=r.merge_patch(r.new_session(),patch(u),'标题')
        self.assertEqual(s['slots']['project_title']['value'],'标题')
        with self.assertRaises(ValueError):r.decode_value('不是实体JSON','user_goals')
    def test_registry_order_survives_roundtrip(self):
        s=r.new_session()
        for k in ('project_summary','user_goals','business_goals','success_metrics'):s['slots'][k]['status']='tbd'
        self.assertEqual(r.choose_slots(r.load_state(r.dumps(s))),['key_user_types'])
    def test_multi_field_and_refs(self):
        s=fixture();self.assertEqual(s['slots']['user_stories']['value'][0]['persona_id'],'P-1');self.assertFalse(r.audit(s)['fatal'])
    def test_unknown_field_atomic(self):
        s=r.new_session();old=r.dumps(s)
        with self.assertRaises(ValueError):r.merge_patch(s,patch(update('oops','x','x')),'x')
        self.assertEqual(old,r.dumps(s))
    def test_bad_evidence(self):
        with self.assertRaises(ValueError):r.merge_patch(r.new_session(),patch(update('project_title','虚构','原话')),'真实')
    def test_bad_ref_atomic(self):
        s=fixture();old=r.dumps(s)
        with self.assertRaises(ValueError):r.merge_patch(s,patch(update('functional_requirements',{'id':'FR-1','story_ids':['US-99']},'改引用',op='upsert')),'改引用')
        self.assertEqual(old,r.dumps(s))
    def test_stable_id_partial_upsert(self):
        s=fixture();s=r.merge_patch(s,patch(update('functional_requirements',{'id':'FR-1','text':'生成12个选题'},'改为12个',op='upsert')),'改为12个')
        self.assertEqual(s['slots']['functional_requirements']['value'][0]['story_ids'],['US-1'])
    def test_preview_no_mutation(self):
        s=fixture();raw=r.dumps(s);out=r.begin(raw,'/预览');self.assertEqual(raw,out['next_session_json']);self.assertIn('预览',out['answer_markdown'])
    def test_review_confirm_generate(self):
        s=fixture();out=r.finish_review(r.dumps(s),' {"overall":"PASS","issues":[]} ');s=r.load_state(out['next_session_json'])
        q='/确认 r%d 接受待确认项'%s['content_revision'];self.assertTrue(r.confirm_gate(s,q)[0]);out=r.begin(r.dumps(s),q)
        result=r.tool_render(out['snapshot_json'],out['review_notes_json']);end=r.finalize(out['snapshot_json'],[result],'')
        self.assertEqual(r.load_state(end['next_session_json'])['stage'],'GENERATED');self.assertEqual(result['markdown'].count('\n## '),11)
        self.assertIn('用户估计40分钟',result['markdown'])
    def test_risk_acceptance(self):
        out=r.finish_review(r.dumps(fixture()),'{"overall":"PASS","issues":[]}');s=r.load_state(out['next_session_json'])
        self.assertFalse(r.confirm_gate(s,'/确认 r%d'%s['content_revision'])[0])
    def test_revision_old_and_mixed(self):
        s=r.load_state(r.finish_review(r.dumps(fixture()),'{"overall":"PASS","issues":[]}')['next_session_json']);rev=s['content_revision']
        s=r.merge_patch(s,patch(update('project_title','新名字','改名为新名字')),'改名为新名字')
        self.assertEqual(s['review'],{});self.assertEqual(s['content_revision'],rev+1)
        self.assertFalse(r.confirm_gate(s,'/确认 r%d 接受待确认项'%rev)[0]);self.assertEqual(r.begin(r.dumps(s),'/确认 r%d，但改成60秒'%rev)['route'],'normal')
    def test_unknown_review_disclosed(self):
        s=r.load_state(r.finish_review(r.dumps(fixture()),'broken')['next_session_json']);self.assertEqual(s['review']['semantic_status'],'UNKNOWN')
    def test_agent_bad_json_fallback(self):
        s=r.new_session();out=r.finish_interview(r.dumps(s),'bad','["project_summary"]');self.assertIn('谁在什么场景',out['answer_markdown']);self.assertNotIn('JSON',out['answer_markdown'])
    def test_bad_state_not_reset(self):
        out=r.begin('{bad','test');self.assertEqual(out['next_session_json'],'{bad');self.assertEqual(out['route'],'reply')
    def test_na_without_reason(self):
        with self.assertRaises(ValueError):r.merge_patch(r.new_session(),patch(update('project_title','','不适用','mark_na')),'不适用')
    def test_delete_no_cascade(self):
        s=fixture()
        with self.assertRaises(ValueError):r.merge_patch(s,patch(update('user_stories',None,'删除US-1','remove','US-1')),'删除US-1')
    def test_new_ids_cannot_be_forged(self):
        with self.assertRaises(ValueError):r.merge_patch(r.new_session(),patch(update('user_goals',[{'id':'G-99','text':'快'}],'快')),'快')
    def test_proposal_not_fact(self):
        s=r.new_session();r.put_proposal(s,{'slot_id':'project_title','value_json':'"建议名称"','reason':'具体'})
        self.assertEqual(s['slots']['project_title']['status'],'missing');self.assertIn('pending_proposals',r.audit(s)['unresolved'])
        s=r.merge_patch(s,patch(update('project_title',None,'接受D-1','accept_proposal',pid='D-1')),'接受D-1')
        self.assertEqual(s['slots']['project_title']['value'],'建议名称');self.assertFalse(s['pending_proposals'])
    def test_renderer_deterministic(self):
        s=r.load_state(r.finish_review(r.dumps(fixture()),'{"overall":"PASS","issues":[]}')['next_session_json'])
        self.assertEqual(r.tool_render(r.dumps(s),r.dumps(s['review']['warnings'])),r.tool_render(r.dumps(s),r.dumps(s['review']['warnings'])))

if __name__=='__main__':unittest.main(verbosity=2)

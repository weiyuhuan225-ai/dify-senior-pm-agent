"""Build a deterministic synthetic PRD example; no model or network calls."""
from pathlib import Path
import json
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'src'))
import runtime as r

r.REGISTRY = json.loads((PROJECT / 'src/registry.json').read_text())
OUT = PROJECT / 'examples'

QUERY = '''以下全部是虚构演示设定，不代表实测结果。
产品叫“书会借阅簿”，给小型读书会组织者记录图书借出、归还和当前状态。
用户是独自维护借阅表的组织者，第一版只有单一管理员角色。
目标是缩短一次借还登记耗时。演示基线设为5分钟，目标2分钟，演示观察期两周；口径为从打开登记页到保存成功的平均耗时。
用户故事：作为组织者，我想登记一本书的借出或归还，以便掌握当前借阅状态。
功能是创建借阅记录并更新为已归还；验收条件是保存成功后列表状态与记录一致。
第一版只做网页入口，不收款，不自动发消息，不做图书推荐。
用户从借阅列表进入新建记录，填写图书名、借阅人代称和日期，保存后返回列表；归还时更新同一条记录。
重复提交时提示记录已存在，保存失败时保留已填内容并允许重试。
界面优先展示当前借出记录和清晰的保存状态。
只保存演示需要的借阅人代称，不使用真实联系方式；数据保留期限仍待定。
建设顺序是先做记录列表和新增，再做归还更新，最后完善错误提示。
其他未说明的字段全部保留待定。'''

def update(key, value, operation='set'):
    return {'slot_id': key, 'operation': operation, 'entity_id': '',
            'value_json': r.dumps(value), 'evidence_quote': QUERY,
            'source_kind': 'user', 'proposal_id': ''}

def main():
    updates = [
        update('project_title', '书会借阅簿'),
        update('project_summary', '供小型读书会组织者记录图书借出、归还和当前状态的网页工具。'),
        update('key_user_types', '小型读书会组织者'),
        update('role_based_access', '第一版单一管理员角色。'),
        update('user_goals', [{'id': 'tmp_goal', 'text': '缩短一次借还登记耗时'}], 'upsert'),
        update('persona_details', [{'id': 'tmp_persona', 'text': '小型读书会组织者', 'context': '独自维护借阅表'}], 'upsert'),
        update('user_stories', [{'id': 'tmp_story', 'text': '作为组织者，我想登记一本书的借出或归还，以便掌握当前借阅状态。', 'persona_id': 'tmp_persona', 'goal_ids': ['tmp_goal']}], 'upsert'),
        update('functional_requirements', [{'id': 'tmp_requirement', 'text': '创建借阅记录并更新为已归还', 'story_ids': ['tmp_story'], 'acceptance_criteria': ['保存成功后列表状态与记录一致']}], 'upsert'),
        update('success_metrics', [{'id': 'tmp_metric', 'name': '一次借还登记平均耗时', 'type': '用户', 'goal_ids': ['tmp_goal'], 'definition': '从打开登记页到保存成功的平均耗时', 'baseline': '5分钟（虚构演示设定）', 'target': '2分钟（虚构演示设定）', 'timeframe': '两周（虚构演示观察期）'}], 'upsert'),
        update('non_goals', '不收款，不自动发消息，不做图书推荐。'),
        update('entry_points', '网页借阅列表。'),
        update('core_experience', '从列表新建记录，填写图书名、借阅人代称和日期；保存后返回列表，归还时更新同一条记录。'),
        update('edge_cases', '重复提交提示记录已存在；保存失败保留内容并允许重试。'),
        update('ux_highlights', '优先展示当前借出记录和清晰的保存状态。'),
        update('data_privacy', '只保存借阅人代称，不使用真实联系方式；数据保留期限待定。'),
        update('build_phases', '先完成列表和新增，再做归还更新，最后完善错误提示。'),
    ]
    state = r.merge_patch(r.new_session(), {'intent': 'answer', 'updates': updates,
                          'proposals': [], 'ambiguities': []}, QUERY)
    routed = r.merge(r.dumps(state), '', '/全部待定')
    reviewed = r.finish_review(routed['state_json'], r.dumps({'overall': 'UNKNOWN', 'issues': []}))
    state = r.load_state(reviewed['next_session_json'])
    command = '/确认 r' + str(state['content_revision'])
    if state['review']['warnings']:
        command += ' 接受待确认项'
    ready = r.begin(r.dumps(state), command)
    if ready['route'] != 'generate':
        raise RuntimeError('Synthetic example did not pass confirmation gate')
    result = r.tool_render(ready['snapshot_json'], ready['review_notes_json'])
    OUT.mkdir(exist_ok=True)
    (OUT / 'input.txt').write_text(QUERY + '\n')
    (OUT / 'reviewed_state.json').write_text(json.dumps(json.loads(ready['snapshot_json']), ensure_ascii=False, indent=2) + '\n')
    (OUT / 'review_notes.json').write_text(json.dumps(json.loads(ready['review_notes_json']), ensure_ascii=False, indent=2) + '\n')
    (OUT / 'prd.md').write_text('> 合成演示：由固定 Python 规则生成，未调用模型。所有数字均为虚构设定。\n\n' + result['markdown'] + '\n')
    print('Wrote synthetic input, reviewed snapshot, review notes and PRD to examples/.')

if __name__ == '__main__':
    main()

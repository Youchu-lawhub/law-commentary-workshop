#!/usr/bin/env python3
"""
法学评注工坊 1.3.1 — 成稿快速体检
用法：python3 validate-skill.py <稿件.md>

定位：快速体检，不是放行依据。正式放行以 scripts/audit_commentary.py 与人工签署为准。
"""

import re
import sys
from pathlib import Path

CASE_TYPE = r'(?:民初|民终|行初|行终|刑初|刑终|民申|民再|行申|行再|刑申|刑再|民辖终|执异|执复)'
CASE_PATTERNS = [
    rf'（[0-9]{{4}}）[^）]+?{CASE_TYPE}[0-9]+号',
    rf'\([0-9]{{4}}\)[^)]+?{CASE_TYPE}[0-9]+号',
]

# 脚注定义行：数字或具名标签均可，与 audit_commentary.py 的口径保持一致
FOOTNOTE_DEF = re.compile(r'^\[\^([^\]\s]+)\]:', re.MULTILINE)


def split_body_and_footnotes(text):
    """从第一条脚注定义处切开正文与脚注区；不依赖标签是否为数字。"""
    match = FOOTNOTE_DEF.search(text)
    if not match:
        return text, '', 0
    return text[:match.start()], text[match.start():], len(FOOTNOTE_DEF.findall(text))


def find_cases(text):
    found = []
    for p in CASE_PATTERNS:
        found.extend(re.findall(p, text))
    return sorted(set(found))


def section_titles(text):
    titles = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r'^#{1,3}\s*(.+)$', s)
        if m:
            titles.append(m.group(1).strip())
    return titles


def validate(paper_path):
    text = Path(paper_path).read_text(encoding='utf-8')

    print('=' * 68)
    print('法学评注工坊 1.3.1 — 成稿快速体检')
    print('=' * 68)
    print(f'文件：{paper_path}')

    results = {}

    # 1. 注密度
    body, footnote_section, notes = split_body_and_footnotes(text)
    cjk = len(re.findall(r'[一-鿿]', body))
    density = notes / (cjk / 1000) if cjk else 0
    if density < 2.0:
        density_pass, density_level = False, 'fail'
    elif density < 4.5:
        density_pass, density_level = True, 'warn'
    else:
        density_pass = True
        density_level = 'warn' if density > 9.0 else 'ok'
    results['density'] = {
        'value': f'{density:.2f} 注/千字（正文 {cjk} 字，脚注 {notes}）',
        'pass': density_pass,
        'level': density_level,
        'detail': '期刊评注 4.5–9.0；工作稿 ≥2.0；>9.0 检查是否脚注堆砌',
    }

    # 2. 中文学术文献
    cn = re.findall(r'《[^》]+》[0-9]{4}年第[0-9]+(?:期|卷)', text)
    results['cn_papers'] = {
        'value': f'{len(set(cn))} 篇',
        'pass': len(set(cn)) >= 5,
        'level': 'ok' if len(set(cn)) >= 5 else 'fail',
        'detail': '要求 ≥5 篇',
    }

    # 3. 外文文献（信息项，不作为门禁）
    fn = footnote_section
    en = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+,.*?(?:19|20)\d{2}', fn)
    de = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+,.*?(?:Aufl\.|S\.\s*\d)', fn)
    jp = re.findall(r'[^\s：]{1,8}：『[^』]+』', fn)
    results['foreign_papers'] = {
        'value': f'{len(set(en + de + jp))} 篇（EN {len(en)} / DE {len(de)} / JP {len(jp)}）',
        'pass': True,
        'level': 'info',
        'detail': '按需使用；不作为数量门禁（比较法必要性见 references/comparative-law.md）',
    }

    # 4. 司法案例
    cases = find_cases(text)
    results['cases'] = {
        'value': f'{len(cases)} 件',
        'pass': len(cases) >= 10,
        'level': 'ok' if len(cases) >= 10 else 'fail',
        'detail': '要求 ≥10 件；须配案例搜集情况说明',
    }

    # 5. 法律法规
    statutes = set(re.findall(r'《[^》]+》第[0-9]+条', text))
    results['statutes'] = {
        'value': f'{len(statutes)} 条',
        'pass': len(statutes) >= 15,
        'level': 'ok' if len(statutes) >= 15 else 'fail',
        'detail': '要求 ≥15 条',
    }

    # 6. 案例搜集情况说明
    has_collection_note = bool(re.search(r'案例(搜集|收集|检索)情况说明|案例来源说明', text))
    results['case_note'] = {
        'value': '有' if has_collection_note else '无',
        'pass': has_collection_note,
        'level': 'ok' if has_collection_note else 'fail',
        'detail': '须含来源、检索式、截止日、命中数、剔除数与有效数',
    }

    # 7. 结构：必须有证明责任且位于末章
    titles = section_titles(text)
    has_burden = any('证明责任' in t for t in titles)
    last_h1 = [t for t in titles if re.match(r'^[一二三四五六七八九十]+、', t)]
    burden_last = bool(last_h1) and ('证明责任' in last_h1[-1] or '程序法' in last_h1[-1])
    results['structure'] = {
        'value': f'证明责任：{"有" if has_burden else "无"}；末章：{last_h1[-1] if last_h1 else "未识别"}',
        'pass': has_burden and burden_last,
        'level': 'ok' if (has_burden and burden_last) else 'fail',
        'detail': '证明责任须存在，且位于末章或在末章“程序法问题”之内',
    }

    # 8. 段码连续性
    codes = [int(x) for x in re.findall(r'[［【\[](\d{1,3})[］】\]]', text)]
    codes = sorted(set(codes))
    gaps = []
    if codes:
        gaps = [i for i in range(codes[0], codes[-1] + 1) if i not in codes]
    results['paragraph_codes'] = {
        'value': f'{len(codes)} 个段码，缺口 {len(gaps)} 处',
        'pass': bool(codes) and not gaps,
        'level': 'ok' if (codes and not gaps) else ('warn' if codes else 'info'),
        'detail': '段码应连续；无段码的稿件可忽略本项',
    }

    # 9. 评注特有要素
    has_norm_attr = bool(re.search(r'规范(属性|性质)|请求权基础规范|辅助规范|抗辩规范|不完全(主要)?规范', text))
    has_note_comment = bool(re.search(r'通说|少数说|有力说|本文认为|本文主张', text))
    has_evidence_mark = bool(re.search(r'\[原文核实\]|\[摘要参考\]|\[二手引用\]|\[需用户核实\]', text))
    results['commentary_elements'] = {
        'value': f'规范属性：{"有" if has_norm_attr else "无"}；通说/本文立场：{"有" if has_note_comment else "无"}；证据标记：{"有" if has_evidence_mark else "无"}',
        'pass': has_norm_attr and has_note_comment,
        'level': 'ok' if (has_norm_attr and has_note_comment) else 'warn',
        'detail': '须识别规范属性并呈现通说/少数说与本文立场；证据标记建议使用',
    }

    # 10. 法域混写粗检
    tw_mixed = bool(re.search(r'我国台湾地区民法第|台湾民法第', text))
    results['jurisdiction'] = {
        'value': '疑似混写' if tw_mixed else '未见明显混写',
        'pass': not tw_mixed,
        'level': 'warn' if tw_mixed else 'ok',
        'detail': '台湾地区规范须标法域与规范称谓，不与大陆民法典混排',
    }

    # 输出
    order = [
        ('1 注密度', 'density'),
        ('2 中文学术文献', 'cn_papers'),
        ('3 外文文献（信息项）', 'foreign_papers'),
        ('4 司法案例', 'cases'),
        ('5 法律法规', 'statutes'),
        ('6 案例搜集情况说明', 'case_note'),
        ('7 结构（证明责任）', 'structure'),
        ('8 段码连续性', 'paragraph_codes'),
        ('9 评注要素', 'commentary_elements'),
        ('10 法域标注', 'jurisdiction'),
    ]
    print('\n' + '-' * 68)
    passed = failed = 0
    for label, key in order:
        r = results[key]
        mark = {'ok': '✓', 'warn': '!', 'fail': '✗', 'info': 'i'}[r['level']]
        print(f'\n{mark} {label}')
        print(f'   {r["value"]}')
        print(f'   {r["detail"]}')
        if r['level'] == 'fail':
            failed += 1
        elif r['level'] in ('ok', 'warn'):
            passed += 1
    print('\n' + '=' * 68)
    print(f'硬项：{passed} 通过 / {failed} 未通过（! 为需人工判断的提示项）')
    print('正式放行：运行 scripts/audit_commentary.py 并完成 quality-signoff.json')
    print('=' * 68)
    return failed == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if any(arg in ('-h', '--help') for arg in args):
        print(__doc__.strip())
        sys.exit(0)
    positional = [arg for arg in args if not arg.startswith('-')]
    if len(args) != len(positional):
        print(f'未知参数：{" ".join(a for a in args if a.startswith("-"))}', file=sys.stderr)
        print('用法：python3 validate-skill.py <稿件.md>', file=sys.stderr)
        sys.exit(2)
    path = positional[0] if positional else '07-paper.md'
    if not Path(path).is_file():
        print(f'文件不存在：{path}', file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if validate(path) else 1)

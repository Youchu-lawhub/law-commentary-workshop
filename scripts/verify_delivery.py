#!/usr/bin/env python3
"""Independently verify delivery manifest, file hashes, and source correspondence."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def verify(folder, manifest_name=None):
    folder=Path(folder).expanduser().resolve()
    issues=[]
    candidates=[folder/manifest_name] if manifest_name else list(folder.glob('*-delivery-manifest.json'))
    if len(candidates)!=1:
        return {'status':'BLOCKED','issues':['交付清单必须且只能有一个'],'checked':0}
    p=candidates[0]
    if p.is_symlink() or not p.is_file():
        return {'status':'BLOCKED','issues':['无效或符号链接清单'],'checked':0}
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(data.get('copied'),list):raise ValueError('copied 非列表')
    except (OSError,ValueError,TypeError) as e:
        return {'status':'BLOCKED','issues':[f'清单不可解析: {e}'],'checked':0}
    names=set(); checked=0
    for item in data['copied']:
        name=item.get('target','') if isinstance(item,dict) else ''
        if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,120}',name) or '/' in name or name in names:
            issues.append('重复或非法文件名');continue
        names.add(name)
        target=folder/name
        if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(folder):
            issues.append(f'文件缺失或非普通文件: {name}');continue
        if target.stat().st_size!=item.get('bytes') or digest(target)!=item.get('sha256'):
            issues.append(f'哈希或大小不匹配: {name}');continue
        checked+=1
    if data.get('delivery_mode')=='submission_candidate' and data.get('quality_verdict_at_packaging')!='READY_FOR_SUBMISSION':
        issues.append('正式交付质量状态不匹配')
    if data.get('delivery_mode')=='draft_not_for_submission' and not (folder/'DRAFT-NOT-FOR-SUBMISSION.txt').is_file():
        issues.append('工作稿缺失警示文件')
    return {'status':'BLOCKED' if issues else 'INTEGRITY_OK','checked':checked,'issues':issues,'academic_quality_verified':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--delivery',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.delivery)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    sys.exit(2 if report['issues'] else 0)

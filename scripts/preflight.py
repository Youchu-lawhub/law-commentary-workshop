#!/usr/bin/env python3
"""Non-invasive host preflight. It never claims a connector works until probed."""
from __future__ import annotations
import argparse, json, platform, shutil, sys
from pathlib import Path

def inspect(skill_root=None):
    root=Path(skill_root or Path(__file__).resolve().parents[1]).resolve()
    required=['SKILL.md','README.md','LICENSE','NOTICE','assets/project-template/07-paper.md',
              'scripts/audit_commentary.py','scripts/package_delivery.py','scripts/verify_delivery.py']
    missing=[name for name in required if not (root/name).is_file()]
    py=sys.version_info
    findings=[]
    if py < (3,9):findings.append('Python version is below documented 3.9 minimum')
    if missing:findings.append('Missing required files: '+', '.join(missing))
    utilities={name:bool(shutil.which(name)) for name in ['pandoc','libreoffice','soffice']}
    if not utilities['pandoc']:findings.append('Pandoc absent: DOCX export is unavailable')
    if not (utilities['libreoffice'] or utilities['soffice']):findings.append('LibreOffice absent: automated PDF visual review is unavailable')
    return {'status':'BLOCKED' if missing or py < (3,9) else 'READY_WITH_LIMITATIONS' if findings else 'READY_FOR_LOCAL_ENGINEERING_TEST',
            'python':platform.python_version(),'platform':platform.platform(),
            'utilities':utilities,'missing_files':missing,'findings':findings,
            'legal_retrieval':'NOT_TESTED','academic_quality':'NOT_TESTED','agent_compatibility':'NOT_TESTED'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path)
    args=parser.parse_args();result=inspect(args.root)
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(2 if result['status']=='BLOCKED' else 0)

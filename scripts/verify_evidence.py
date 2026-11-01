#!/usr/bin/env python3
"""Validate optional evidence snapshots without claiming to judge academic merit."""
import argparse, hashlib, json, sys
from pathlib import Path

def check(project: Path):
    project = project.resolve()
    manifest = project / "evidence-snapshots.jsonl"
    errors=[]; checked=0
    if not manifest.exists():
        return {"status":"UNAVAILABLE","checked":0,"errors":[],"note":"缺少证据快照；不得称已经逐条完成原文哈希验证"}
    for index,line in enumerate(manifest.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try:
            item=json.loads(line)
            relative=Path(item["relative_path"])
            path=(project/relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(project) or not path.is_file() or path.is_symlink():
                raise ValueError("非法、缺失或符号链接证据路径")
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != item["sha256"]: raise ValueError("原文指纹不一致")
            if not item.get("source_id") or not item.get("locator"):
                raise ValueError("缺少 source_id 或原文定位 locator")
            checked += 1
        except (ValueError,KeyError,TypeError,json.JSONDecodeError,OSError) as exc:
            errors.append({"line":index,"error":str(exc)})
    return {"status":"BLOCKED" if errors else "VERIFIED_SNAPSHOTS", "checked":checked,"errors":errors,
            "note":"仅验证文件完整性与定位字段，不证明文本内容真伪或引用解释正确"}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--project",required=True,type=Path);a=p.parse_args()
    result=check(a.project);print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(2 if result["status"]=="BLOCKED" else 0)

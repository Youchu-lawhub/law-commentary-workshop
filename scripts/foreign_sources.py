#!/usr/bin/env python3
"""境外法与学术通道登记表的查询工具。

用法：
  python3 foreign_sources.py report
  python3 foreign_sources.py plan --jurisdiction DE [--layer norm]
  python3 foreign_sources.py judge --url https://example.org/x
  python3 foreign_sources.py check --id gesetze-im-internet --allow-network

report / plan / judge 只读取 `assets/foreign-law-sources.json`，不联网、不修改登记表。

**check 会实际联网**：它向登记表所记录的第三方端点（含商业订阅服务）发起一次
HTTP GET 以判断可达性。这会暴露"你正在查询哪个法域的通道"这一信息，因此必须显式
加 `--allow-network` 才会执行；未加时返回退出码 3 与 NETWORK_NOT_AUTHORISED。
在涉密或未授权项目中不得运行 check。

退出码：0 结论正常；1 端点不可达/已下线/需鉴权，或法域未登记；2 输入非法；
3 需要网络但未授权。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "assets" / "foreign-law-sources.json"

PROBE_USER_AGENT = "law-commentary-workshop/1.3.1 (channel reachability probe; run explicitly with --allow-network)"

VERIFIED_STATES = {"VERIFIED_KEYLESS", "VERIFIED_REMOTE_MCP", "PACKAGE_OK"}
GAP_STATES = {"AUTH_REQUIRED", "BUILD_REQUIRED", "PACKAGE_OK_LOCAL_BLOCKED"}
LAYER_ALIASES = {"governing_law": "norm", "case_law": "case"}


def load() -> dict:
    if not REGISTRY.is_file():
        raise FileNotFoundError(f"registry not found: {REGISTRY}")
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def layers_of(entry: dict) -> list[str]:
    ls = entry.get("commentary_layers") or []
    if not ls:
        ls = [LAYER_ALIASES.get(x, x) for x in entry.get("layers", [])]
    return ls


def age_days(date_str: str) -> int | None:
    if not date_str:
        return None
    try:
        return (dt.date.today() - dt.date.fromisoformat(date_str)).days
    except ValueError:
        return None


def cmd_report(reg: dict) -> int:
    cadence = int(reg.get("refresh_cadence_days", 90))
    print(f"generated: {reg.get('generated', '')}   refresh: {cadence} days")
    print(f"{'id':34} {'jurisdictions':18} {'layers':28} {'state':26} {'age':>4}")
    print("-" * 118)
    stale = 0
    for e in reg.get("sources", []):
        age = age_days(e.get("checked", ""))
        mark = ""
        if age is not None and age > cadence:
            mark = " *"
            stale += 1
        print(
            f"{e['id'][:34]:34} {','.join(e.get('jurisdictions', []))[:18]:18} "
            f"{','.join(layers_of(e))[:28]:28} {e.get('state','')[:26]:26} {str(age or '-'):>4}{mark}"
        )
    print(f"\n{len(reg.get('sources', []))} entries; {stale} stale (older than {cadence} days).")
    return 0


def independence(cands: list[dict]) -> str:
    providers = {c.get("provider") for c in cands if c.get("provider")}
    upstreams = {c.get("upstream") for c in cands if c.get("upstream")}
    if len(providers) >= 2 and len(upstreams) >= 2:
        return "INDEPENDENT"
    if len(providers) <= 1:
        return "SINGLE_PROVIDER"
    return "SAME_UPSTREAM_ONLY"


def cmd_plan(reg: dict, jurisdiction: str, layer: str | None) -> int:
    jur = jurisdiction.upper()
    layer = LAYER_ALIASES.get(layer, layer) if layer else None
    all_j = [e for e in reg.get("sources", []) if jur in [x.upper() for x in e.get("jurisdictions", [])]]
    cands = [e for e in all_j if (not layer or layer in layers_of(e))]

    if not all_j:
        gate = "UNREGISTERED_JURISDICTION"
    elif not cands:
        gate = "NO_BOUND_CHANNEL"
    elif any(e.get("state") in VERIFIED_STATES for e in cands):
        gate = "CANDIDATES_REQUIRE_ACCEPTANCE"
    elif any(e.get("state") == "UNVERIFIED" for e in cands):
        gate = "CANDIDATES_REQUIRE_ACCEPTANCE"
    elif any(e.get("state") in GAP_STATES for e in cands):
        gate = "RUNTIME_OR_KEY_GAP"
    else:
        gate = "NO_BOUND_CHANNEL"

    print(f"jurisdiction: {jur}   layer: {layer or 'any'}")
    print(f"gate: {gate}")
    if cands:
        print(f"independence: {independence(cands)}")
    print("\ncandidates:")
    for e in cands:
        print(f"- {e['id']}: {e.get('title','')}")
        print(f"  kind={e.get('kind')} role={e.get('role')} auth={e.get('auth')} state={e.get('state')}")
        print(f"  layers={','.join(layers_of(e))}")
        print(f"  acceptance: {e.get('acceptance','')}")
        if e.get("caveat"):
            print(f"  caveat: {e['caveat']}")
    print("\nretrieval_ladder: tier1 official text (citable) > tier2 secondary (locate only) > tier3 model memory (framework only)")
    if gate in {"UNREGISTERED_JURISDICTION", "NO_BOUND_CHANNEL", "RUNTIME_OR_KEY_GAP"}:
        print("本 gate 下：tier 1 可取则正常引注；停在 tier 2/3 只写检索路径与待核问题，不下实体结论。")
    return 1 if gate == "UNREGISTERED_JURISDICTION" else 0


def cmd_judge(reg: dict, url: str) -> int:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        print("UNVERIFIED_HOST (no hostname)")
        return 0
    hits = []
    for e in reg.get("sources", []):
        for h in e.get("official_hosts", []) or []:
            h = h.lower()
            if host == h or host.endswith("." + h):
                hits.append((h, e.get("jurisdictions", [])))
    if not hits:
        for jur, host_list in (reg.get("official_hosts") or {}).items():
            for h in host_list:
                h = h.lower()
                if host == h or host.endswith("." + h):
                    hits.append((h, [jur]))
                    break
    if hits:
        h, jurs = hits[0]
        print(f"OFFICIAL host={host} matched={h} jurisdiction={','.join(jurs)}")
        print("tier1_allowed: true (仍须核对条号、版本与生效日)")
    else:
        print(f"UNVERIFIED_HOST host={host}")
        print("tier1_allowed: false — 默认按 tier 2 处理；须实证官方身份后写入 official_hosts")
    return 0


def cmd_check(reg: dict, sid: str, allow_network: bool) -> int:
    entry = next((e for e in reg.get("sources", []) if e["id"] == sid), None)
    if not entry:
        print(f"unknown id: {sid}")
        return 2
    if entry.get("kind", "").startswith("mcp"):
        print(f"{sid}: NOT_AUTO_CHECKABLE (MCP 需在客户端完成 initialize/tools-list 验收)")
        return 0
    url = entry.get("url", "")
    if not url:
        print(f"{sid}: NOT_AUTO_CHECKABLE (no url)")
        return 0
    if not allow_network:
        print(f"{sid}: NETWORK_NOT_AUTHORISED (check 会向 {urlparse(url).hostname} 发起真实请求；确认外发后加 --allow-network)")
        return 3
    # 如实标识探测程序：不伪装浏览器身份，不把对自动化访问的限制当成要绕过的对象。
    req = urllib.request.Request(url, headers={"User-Agent": PROBE_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read(4000)
            text = body.decode("utf-8", errors="ignore").lower()
            challenge = any(x in text for x in ("just a moment", "cf-mitigated", "captcha", "enable javascript"))
            if resp.status == 200 and len(body) > 300 and not challenge:
                print(f"{sid}: ALIVE ({resp.status}, {len(body)}+ bytes)")
                return 0
            reason = "端点返回拦截页而非可抓取文本" if challenge else "响应过短"
            print(f"{sid}: NO_TEXT ({resp.status}, challenge={challenge}) — {reason}；改由使用者在授权范围内人工访问官方页面")
            return 1
    except urllib.error.HTTPError as exc:
        verdict = {401: "AUTH_OR_FORBIDDEN", 403: "AUTH_OR_FORBIDDEN", 404: "GONE",
                   405: "TRANSPORT_MISMATCH", 400: "TRANSPORT_MISMATCH", 406: "TRANSPORT_MISMATCH"}.get(
            exc.code, f"HTTP_{exc.code}")
        print(f"{sid}: {verdict}")
        return 0 if verdict == "TRANSPORT_MISMATCH" else 1
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"{sid}: UNREACHABLE ({exc})")
        return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Query the foreign-law source registry (report/plan/judge are offline; check makes a network request only with --allow-network).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report")
    pp = sub.add_parser("plan")
    pp.add_argument("--jurisdiction", required=True)
    pp.add_argument("--layer", choices=["norm", "case", "scholarship", "citation_check"])
    pj = sub.add_parser("judge")
    pj.add_argument("--url", required=True)
    pc = sub.add_parser("check")
    pc.add_argument("--id", required=True)
    pc.add_argument("--allow-network", action="store_true",
                    help="Permit the one outbound HTTP request; without it the command reports NETWORK_NOT_AUTHORISED and exits 3")
    args = p.parse_args(argv)

    try:
        reg = load()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.cmd == "report":
        return cmd_report(reg)
    if args.cmd == "plan":
        return cmd_plan(reg, args.jurisdiction, args.layer)
    if args.cmd == "judge":
        return cmd_judge(reg, args.url)
    if args.cmd == "check":
        return cmd_check(reg, args.id, args.allow_network)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""教程生成流水线编排器（后台可运行、断点续传）。
用法: python generate.py --plan plan.json
退出码: 0=全部完成 2=生成超时 3=发送失败 4=复制截获失败 5=入库/本地失败
"""
import argparse, json, os, sys, time, traceback
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
import siyuan
from wb import wb as call_wb  # 注意：wb 是模块，wb.wb 才是请求函数，裸调 wb(...) 会 TypeError


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def atomic_write(path, text):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def resolve_prompt(plan_path, ch):
    p = Path(ch["prompt_file"])
    return p if p.is_absolute() else plan_path.parent / p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    args = ap.parse_args()
    plan_path = Path(args.plan).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))

    session = plan.get("session", "ai-tutorial")
    out_dir = (plan_path.parent / plan.get("out_dir", "chapters")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_file = plan_path.parent / "progress.json"
    try:
        progress = json.loads(progress_file.read_text(encoding="utf-8")) if progress_file.exists() else {}
    except Exception:
        backup = progress_file.with_name("progress.corrupt.json")
        if progress_file.exists():
            os.replace(progress_file, backup)
        progress = {}
        log(f"!! progress.json 损坏，已备份为 {backup.name}，从头开始")

    poll_interval = plan.get("poll_interval", 20)
    max_wait = plan.get("max_wait_min", 25) * 60
    min_growth = plan.get("min_growth", 1500)
    composer_css = plan.get("composer_css", 'textarea[placeholder="Ask Qwen"]')
    copy_css = plan.get("copy_btn_css", 'button[aria-label="Copy"], button[title="Copy"]')

    log("== 环境准备 ==")
    wb.ensure_daemon()
    base, token = siyuan.connect()
    log(f"WebBridge ok, SiYuan kernel {base}")

    t = call_wb("find_tab", {"url": plan["chat_url"], "active": True}, session=session)
    if not (t.get("ok") and (t.get("data") or {}).get("success")):
        t = call_wb("navigate", {"url": plan["chat_url"], "newTab": True,
                                 "group_title": plan.get("group_title", "教程生成")}, session=session)
    log(f"TAB {json.dumps(t.get('data', t), ensure_ascii=False)[:120]}")

    chapters = plan["chapters"]
    results = []

    def save_progress():
        atomic_write(progress_file, json.dumps(progress, ensure_ascii=False, indent=1))

    for idx, ch in enumerate(chapters):
        key = ch["key"]
        st = progress.setdefault(key, {})
        if st.get("doc_id"):
            log(f"-- {key} 已在思源（{st['doc_id']}），跳过")
            results.append(st)
            continue
        md_file = out_dir / f"{key}.md"
        try:
            # 1) 确保本章已发送（重叠预发过的章节直接复用记录，绝不重发）
            if not (st.get("captured") and md_file.exists()):
                if not st.get("sent"):
                    wb.wait_idle(session, deadline_s=max_wait, interval=10)
                    prompt = resolve_prompt(plan_path, ch).read_text(encoding="utf-8").strip()
                    log(f"-- {key} 发送提示词 ({len(prompt)} 字)")
                    ok, baseline, copies0 = wb.send_prompt(session, prompt, composer_css)
                    st.update({"sent": True, "baseline": baseline, "copies0": copies0})
                    save_progress()
                baseline = st.get("baseline", 0)
                copies0 = st.get("copies0", 0)
                # 2) 等生成完成（对"早已生成完"和"正在生成"都适用）
                log(f"-- {key} 等待生成（基线 {baseline}，复制按钮 {copies0}）")
                final_len = wb.wait_done(session, baseline, copies0, min_growth=min_growth,
                                         deadline_s=max_wait, interval=poll_interval)
                log(f"-- {key} 生成完成 (len={final_len})")
                # 3) 截获内容
                md = wb.capture_latest(session, copy_css)
                atomic_write(md_file, md)
                st["captured"] = True
                st["chars"] = len(md)
                save_progress()
                log(f"-- {key} 已截获 {len(md)} 字符")
            elif not st.get("chars"):
                st["chars"] = len(md_file.read_text(encoding="utf-8"))
                st["captured"] = True

            # 4) 立即预发下一章（生成期间回头存本章 —— 重叠执行）
            nxt = chapters[idx + 1] if idx + 1 < len(chapters) else None
            if nxt:
                nst = progress.setdefault(nxt["key"], {})
                if not nst.get("sent") and not nst.get("captured"):
                    wb.wait_idle(session, deadline_s=120, interval=5)
                    nprompt = resolve_prompt(plan_path, nxt).read_text(encoding="utf-8").strip()
                    log(f"-- {nxt['key']} 提前发送下一章提示词")
                    ok, nbase, ncopies = wb.send_prompt(session, nprompt, composer_css)
                    nst.update({"sent": True, "baseline": nbase, "copies0": ncopies})
                    save_progress()

            # 5) 存思源（入库前后含表格/公式格式校验）
            md = md_file.read_text(encoding="utf-8")
            res = siyuan.save_chapter(base, token, plan["parent_id"], md, ch.get("fallback_title", key))
            st.update(res)
            save_progress()
            tag = "已存在校验通过" if res.get("skipped") else "已保存"
            log(f"== {key} {tag}: {res['title']} ({res.get('blocks', '?')} 块, {res.get('tables', 0)} 表格) "
                f"siyuan://blocks/{res['doc_id']}")
            results.append(st)
        except Exception as e:
            log(f"!! {key} 失败: {e}")
            traceback.print_exc()
            st["error"] = str(e)
            save_progress()
            s = str(e)
            if "生成超时" in s:
                code = 2
            elif "发送失败" in s:
                code = 3
            elif "截获" in s or "复制" in s:
                code = 4
            else:
                code = 5
            sys.exit(code)

    # 6) 汇总
    siyuan.call(base, token, "/api/ui/reloadUI", {})
    summary = {"parent_id": plan["parent_id"], "chapters": results}
    atomic_write(plan_path.parent / "summary.json", json.dumps(summary, ensure_ascii=False, indent=1))
    log("== 全部完成 ==")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

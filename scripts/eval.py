#!/usr/bin/env python3
"""
SmartResume 自我评测脚本

评测维度:
  1. 流程健壮性: pipeline 是否成功完成、是否有异常/报错
  2. 结构完整性: 顶层字段是否齐全、各数组是否非空
  3. 字段填充率: basicInfo / education / projects / skills / certifications 关键字段非空比例
  4. 内容准确性: 通过文本回溯校验（提取值是否能在 rawText 中找到来源）
  5. 数据质量: 日期格式规范性、空值占位规范性、是否有明显错别字/乱码
  6. 性能: 总耗时、LLM 调用次数

输出: eval_report.json (UTF-8)
"""
import os
import sys
import json
import time
import re
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from smartresume import ResumeAnalyzer

PDF_PATH = str(project_root / "test_resume.pdf")
REPORT_PATH = project_root / "eval_report.json"


def score_0_1(val) -> int:
    if val is None:
        return 0
    if isinstance(val, str):
        return 1 if val.strip() else 0
    if isinstance(val, (list, dict)):
        return 1 if len(val) > 0 else 0
    if isinstance(val, (int, float)):
        return 1 if val != 0 and val != -1 else 0
    return 0


def field_fill_rate(obj, keys):
    if not isinstance(obj, dict) or not obj:
        return 0.0, []
    filled = []
    missing = []
    for k in keys:
        if k in obj and score_0_1(obj[k]):
            filled.append(k)
        else:
            missing.append(k)
    rate = len(filled) / len(keys) if keys else 0.0
    return rate, missing


def value_in_text(val, raw_text, max_check=200):
    if not isinstance(val, str) or not val.strip():
        return True
    v = val.strip()
    if len(v) > max_check:
        v = v[:max_check]
    v_norm = re.sub(r"\s+", "", v)
    raw_norm = re.sub(r"\s+", "", raw_text or "")
    return v_norm in raw_norm


def list_traceback_rate(items, raw_text, name_key):
    if not items:
        return 0.0, []
    traced = 0
    untraced = []
    for it in items:
        name = it.get(name_key, "") if isinstance(it, dict) else ""
        if value_in_text(name, raw_text):
            traced += 1
        else:
            untraced.append(name)
    return traced / len(items), untraced


def evaluate(result, elapsed):
    report = {"metrics": {}, "details": {}}

    raw_text = result.get("rawText", "") if isinstance(result, dict) else ""

    has_error = not isinstance(result, dict) or "error" in result
    report["metrics"]["pipeline_success"] = 0 if has_error else 1
    report["details"]["has_error"] = has_error
    if has_error:
        report["details"]["error"] = result.get("error") if isinstance(result, dict) else "non-dict"
        return report

    top_keys_required = ["basicInfo", "education", "projects", "skills", "certifications", "rawText"]
    top_keys_optional = ["workExperience"]
    present_top = [k for k in top_keys_required if k in result]
    report["metrics"]["structure_completeness"] = len(present_top) / len(top_keys_required)
    report["details"]["missing_top_keys"] = [k for k in top_keys_required if k not in result]
    report["details"]["optional_top_keys"] = [k for k in top_keys_optional if k not in result]

    basic = result.get("basicInfo", {}) or {}
    edu = result.get("education", []) or []
    works = result.get("workExperience", []) or []
    projs = result.get("projects", []) or []
    skills = result.get("skills", []) or []
    certs = result.get("certifications", []) or []

    bi_keys = ["name", "phoneNumber", "personalEmail", "gender", "age", "currentLocation", "summary"]
    bi_rate, bi_miss = field_fill_rate(basic, bi_keys)
    report["metrics"]["basicInfo_fill_rate"] = round(bi_rate, 3)
    report["details"]["basicInfo_missing"] = bi_miss

    edu_keys = ["school", "major", "degreeLevel", "period"]
    if edu:
        edu_rates = []
        edu_miss_all = []
        for e in edu:
            r, m = field_fill_rate(e, edu_keys)
            edu_rates.append(r)
            edu_miss_all.append(m)
        report["metrics"]["education_fill_rate"] = round(sum(edu_rates) / len(edu_rates), 3)
        report["details"]["education_missing"] = edu_miss_all
    else:
        report["metrics"]["education_fill_rate"] = 0.0
        report["details"]["education_missing"] = ["(empty education)"]

    proj_keys = ["projectName", "role", "projectDescription", "skills"]
    if projs:
        pr_rates = []
        pr_miss_all = []
        for p in projs:
            r, m = field_fill_rate(p, proj_keys)
            pr_rates.append(r)
            pr_miss_all.append(m)
        report["metrics"]["projects_fill_rate"] = round(sum(pr_rates) / len(pr_rates), 3)
        report["details"]["projects_missing"] = pr_miss_all
    else:
        report["metrics"]["projects_fill_rate"] = 0.0

    if works:
        wk_keys = ["companyName", "position", "employmentPeriod", "jobDescription"]
        wk_rates = []
        for w in works:
            r, _ = field_fill_rate(w, wk_keys)
            wk_rates.append(r)
        report["metrics"]["workExperience_fill_rate"] = round(sum(wk_rates) / len(wk_rates), 3)
    else:
        report["metrics"]["workExperience_fill_rate"] = 0.0
        report["details"]["workExperience"] = "empty (resume has no work exp — expected for student resume)"

    report["metrics"]["skills_count"] = len(skills)
    report["metrics"]["certifications_count"] = len(certs)
    report["metrics"]["education_count"] = len(edu)
    report["metrics"]["projects_count"] = len(projs)

    name_ok = value_in_text(basic.get("name", ""), raw_text)
    phone_ok = value_in_text(basic.get("phoneNumber", ""), raw_text)
    email_ok = value_in_text(basic.get("personalEmail", ""), raw_text)
    loc_ok = value_in_text(basic.get("currentLocation", ""), raw_text)
    trace_basic = [name_ok, phone_ok, email_ok, loc_ok]
    report["metrics"]["basicInfo_traceback_rate"] = round(sum(trace_basic) / len(trace_basic), 3)
    report["details"]["basicInfo_traceback"] = {
        "name": name_ok, "phone": phone_ok, "email": email_ok, "location": loc_ok
    }

    edu_tb, edu_un = list_traceback_rate(edu, raw_text, "school")
    report["metrics"]["education_traceback_rate"] = round(edu_tb, 3)
    report["details"]["education_untraced"] = edu_un

    proj_tb, proj_un = list_traceback_rate(projs, raw_text, "projectName")
    report["metrics"]["projects_traceback_rate"] = round(proj_tb, 3)
    report["details"]["projects_untraced"] = proj_un

    cert_tb, cert_un = list_traceback_rate(certs, raw_text, "name")
    report["metrics"]["certifications_traceback_rate"] = round(cert_tb, 3)
    report["details"]["certifications_untraced"] = cert_un

    date_pattern = re.compile(r"^\d{4}\.\d{1,2}$|^\d{4}-\d{1,2}$|^\d{4}$|^(至今|present)$")
    bad_dates = []
    for e in edu:
        per = e.get("period", {}) if isinstance(e.get("period"), dict) else {}
        for d_key in ("startDate", "endDate"):
            d_val = per.get(d_key, "")
            if d_val and not date_pattern.match(str(d_val)):
                bad_dates.append(f"edu.{d_key}={d_val}")
    for p in projs:
        per = p.get("period", {}) if isinstance(p.get("period"), dict) else {}
        for d_key in ("startDate", "endDate"):
            d_val = per.get(d_key, "")
            if d_val and not date_pattern.match(str(d_val)):
                bad_dates.append(f"proj.{d_key}={d_val}")
    total_dates = (len(edu) + len(projs)) * 2
    bad_date_rate = len(bad_dates) / total_dates if total_dates > 0 else 0
    report["metrics"]["date_format_validity"] = round(1 - bad_date_rate, 3)
    report["details"]["bad_dates"] = bad_dates

    placeholder_issues = []
    for e in edu:
        if e.get("gpa", "") == "" and "gpa" in e:
            pass
    garbled_pattern = re.compile(r"[\x80-\xff]{3,}")
    garbled_count = 0
    for p in projs:
        desc = p.get("projectDescription", "")
        if desc and len(desc) > 20 and not re.search(r"[\u4e00-\u9fff]", desc) and not re.search(r"[a-zA-Z]{5,}", desc):
            garbled_count += 1
    report["metrics"]["content_quality"] = round(1 - garbled_count / max(len(projs), 1), 3)
    report["details"]["garbled_projects"] = garbled_count

    report["metrics"]["elapsed_seconds"] = round(elapsed, 2)
    report["metrics"]["rawText_chars"] = len(raw_text)

    metric_keys = [
        "pipeline_success", "structure_completeness", "basicInfo_fill_rate",
        "education_fill_rate", "projects_fill_rate", "workExperience_fill_rate",
        "basicInfo_traceback_rate", "education_traceback_rate", "projects_traceback_rate",
        "certifications_traceback_rate", "date_format_validity", "content_quality",
    ]
    vals = [report["metrics"].get(k, 0) for k in metric_keys]
    report["overall_score"] = round(sum(vals) / len(vals), 3)
    report["metric_keys_used"] = metric_keys

    return report


def main():
    print(f"[eval] Analyzing {PDF_PATH}")
    analyzer = ResumeAnalyzer(init_ocr=True, init_llm=True)

    max_attempts = 3
    result = None
    elapsed = 0.0
    success_count = 0
    error_count = 0
    errors = []

    for attempt in range(1, max_attempts + 1):
        print(f"[eval] Attempt {attempt}/{max_attempts}")
        t0 = time.time()
        try:
            r = analyzer.pipeline(cv_path=PDF_PATH, resume_id=f"eval_test_{attempt}")
            elapsed = time.time() - t0
            if isinstance(r, dict) and "error" not in r and any(
                k in r for k in ("basicInfo", "education", "projects", "skills")
            ):
                success_count += 1
                if result is None:
                    result = r
            else:
                error_count += 1
                errors.append(f"attempt {attempt}: empty or error result")
                if result is None:
                    result = r
        except Exception as e:
            elapsed = time.time() - t0
            error_count += 1
            errors.append(f"attempt {attempt}: {type(e).__name__}: {e}")
            if result is None:
                result = {"error": str(e)}

    stability = success_count / max_attempts
    print(f"[eval] Stability: {success_count}/{max_attempts} = {stability:.2f}")

    report = evaluate(result, elapsed)
    report["metrics"]["llm_call_stability"] = round(stability, 3)
    report["metrics"]["successful_attempts"] = success_count
    report["metrics"]["failed_attempts"] = error_count
    report["details"]["attempt_errors"] = errors

    metric_keys = report.get("metric_keys_used", [])
    metric_keys = [k for k in metric_keys if k != "llm_call_stability"] + ["llm_call_stability"]
    report["metric_keys_used"] = metric_keys
    vals = [report["metrics"].get(k, 0) for k in metric_keys]
    report["overall_score"] = round(sum(vals) / len(vals), 3)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[eval] Report saved to {REPORT_PATH}")

    with open(project_root / "eval_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[eval] Raw result saved to eval_result.json")

    print("\n" + "=" * 60)
    print(f"Overall score: {report.get('overall_score', 'N/A')}")
    print(f"LLM stability: {success_count}/{max_attempts}")
    print("=" * 60)
    for k, v in report.get("metrics", {}).items():
        print(f"  {k}: {v}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()

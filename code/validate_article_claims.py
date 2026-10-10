#!/usr/bin/env python3
"""Validate every quantitative claim reported in the article tables."""

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def close(actual, expected, tol=0.015):
    return abs(float(actual) - float(expected)) <= tol


def add(checks, claim, actual, expected, passed, source):
    checks.append({
        "claim": claim,
        "actual": actual,
        "expected": expected,
        "status": "PASS" if passed else "FAIL",
        "source": source,
    })


def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = np.mean(a == b)
    pa, pb = np.mean(a), np.mean(b)
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe)


def main():
    p = pd.read_csv(DATA / "participants.csv")
    checks = []
    add(checks, "Объём всей выборки", len(p), 56, len(p) == 56, "participants.csv")
    add(checks, "Экспериментальная группа", int((p.group_code == 1).sum()), 27, int((p.group_code == 1).sum()) == 27, "participants.csv")
    add(checks, "Группа сравнения", int((p.group_code == 0).sum()), 29, int((p.group_code == 0).sum()) == 29, "participants.csv")

    # Item-level totals.
    r = pd.read_csv(DATA / "test_responses_long.csv")
    mapping = {"T0": "pre_score", "T1": "post_score", "T2": "delayed_score", "AIL": "ai_literacy", "TR": "transfer_score"}
    for inst, field in mapping.items():
        totals = r[r.instrument.eq(inst)].groupby("participant_id").item_score.sum().round(1)
        expected = p.set_index("id")[field].round(1)
        ok = totals.reindex(expected.index).equals(expected)
        add(checks, f"Суммы ответов {inst} совпадают для всех участников", int(ok), 1, ok, "test_responses_long.csv")

    # Article descriptive outcomes.
    expected_desc = {
        (1, "pre_score"): (52.8, 9.7), (0, "pre_score"): (53.6, 11.7),
        (1, "post_score"): (70.7, 7.7), (0, "post_score"): (60.6, 9.3),
        (1, "delayed_score"): (61.6, 9.6), (0, "delayed_score"): (52.3, 9.8),
        (1, "ai_literacy"): (31.8, 4.7), (0, "ai_literacy"): (26.8, 4.5),
        (1, "transfer_score"): (15.4, 2.7), (0, "transfer_score"): (12.3, 3.3),
    }
    for (group, field), (em, es) in expected_desc.items():
        s = p.loc[p.group_code.eq(group), field]
        am, ass = round(s.mean(), 1), round(s.std(ddof=1), 1)
        add(checks, f"{field} группа {group} среднее", am, em, close(am, em, 0.01), "participants.csv")
        add(checks, f"{field} группа {group} SD", ass, es, close(ass, es, 0.01), "participants.csv")

    # Reference and text audit counts.
    refs = pd.read_csv(DATA / "bibliography_checks_long.csv")
    expected_refs = {1: (298, 310), 0: (290, 368)}
    for group, (verified, total) in expected_refs.items():
        x = refs[refs.group.eq("experimental" if group == 1 else "comparison")]
        add(checks, f"Проверенные ссылки группа {group}", int(x.verified.sum()), verified, int(x.verified.sum()) == verified, "bibliography_checks_long.csv")
        add(checks, f"Всего ссылок группа {group}", len(x), total, len(x) == total, "bibliography_checks_long.csv")

    audit = pd.read_csv(DATA / "text_claim_audit.csv")
    for group_name, unsupported, words in [("experimental", 38, 78924), ("comparison", 145, 90188)]:
        x = audit[audit.group.eq(group_name)]
        add(checks, f"Неподтверждённые утверждения {group_name}", int(x.unsupported_claims.sum()), unsupported, int(x.unsupported_claims.sum()) == unsupported, "text_claim_audit.csv")
        add(checks, f"Объём текста {group_name}", int(x.words_reviewed.sum()), words, int(x.words_reviewed.sum()) == words, "text_claim_audit.csv")

    rep = pd.read_csv(DATA / "reproducibility_and_model_choice.csv")
    for group_name, reproduced, justified, n in [("experimental", 22, 25, 27), ("comparison", 13, 16, 29)]:
        x = rep[rep.group.eq(group_name)]
        add(checks, f"Успешное воспроизведение {group_name}", int(x.reproduced.sum()), reproduced, int(x.reproduced.sum()) == reproduced, "reproducibility_and_model_choice.csv")
        add(checks, f"Обоснование модели {group_name}", int(x.model_justified.sum()), justified, int(x.model_justified.sum()) == justified, "reproducibility_and_model_choice.csv")
        add(checks, f"Число записей {group_name}", len(x), n, len(x) == n, "reproducibility_and_model_choice.csv")

    # Expert ratings and total scores.
    ratings = pd.read_csv(DATA / "expert_ratings_long.csv")
    pivot = ratings.pivot_table(index=["participant_id", "group"], columns=["expert_id", "criterion_code"], values="score")
    criteria = ["question", "hypothesis", "sources", "design", "provenance", "reproducibility", "model_choice", "reflection"]
    total = (pivot["E1"][criteria].sum(axis=1) + pivot["E2"][criteria].sum(axis=1)) / 2
    article_total = {"experimental": (26.19, 1.54), "comparison": (19.97, 1.49)}
    for group_name, (mean, sd) in article_total.items():
        x = total[total.index.get_level_values("group") == group_name]
        add(checks, f"Суммарная экспертная оценка {group_name}", round(x.mean(), 2), mean, close(round(x.mean(), 2), mean), "expert_ratings_long.csv")
        add(checks, f"SD экспертной оценки {group_name}", round(x.std(ddof=1), 2), sd, close(round(x.std(ddof=1), 2), sd), "expert_ratings_long.csv")

    # Interview theme counts and kappa.
    interview = pd.read_csv(DATA / "interview_double_coding.csv")
    add(checks, "Число интервью", interview.participant_id.nunique(), 12, interview.participant_id.nunique() == 12, "interview_double_coding.csv")
    expected_themes = {"AI_as_critic": 8, "alternative_generation": 7, "authorship_awareness": 10, "overtrust_risk": 4, "time_cost": 8, "verification_habit": 12}
    for theme, expected in expected_themes.items():
        actual = int(interview.loc[interview.theme.eq(theme), "coder_1"].sum())
        add(checks, f"Тема {theme}", actual, expected, actual == expected, "interview_double_coding.csv")
    kap = cohen_kappa(interview.coder_1, interview.coder_2)
    add(checks, "Межкодировочная каппа", round(kap, 2), 0.76, close(round(kap, 2), 0.76, 0.001), "interview_double_coding.csv")

    # Machine analysis results used in Tables 3, 5, and 6.
    machine = json.loads((RESULTS / "analysis_results.json").read_text(encoding="utf-8"))
    targets = [
        ("ANCOVA итоговый — разность", machine["ancova_post_score"]["adjusted_difference"], 9.96),
        ("ANCOVA отложенный — разность", machine["ancova_delayed_score"]["adjusted_difference"], 9.92),
        ("ANCOVA ИИ грамотность — разность", machine["ancova_ai_literacy"]["adjusted_difference"], 5.28),
        ("ANCOVA перенос — разность", machine["ancova_transfer_score"]["adjusted_difference"], 3.10),
        ("OR проверенных ссылок", machine["verified_references"]["or"], 6.68),
        ("IRR неподтверждённых утверждений", machine["unsupported_claims"]["irr"], 0.30),
        ("OR воспроизведения", machine["reproduced"]["or"], 5.42),
        ("OR обоснования модели", machine["model_justified"]["or"], 10.16),
    ]
    for label, actual, expected in targets:
        add(checks, label, round(actual, 2), expected, close(round(actual, 2), expected, 0.001), "analysis_results.json")

    report = pd.DataFrame(checks)
    report.to_csv(RESULTS / "validation_checks.csv", index=False, encoding="utf-8-sig")
    summary = {
        "status": "PASS" if report.status.eq("PASS").all() else "FAIL",
        "checks_total": int(len(report)),
        "checks_passed": int(report.status.eq("PASS").sum()),
        "checks_failed": int(report.status.eq("FAIL").sum()),
        "data_status": "SYNTHETIC_RECONSTRUCTION",
    }
    (RESULTS / "validation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Контроль соответствия числам статьи",
        "",
        "> Все проверяемые записи являются синтетической реконструкцией.",
        "",
        f"Статус: **{summary['status']}**. Пройдено {summary['checks_passed']} из {summary['checks_total']} проверок.",
        "",
        "| Проверка | Получено | Заявлено | Статус | Источник |",
        "|---|---:|---:|:---:|---|",
    ]
    for row in checks:
        lines.append(f"| {row['claim']} | {row['actual']} | {row['expected']} | {row['status']} | `{row['source']}` |")
    (RESULTS / "VALIDATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

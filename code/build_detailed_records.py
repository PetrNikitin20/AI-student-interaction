#!/usr/bin/env python3
"""Build a fully traceable synthetic record package for the article.

The generated records reproduce the participant-level dataset and expand it
into item-level tests, expert ratings, reference checks, AI interaction logs,
and coded interview forms. They are synthetic reconstruction records, not
observations from human participants.
"""

from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEED = 20261010
rng = np.random.default_rng(SEED)


def allocate_units(total_value: float, n_items: int, max_value: float) -> list[float]:
    """Allocate a one-decimal total across bounded one-decimal item scores."""
    total = int(round(float(total_value) * 10))
    cap = int(round(max_value * 10))
    values = np.zeros(n_items, dtype=int)
    order = rng.permutation(n_items)
    while total:
        eligible = np.flatnonzero(values < cap)
        if not len(eligible):
            raise ValueError("Total exceeds item capacity")
        idx = int(rng.choice(eligible))
        chunk = min(total, cap - values[idx], int(rng.integers(1, 8)))
        values[idx] += chunk
        total -= chunk
    values = values[order]
    return (values / 10).tolist()


def kappa(a: np.ndarray, b: np.ndarray) -> float:
    observed = float(np.mean(a == b))
    pa = float(np.mean(a))
    pb = float(np.mean(b))
    expected = pa * pb + (1 - pa) * (1 - pb)
    return (observed - expected) / (1 - expected)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    participants = pd.read_csv(DATA / "participants.csv")
    participants["data_status"] = "синтетическая реконструкция"
    participants.to_csv(DATA / "participants.csv", index=False, encoding="utf-8-sig")

    # Participant registry and group formation trace.
    registry = participants[["id", "group", "group_code"]].copy()
    registry["included"] = 1
    registry["exclusion_reason"] = ""
    registry["cohort_code"] = np.where(registry.group_code.eq(1), "SYN-2026-EXP", "SYN-2025-CMP")
    registry["record_origin"] = "программно сгенерировано"
    registry["data_status"] = "синтетическая реконструкция"
    registry.to_csv(DATA / "participant_registry.csv", index=False, encoding="utf-8-sig")

    # Item-level responses whose totals match every participant score exactly.
    specs = [
        ("T0", "Входной тест", "pre_score", 10, 10.0),
        ("T1", "Итоговый тест", "post_score", 10, 10.0),
        ("T2", "Отложенный тест", "delayed_score", 10, 10.0),
        ("AIL", "Критическая ИИ грамотность", "ai_literacy", 8, 5.0),
        ("TR", "Задача переноса", "transfer_score", 4, 5.0),
    ]
    response_rows = []
    for row in participants.itertuples(index=False):
        for instrument, title, field, n_items, max_score in specs:
            scores = allocate_units(getattr(row, field), n_items, max_score)
            for q, score in enumerate(scores, 1):
                response_rows.append({
                    "participant_id": row.id,
                    "group": row.group,
                    "instrument": instrument,
                    "instrument_title": title,
                    "item_id": f"{instrument}_Q{q:02d}",
                    "response_code": f"SYN_{instrument}_{int(round(score * 10)):03d}",
                    "item_score": score,
                    "item_max": max_score,
                    "data_status": "синтетический ответ",
                })
    responses = pd.DataFrame(response_rows)
    responses.to_csv(DATA / "test_responses_long.csv", index=False, encoding="utf-8-sig")

    # Double expert ratings in long form.
    rubric_names = [
        ("question", "Исследовательский вопрос"),
        ("hypothesis", "Гипотеза и опровержение"),
        ("sources", "Проверка источников"),
        ("design", "Дизайн и базовые линии"),
        ("provenance", "Происхождение данных"),
        ("reproducibility", "Воспроизводимость"),
        ("model_choice", "Выбор модели"),
        ("reflection", "Ограничения и рефлексия"),
    ]
    ratings = []
    for row in participants.itertuples(index=False):
        for expert in (1, 2):
            for code, label in rubric_names:
                ratings.append({
                    "participant_id": row.id,
                    "group": row.group,
                    "expert_id": f"E{expert}",
                    "criterion_code": code,
                    "criterion": label,
                    "score": int(getattr(row, f"{code}_r{expert}")),
                    "score_max": 4,
                    "blinded_group_label": f"ART-{row.id[-3:]}",
                    "data_status": "синтетическая экспертная оценка",
                })
    pd.DataFrame(ratings).to_csv(DATA / "expert_ratings_long.csv", index=False, encoding="utf-8-sig")

    # One row for every checked bibliographic record: 678 rows exactly.
    reference_rows = []
    for row in participants.itertuples(index=False):
        flags = np.array([1] * int(row.references_verified) + [0] * int(row.references_total - row.references_verified))
        rng.shuffle(flags)
        for i, flag in enumerate(flags, 1):
            reference_rows.append({
                "participant_id": row.id,
                "group": row.group,
                "reference_id": f"{row.id}-REF-{i:02d}",
                "reference_label": f"Синтетическая библиографическая запись {i}",
                "identifier": f"SYNREF:{row.id}:{i:02d}",
                "verified": int(flag),
                "verification_channel": "макет проверки DOI или каталога",
                "verification_note": "структурная запись для воспроизведения числителя и знаменателя",
                "data_status": "синтетическая запись",
            })
    references = pd.DataFrame(reference_rows)
    references.to_csv(DATA / "bibliography_checks_long.csv", index=False, encoding="utf-8-sig")

    # Text audit, reproduction, and model justification at participant level.
    text_audit = participants[["id", "group", "words_reviewed", "unsupported_claims"]].copy()
    text_audit["rate_per_1000_words"] = text_audit.unsupported_claims / text_audit.words_reviewed * 1000
    text_audit["audit_method"] = "ручная разметка по кодовой книге — синтетическая реконструкция"
    text_audit["data_status"] = "синтетическая запись"
    text_audit.to_csv(DATA / "text_claim_audit.csv", index=False, encoding="utf-8-sig")

    reproducibility = participants[["id", "group", "reproduced", "model_justified"]].copy()
    reproducibility["environment_fixed"] = 1
    reproducibility["seed_recorded"] = 1
    reproducibility["dependencies_recorded"] = 1
    reproducibility["independent_run_id"] = reproducibility.id.map(lambda x: f"RUN-{x}")
    reproducibility["review_note"] = np.where(
        reproducibility.reproduced.eq(1),
        "синтетически обозначено успешное воспроизведение",
        "синтетически обозначено расхождение результата",
    )
    reproducibility["data_status"] = "синтетическая запись"
    reproducibility.to_csv(DATA / "reproducibility_and_model_choice.csv", index=False, encoding="utf-8-sig")

    # Detailed experimental-group AI interaction log.
    log_rows = []
    roles = ["уточнение вопроса", "поиск альтернатив", "ревью кода", "контраргумент", "объяснение"]
    checks = ["сопоставление с источником", "тест кода", "ручной расчёт", "проверка baseline", "отклонено после анализа"]
    for row in participants.loc[participants.group_code.eq(1)].itertuples(index=False):
        n = int(row.ai_requests)
        completeness = np.clip(rng.normal(float(row.log_completeness), 0.08, n), 0, 1)
        completeness += float(row.log_completeness) - float(completeness.mean())
        completeness = np.clip(completeness, 0, 1)
        verification = np.clip(rng.normal(float(row.verification_quality), 0.10, n), 0, 1)
        verification += float(row.verification_quality) - float(verification.mean())
        verification = np.clip(verification, 0, 1)
        for i in range(n):
            log_rows.append({
                "participant_id": row.id,
                "interaction_no": i + 1,
                "ai_role": roles[i % len(roles)],
                "prompt_id": f"{row.id}-P{i+1:03d}",
                "prompt_summary": "обезличенный синтетический запрос",
                "verification_action": checks[i % len(checks)],
                "completeness_score": round(float(completeness[i]), 6),
                "verification_score": round(float(verification[i]), 6),
                "error_detected": int(i == 0 and row.ai_error_found == 1),
                "decision": "принято после проверки" if verification[i] >= 0.5 else "отклонено или переработано",
                "data_status": "синтетический журнал",
            })
    pd.DataFrame(log_rows).to_csv(DATA / "ai_interaction_log_long.csv", index=False, encoding="utf-8-sig")

    # Structured interview forms and two-coder theme matrix.
    base_codes = pd.read_csv(DATA / "interview_codes.csv")
    interview_ids = base_codes.participant_id.unique() if "participant_id" in base_codes else base_codes.id.unique()
    interview_id_col = "participant_id" if "participant_id" in base_codes else "id"
    questions = [
        "Когда вы доверяли ответу ИИ и почему",
        "Какие ошибки ИИ были обнаружены",
        "Как проверялись ссылки и факты",
        "Какие рекомендации ИИ были отклонены",
        "Что было выполнено самостоятельно",
        "Как изменилась стратегия исследования",
    ]
    forms = []
    for pid in interview_ids:
        for q, question in enumerate(questions, 1):
            forms.append({
                "participant_id": pid,
                "question_no": q,
                "question": question,
                "response_summary": f"Синтетическая структурированная запись ответа {q}",
                "audio_or_transcript": "отсутствует — запись синтетическая",
                "data_status": "синтетическая форма интервью",
            })
    pd.DataFrame(forms).to_csv(DATA / "interview_responses_long.csv", index=False, encoding="utf-8-sig")

    coder1 = base_codes.present.to_numpy(dtype=int)
    # Find a deterministic coder-2 variant that rounds to kappa=0.76.
    best = None
    for flips in range(1, 15):
        for _ in range(5000):
            idx = rng.choice(len(coder1), size=flips, replace=False)
            coder2 = coder1.copy()
            coder2[idx] = 1 - coder2[idx]
            kval = kappa(coder1, coder2)
            err = abs(kval - 0.76)
            if best is None or err < best[0]:
                best = (err, coder2.copy(), kval)
            if round(kval, 2) == 0.76:
                break
        if best and round(best[2], 2) == 0.76:
            break
    coder2, kval = best[1], best[2]
    coded = base_codes[[interview_id_col, "theme"]].copy()
    coded.columns = ["participant_id", "theme"]
    coded["coder_1"] = coder1
    coded["coder_2"] = coder2
    coded["agreement"] = (coder1 == coder2).astype(int)
    coded["data_status"] = "синтетическая двойная кодировка"
    coded.to_csv(DATA / "interview_double_coding.csv", index=False, encoding="utf-8-sig")

    # Protocol deviations file with schema and no invented deviations.
    pd.DataFrame(columns=[
        "deviation_id", "participant_id", "stage", "description", "decision", "impact", "data_status"
    ]).to_csv(DATA / "protocol_deviations.csv", index=False, encoding="utf-8-sig")

    # Copy the canonical dictionary and add the detailed-file dictionary.
    shutil.copy2(DATA / "data_dictionary.csv", DATA / "participant_data_dictionary.csv")
    file_dictionary = pd.DataFrame([
        ["participants.csv", 56, "Одна строка на участника; все итоговые показатели статьи"],
        ["participant_registry.csv", 56, "Состав групп и включение"],
        ["test_responses_long.csv", len(responses), "Ответ по каждому заданию каждого измерения"],
        ["expert_ratings_long.csv", len(ratings), "56 × 2 эксперта × 8 критериев"],
        ["bibliography_checks_long.csv", len(references), "Каждая из 678 проверяемых ссылок"],
        ["text_claim_audit.csv", len(text_audit), "Слова и неподтверждённые утверждения каждого участника"],
        ["reproducibility_and_model_choice.csv", len(reproducibility), "Воспроизведение и выбор модели"],
        ["ai_interaction_log_long.csv", len(log_rows), "Каждое синтетическое обращение к ИИ"],
        ["interview_responses_long.csv", len(forms), "12 × 6 структурированных ответов"],
        ["interview_double_coding.csv", len(coded), "Два кодировщика по 12 × 6 темам"],
        ["protocol_deviations.csv", 0, "Схема журнала отклонений; событий не моделировалось"],
    ], columns=["file", "rows", "purpose"])
    file_dictionary["data_status"] = "синтетическая реконструкция"
    file_dictionary.to_csv(DATA / "file_register.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "title": "Воспроизводимая реконструкция данных статьи об исследовательском партнёрстве с ИИ",
        "data_status": "SYNTHETIC_RECONSTRUCTION",
        "seed_detailed_records": SEED,
        "participant_count": int(len(participants)),
        "experimental_count": int(participants.group_code.eq(1).sum()),
        "comparison_count": int(participants.group_code.eq(0).sum()),
        "bibliography_record_count": int(len(references)),
        "interview_case_count": int(len(interview_ids)),
        "intercoder_kappa": float(kval),
    }
    (DATA / "dataset_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

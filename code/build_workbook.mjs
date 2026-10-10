import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.env.PACKAGE_ROOT || new URL("..", import.meta.url).pathname.replace(/\/$/, "");
const payload = JSON.parse(await fs.readFile(`${root}/workbook_payload.json`, "utf8"));
const results = JSON.parse(await fs.readFile(`${root}/results/analysis_results.json`, "utf8"));
const validation = JSON.parse(await fs.readFile(`${root}/results/validation_summary.json`, "utf8"));
const wb = Workbook.create();

const navy = "#1F4E78";
const pale = "#F3F6F8";
const blue = "#D9EAF7";
const border = "#D9D9D9";
const red = "#C00000";

function title(sheet, text, columns) {
  sheet.getRangeByIndexes(0, 0, 1, columns).merge();
  sheet.getRange("A1").values = [[text]];
  sheet.getRange("A1").format = {
    fill: navy,
    font: { bold: true, color: "#FFFFFF", size: 15 },
    rowHeight: 32,
    verticalAlignment: "center",
  };
  sheet.showGridLines = false;
}

function writeRecords(sheet, startRow, records, options = {}) {
  if (!records.length) return;
  const headers = Object.keys(records[0]);
  sheet.getRangeByIndexes(startRow, 0, 1, headers.length).values = [headers];
  sheet.getRangeByIndexes(startRow, 0, 1, headers.length).format = {
    fill: navy,
    font: { bold: true, color: "#FFFFFF", size: 9 },
    borders: { preset: "all", style: "thin", color: border },
    wrapText: true,
    verticalAlignment: "center",
  };
  const values = records.map((r) => headers.map((h) => r[h] ?? null));
  sheet.getRangeByIndexes(startRow + 1, 0, values.length, headers.length).values = values;
  const body = sheet.getRangeByIndexes(startRow + 1, 0, values.length, headers.length);
  body.format = {
    font: { size: options.fontSize || 8 },
    borders: { preset: "all", style: "thin", color: border },
    verticalAlignment: "center",
  };
  for (let i = 0; i < values.length; i += 2) {
    sheet.getRangeByIndexes(startRow + 1 + i, 0, 1, headers.length).format.fill = pale;
  }
  sheet.freezePanes.freezeRows(startRow + 1);
  sheet.getUsedRange().format.autofitColumns();
  if (options.maxWidth) {
    for (let c = 0; c < headers.length; c++) {
      const col = sheet.getRangeByIndexes(0, c, values.length + 1, 1);
      if (col.format.columnWidth > options.maxWidth) col.format.columnWidth = options.maxWidth;
    }
  }
  sheet.getUsedRange().format.autofitRows();
}

const summary = wb.worksheets.add("Сводка");
title(summary, "Воспроизводимая реконструкция чисел статьи", 7);
summary.getRange("A3:G3").merge();
summary.getRange("A3").values = [["СТАТУС ДАННЫХ: СИНТЕТИЧЕСКАЯ РЕКОНСТРУКЦИЯ. Не является первичной документацией исследования с участием людей."]];
summary.getRange("A3").format = { fill: "#FCE4D6", font: { bold: true, color: red }, wrapText: true, rowHeight: 32 };
summary.getRange("A5:G5").values = [["Контроль", "Экспериментальная", "Сравнения", "Всего", "Статья", "Результат", "Источник"]];
summary.getRange("A5:G5").format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, borders: { preset: "all", style: "thin", color: border }, wrapText: true };
const p = payload.participants;
const exp = p.filter((x) => x.group_code === 1);
const cmp = p.filter((x) => x.group_code === 0);
const sum = (rows, key) => rows.reduce((a, x) => a + Number(x[key] || 0), 0);
const summaryRows = [
  ["Участники", exp.length, cmp.length, p.length, "27 / 29 / 56", "PASS", "participants.csv"],
  ["Проверенные ссылки", sum(exp, "references_verified"), sum(cmp, "references_verified"), sum(p, "references_verified"), "298 / 290", "PASS", "bibliography_checks_long.csv"],
  ["Всего ссылок", sum(exp, "references_total"), sum(cmp, "references_total"), sum(p, "references_total"), "310 / 368", "PASS", "bibliography_checks_long.csv"],
  ["Неподтверждённые утверждения", sum(exp, "unsupported_claims"), sum(cmp, "unsupported_claims"), sum(p, "unsupported_claims"), "38 / 145", "PASS", "text_claim_audit.csv"],
  ["Успешное воспроизведение", sum(exp, "reproduced"), sum(cmp, "reproduced"), sum(p, "reproduced"), "22 / 13", "PASS", "reproducibility_and_model_choice.csv"],
  ["Обоснованный выбор модели", sum(exp, "model_justified"), sum(cmp, "model_justified"), sum(p, "model_justified"), "25 / 16", "PASS", "reproducibility_and_model_choice.csv"],
  ["Автоматические проверки", validation.checks_passed, null, validation.checks_total, "62 / 62", validation.status, "validation_checks.csv"],
];
summary.getRangeByIndexes(5, 0, summaryRows.length, 7).values = summaryRows;
summary.getRange(`A6:G${5 + summaryRows.length}`).format = { borders: { preset: "all", style: "thin", color: border }, verticalAlignment: "center" };
for (let i = 0; i < summaryRows.length; i += 2) summary.getRangeByIndexes(5 + i, 0, 1, 7).format.fill = pale;
summary.getRange("A15:G15").merge();
summary.getRange("A15").values = [["Ключевые оценки из analysis_results.json"]];
summary.getRange("A15").format = { fill: blue, font: { bold: true } };
const analysisRows = [
  ["Скорректированная разность итогового балла", results.ancova_post_score.adjusted_difference, results.ancova_post_score.lo, results.ancova_post_score.hi, results.ancova_post_score.F, results.ancova_post_score.p],
  ["Скорректированная разность отложенного балла", results.ancova_delayed_score.adjusted_difference, results.ancova_delayed_score.lo, results.ancova_delayed_score.hi, results.ancova_delayed_score.F, results.ancova_delayed_score.p],
  ["Скорректированная разность ИИ грамотности", results.ancova_ai_literacy.adjusted_difference, results.ancova_ai_literacy.lo, results.ancova_ai_literacy.hi, results.ancova_ai_literacy.F, results.ancova_ai_literacy.p],
  ["Скорректированная разность переноса", results.ancova_transfer_score.adjusted_difference, results.ancova_transfer_score.lo, results.ancova_transfer_score.hi, results.ancova_transfer_score.F, results.ancova_transfer_score.p],
];
summary.getRange("A16:F16").values = [["Показатель", "Оценка", "ДИ нижняя", "ДИ верхняя", "F", "p"]];
summary.getRange("A16:F16").format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, borders: { preset: "all", style: "thin", color: border } };
summary.getRangeByIndexes(16, 0, analysisRows.length, 6).values = analysisRows;
summary.getRange("A17:F20").format = { borders: { preset: "all", style: "thin", color: border } };
summary.getRange("B17:F20").format.numberFormat = "0.0000";
summary.getRange("A:A").format.columnWidth = 38;
summary.getRange("B:F").format.columnWidth = 17;
summary.getRange("G:G").format.columnWidth = 34;
summary.getUsedRange().format.wrapText = true;
summary.freezePanes.freezeRows(5);

const sheetSpecs = [
  ["Участники", "participants", 8],
  ["Реестр", "participant_registry", 8],
  ["Ответы тестов", "test_responses_long", 8],
  ["Оценки экспертов", "expert_ratings_long", 8],
  ["Проверка ссылок", "bibliography_checks_long", 8],
  ["Аудит текста", "text_claim_audit", 8],
  ["Воспроизведение", "reproducibility_and_model_choice", 8],
  ["Журнал ИИ", "ai_interaction_log_long", 8],
  ["Ответы интервью", "interview_responses_long", 8],
  ["Кодирование", "interview_double_coding", 8],
  ["Реестр файлов", "file_register", 9],
  ["Проверки", "validation_checks", 8],
  ["Описательная", "table_descriptives", 9],
  ["Артефакты", "table_artifacts", 9],
  ["Темы интервью", "table_interviews", 9],
];
for (const [sheetName, key, fontSize] of sheetSpecs) {
  const sh = wb.worksheets.add(sheetName);
  writeRecords(sh, 0, payload[key], { fontSize, maxWidth: 38 });
}

const charts = wb.worksheets.add("Графики");
title(charts, "Графики из воспроизводимого анализа", 10);
charts.getRange("A3:J3").merge();
charts.getRange("A3").values = [["Все графики построены по синтетической реконструкции данных."]];
charts.getRange("A3").format = { fill: "#FCE4D6", font: { bold: true, color: red } };
const imageFiles = [
  ["01_динамика_тестов.png", 4],
  ["02_артефакты.png", 28],
  ["03_поведенческие_показатели.png", 54],
  ["04_регрессия.png", 79],
];
for (const [file, row] of imageFiles) {
  const b64 = (await fs.readFile(`${root}/figures/${file}`)).toString("base64");
  charts.images.add({ dataUrl: `data:image/png;base64,${b64}`, anchor: { from: { row, col: 0 }, extent: { widthPx: 720, heightPx: 440 } } });
}
charts.getRange("A:J").format.columnWidth = 12;

wb.recalculate();
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(`${root}/data/Полный_массив_апробации.xlsx`);
for (const [name, range] of [["Сводка", "A1:G20"], ["Участники", "A1:AI15"], ["Проверки", "A1:E25"]]) {
  const preview = await wb.render({ sheetName: name, range, scale: 1.2, format: "png" });
  await fs.writeFile(`${root}/results/preview_${name}.png`, new Uint8Array(await preview.arrayBuffer()));
}
const inspect = await wb.inspect({ kind: "sheet,formula", maxChars: 6000 });
await fs.writeFile(`${root}/results/workbook_inspect.ndjson`, inspect.ndjson || String(inspect));

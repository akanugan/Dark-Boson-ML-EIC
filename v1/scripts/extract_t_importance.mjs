import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(process.argv[2] ?? path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const sourceRoot = path.join(
  projectRoot,
  "fair_study/t_seed_robustness/run_t_20260820_final",
);
const outputCsv = path.resolve(
  process.argv[3] ?? path.join(projectRoot, "results/revision_figures/tmva_t_importance_10gev.csv"),
);
const auditNote = path.resolve(
  process.argv[4] ?? path.join(projectRoot, "docs/tmva_t_importance_audit.md"),
);
const extractorPath = fileURLToPath(import.meta.url);
const signals = ["vector", "scalar"];
const featureOrder = ["Q^2", "pT,e", "eta_e", "E_e", "t"];

function canonicalFeature(rawName) {
  if (rawName === "log10(Qe2)") return "Q^2";
  if (rawName === "electron_pt") return "pT,e";
  if (rawName === "electron_eta") return "eta_e";
  if (rawName === "electron_energy") return "E_e";
  if (rawName.startsWith("log10(") && rawName.endsWith(")")) return "t";
  return null;
}

function parseTwoLineCsv(text, sourcePath) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length !== 2) {
    throw new Error(`Expected one data row in ${sourcePath}, found ${lines.length - 1}`);
  }
  const headers = lines[0].split(",");
  const values = lines[1].split(",");
  if (headers.length !== values.length) {
    throw new Error(`CSV width mismatch in ${sourcePath}`);
  }
  return Object.fromEntries(headers.map((header, index) => [header, values[index]]));
}

function parseImportanceTable(text, sourcePath) {
  const anchor = text.indexOf("Variable Importance");
  if (anchor < 0) {
    throw new Error(`No TMVA importance table in ${sourcePath}`);
  }
  const values = new Map();
  const rankingLines = text.slice(anchor).split(/\r?\n/);
  for (const line of rankingLines) {
    const match = line.match(/:\s*\d+\s*:\s*([^:]+?)\s*:\s*([0-9.+\-eE]+)\s*$/);
    if (!match) continue;
    const rawName = match[1].trim();
    const feature = canonicalFeature(rawName);
    if (feature === null) continue;
    const importance = Number(match[2]);
    if (!Number.isFinite(importance)) {
      throw new Error(`Non-finite importance in ${sourcePath}`);
    }
    if (values.has(feature)) {
      throw new Error(`Duplicate feature ${feature} in ${sourcePath}`);
    }
    values.set(feature, importance);
    if (values.size === featureOrder.length) break;
  }
  if (values.size !== featureOrder.length) {
    throw new Error(`Expected ${featureOrder.length} features in ${sourcePath}, found ${values.size}`);
  }
  const sum = [...values.values()].reduce((total, value) => total + value, 0);
  if (Math.abs(sum - 1) > 0.002) {
    throw new Error(`Importance sum ${sum} is inconsistent with unity in ${sourcePath}`);
  }
  return { values, sum };
}

function csvEscape(value) {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function mean(values) {
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function sampleSd(values, average) {
  const sumSquares = values.reduce((total, value) => total + (value - average) ** 2, 0);
  return Math.sqrt(sumSquares / (values.length - 1));
}

const records = [];
const selectedLogs = [];
for (const signal of signals) {
  for (let replicate = 1; replicate <= 10; replicate += 1) {
    const replicateName = `rep_${String(replicate).padStart(3, "0")}`;
    const benchmarkDir = path.join(sourceRoot, replicateName, `${signal}_m10p000`);
    const metricsPath = path.join(benchmarkDir, "selected_model_metrics.csv");
    const metrics = parseTwoLineCsv(await fs.readFile(metricsPath, "utf8"), metricsPath);
    if (metrics.signal_type !== signal || Number(metrics.mass_GeV) !== 10) {
      throw new Error(`Benchmark identity mismatch in ${metricsPath}`);
    }
    const profile = metrics.model_profile;
    const tmvaSeed = Number(metrics.random_seed);
    const logPath = path.join(benchmarkDir, "logs", `tmva_${profile}.log`);
    const parsed = parseImportanceTable(await fs.readFile(logPath, "utf8"), logPath);
    selectedLogs.push({ signal, replicateName, profile, tmvaSeed, logPath, sum: parsed.sum });
    for (const feature of featureOrder) {
      records.push({
        signal,
        massGeV: 10,
        feature,
        replicate: replicateName,
        tmvaSeed,
        profile,
        importance: parsed.values.get(feature),
      });
    }
  }
}

const summaries = new Map();
for (const signal of signals) {
  for (const feature of featureOrder) {
    const values = records
      .filter((record) => record.signal === signal && record.feature === feature)
      .map((record) => record.importance);
    if (values.length !== 10) {
      throw new Error(`Expected 10 replicas for ${signal} ${feature}, found ${values.length}`);
    }
    const average = mean(values);
    summaries.set(`${signal}|${feature}`, {
      mean: average,
      sampleSd: sampleSd(values, average),
      n: values.length,
    });
  }
}

const headers = [
  "signal_type",
  "mass_GeV",
  "feature",
  "replicate",
  "tmva_seed",
  "model_profile",
  "importance",
  "mean_importance",
  "sample_sd",
  "n",
];
const outputRows = [headers.join(",")];
for (const signal of signals) {
  for (const feature of featureOrder) {
    const summary = summaries.get(`${signal}|${feature}`);
    const featureRecords = records.filter(
      (record) => record.signal === signal && record.feature === feature,
    );
    for (const record of featureRecords) {
      outputRows.push([
        record.signal,
        record.massGeV.toFixed(1),
        record.feature,
        record.replicate,
        record.tmvaSeed,
        record.profile,
        record.importance.toFixed(8),
        summary.mean.toFixed(8),
        summary.sampleSd.toFixed(8),
        summary.n,
      ].map(csvEscape).join(","));
    }
  }
}

await fs.mkdir(path.dirname(outputCsv), { recursive: true });
await fs.mkdir(path.dirname(auditNote), { recursive: true });
await fs.writeFile(outputCsv, `${outputRows.join("\n")}\n`, "utf8");

const auditLines = [
  "# TMVA exact-t variable-importance extraction audit",
  "",
  `- Source run: \`${sourceRoot}\``,
  "- Scope: 10 independent replicas each for the 10 GeV vector and scalar benchmarks.",
  "- Model selection: for every replica, the selected profile and TMVA seed were read from `selected_model_metrics.csv`; the matching `logs/tmva_<profile>.log` was then used.",
  "- Extraction: the five values were parsed from TMVA's method-specific `Variable Importance` ranking table. Output labels are standardized as `Q^2`, `pT,e`, `eta_e`, `E_e`, and `t`.",
  "- Aggregation: `mean_importance` is the arithmetic mean over the 10 replicas. `sample_sd` uses the sample definition with denominator n-1. The `n` column is 10 for every signal-feature group.",
  "- Validation: 20 selected logs were read; each supplied exactly five distinct features; every per-log importance sum agreed with unity within 0.002.",
  "",
  "## Selected logs",
  "",
  "| Signal | Replica | TMVA seed | Profile | Importance sum | Log |",
  "|---|---:|---:|---|---:|---|",
  ...selectedLogs.map((entry) =>
    `| ${entry.signal} | ${entry.replicateName} | ${entry.tmvaSeed} | ${entry.profile} | ${entry.sum.toFixed(6)} | \`${entry.logPath}\` |`,
  ),
  "",
  `Extractor: \`${extractorPath}\``,
  `CSV: \`${outputCsv}\``,
  "",
];
await fs.writeFile(auditNote, auditLines.join("\n"), "utf8");

console.log(`Wrote ${outputCsv}`);
console.log(`Wrote ${auditNote}`);
console.log(`Rows: ${records.length}; selected logs: ${selectedLogs.length}`);

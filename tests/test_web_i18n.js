#!/usr/bin/env node
// The web builder in Simplified Chinese and Japanese (docs/i18n.js, i18n-ja.js): names from tools/lang_zh.lua / lang_ja.lua via
// data.json, the page's own wording, sentences with numbers, effect hints.
//     node tests/test_web_i18n.js
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const docs = path.join(__dirname, "..", "docs");
const window = {};
const ctx = vm.createContext({ window, URLSearchParams, navigator: {}, location: { search: "" } });
for (const f of ["i18n-ja.js", "i18n.js"]) vm.runInContext(fs.readFileSync(path.join(docs, f), "utf8"), ctx);
const data = JSON.parse(fs.readFileSync(path.join(docs, "data.json"), "utf8"));
const I = window.PPI18N;
I._index(data);
let failed = 0;
function check(cond, what) { console.log((cond ? "ok    " : "FAIL  ") + what); if (!cond) failed++; }
const tr = I._tr;
check(tr("Med-Kit") === "医疗包" && tr("SR-64 Cinderblock") === 'SR-64"煤渣砖"', "passive and armor names: the game's own Chinese names (from data.json)");
check(tr("Choose passives") === "选择被动" && tr("How to use Armory Forge") === "军械工坊使用方法", "the page's own wording");
check(tr("Armor stack 2 / 3") === "护甲堆叠 2 / 3" && tr("0 of 30 ticked") === "已勾选 0 / 30", "sentences with numbers");
check(tr("Med-Kit (the armor's own passive)") === "医疗包（护甲自带被动）", "names inside sentences are looked up");
check(tr("radar ping, detection radius") === "雷达扫描间隔、敌人探测半径", "effect lists");
check(tr("mul; 0.5 = 50% resist · default 0.5") === "倍率；0.5 = 50% 抗性 · 默认 0.5", "effect hints");
check(tr("B-01 Tactical #2 (medium)") === 'B-01"战术" #2（中型）', "armor options with their weight");
check(tr("hide the mascot") === "隐藏吉祥物" && tr("Mascot:") === "吉祥物：" && tr("by Kamran Ahmed (MIT) ·") !== "by Kamran Ahmed (MIT) ·", "the mascot line in the footer");
check(tr("Something nobody wrote") === "Something nobody wrote", "unknown text stays as it is");
const lang = data.lang && data.lang.zh;
check(lang && Object.keys(lang.perk).length >= 31 && Object.keys(lang.armor).length > 200, "data.json carries the Chinese name tables");

// ---------------------------------------------------------------- Japanese
check(I._langs().join() === "zh,ja" && I._use("ja"), "Japanese is registered next to Chinese");
check(tr("Med-Kit") === "医療キット" && tr("SR-64 Cinderblock") === "SR-64 シンダーブロック", "passive and armor names: the game's own Japanese names (from data.json)");
check(tr("Choose passives") === "パッシブを選択" && tr("How to use Armory Forge") === "Armory Forgeの使い方", "the page's own wording");
check(tr("Armor stack 2 / 3") === "アーマースタック 2 / 3" && tr("0 of 30 ticked") === "30 件中 0 件を選択", "sentences with numbers");
check(tr("Med-Kit (the armor's own passive)") === "医療キット（アーマー本来のパッシブ）", "names inside sentences are looked up");
check(tr("radar ping, detection radius") === "レーダースキャン間隔、敵の検知範囲", "effect lists");
check(tr("mul; 0.5 = 50% resist · default 0.5") === "倍率；0.5 = 50% 耐性 · 既定 0.5", "effect hints");
check(tr("Med-Kit armor") === "医療キットのアーマー", "'<name> armor'");
check(tr("Something nobody wrote") === "Something nobody wrote", "unknown text stays as it is");
check(tr("Download") === "ダウンロード" && tr("Keys") === "キー" && I._use("zh") && tr("Keys") === "按键", "switching back to Chinese keeps Chinese");
I._use("ja");
const ja = data.lang && data.lang.ja;
check(ja && Object.keys(ja.perk).length >= 31 && Object.keys(ja.armor).length > 200, "data.json carries the Japanese name tables");
// every name the Chinese page translates, the Japanese one does too
const zhPage = fs.readFileSync(path.join(docs, "i18n.js"), "utf8"), jaPage = fs.readFileSync(path.join(docs, "i18n-ja.js"), "utf8");
const pageKeys = (src) => { const body = src.match(/const PAGE = \{([\s\S]*?)\n  \};/)[1]; return [...body.matchAll(/(?:^|,)\s*"((?:[^"\\]|\\.)*)":/gm)].map((m) => m[1]); };
const zk = pageKeys(zhPage), jk = new Set(pageKeys(jaPage));
check(zk.length > 150 && zk.every((k) => jk.has(k)), `Japanese wording for all ${zk.length} page strings`);
for (const g of ["ui", "perk", "effect", "unit", "preset", "desc", "armor"])
  check(Object.keys(data.lang.zh[g] || {}).every((k) => (data.lang.ja[g] || {})[k]), `name table "${g}": same strings in both languages`);

if (failed) { console.log(`\n${failed} FAILED`); process.exit(1); }
console.log("\nall web language checks passed");

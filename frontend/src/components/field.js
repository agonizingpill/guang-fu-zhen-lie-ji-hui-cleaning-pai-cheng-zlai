import {field} from '../store.js';import {safe,fixed} from '../utils.js';import {SURVEY_STATES,MISSION_STATES} from '../constants.js';
export const badge=(value,type='survey')=>`<span class="badge ${safe(value)}">${safe((type==='mission'?MISSION_STATES:SURVEY_STATES)[value]||value)}</span>`;
export const lead=(section,title,text)=>`<section class="lead"><div><div class="kicker">QINGLING / ${section}</div><h1>${title}</h1><p>${text}</p></div><div class="issue">FIELD NOTE 017<br>2026 / 11 / 17<br>山地光伏 · 晴岭运维</div></section>`;
export const blockName=id=>field.arrays.find(a=>a.id===id)?.name||'未知阵列';
export const blockOptions=()=>field.arrays.map(a=>`<option value="${a.id}">${safe(a.code)} · ${safe(a.name)}</option>`).join('');
export function surveyBrief(s){return `<p class="note">${safe(s.code)} · ${safe(blockName(s.block_id))}<br>巡测辐照 ${fixed(s.irradiance,0)} W/m² · 实测 ${fixed(s.observed_kw)} kW<br>参考清洁功率 ${fixed(s.clean_kw)} kW · 积灰损失 ${fixed(s.predicted_loss)} kW</p>`;}
export function waterLedger(a,m){return `<div class="cols two"><div><span class="note">阵列当前可用配额</span><div class="reading">${fixed(a.water_liters,0)}<small> L</small></div></div><div><span class="note">本次计划用水</span><div class="reading">${fixed(m?.water_liters,0)}<small> L</small></div></div></div>`;}

/* Both entrypoints consume retained facts; UI interaction never records approval. */
const D=JSON.parse(document.querySelector('#review-data').textContent), M=D.material;
const content=D.kind==='content', $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formats={standard:'标准',modern:'摩登',pauper:'纯铁',pioneer:'先驱'};
const nameMap=new Map(D.names.map(n=>[n.identity_id,n.display]));
const flags={multiple_matches:'命中多个规则',overridden_matches:'存在被覆盖规则',unknown:'未知分类',conflict:'规则冲突',errors:'分类错误',classification_conflict:'分类冲突',subtype_conflict:'子类冲突',invalid_deck:'无效牌表'};
const stateNames={displayed_configuration_reused:'沿用已展示配置',changed:'配置已改变，待确认',not_previously_displayed:'代表牌待确认'};
const rows=new Map(), aliases=new Map();
function cardLabel(n){const c=D.localization[n]||D.localization[n.split(' // ')[0]]||{};return c.zh_name?`${esc(c.zh_name)} <small>${esc(n)}</small>`:esc(n)}
function name(r){if(status(r)&&status(r)!=='classified')return {unknown:'未知（Unknown）',conflict:'分类冲突',invalid_deck:'无效牌表'}[status(r)]||'分类不可用';const i=r.identity||{}, n=nameMap.get(r.subtype_id?`${r.parent_id}/${r.subtype_id}`:r.parent_id)||nameMap.get(r.parent_id)||{};return i.subtype_chinese||i.parent_chinese||n.zh||r.display_name||i.subtype_english||i.parent_english||r.parent_id||'未知（Unknown）'}
function englishName(r){const i=r.identity||{},n=nameMap.get(r.subtype_id?`${r.parent_id}/${r.subtype_id}`:r.parent_id)||nameMap.get(r.parent_id)||{};return i.subtype_english||i.parent_english||n.en||r.display_name||''}
function ref(r){return r.reference||`mtgo:${r.event_id}:${r.final_rank??r.rank}`}
function status(r){return r.classification?.status||r.classification_status}
function rank(r){return r.final_rank??r.rank??'—'}
function searchText(r){return [ref(r),rank(r),r.alias,name(r),r.display_name,r.player,r.date,r.identity?.parent_english,r.identity?.subtype_english].join(' ').toLowerCase()}
function button(r,text){return `<button data-deck="${esc(ref(r))}">${text||`${r.alias?`<b>${esc(r.alias)}</b> · `:''}${esc(name(r))} · ${esc(r.event_id)} 第${esc(rank(r))}名 · ${esc(r.player||'—')}`}</button>`}
function zone(r,k){return k==='sideboard'?(r.sideboard===undefined?r.side_deck:r.sideboard):r[k]}
function total(cards){return Array.isArray(cards)?cards.reduce((n,c)=>n+c.qty,0):'不可用'}
function add(r){const key=ref(r);if(!rows.has(key))rows.set(key,r);return rows.get(key)}
if(content){
  for(const d of M.all_top8){const r=add({...d,alias:M.active_aliases[d.token]});aliases.set(r.alias,ref(r))}
  for(const e of M.environment)for(const d of e.decks)add(d);
}else for(const m of M.members)for(const r of m.records)add(r);
const style=document.createElement('style');style.textContent=`
nav{position:sticky;top:0;z-index:4;background:#f3f5f0;padding:10px 0;margin:10px 0}
.content-table th{background:#edf3ed;position:sticky;top:0}.content-table td{vertical-align:middle}
.content-table small{display:block}.content-table button{text-align:left}.tag{display:inline-block;font-size:12px;padding:2px 7px;border-radius:4px;background:#e2eee5;margin:2px}.pending{background:#fff0cf;color:#785014}
.deck-meta{display:flex;gap:10px;flex-wrap:wrap}.card{display:grid;grid-template-columns:30px 1fr;gap:8px;padding:7px 0}.card small{display:block}.card .qty{text-align:right;font-weight:700}
dialog .close{position:sticky;top:0;background:white;z-index:1}.zones h3{background:#edf3ed;padding:8px;border-radius:5px}.reason p{overflow-wrap:anywhere}
#matrix td button b{display:block}#matrix td{min-width:215px}.scroll{max-height:720px}.env-cards{min-width:170px}.representative+.representative{margin-top:6px}.catalog-row{align-items:start}#environment-detail .toolbar{margin-top:20px}
.empty{padding:20px;color:#5d706b}.counts{font-variant-numeric:tabular-nums}button:focus-visible,a:focus-visible{outline:3px solid #bb8022;outline-offset:2px}
@media(max-width:600px){nav{gap:5px;font-size:13px}.zones{grid-template-columns:1fr}.content-table{min-width:670px}}`;
document.head.appendChild(style);
document.title=`${formats[M.format]||M.format} · ${M.week} · ${content?'内容':'分类'}审阅`;
$('.eyebrow').textContent='WEEKLY REVIEW';$('#title').textContent=document.title;
$('header > p').textContent=content?'环境总览、筛选依据和全部八强牌表分区查阅；沿用原 F 编号。':'全量分类按赛事排列；搜索、筛选后点击任一条目查看完整主备牌。';
$('nav').innerHTML=content?'<a href="#overview">待定内容</a><a href="#environment">环境总览</a><a href="#candidates">Feature 候选</a><a href="#catalog">全部八强</a>':'<a href="#overview">本批概况</a><a href="#classification">MTGO 全量分类</a>';
$('#classification').hidden=content;$('#candidates').hidden=!content;$('#catalog').hidden=!content;
$('#share-context').hidden=true;$('#accepted').textContent='';
$('#overview .note').textContent='只读材料：筛选、展开和复制不会保存选择或表示确认。请在对话中给出意见；已有确认继续保留。';
$('#example').textContent=content?'标准 F3 或 mtgo:赛事编号:名次':'mtgo:赛事编号:名次；Melee 使用条目中的固定引用';
$('#provenance').textContent=JSON.stringify(content?{source_digest:M.source_digest,displayed_page_digest:M.displayed_page_digest}:{packets:M.members.map(m=>({source:m.source,events:m.events,digest:m.packet?.digest}))},null,2);
const stats=content?[[M.all_top8.length,'完整八强牌表'],[M.candidate_evidence.length,'程序筛选候选'],[M.environment.filter(e=>e.status!=='displayed_configuration_reused').length,'待定环境配置']]:M.members.map(m=>[m.records.length,`${m.source.toUpperCase()}${m.source==='melee'?' '+m.events.join('、'):''} 牌表`]);
$('#stats').innerHTML=stats.map(([n,t])=>`<div class="stat"><b>${n}</b>${esc(t)}</div>`).join('');
const notices=content?M.errors:M.blocked.map(b=>`${b.source} ${b.event_id}：${b.error}`);
if(notices.length)$('#stats').insertAdjacentHTML('afterend',`<div class="note"><b>材料缺口</b><ul>${notices.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></div>`);
function card(c){const l=D.localization[c.name]||{}, url=l.mtgch_url;return `<div class="card"><span class="qty">${esc(c.qty)}</span><span>${url?.startsWith('https://mtgch.com/')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${cardLabel(c.name)}</a>`:cardLabel(c.name)}</span></div>`}
function openDeck(r){
 if(!r)return;
 $('#detail-body').innerHTML=`<h2>${r.alias?esc(r.alias)+' · ':''}${esc(name(r))}</h2><p class="muted">${esc(englishName(r))}</p><div class="deck-meta"><span>${esc(r.event_id)} · 第 ${esc(rank(r))} 名</span><span>${esc(r.player||'—')}</span><span>${esc(r.date||'日期未提供')}</span></div><p class="ref">${esc(ref(r))}</p><button id="copy-ref">复制引用编号</button>${r.priority_reasons?.length?`<p class="note">${r.priority_reasons.map(x=>esc(flags[x]||x)).join('；')}</p>`:''}<div class="zones">${[['main_deck','主牌'],['sideboard','备牌']].map(([k,t])=>{const cards=zone(r,k);return `<section><h3>${t} · ${total(cards)}${Array.isArray(cards)?' 张':''}</h3>${Array.isArray(cards)?cards.map(card).join('')||'<p>0 张</p>':'<p>此分区资料不可用，未补为 0 张。</p>'}</section>`}).join('')}</div>${r.source_locator?`<details><summary>来源与分类定位</summary><p class="ref">${esc(r.source_locator)}</p><p>选中规则：${esc(r.classification?.selected?.rule_id||'未提供')}</p></details>`:''}`;
 $('#toast').textContent='';if(!$('#detail').open)$('#detail').showModal();
 $('#copy-ref').onclick=async()=>{try{await navigator.clipboard.writeText(r.alias?`${formats[M.format]||M.format} ${r.alias}（${ref(r)}）`:ref(r));$('#toast').textContent='已复制，可贴到对话中。'}catch{$('#toast').textContent='请选中上方引用编号复制。'}};
}
function linked(){const hash=decodeURIComponent(location.hash.slice(1));openDeck(rows.get(aliases.get(hash)||hash.replace(/^deck=/,'')))}
document.addEventListener('click',e=>{const b=e.target.closest('[data-deck]');if(b){history.replaceState(null,'','#'+encodeURIComponent(b.dataset.deck));openDeck(rows.get(b.dataset.deck))}});
$('#close').onclick=()=>$('#detail').close();$('#detail').addEventListener('close',()=>{if(rows.has(decodeURIComponent(location.hash.slice(1)))||aliases.has(decodeURIComponent(location.hash.slice(1))))history.replaceState(null,'',location.pathname+location.search)});window.addEventListener('hashchange',linked);
function catalog(target,list,{id,mode=false}={}){
 const events=[...new Set(list.map(r=>r.event_id))];
 target.innerHTML=`<div class="toolbar"><input id="${id}-search" type="search" aria-label="搜索${id}" placeholder="编号、牌手、中英文类别、赛事"><select id="${id}-event" aria-label="赛事筛选"><option value="">全部赛事</option>${events.map(v=>`<option>${esc(v)}</option>`).join('')}</select>${mode?`<select id="${id}-mode" aria-label="分类状态"><option value="">全部分类</option><option value="unknown">Unknown</option><option value="priority">机器提示</option></select>`:''}<span id="${id}-count" aria-live="polite"></span></div><div class="scroll"><table class="content-table"><thead><tr><th>编号／分类</th><th>赛事与名次</th><th>牌手</th><th>主／备</th></tr></thead><tbody id="${id}-body"></tbody></table></div>`;
 function filter(){const q=$(`#${id}-search`).value.trim().toLowerCase(),ev=$(`#${id}-event`).value,md=mode?$(`#${id}-mode`).value:'';const found=list.filter(r=>searchText(r).includes(q)&&(!ev||r.event_id===ev)&&(!md||(md==='unknown'?status(r)==='unknown':r.priority_reasons?.length)));$(`#${id}-count`).textContent=`${found.length} / ${list.length} 份`;$(`#${id}-body`).innerHTML=found.map(r=>`<tr><td>${button(r,`${r.alias?`<b>${esc(r.alias)}</b> · `:''}${esc(name(r))}`)}</td><td>${esc(r.event_id)}<small>第 ${esc(rank(r))} 名 · ${esc(r.date||'')}</small></td><td>${esc(r.player||'—')}</td><td class="counts">${total(zone(r,'main_deck'))} / ${total(zone(r,'sideboard'))}</td></tr>`).join('')||'<tr><td colspan="4" class="empty">没有匹配的牌表；清除筛选可返回全部。</td></tr>'}
 $(`#${id}-search`).oninput=filter;$(`#${id}-event`).onchange=filter;if(mode)$(`#${id}-mode`).onchange=filter;filter();
}
function reason(x){
 if(x.type==='share_increase'||x.type==='return')return `<div class="reason"><b>${x.type==='return'?'高分环境重新出现':'高分牌表占比上升'}</b><p>本周 ${x.current_high_score_count}/${x.current_high_score_denominator}（${(x.current_share*100).toFixed(2)}%）；参考期 ${x.reference_high_score_count}/${x.reference_high_score_denominator}（${(x.reference_share*100).toFixed(2)}%）${x.delta_pp!=null?`；增加 ${x.delta_pp} 个百分点`:''}。</p></div>`;
 if(x.type==='build_shift')return `<div class="reason"><b>构筑差异 ${x.score}</b> · 对照 ${x.reference_sample_size} 份<details><summary>展开增减明细</summary><div class="diff">${['more','fewer'].map(k=>`<div><b>${k==='more'?'增加／新增':'减少／未使用'}</b><ul>${(x.difference[k]||[]).map(c=>`<li>${cardLabel(c.name)}：本套 ${c.deck_qty}／历史参考 ${c.typical_qty}</li>`).join('')}</ul></div>`).join('')}</div></details><small>差异分值不是强度或入选建议。</small></div>`;
 if(x.type==='new_archetype')return `<div class="reason"><b>类别登记提示</b><p>当前分类下历史记录 ${x.prior_record_count_under_current_classifier} 份；${x.known_state_match?'已':'未'}命中既有登记，${x.continuity_alias_match?'已':'未'}命中连续性别名。</p><small>登记缺失不等于这套牌从未出现。</small></div>`;
 if(x.type==='new_card')return `<div class="reason"><b>${esc(x.set_code)} 新牌</b><ul>${x.cards.map(c=>`<li>${cardLabel(c.name)} · 主 ${c.main_qty}／备 ${c.side_qty}</li>`).join('')}</ul></div>`;
 return '<p class="note">有未识别的筛选依据，需要 Codex 补齐展示后判断。</p>';
}
if(content){
 $('#overview h2').textContent='本周内容 · 待定事项';
 const pending=M.required_user.map(t=>{for(const e of M.environment)t=t.replace(`环境栏 ${e.archetype_id}:`,`环境栏 ${e.name}:`);return t});
 $('#stats').insertAdjacentHTML('afterend',`<ul>${pending.map(t=>`<li>${esc(t)}</li>`).join('')}</ul><p class="muted">Feature：选择牌表与新套牌／新科技类别、四张展示牌及顺序、中文说明。首页中文正文可分批提供。</p>`);
 $('#overview').insertAdjacentHTML('afterend','<section class="panel" id="environment"><h2>环境总览</h2><p class="muted">高分牌表占比，不是胜率。点击类别查看其全部高分牌表与牌张出现次数。</p><div class="scroll"><table class="content-table"><thead><tr><th>类别</th><th>本周</th><th>上周</th><th>前四周</th><th>代表牌</th><th>展示状态</th></tr></thead><tbody id="environment-rows"></tbody></table></div><div id="environment-detail"></div></section>');
 $('#environment-rows').innerHTML=M.environment.map((e,i)=>`<tr><td><button data-env="${i}">${esc(e.name)}</button></td>${['current','previous_week','previous_four_weeks'].map(k=>{const m=e.facts[k]||{};return `<td class="counts">${typeof m.share==='number'?(m.share*100).toFixed(2)+'%':'—'}<small>${m.count??'—'} / ${m.denominator??'—'}</small></td>`}).join('')}<td class="env-cards">${e.cards.length?e.cards.map(n=>`<div class="representative">${cardLabel(n)}</div>`).join(''):'待指定两张代表牌'}</td><td><span class="tag ${e.status==='displayed_configuration_reused'?'':'pending'}">${stateNames[e.status]}</span></td></tr>`).join('');
 document.addEventListener('click',event=>{const b=event.target.closest('[data-env]');if(!b)return;const e=M.environment[+b.dataset.env],counts=new Map();for(const d of e.decks)for(const n of new Set([...(d.main_deck||[]),...(d.side_deck||[])].map(c=>c.name)))counts.set(n,(counts.get(n)||0)+1);$('#environment-detail').innerHTML=`<h3>${esc(e.name)} · ${e.decks.length} 份高分牌表</h3><details><summary>牌张出现次数（非推荐）</summary><div class="scroll"><table><thead><tr><th>牌名</th><th>出现牌表数</th></tr></thead><tbody>${[...counts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([n,c])=>`<tr><td>${cardLabel(n)}</td><td>${c} / ${e.decks.length}</td></tr>`).join('')}</tbody></table></div></details><div id="env-decks"></div>`;catalog($('#env-decks'),e.decks.map(d=>rows.get(ref(d))),{id:'环境牌表'});$('#environment-detail').scrollIntoView({block:'start'})});
 const top=M.all_top8.map(d=>rows.get(ref(d)));
 $('#candidate-list').innerHTML=M.candidate_evidence.map(c=>{const r=top.find(d=>d.token===c.token);return `<article class="candidate"><div class="candidate-head"><h3>${esc(r.alias)} · ${esc(name(r))}</h3><span class="chip">程序筛选</span></div>${button(r)}<p class="muted">${esc(r.date||'')} · ${r.player_count??'—'} 人赛事</p>${c.reasons.map(reason).join('')}</article>`}).join('')||'<p class="empty">没有程序候选；仍可从全部八强中选择。</p>';
 $('#catalog').innerHTML='<h2>全部八强牌表</h2><div id="all-decks"></div>';catalog($('#all-decks'),top,{id:'八强'});
}else{
 const mtgo=M.members.find(m=>m.source==='mtgo');
 if(mtgo){const events=mtgo.events, records=mtgo.records;$('#matrix').style.minWidth=(65+events.length*240)+'px';let table='<thead><tr><th>排名</th>'+events.map(e=>{const r=records.find(r=>r.event_id===e);return `<th>${esc(e)}<br>${esc(r?.date||'')}<br>${esc(r?.event_name||'')}<br><small>参赛 ${r?.player_count??'—'} 人 · 高分 ${r?.high_score_count??'—'} 份<br>公布 ${records.filter(r=>r.event_id===e).length} 份</small></th>`}).join('')+'</tr></thead><tbody>';for(let n=1;n<=Math.max(0,...records.map(rank));n++){table+=`<tr><th>${n}</th>`;for(const ev of events){const r=records.find(r=>r.event_id===ev&&rank(r)===n);table+=r?`<td data-cell="${esc(ref(r))}">${button(r,`<b>${esc(name(r))}</b><small>${esc(r.player||'—')}</small>`)}${r.priority_reasons?.length?`<span class="flag">${r.priority_reasons.map(x=>esc(flags[x]||x)).join('；')}</span>`:''}</td>`:'<td class="muted">无公布记录</td>'}table+='</tr>'}$('#matrix').innerHTML=table+'</tbody>';
 $('#priority').parentElement.insertAdjacentHTML('afterend','<label><input type="checkbox" id="unknown-only"> 仅突出 Unknown</label>');
 function filter(){const q=$('#search').value.trim().toLowerCase();let n=0;for(const r of records){const match=searchText(r).includes(q)&&(!$('#priority').checked||r.priority_reasons?.length)&&(!$('#unknown-only').checked||status(r)==='unknown');document.querySelector(`[data-cell="${ref(r)}"]`).classList.toggle('dim',!match);if(match)n++}$('#matches').textContent=`突出 ${n} / ${records.length} 份（完整表仍保留）`}
 $('#search').oninput=$('#priority').onchange=$('#unknown-only').onchange=filter;$('#reset').onclick=()=>{$('#search').value='';$('#priority').checked=$('#unknown-only').checked=false;filter()};filter();
 }else $('#classification').hidden=true;
 function quality(member){const q=member.known_input_quality;if(!q)return '';return `<details><summary>保留输入的质量信息</summary><p>状态：${esc(({valid:'有效',partial:'部分',invalid:'无效'})[q.status]||q.status||'未提供')}；交接时可发布：${q.publishable===true?'是':q.publishable===false?'否':'未提供'}。此信息不代替本次发布确认。</p>${q.issues?.length?`<ul>${q.issues.map(x=>`<li>${esc(typeof x==='string'?x:x.message||x.reason||x.code||'输入问题，待核对')}</li>`).join('')}</ul>`:''}</details>`}
 for(const member of M.members.filter(m=>m.source==='melee')){const id='melee-'+member.events[0];$('nav').insertAdjacentHTML('beforeend',`<a href="#${id}">Melee ${esc(member.events[0])}</a>`);$('main').insertAdjacentHTML('beforeend',`<section class="panel" id="${id}"><h2>Melee ${esc(member.events[0])} · ${member.records.length} 份可用牌表</h2><p>独立来源与确认范围；${member.unavailable.length} 份不可用牌表另列。</p>${quality(member)}<div id="${id}-list"></div>${member.unavailable.length?`<details><summary>不可用牌表 ${member.unavailable.length} 份</summary><ul>${member.unavailable.map(r=>`<li>${esc(r.reference||r.participant_id)} · ${esc(r.player||'')} · ${esc(r.status||'unavailable')}</li>`).join('')}</ul></details>`:''}</section>`);catalog($(`#${id}-list`),member.records,{id,mode:true})}
}
$('main > p.muted').textContent='下一步：在对话中引用固定编号即可。展示修复不改变分类、选稿或已确认内容。';
linked();
